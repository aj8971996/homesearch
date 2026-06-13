"""
Amenity filter applied to the Zillow property detail response.

All three must pass for a listing to be included:
  - AC in unit
  - Washer / Dryer in unit
  - Cats OK

Fields come from the `resoFacts` block of the /property endpoint.
When a field is absent we default to False (conservative exclusion).
"""


def passes_criteria(detail: dict) -> tuple[bool, dict]:
    """
    Returns (passes, reasons) where reasons is a dict of each check result.
    Logging the reasons helps diagnose why listings are excluded.
    """
    facts = detail.get("resoFacts", {})

    # ── AC ────────────────────────────────────────────────────────────────────
    cooling_raw = " ".join(filter(None, [
        str(facts.get("cooling", "") or ""),
        str(facts.get("coolingFeatures", "") or ""),
        str(facts.get("hasAirConditioning", "") or ""),
    ])).lower()
    has_ac = any(kw in cooling_raw for kw in [
        "central air", "air condition", "central", "electric", "refrigerated", "true"
    ])

    # ── Washer / Dryer in unit ────────────────────────────────────────────────
    laundry_raw = str(facts.get("laundryFeatures", "") or "").lower()
    has_wd = any(kw in laundry_raw for kw in [
        "in unit", "washer/dryer", "laundry in unit", "in-unit", "washer and dryer"
    ])

    # ── Cats OK ───────────────────────────────────────────────────────────────
    # Zillow surfaces pet policy in several places depending on listing type
    pet_policy = str(detail.get("petPolicy", "") or "").lower()
    at_glance = " ".join(
        str(f.get("factValue", "") or "")
        for f in (detail.get("atAGlanceFacts") or [])
    ).lower()
    home_facts = " ".join(
        str(f.get("factValue", "") or "")
        for f in (detail.get("homeFactsAndFeatures") or [])
    ).lower()
    combined_pet = " ".join([pet_policy, at_glance, home_facts])

    cats_ok = (
        ("cat" in combined_pet and "no cat" not in combined_pet)
        or "pets allowed" in combined_pet
        or "cats allowed" in combined_pet
    )

    reasons = {"has_ac": has_ac, "has_washer_dryer": has_wd, "cats_ok": cats_ok}
    return (has_ac and has_wd and cats_ok), reasons


def extract_photos(detail: dict, fallback_img: str) -> list[str]:
    """Pull photo URLs from the detail response, falling back to the thumbnail."""
    urls: list[str] = []

    # Primary: detail.photos.data[]
    for p in (detail.get("photos", {}) or {}).get("data", []) or []:
        url = p.get("url") or ""
        if not url:
            # Some responses nest under mixedSources
            srcs = (p.get("mixedSources", {}) or {}).get("jpeg", []) or []
            url = srcs[-1].get("url", "") if srcs else ""
        if url:
            urls.append(url)

    # Fallback to search thumbnail
    if not urls and fallback_img:
        urls.append(fallback_img)

    return urls


def extract_listing(raw: dict, detail: dict, zipcode: str, today: str) -> dict:
    """Normalise a raw search result + its detail into our storage schema."""
    zpid = str(raw.get("zpid", ""))
    detail_url = raw.get("detailUrl", "") or ""

    photos = extract_photos(detail, raw.get("imgSrc", ""))

    return {
        "zpid": zpid,
        "address": raw.get("address", ""),
        "zipcode": zipcode,
        "city": "Las Vegas",
        "state": "NV",
        "rent": int(raw.get("price", 0)),
        "rent_history": [],
        "bedrooms": int(raw.get("bedrooms", 0)),
        "bathrooms": float(raw.get("bathrooms", 0)),
        "sqft": int(raw.get("livingArea", 0)),
        "has_ac": True,
        "has_washer_dryer": True,
        "cats_ok": True,
        "days_on_market": int(raw.get("daysOnZillow", 0) or 0),
        "first_seen_date": today,
        "last_confirmed_date": today,
        "available": True,
        "photo_count": len(photos),
        "photos": photos,
        "listing_url": f"https://www.zillow.com{detail_url}" if detail_url else "",
        "description": str(detail.get("description", "") or ""),
    }
