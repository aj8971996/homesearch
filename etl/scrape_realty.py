"""
Realtor.com ETL (Realty US API) — fetches rental listings, normalises them,
deduplicates against Zillow entries, and writes:
  - public/data/listings.json   (listing metadata, no inline photos)
  - public/data/photos/{zpid}.json  (full-size photo URLs, fetched once per listing)
  - public/data/meta.json

Photo strategy:
  - Search results only return thumbnail URLs (s.jpg) — not usable for display.
  - properties/detail is called once per new listing (or any listing missing photos)
    to obtain full-size photo URLs, which are saved to the per-listing photo file.
  - Re-confirmation runs skip the detail call if the photo file already exists.
"""

import json
import os
import re
import sys
from datetime import date, datetime, timezone

from realty_client import search_rentals, get_listing_detail
from raw_store import save_raw
from store import load_store, save_store, upsert_listing

ROOT         = os.path.join(os.path.dirname(__file__), "..")
LISTINGS_FILE = os.path.join(ROOT, "public", "data", "listings.json")
META_FILE    = os.path.join(ROOT, "public", "data", "meta.json")
PHOTOS_DIR   = os.path.join(ROOT, "public", "data", "photos")

MIN_SQFT = 1300
MAX_RENT = 2500
MIN_BEDS = 3
MIN_BATHS = 2.0


# ── Photo store helpers ────────────────────────────────────────────────────────

def _photo_path(zpid: str) -> str:
    return os.path.join(PHOTOS_DIR, f"{zpid}.json")

def _photos_exist(zpid: str) -> bool:
    return os.path.exists(_photo_path(zpid))

def _save_photos(zpid: str, photos: list[str], today: str) -> None:
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    with open(_photo_path(zpid), "w") as f:
        json.dump({"zpid": zpid, "photos": photos, "fetched_date": today}, f, indent=2)

def _extract_photos_from_detail(detail: dict, zpid: str, first_call: bool) -> list[str]:
    if first_call:
        print(f"  [detail] response top-level keys: {list(detail.keys())}")
        inner = detail.get("data") or {}
        if isinstance(inner, dict):
            print(f"  [detail] data keys: {list(inner.keys())}")
        if detail.get("message"):
            print(f"  [detail] message: {detail['message']}")
        if detail.get("errors"):
            print(f"  [detail] errors: {detail['errors']}")

    data = detail.get("data") or {}
    photos_raw = data.get("photos") or []

    photos: list[str] = []
    for p in (photos_raw or []):
        href = (p.get("href") or p.get("url") or p.get("src") or "").strip()
        if href:
            photos.append(href.replace("http://", "https://"))

    print(f"  [detail] {len(photos)} photos for {zpid}")
    return photos


# ── Normalisation helpers ──────────────────────────────────────────────────────

def _normalise_address(raw: str) -> str:
    s = raw.lower()
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", " ", s).strip()

def _build_dedup_index(store: dict) -> dict[str, str]:
    idx: dict[str, str] = {}
    for zpid, listing in store.items():
        addr = _normalise_address(listing.get("address", ""))
        postal = listing.get("zipcode", "")
        if addr and postal:
            idx[f"{addr}|{postal}"] = zpid
    return idx

