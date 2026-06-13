"""
Zillow.com Live Data Scraper ETL — active for-rent listings pulled directly
from Zillow via the /bylocation endpoint (zillow-com-live-data-scraper-api).

Unlike the primary Zillow ETL (quota-exhausted) and the APIllow backup (for-sale
listings filtered by rent_zestimate), this ETL returns genuine for-rent listings.
Listings are stored with a "zillow_scraper_" zpid prefix so stale-marking
stays scoped to this source and does not affect Zillow or Realtor entries.

Run manually:
  RAPIDAPI_KEY_ZILLOW_SCRAPER=<key> python etl/scrape_zillow_scraper.py
"""

import json
import os
import re
import sys
from datetime import date, datetime, timezone

from zillow_scraper_client import search_rentals
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
    idx: dict[str, str] = {}
    for zpid, listing in store.items():
        addr   = _normalise_address(listing.get("address", ""))
        postal = listing.get("zipcode", "")
        if addr and postal:
            idx[f"{addr}|{postal}"] = zpid
    return idx


def _extract_listing(raw: dict, today: str) -> dict | None:
    """
    Map a /bylocation result to our storage schema.
    Returns None to skip.

    Debug logging is verbose on first runs to surface any field-name
    differences between API versions.
    """
    # ── zpid ─────────────────────────────────────────────────────────────────
    zpid_raw = str(raw.get("zpid") or "").strip()
    if not zpid_raw or zpid_raw == "0":
        print(f"  [debug] skip — no valid zpid")
        return None

    # ── Zip code gate ─────────────────────────────────────────────────────────
    # Field name may be zipCode, zipcode, or zip
    zipcode = str(
        raw.get("zipCode") or raw.get("zipcode") or raw.get("zip") or ""
    ).strip()
    if zipcode not in TARGET_ZIPS:
        return None  # silent — most Las Vegas results will be outside our 6 zips

    # ── Numeric fields ────────────────────────────────────────────────────────
    beds  = int(raw.get("bedrooms") or raw.get("beds") or 0)
    baths = float(raw.get("bathrooms") or raw.get("baths") or 0)
    sqft  = int(
        raw.get("livingArea") or raw.get("sqft") or raw.get("livingAreaValue") or 0
    )
    rent  = int(raw.get("price") or raw.get("listPrice") or 0)

    print(f"  [debug] candidate: zpid={zpid_raw!r} zip={zipcode!r} "
          f"beds={beds} baths={baths} sqft={sqft} rent=${rent} "
          f"addr={raw.get('streetAddress') or raw.get('address', '')!r}")

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
    raw_type = str(raw.get("homeType") or raw.get("propertyType") or "").upper()
    print(f"    [debug] homeType={raw_type!r}")
    if "TOWN" in raw_type:
        home_type = "TOWNHOUSE"
    elif any(kw in raw_type for kw in ("SINGLE", "HOUSE", "RESIDENTIAL", "FAMILY")):
        home_type = "HOUSE"
    else:
        print(f"    [debug] unrecognised homeType={raw_type!r} — defaulting to HOUSE")
        home_type = "HOUSE"

    # ── Address ───────────────────────────────────────────────────────────────
    street = str(raw.get("streetAddress") or raw.get("address") or "").strip()
    city   = str(raw.get("city") or "Las Vegas").strip()
    state  = str(raw.get("state") or "NV").strip()
    full_address = f"{street}, {city}, {state} {zipcode}".strip(", ")

    # ── Photos ────────────────────────────────────────────────────────────────
    # API may return imgSrc (thumbnail) or a photos list
    thumbnail = str(raw.get("imgSrc") or raw.get("img_src") or "").strip()
    raw_photos = raw.get("photos") or raw.get("images") or []
    if isinstance(raw_photos, list) and raw_photos:
        photos = [str(p.get("url") or p.get("src") or p) for p in raw_photos if p]
    elif thumbnail:
        photos = [thumbnail]
    else:
        photos = []
    print(f"    [debug] {len(photos)} photo(s)")

    # ── Listing URL ───────────────────────────────────────────────────────────
    detail_url = str(raw.get("detailUrl") or raw.get("url") or "").strip()
    if detail_url and not detail_url.startswith("http"):
        detail_url = f"https://www.zillow.com{detail_url}"

    return {
        "zpid":                f"zillow_scraper_{zpid_raw}",
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
        "days_on_market":      int(raw.get("daysOnZillow") or raw.get("days_on_zillow") or 0),
        "first_seen_date":     today,
        "last_confirmed_date": today,
        "available":           True,
        "photo_count":         len(photos),
        "photos":              photos,
        "listing_url":         detail_url,
        "description":         str(raw.get("description") or ""),
        "source":              "zillow_scraper",
    }


