import os
import httpx

_HOST = "realty-us.p.rapidapi.com"
_BASE = f"https://{_HOST}"
_HEADERS = {
    "x-rapidapi-host": _HOST,
    "x-rapidapi-key": os.environ["RAPIDAPI_KEY"],
}


def search_rentals() -> tuple[list[dict], int]:
    """
    Fetch rentals from Realty US API.
    Returns (all_raw_results, api_calls_made) — unfiltered; caller saves raw then filters.
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
            print(f"  [realty p{page}] HTTP {resp.status_code} — {resp.text}")
            resp.raise_for_status()

        data = resp.json()

        # Log response shape so API contract changes are immediately visible in CI logs
        if page == 1:
            print(f"  [realty] top-level keys: {list(data.keys())}")
            if isinstance(data.get("data"), dict):
                print(f"  [realty] data keys: {list(data['data'].keys())}")
            if data.get("meta"):
                print(f"  [realty] meta: {data['meta']}")

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

    return all_results, api_calls
