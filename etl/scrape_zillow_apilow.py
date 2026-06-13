"""
Zillow Property Data (APIllow) ETL — backup source for Zillow rental listings.

Triggers a batch search job via POST /v1/properties, then polls GET /v1/properties
until the job completes. Each run costs at least 2 API calls (1 POST + 1 GET).
50 calls/month limit → budget for ~25 runs; scheduled every 3 days (~10 runs = 20 calls).

Run manually:
  RAPIDAPI_KEY_APILOW=<key> python etl/scrape_zillow_apilow.py
"""

import json
import os
import re
import sys
from datetime import date, datetime, timezone

from zillow_apilow_client import search_rentals
from store import load_store, save_store, upsert_listing

ROOT          = os.path.join(os.path.dirname(__file__), "..")
LISTINGS_FILE = os.path.join(ROOT, "public", "data", "listings.json")
META_FILE     = os.path.join(ROOT, "public", "data", "meta.json")
PHOTOS_DIR    = os.path.join(ROOT, "public", "data", "photos")

TARGET_ZIPS = {"89134", "89144", "89145", "89128", "89138", "89135"}
MIN_BEDS    = 3
MIN_BATHS   = 2.0
MIN_SQFT    = 1300
MAX_RENT    = 2500


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_address(raw: str) -> str:
    s = raw.lower()
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _build_dedup_index(store: dict) -> dict[str, str]:
    """Build normalised-address → zpid index for cross-source dedup."""
    idx: dict[str, str] = {}
    for zpid, listing in store.items():
        addr   = _normalise_address(listing.get("address", ""))
        postal = listing.get("zipcode", "")
        if addr and postal:
            idx[f"{addr}|{postal}"] = zpid
    return idx


def _extract_listing(prop: dict, today: str) -> dict | None:
    """
    Map an APIllow property dict to our storage schema.
    Returns None for any listing that should be skipped.

    Debug logging is intentionally verbose here to help diagnose
    unexpected API field names or value formats on first runs.
    """
    zpid_raw = str(prop.get("zpid") or "").strip()
    if not zpid_raw or zpid_raw == "0":
        print(f"  [debug] skip — no valid zpid for {prop.get('street_address', '?')!r}")
        return None

    # ── Zip-code gate ─────────────────────────────────────────────────────────
    zipcode = str(prop.get("zipcode") or "").strip()
    if zipcode not in TARGET_ZIPS:
        # Silent: most Las Vegas results won't be in our 6 target zips
        return None

    # ── Numeric fields ────────────────────────────────────────────────────────
    beds  = int(prop.get("bedrooms")    or 0)
    baths = float(prop.get("bathrooms") or 0)
    sqft  = int(prop.get("living_area") or 0)
    rent  = int(prop.get("price")       or 0)

    print(f"  [debug] candidate: zpid={zpid_raw!r} zip={zipcode!r} "
          f"beds={beds} baths={baths} sqft={sqft} rent=${rent} "
          f"addr={prop.get('street_address', '')!r}")

    if beds < MIN_BEDS:
        print(f"    [skip] beds={beds} < {MIN_BEDS}")
        return None
    if baths < MIN_BATHS:
        print(f"    [skip] baths={baths} < {MIN_BATHS}")
        return None
    if rent == 0 or rent > MAX_RENT:
        print(f"    [skip] rent=${rent} (max ${MAX_RENT})")
        return None
    if sqft > 0 and sqft < MIN_SQFT:
        print(f"    [skip] sqft={sqft} < {MIN_SQFT}")
        return None

    # ── Home type ─────────────────────────────────────────────────────────────
    raw_type  = str(prop.get("property_type") or "").upper()
    home_status = str(prop.get("home_status") or "").upper()
    print(f"    [debug] property_type={raw_type!r}  home_status={home_status!r}")

    if "TOWN" in raw_type:
        home_type = "TOWNHOUSE"
    elif any(kw in raw_type for kw in ("SINGLE", "HOUSE", "RESIDENTIAL", "FAMILY")):
        home_type = "HOUSE"
    else:
        # Unknown type — include optimistically (same strategy as primary Zillow ETL)
        print(f"    [debug] unrecognised property_type={raw_type!r} — defaulting to HOUSE")
        home_type = "HOUSE"

    # ── Address ───────────────────────────────────────────────────────────────
    street = str(prop.get("street_address") or "").strip()
    city   = str(prop.get("city")           or "Las Vegas").strip()
    state  = str(prop.get("state")          or "NV").strip()
    full_address = f"{street}, {city}, {state} {zipcode}".strip(", ")

    # ── Photos ────────────────────────────────────────────────────────────────
    image_urls = prop.get("image_urls") or []
    photos = [str(u) for u in image_urls if u] if isinstance(image_urls, list) else []
    print(f"    [debug] {len(photos)} photo URL(s)")

    # ── Listing URL ───────────────────────────────────────────────────────────
    listing_url = str(prop.get("url") or "").strip()
    if listing_url and not listing_url.startswith("http"):
        listing_url = f"https://www.zillow.com{listing_url}"

    return {
        "zpid":                f"apilow_{zpid_raw}",
        "address":             full_address,
        "zipcode":             zipcode,
        "city":                city,
        "state":               state,
        "home_type":           home_type,
        "rent":                rent,
        "rent_history":        [],
        "bedrooms":            beds,
        "bathrooms":           baths,
        "sqft":                sqft,
        "has_ac":              True,
        "has_washer_dryer":    True,
        "cats_ok":             True,
        "days_on_market":      int(prop.get("days_on_zillow") or 0),
        "first_seen_date":     today,
        "last_confirmed_date": today,
        "available":           True,
        "photo_count":         len(photos),
        "photos":              photos,
        "listing_url":         listing_url,
        "description":         str(prop.get("description") or ""),
        "source":              "zillow_apilow",
    }