def _photo_path(zpid: str) -> str:
    return os.path.join(PHOTOS_DIR, f"{zpid}.json")


def _save_photos(zpid: str, photos: list[str], today: str) -> None:
    if not photos or os.path.exists(_photo_path(zpid)):
        return
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    with open(_photo_path(zpid), "w") as f:
        json.dump({"zpid": zpid, "photos": photos, "fetched_date": today}, f, indent=2)
    print(f"    [photos] saved {len(photos)} for {zpid}")


def _mark_scraper_stale(store: dict, seen_zpids: set) -> int:
    """Mark only zillow_scraper_ listings not seen this run as unavailable."""
    count = 0
    for zpid, listing in store.items():
        if (zpid.startswith("zillow_scraper_")
                and listing.get("available")
                and zpid not in seen_zpids):
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

    print(f"=== Zillow Scraper ETL — {today} ===\n")
    print(f"  Source      : Zillow.com Live Data Scraper (RapidAPI)")
    print(f"  Target zips : {sorted(TARGET_ZIPS)}")
    print(f"  Criteria    : {MIN_BEDS}+ beds, {MIN_BATHS}+ baths, "
          f"{MIN_SQFT}+ sqft, up to ${MAX_RENT}/mo\n")

    # ── Fetch ─────────────────────────────────────────────────────────────────
    try:
        raw_results, api_calls = search_rentals()
    except Exception as exc:
        msg = f"Zillow scraper fetch failed: {exc}"
        print(f"  ERROR: {msg}", file=sys.stderr)
        errors.append(msg)
        raw_results = []

    print(f"\n  {len(raw_results)} raw results\n")

    # ── Debug: inspect structure of first result ───────────────────────────────
    if raw_results:
        r0 = raw_results[0]
        print(f"  [debug] first result top-level keys: {list(r0.keys())}")
        for k in ("zpid", "streetAddress", "address", "city", "state",
                  "zipCode", "zipcode", "price", "listPrice",
                  "bedrooms", "beds", "bathrooms", "baths",
                  "livingArea", "sqft", "homeType", "propertyType",
                  "daysOnZillow", "detailUrl", "url", "imgSrc"):
            if k in r0:
                print(f"    {k}: {r0[k]!r}")
        print()

    skipped_filter = skipped_dedup = 0

    for raw in raw_results:
        listing = _extract_listing(raw, today)
        if listing is None:
            skipped_filter += 1
            continue

        zpid = listing["zpid"]
        dedup_key = f"{_normalise_address(listing['address'])}|{listing['zipcode']}"

        # Skip if a higher-priority source already covers this address
        existing_zpid = dedup.get(dedup_key)
        if existing_zpid and not existing_zpid.startswith("zillow_scraper_"):
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
            print(f"  + Added {listing['address']} — "
                  f"${listing['rent']}/mo — {listing['photo_count']} photo(s)")
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

    removed = _mark_scraper_stale(store, seen_zpids)
    save_store(store, LISTINGS_FILE)

    print(f"\n  filter skipped: {skipped_filter}  dedup skipped: {skipped_dedup}")

    total_active = sum(1 for l in store.values() if l.get("available"))

    existing_meta: dict = {}
    if os.path.exists(META_FILE):
        with open(META_FILE) as f:
            existing_meta = json.load(f)

    meta = {
        **existing_meta,
        "last_updated":                 datetime.now(timezone.utc).isoformat(),
        "total_active":                 total_active,
        "zillow_scraper_added":         added,
        "zillow_scraper_removed":       removed,
        "zillow_scraper_api_calls":     api_calls,
        "errors":                       (existing_meta.get("errors") or []) + errors,
    }
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n=== Done ===")
    print(f"  +{added} added  -{removed} removed  {total_active} total active")
    print(f"  {api_calls} API call(s) this run")
    if errors:
        print(f"\n  {len(errors)} error(s) — see above", file=sys.stderr)
        if added == 0 and total_active == 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
