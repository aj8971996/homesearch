"""
ETL orchestrator — fetches rental listings from Zillow for each target zip code,
applies amenity filters, updates listings.json, and writes meta.json.

Run via GitHub Actions on a schedule, or manually with:
  RAPIDAPI_KEY=<key> python etl/scrape.py
"""

import json
import os
import sys
from datetime import date, datetime, timezone

from zillow_client import ZIP_CODES, get_details, search_rentals
from filters import extract_listing, passes_criteria
from store import load_store, mark_stale, save_store, upsert_listing

ROOT = os.path.join(os.path.dirname(__file__), "..")
LISTINGS_FILE = os.path.join(ROOT, "public", "data", "listings.json")
META_FILE = os.path.join(ROOT, "public", "data", "meta.json")


def main() -> None:
    today = date.today().isoformat()
    store = load_store(LISTINGS_FILE)
    seen_zpids: set[str] = set()
    added = removed = api_calls = 0
    errors: list[str] = []

    print(f"=== Homesearch ETL — {today} ===\n")

    for zipcode in ZIP_CODES:
        print(f"── {zipcode} ──────────────────────────")
        try:
            raw_listings = search_rentals(zipcode)
            api_calls += 1
        except Exception as exc:
            msg = f"Search failed for {zipcode}: {exc}"
            print(f"  ERROR: {msg}", file=sys.stderr)
            errors.append(msg)
            continue

        for raw in raw_listings:
            zpid = str(raw.get("zpid", ""))
            if not zpid:
                continue

            seen_zpids.add(zpid)
            existing = store.get(zpid)

            # Only fetch details for listings we haven't vetted yet
            if existing is not None:
                print(f"  ~ Re-confirmed {existing.get('address', zpid)}")
                upsert_listing(store, zpid, {
                    "zpid": zpid,
                    "rent": int(raw.get("price", existing.get("rent", 0))),
                    "days_on_market": int(raw.get("daysOnZillow", 0) or 0),
                    "last_confirmed_date": today,
                    "photo_count": existing.get("photo_count", 0),
                    "photos": existing.get("photos", []),
                })
                continue

            # New listing — fetch detail for amenity verification
            try:
                detail = get_details(zpid)
                api_calls += 1
            except Exception as exc:
                msg = f"Detail fetch failed for zpid {zpid}: {exc}"
                print(f"  ERROR: {msg}", file=sys.stderr)
                errors.append(msg)
                seen_zpids.discard(zpid)  # don't mark it unavailable, just skip
                continue

            passes, reasons = passes_criteria(detail)
            if not passes:
                failed = [k for k, v in reasons.items() if not v]
                print(f"  ✗ Excluded {raw.get('address', zpid)} — failed: {', '.join(failed)}")
                seen_zpids.discard(zpid)
                continue

            listing = extract_listing(raw, detail, zipcode, today)
            upsert_listing(store, zpid, listing)
            added += 1
            print(f"  + Added {listing['address']} — ${listing['rent']}/mo — {listing['photo_count']} photos")

    removed = mark_stale(store, seen_zpids)
    save_store(store, LISTINGS_FILE)

    total_active = sum(1 for l in store.values() if l.get("available"))
    meta = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_active": total_active,
        "added_this_run": added,
        "removed_this_run": removed,
        "api_calls_used": api_calls,
        "errors": errors,
    }
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n=== Done ===")
    print(f"  +{added} added  -{removed} removed  {total_active} total active")
    print(f"  {api_calls} API calls used this run")
    if errors:
        print(f"  {len(errors)} errors — see above", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
