"""
Realtor.com ETL (DataCrawler US Realtor API) — fetches rental listings,
normalises them into our storage schema, deduplicates against Zillow entries
already in the store, and writes updated listings.json + meta.json.

Run manually:
    RAPIDAPI_KEY=<key> python etl/scrape_realty.py

Or via GitHub Actions (see refresh-listings.yml).

Dedup strategy:
    - Zillow syndicates many listings to Realtor.com; they appear in both APIs.
    - We key Realtor entries as "realty_<property_id>" to namespace them.
    - Before inserting, we check whether the normalised address already exists
      in the store under a Zillow zpid; if so, we skip (Zillow entry wins).
    - Mark-stale only touches "realty_*" entries — Zillow entries are managed
      by scrape.py.
"""

import json
import os
import re
import sys
from datetime import date, datetime, timezone

from realty_client import search_rentals
from raw_store import save_raw
from store import load_store, save_store, upsert_listing

ROOT = os.path.join(os.path.dirname(__file__), "..")
LISTINGS_FILE = os.path.join(ROOT, "public", "data", "listings.json")
META_FILE = os.path.join(ROOT, "public", "data", "meta.json")

# Minimum sqft — skip only when sqft is known AND below threshold (optimistic on missing)
MIN_SQFT = 1300
MAX_RENT = 2500
MIN_BEDS = 3
MIN_BATHS = 2.0


# ── Normalisation helpers ──────────────────────────────────────────────────────

def _normalise_address(raw: str) -> str:
    """Lower-case, collapse whitespace, strip punctuation for dedup matching."""
    s = raw.lower()
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _build_dedup_index(store: dict) -> dict[str, str]:
    """
    Build a map of normalised_address|postal_code → zpid for all store entries.
    Used to detect Zillow-syndicated duplicates before inserting Realty records.
    """
    idx: dict[str, str] = {}
    for zpid, listing in store.items():
        addr = _normalise_address(listing.get("address", ""))
        postal = listing.get("zipcode", "")
        if addr and postal:
            idx[f"{addr}|{postal}"] = zpid
    return idx


def _extract_realty_listing(r: dict, today: str) -> dict | None:
    """
    Normalise a single DataCrawler search-rent result into our storage schema.
    Returns None if the listing should be skipped (wrong type, missing data, etc.)
    """
    # ── Property type ──────────────────────────────────────────────────────────
    desc = r.get("description") or {}
    raw_type = str(desc.get("type", "") or "").lower()
    if "single_family" in raw_type or "single family" in raw_type:
        home_type = "HOUSE"
    elif "town" in raw_type:
        home_type = "TOWNHOUSE"
    else:
        return None  # apartment, condo, etc.

    # ── Beds / baths / sqft ───────────────────────────────────────────────────
    beds = desc.get("beds") or desc.get("beds_min") or 0
    baths = desc.get("baths_consolidated") or desc.get("baths_min") or 0
    sqft = desc.get("sqft") or desc.get("sqft_min") or 0

    try:
        beds = int(beds)
        baths = float(baths)
        sqft = int(sqft)
    except (TypeError, ValueError):
        beds = baths = sqft = 0

    if beds < MIN_BEDS or baths < MIN_BATHS:
        return None

    # ── Rent ──────────────────────────────────────────────────────────────────
    list_price = r.get("list_price")
    if list_price is None:
        list_price = r.get("list_price_min") or 0
    try:
        rent = int(list_price)
    except (TypeError, ValueError):
        rent = 0

    if rent == 0 or rent > MAX_RENT:
        return None

    # ── Sqft — optimistic: skip only if known AND below threshold ─────────────
    if sqft > 0 and sqft < MIN_SQFT:
        return None

    # ── Cats ──────────────────────────────────────────────────────────────────
    pet_policy = r.get("pet_policy") or {}
    cats_val = pet_policy.get("cats")       # True / False / None
    if cats_val is False:
        return None  # explicitly banned

    # ── Address ───────────────────────────────────────────────────────────────
    location = r.get("location") or {}
    addr_obj = (location.get("address") or {})
    street = addr_obj.get("line", "") or ""
    city   = addr_obj.get("city", "Las Vegas") or "Las Vegas"
    state  = addr_obj.get("state_code", "NV") or "NV"
    postal = addr_obj.get("postal_code", "") or ""

    full_address = f"{street}, {city}, {state} {postal}".strip(", ")

    # ── Photos ────────────────────────────────────────────────────────────────
    photos: list[str] = []
    for p in (r.get("photos") or []):
        href = (p.get("href") or "").strip()
        if href:
            photos.append(href)
    if not photos:
        primary = (r.get("primary_photo") or {}).get("href", "") or ""
        if primary:
            photos.append(primary)

    # ── Days on market ────────────────────────────────────────────────────────
    list_date = r.get("list_date") or ""
    try:
        listed_on = date.fromisoformat(list_date[:10])
        dom = (date.today() - listed_on).days
    except (ValueError, TypeError):
        dom = 0

    # ── IDs ───────────────────────────────────────────────────────────────────
    property_id = str(r.get("property_id") or r.get("listing_id") or "")
    if not property_id:
        return None
    zpid = f"realty_{property_id}"

    listing_url = r.get("href") or ""
    if not listing_url.startswith("http") and listing_url:
        listing_url = f"https://www.realtor.com{listing_url}"

    return {
        "zpid": zpid,
        "address": full_address,
        "zipcode": postal,
        "city": city,
        "state": state,
        "home_type": home_type,
        "rent": rent,
        "rent_history": [],
        "bedrooms": beds,
        "bathrooms": baths,
        "sqft": sqft,
        "has_ac": True,        # Las Vegas: nearly universal, optimistic
        "has_washer_dryer": True,
        "cats_ok": cats_val is not False,
        "days_on_market": dom,
        "first_seen_date": today,
        "last_confirmed_date": today,
        "available": True,
        "photo_count": len(photos),
        "photos": photos,
        "listing_url": listing_url,
        "description": str(desc.get("text", "") or ""),
        "source": "realtor",
    }


