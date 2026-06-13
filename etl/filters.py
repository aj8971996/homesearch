"""
Amenity filter applied to the Zillow property detail response.

Strategy: optimistic inclusion.
  - If a field is absent or unpopulated, we INCLUDE the listing (data missing ≠ feature absent).
  - We only EXCLUDE when the data explicitly says the feature is not present.

This matters for house/townhome rentals — Zillow rarely populates laundry or pet
policy fields for single-family homes. Excluding on missing data loses good listings.

Hard exclusion cases:
  - Cooling field present and explicitly says no AC
  - Laundry field present and explicitly says shared/none
  - Pet policy present and explicitly says no cats / no pets
"""


def passes_criteria(detail: dict) -> tuple[bool, dict]:
    """
    Returns (passes, reasons).
    True = include listing. False = exclude with reason logged.
    """
    facts = detail.get("resoFacts", {}) or {}

    # ── AC: exclude only if cooling field exists and explicitly denies it ─────
    cooling_raw = " ".join(filter(None, [
        str(facts.get("cooling", "") or ""),
        str(facts.get("coolingFeatures", "") or ""),
        str(facts.get("hasAirConditioning", "") or ""),
    ])).lower()

    if cooling_raw.strip():
        # Data is present — check it
        has_ac = any(kw in cooling_raw for kw in [
            "central air", "air condition", "central", "electric",
            "refrigerated", "true", "yes",
        ])
        no_ac_explicit = any(kw in cooling_raw for kw in ["none", "no cooling", "false"])
        if no_ac_explicit:
            has_ac = False
    else:
        # No data — assume AC present (Las Vegas, nearly universal)
        has_ac = True

    # ── W/D: exclude only if laundry field exists and says shared/none ────────
    laundry_raw = str(facts.get("laundryFeatures", "") or "").lower()

    if laundry_raw.strip():
        has_wd = any(kw in laundry_raw for kw in [
            "in unit", "washer/dryer", "in-unit", "washer and dryer", "laundry in unit",
        ])
        wd_denied = any(kw in laundry_raw for kw in [
            "shared", "common", "laundromat", "none", "no laundry",
        ])
        if wd_denied and not has_wd:
            has_wd = False
        elif not has_wd and not wd_denied:
            # Field present but ambiguous — include
            has_wd = True
    else:
        # No data — assume W/D present
        has_wd = True

    # ── Cats OK: exclude only if policy explicitly bans cats/pets ─────────────
    pet_policy = str(detail.get("petPolicy", "") or "").lower()
    at_glance = " ".join(
        str(f.get("factValue", "") or "")
        for f in (detail.get("atAGlanceFacts") or [])
    ).lower()
    home_facts = " ".join(
        str(f.get("factValue", "") or "")
        for f in (detail.get("homeFactsAndFeatures") or [])
    ).lower()
    combined_pet = " ".join([pet_policy, at_glance, home_facts]).strip()

    if combined_pet:
        explicitly_denied = any(kw in combined_pet for kw in [
            "no cats", "no pets", "cats not allowed", "pets not allowed",
            "no animals", "no cat",
        ])
        cats_ok = not explicitly_denied
    else:
        # No policy data — assume cats negotiable (common for house rentals)
        cats_ok = True

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
    detail_url = raw.get("detailUrl", raw.get("detail_url", raw.get("propertyUrl", ""))) or ""

    photos = extract_photos(detail, raw.get("imgSrc", raw.get("img_src", raw.get("thumbnail", ""))))

    # home_type: normalise to HOUSE or TOWNHOUSE for frontend filtering
    # Confirmed field names from /search response
    raw_type = str(raw.get("homeType", "") or "").upper()
    home_type = "TOWNHOUSE" if "TOWN" in raw_type else "HOUSE"

    return {
        "zpid": zpid,
        "address": raw.get("address", ""),
        "zipcode": raw.get("zipcode", zipcode),
        "city": raw.get("city", "Las Vegas"),
        "state": raw.get("state", "NV"),
        "home_type": home_type,
        "rent": int(raw.get("price", 0)),
        "rent_history": [],
        "bedrooms": int(raw.get("bedrooms", raw.get("beds", 0))),
        "bathrooms": float(raw.get("bathrooms", raw.get("baths", 0))),
        "sqft": int(raw.get("livingArea", raw.get("area", 0))),
        "has_ac": True,
        "has_washer_dryer": True,
        "cats_ok": True,
        "days_on_market": int(raw.get("daysOnZillow", 0) or 0),
        "first_seen_date": today,
        "last_confirmed_date": today,
        "available": True,
        "photo_count": len(photos),
        "photos": photos,
        "listing_url": f"https://www.zillow.com{detail_url}" if detail_url.startswith("/") else detail_url,
        "description": str(detail.get("description", "") or ""),
        "source": "zillow",
    }
