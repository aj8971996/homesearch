import os
import httpx

_HOST = "real-time-real-estate-data-mega.p.rapidapi.com"
_BASE = f"https://{_HOST}"
_HEADERS = {
    "x-rapidapi-host": _HOST,
    "x-rapidapi-key": os.environ["RAPIDAPI_KEY"],
}

ZIP_CODES = ["89134", "89144", "89145", "89128", "89138", "89135"]

_SEARCH_ENDPOINT = "/search"
_DETAIL_ENDPOINT = "/property-details"


def search_rentals(zipcode: str) -> list[dict]:
    """Search for rental listings in a zip code."""
    resp = httpx.get(
        f"{_BASE}{_SEARCH_ENDPOINT}",
        headers=_HEADERS,
        params={
            "location": zipcode,
            "status_type": "ForRent",
            "home_type": "Houses,Apartments,Condos,Townhomes,MultiFamily",
            "rentMaxPrice": 2500,
            "bedsMin": 3,
            "bathsMin": 2,
            "sqftMin": 1300,
        },
        timeout=30,
    )
    if not resp.is_success:
        print(f"  [{zipcode}] HTTP {resp.status_code} — body: {resp.text[:600]}")
        resp.raise_for_status()

    data = resp.json()
    print(f"  [{zipcode}] top-level keys: {list(data.keys())}")

    # Try common result-list field names across OpenWebNinja API versions
    props = data.get("data", data.get("props", data.get("results", data.get("listings", []))))
    print(f"  [{zipcode}] {len(props)} raw results")

    # Log the first result's keys so we can map field names in extract_listing
    if props:
        print(f"  [{zipcode}] first result keys: {list(props[0].keys())}")

    return props


def get_details(zpid: str) -> dict:
    """Fetch full property detail by zpid for amenity checking."""
    resp = httpx.get(
        f"{_BASE}{_DETAIL_ENDPOINT}",
        headers=_HEADERS,
        params={"zpid": zpid},
        timeout=30,
    )
    if not resp.is_success:
        print(f"  [detail {zpid}] HTTP {resp.status_code} — body: {resp.text[:600]}")
        resp.raise_for_status()

    data = resp.json()
    # Log detail keys on first call so we can map amenity fields
    detail = data.get("data", data) if isinstance(data.get("data"), dict) else data
    print(f"  [detail {zpid}] keys: {list(detail.keys())[:20]}")
    return detail
