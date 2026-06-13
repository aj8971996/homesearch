import os
import httpx

_HOST = "real-time-real-estate-data-mega.p.rapidapi.com"
_BASE = f"https://{_HOST}"
_HEADERS = {
    "x-rapidapi-host": _HOST,
    "x-rapidapi-key": os.environ["RAPIDAPI_KEY"],
}

ZIP_CODES = ["89134", "89144", "89145", "89128", "89138", "89135"]

# Endpoint names — update these once confirmed from the RapidAPI docs sidebar
_SEARCH_ENDPOINT  = "/search-for-rent-listings"
_DETAIL_ENDPOINT  = "/property-details"


def search_rentals(zipcode: str) -> list[dict]:
    """Search for rental listings in a zip code. Prints raw response on error for debugging."""
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
        print(f"  [{zipcode}] HTTP {resp.status_code} — body: {resp.text[:400]}")
        resp.raise_for_status()
    data = resp.json()
    # Print top-level keys so we can verify the response shape
    print(f"  [{zipcode}] response keys: {list(data.keys())}")
    props = data.get("data", data.get("props", data.get("results", [])))
    print(f"  [{zipcode}] {len(props)} raw results")
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
        print(f"  [detail {zpid}] HTTP {resp.status_code} — body: {resp.text[:400]}")
        resp.raise_for_status()
    return resp.json()
