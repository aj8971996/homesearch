import os
import httpx

_HOST = "zillow-com1.p.rapidapi.com"
_BASE = f"https://{_HOST}"
_HEADERS = {
    "X-RapidAPI-Host": _HOST,
    "X-RapidAPI-Key": os.environ["RAPIDAPI_KEY"],
}

ZIP_CODES = ["89134", "89144", "89145", "89128", "89138", "89135"]


def search_rentals(zipcode: str) -> list[dict]:
    """Search Zillow for rental listings in a zip code matching our base criteria."""
    resp = httpx.get(
        f"{_BASE}/propertyExtendedSearch",
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
    resp.raise_for_status()
    data = resp.json()
    props = data.get("props", [])
    print(f"  [{zipcode}] {len(props)} raw results from search")
    return props


def get_details(zpid: str) -> dict:
    """Fetch full property detail for a single listing (used for amenity checks)."""
    resp = httpx.get(
        f"{_BASE}/property",
        headers=_HEADERS,
        params={"zpid": zpid},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