def _extract_realty_listing(r: dict, today: str) -> dict | None:
    desc = r.get("description") or {}
    raw_type = str(desc.get("type", "") or "").lower()
    if "single_family" in raw_type or "single family" in raw_type or raw_type == "home":
        home_type = "HOUSE"
    elif "town" in raw_type:
        home_type = "TOWNHOUSE"
    else:
        print(f"  [skip] unrecognised type={raw_type!r} — {r.get('property_id')} "
              f"{((r.get('location') or {}).get('address') or {}).get('line','')}")
        return None

    beds  = desc.get("beds") or desc.get("beds_min") or 0
    baths = (desc.get("baths_consolidated") or desc.get("baths_full_calc")
             or desc.get("baths") or desc.get("baths_min") or 0)
    sqft  = desc.get("sqft") or desc.get("sqft_min") or 0

    try:
        beds  = int(beds)
        baths = float(baths)
        sqft  = int(sqft)
    except (TypeError, ValueError):
        beds = baths = sqft = 0

    if beds < MIN_BEDS or baths < MIN_BATHS:
        return None

    list_price = r.get("list_price")
    if list_price is None:
        list_price = r.get("list_price_min") or 0
    try:
        rent = int(list_price)
    except (TypeError, ValueError):
        rent = 0

    if rent == 0 or rent > MAX_RENT:
        return None

    if sqft > 0 and sqft < MIN_SQFT:
        return None

    pet_policy = r.get("pet_policy") or {}
    if pet_policy.get("cats") is False:
        return None

    location = r.get("location") or {}
    addr_obj = (location.get("address") or {})
    street = addr_obj.get("line", "") or ""
    city   = addr_obj.get("city", "Las Vegas") or "Las Vegas"
    state  = addr_obj.get("state_code", "NV") or "NV"
    postal = addr_obj.get("postal_code", "") or ""
    full_address = f"{street}, {city}, {state} {postal}".strip(", ")

    photo_count = int(r.get("photo_count") or 0)

    # Extract thumbnail URLs from the search result directly.
    # Note: detail endpoint returns the same s.jpg thumbnails, so we skip it.
    photos_raw = r.get("photos") or []
    search_photos: list[str] = [
        p["href"].replace("http://", "https://")
        for p in photos_raw
        if isinstance(p, dict) and p.get("href")
    ]

    list_date = r.get("list_date") or ""
    try:
        listed_on = date.fromisoformat(list_date[:10])
        dom = (date.today() - listed_on).days
    except (ValueError, TypeError):
        dom = 0

    property_id = str(r.get("property_id") or r.get("listing_id") or "")
    if not property_id:
        return None
    zpid = f"realty_{property_id}"

    listing_url = r.get("href") or ""
    if listing_url and not listing_url.startswith("http"):
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
        "has_ac": True,
        "has_washer_dryer": True,
        "cats_ok": pet_policy.get("cats") is not False,
        "days_on_market": dom,
        "first_seen_date": today,
        "last_confirmed_date": today,
        "available": True,
        "photo_count": photo_count,
        "search_photos": search_photos,  # extracted at search time, stripped before store
        "listing_url": listing_url,
        "description": str(desc.get("text", "") or ""),
        "source": "realtor",
    }


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
    added = removed = search_calls = detail_calls = 0
    errors: list[str] = []
    first_detail_call = True
    DETAIL_CAP = 20  # max detail calls per run to protect quota

    print(f"=== Realty ETL — {today} ===\n")

    try:
        raw_results, search_calls = search_rentals()
    except Exception as exc:
        msg = f"Realty search failed: {exc}"
        print(f"  ERROR: {msg}", file=sys.stderr)
        errors.append(msg)
        raw_results = []

    if raw_results:
        path = save_raw("realty", raw_results)
        print(f"  [raw] saved {len(raw_results)} results → {path}")

    type_counts: dict[str, int] = {}
    for r in raw_results:
        t = str(((r.get("description") or {}).get("type") or "unknown")).lower()
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"  [realty] type breakdown: {type_counts}\n")

    skipped_dedup = skipped_filter = 0

    for r in raw_results:
        listing = _extract_realty_listing(r, today)
        if listing is None:
            skipped_filter += 1
            continue

        zpid = listing["zpid"]
        dedup_key = f"{_normalise_address(listing['address'])}|{listing['zipcode']}"

        existing_zpid = dedup.get(dedup_key)
        if existing_zpid and not existing_zpid.startswith("realty_"):
            skipped_dedup += 1
            continue

        seen_zpids.add(zpid)
        is_new = not store.get(zpid)

        search_photos = listing.pop("search_photos", [])  # strip before storing

        if is_new:
            upsert_listing(store, zpid, listing)
            dedup[dedup_key] = zpid
            added += 1
            print(f"  + Added {listing['address']} — ${listing['rent']}/mo")
        else:
            upsert_listing(store, zpid, {
                "zpid": zpid,
                "rent": listing["rent"],
                "days_on_market": listing["days_on_market"],
                "last_confirmed_date": today,
                "photo_count": listing["photo_count"],
            })
            print(f"  ~ Re-confirmed {listing['address']}")

        if not _photos_exist(zpid):
            if search_photos:
                # Photos available from search result — save them, no detail call needed
                _save_photos(zpid, search_photos, today)
                print(f"  [photos] {len(search_photos)} from search for {zpid}")
            elif detail_calls < DETAIL_CAP:
                # No search photos — fall back to detail endpoint (capped per run)
                raw_property_id = zpid[len("realty_"):]
                raw_listing_id = str(r.get("listing_id") or "")
                try:
                    detail = get_listing_detail(raw_property_id, raw_listing_id)
                    detail_calls += 1
                    photos = _extract_photos_from_detail(detail, zpid, first_detail_call)
                    first_detail_call = False
                    _save_photos(zpid, photos, today)
                    if not photos:
                        print(f"  [detail] no photos in response for {zpid}")
                except Exception as exc:
                    msg = f"detail fetch failed for {zpid}: {exc}"
                    print(f"  [detail] ERROR: {msg}", file=sys.stderr)
                    errors.append(msg)

    removed = _mark_realty_stale(store, seen_zpids)
    save_store(store, LISTINGS_FILE)

    print(f"\n  {skipped_filter} skipped (filter)  {skipped_dedup} skipped (dedup)")

    total_active = sum(1 for l in store.values() if l.get("available"))

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
        "realty_search_calls": search_calls,
        "realty_detail_calls": detail_calls,
        "errors": (existing_meta.get("errors") or []) + errors,
    }
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n=== Done ===")
    print(f"  +{added} added  -{removed} removed  {total_active} total active")
    print(f"  {search_calls} search call(s)  {detail_calls} detail call(s)")
    if errors:
        print(f"\n  {len(errors)} error(s) — see above", file=sys.stderr)
        if added == 0 and total_active == 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
