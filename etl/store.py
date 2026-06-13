import json
import os


def load_store(path: str) -> dict:
    """Load existing listings.json as a dict keyed by zpid."""
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return {l["zpid"]: l for l in data.get("listings", [])}


def upsert_listing(store: dict, zpid: str, incoming: dict) -> bool:
    """
    Insert or update a listing.
    Returns True if this is a brand-new listing, False if it already existed.
    """
    existing = store.get(zpid)

    if existing is None:
        store[zpid] = incoming
        return True  # new

    # Track price change
    old_rent = existing.get("rent", 0)
    new_rent = incoming.get("rent", 0)
    if new_rent and old_rent and new_rent != old_rent:
        history = existing.get("rent_history", [])
        history.insert(0, {
            "date": existing.get("last_confirmed_date"),
            "rent": old_rent,
        })
        existing["rent_history"] = history

    # Refresh volatile fields
    existing["rent"] = incoming["rent"]
    existing["last_confirmed_date"] = incoming["last_confirmed_date"]
    existing["available"] = True
    existing["days_on_market"] = incoming["days_on_market"]

    # Accept more photos if the new fetch returned a larger set
    if incoming.get("photo_count", 0) > existing.get("photo_count", 0):
        existing["photos"] = incoming["photos"]
        existing["photo_count"] = incoming["photo_count"]

    store[zpid] = existing
    return False  # existing


def mark_stale(store: dict, seen_zpids: set) -> int:
    """Mark any listing not confirmed this run as unavailable. Returns count."""
    count = 0
    for zpid, listing in store.items():
        if listing.get("available") and zpid not in seen_zpids:
            listing["available"] = False
            count += 1
    return count


def save_store(store: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    listings = sorted(
        store.values(),
        key=lambda l: (l.get("rent", 0), l.get("address", "")),
    )
    with open(path, "w") as f:
        json.dump({"listings": listings}, f, indent=2)
