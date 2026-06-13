import os
import httpx

# Verify this host from the RapidAPI "Code Snippets" tab for DataCrawler/us-realtor
_HOST = "us-realtor.p.rapidapi.com"
_BASE = f"https://{_HOST}"
_HEADERS = {
    "x-rapidapi-host": _HOST,
    "x-rapidapi-key": os.environ["RAPIDAPI_KEY"],  # same RapidAPI account key as Zillow
}

TARGET_ZIPS = {"89134", "89144", "89145", "89128", "89138", "89135"}


def search_rentals() -> tuple[list[dict], int]:
    """
    Fetch house/townhome rentals in Las Vegas matching our hard criteria.
    Returns (results_in_target_zips, api_calls_made).

    Uses city-level search (no zip param available) then filters to target zips.
    With propertyType + beds + baths + price filters, expect ~1-2 pages at 200/page.
    """
    all_results: list[dict] = []
    page = 1
    api_calls = 0

    while True:
        resp = httpx.get(
            f"{_BASE}/properties/search-rent",
            headers=_HEADERS,
            params={
                "location": "city:Las Vegas, NV",
                "zoneId": "America/Los_Angeles",
                "propertyType": "single_family_home,townhome",
                "bedrooms": 3,
                "bathrooms": 2,
                "prices": ",2500",
                "resultsPerPage": 200,
                "page": page,
                "sortBy": "relevance",
            },
            timeout=30,
        )
        api_calls += 1

        if not resp.is_success:
            print(f"  [realty p{page}] HTTP {resp.status_code} — {resp.text[:400]}")
            resp.raise_for_status()

        data = resp.json()
        results = (data.get("data") or {}).get("results") or []
        meta = data.get("meta") or {}
        total_pages = int(meta.get("totalPage") or 1)

        print(f"  [realty] page {page}/{total_pages} — {len(results)} results")
        if not results:
            break

        all_results.extend(results)

        if page >= total_pages:
            break
        page += 1

    in_target = [
        r for r in all_results
        if ((r.get("location") or {}).get("address") or {}).get("postal_code", "") in TARGET_ZIPS
    ]
    print(f"  [realty] {len(in_target)} in target zips (of {len(all_results)} Las Vegas total)")
    return in_target, api_calls