# ── Mark-stale (Realty-only) ──────────────────────────────────────────────────

def _mark_realty_stale(store: dict, seen_zpids: set) -> int:
    count = 0
    for zpid, listing in store.items():
        if zpid.startswith("realty_") and listing.get("available") and zpid not in seen_zpids:
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

    print(f"=== Realty ETL — {today} ===\n")

    try:
        raw_results, api_calls = search_rentals()
    except Exception as exc:
        msg = f"Realty search failed: {exc}"
        print(f"  ERROR: {msg}", file=sys.stderr)
        errors.append(msg)
        raw_results = []

    # Persist raw data for later inspection / offline reprocessing
    if raw_results:
        path = save_raw("realty", raw_results)
        print(f"  [raw] saved {len(raw_results)} results → {path}")

    skipped_dedup = skipped_filter = 0

    for r in raw_results:
        listing = _extract_realty_listing(r, today)
        if listing is None:
            skipped_filter += 1
            continue

        zpid = listing["zpid"]

        # Dedup: skip if the same address is already tracked under a Zillow entry
        dedup_key = f"{_normalise_address(listing['address'])}|{listing['zipcode']}"
        existing_zpid = dedup.get(dedup_key)
        if existing_zpid and not existing_zpid.startswith("realty_"):
            skipped_dedup += 1
            continue

        seen_zpids.add(zpid)

        if store.get(zpid):
            upsert_listing(store, zpid, {
                "zpid": zpid,
                "rent": listing["rent"],
                "days_on_market": listing["days_on_market"],
                "last_confirmed_date": today,
                "photo_count": listing["photo_count"],
                "photos": listing["photos"],
            })
            print(f"  ~ Re-confirmed {listing['address']}")
        else:
            upsert_listing(store, zpid, listing)
            # Register in dedup index for intra-run collision avoidance
            dedup[dedup_key] = zpid
            added += 1
            print(f"  + Added {listing['address']} — ${listing['rent']}/mo — {listing['photo_count']} photos")

    removed = _mark_realty_stale(store, seen_zpids)
    save_store(store, LISTINGS_FILE)

    print(f"\n  {skipped_filter} skipped (type/beds/rent filter)")
    print(f"  {skipped_dedup} skipped (duplicate of Zillow entry)")

    total_active = sum(1 for l in store.values() if l.get("available"))

    # Merge with any existing meta (Zillow run may have written it first)
    existing_meta: dict = {}
    if os.path.exists(META_FILE):
        with open(META_FILE) as f:
            existing_meta = json.load(f)

    meta = {
        **existing_meta,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_active": total_active,
        "realty_added_this_run": added,
        "realty_removed_this_run": removed,
        "realty_api_calls_used": api_calls,
        "errors": (existing_meta.get("errors") or []) + errors,
    }
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n=== Done ===")
    print(f"  +{added} added  -{removed} removed  {total_active} total active")
    print(f"  {api_calls} Realty API calls used this run")
    if errors:
        print(f"\n  {len(errors)} error(s) — see above", file=sys.stderr)
        if added == 0 and total_active == 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