def _photo_path(zpid: str) -> str:
    return os.path.join(PHOTOS_DIR, f"{zpid}.json")


def _save_photos(zpid: str, photos: list[str], today: str) -> None:
    """Write per-listing photo file (once only; skips if already present)."""
    if not photos or os.path.exists(_photo_path(zpid)):
        return
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    with open(_photo_path(zpid), "w") as f:
        json.dump({"zpid": zpid, "photos": photos, "fetched_date": today}, f, indent=2)
    print(f"    [photos] saved {len(photos)} photo URLs for {zpid}")


def _mark_apilow_stale(store: dict, seen_zpids: set) -> int:
    """Mark apilow_ listings that weren't seen this run as unavailable."""
    count = 0
    for zpid, listing in store.items():
        if zpid.startswith("apilow_") and listing.get("available") and zpid not in seen_zpids:
            listing["available"] = False
            count += 1
    return count


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    today = date.today().isoformat()
    store = load_store(LISTINGS_FILE)
    dedup = _build_dedup_index(store)

    seen_zpids: set[str] = set()
    added = removed = api_calls = 0
    errors: list[str] = []

    print(f"=== Zillow APIllow ETL — {today} ===\n")
    print(f"  Source      : Zillow Property Data by APIllow (RapidAPI)")
    print(f"  Target zips : {sorted(TARGET_ZIPS)}")
    print(f"  Criteria    : {MIN_BEDS}+ beds, {MIN_BATHS}+ baths, {MIN_SQFT}+ sqft, ≤${MAX_RENT}/mo")
    print(f"  API budget  : 50 calls/month (this run costs ≥2 calls)\n")

    # ── Fetch listings from API ───────────────────────────────────────────────
    try:
        raw_properties, api_calls = search_rentals()
    except Exception as exc:
        msg = f"APIllow fetch failed: {exc}"
        print(f"  ERROR: {msg}", file=sys.stderr)
        errors.append(msg)
        raw_properties = []

    print(f"\n  {len(raw_properties)} raw properties returned\n")

    # ── Debug: inspect structure of first returned property ───────────────────
    if raw_properties:
        p0 = raw_properties[0]
        print(f"  [debug] first property top-level keys: {list(p0.keys())}")
        print(f"  [debug] sample field values:")
        for k in ("zpid", "street_address", "city", "state", "zipcode",
                  "price", "bedrooms", "bathrooms", "living_area",
                  "property_type", "home_status", "days_on_zillow", "url"):
            print(f"    {k}: {p0.get(k)!r}")
        image_urls = p0.get("image_urls") or []
        print(f"    image_urls: {len(image_urls)} URL(s)")
        print()

    # ── Process each property ─────────────────────────────────────────────────
    skipped_filter = skipped_dedup = 0

    for prop in raw_properties:
        listing = _extract_listing(prop, today)
        if listing is None:
            skipped_filter += 1
            continue

        zpid = listing["zpid"]
        dedup_key = f"{_normalise_address(listing['address'])}|{listing['zipcode']}"

        # Skip if a higher-priority source (Zillow primary or Realtor) already has this address
        existing_zpid = dedup.get(dedup_key)
        if existing_zpid and not existing_zpid.startswith("apilow_"):
            print(f"  [dedup] skip {listing['address']!r} — covered by {existing_zpid}")
            skipped_dedup += 1
            continue

        seen_zpids.add(zpid)
        is_new = store.get(zpid) is None
        photos = listing.pop("photos", [])

        if is_new:
            listing["photos"] = []
            upsert_listing(store, zpid, listing)
            dedup[dedup_key] = zpid
            added += 1
            print(f"  + Added {listing['address']} — ${listing['rent']}/mo — {listing['photo_count']} photos")
        else:
            upsert_listing(store, zpid, {
                "zpid":                zpid,
                "rent":                listing["rent"],
                "days_on_market":      listing["days_on_market"],
                "last_confirmed_date": today,
                "photo_count":         listing["photo_count"],
            })
            print(f"  ~ Re-confirmed {listing['address']}")

        _save_photos(zpid, photos, today)

    removed = _mark_apilow_stale(store, seen_zpids)
    save_store(store, LISTINGS_FILE)

    print(f"\n  filter skipped: {skipped_filter}  dedup skipped: {skipped_dedup}")

    total_active = sum(1 for l in store.values() if l.get("available"))

    existing_meta: dict = {}
    if os.path.exists(META_FILE):
        with open(META_FILE) as f:
            existing_meta = json.load(f)

    meta = {
        **existing_meta,
        "last_updated":            datetime.now(timezone.utc).isoformat(),
        "total_active":            total_active,
        "apilow_added_this_run":   added,
        "apilow_removed_this_run": removed,
        "apilow_api_calls":        api_calls,
        "errors":                  (existing_meta.get("errors") or []) + errors,
    }
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n=== Done ===")
    print(f"  +{added} added  -{removed} removed  {total_active} total active")
    print(f"  {api_calls} API call(s) used this run (budget: 50/month)")
    if errors:
        print(f"\n  {len(errors)} error(s) — see above", file=sys.stderr)
        if added == 0 and total_active == 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
