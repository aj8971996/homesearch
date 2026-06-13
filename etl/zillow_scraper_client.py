import os
import httpx

_HOST = "zillow-com-live-data-scraper-api.p.rapidapi.com"
_BASE = f"https://{_HOST}"
_HEADERS = {
    "x-rapidapi-host": _HOST,
    "x-rapidapi-key": os.environ["RAPIDAPI_KEY_ZILLOW_SCRAPER"],
    "Content-Type": "application/json",
}

# Bounding box covering all 6 target zip codes (Summerlin / NW Las Vegas).
# /bymapbounds returns individual property listings (with real zpids) rather
# than the building-level apartment complex entries that /bylocation returns.
_BOUNDS = {
    "north":  36.32,
    "south":  36.05,
    "east":  -115.24,
    "west":  -115.43,
}
_PAGE_CAP = 3  # max pages per run to stay within quota


def search_rentals() -> tuple[list[dict], int]:
    """
    GET /bymapbounds — fetch for-rent listings within the Summerlin map bounds.
    Returns (all_raw_results, api_calls_made).
    Individual property filtering (beds, price, sqft, type) is done client-side
    since the endpoint only accepts listType and page as query params.
    """
    all_results: list[dict] = []
    api_calls = 0

    for page in range(1, _PAGE_CAP + 1):
        print(f"  [scraper] GET /bymapbounds page {page}  bounds={_BOUNDS}")
        resp = httpx.get(
            f"{_BASE}/bymapbounds",
            headers=_HEADERS,
            params={
                **_BOUNDS,
                "listType": "for_rent",
                "page":     page,
            },
            timeout=30,
        )
        api_calls += 1
        print(f"  [scraper] HTTP {resp.status_code}")

        if not resp.is_success:
            print(f"  [scraper] error body: {resp.text[:600]}")
            resp.raise_for_status()

        data = resp.json()

        if page == 1:
            print(f"  [scraper] top-level keys: {list(data.keys())}")
            pagination = data.get("pagination") or {}
            if pagination:
                print(f"  [scraper] pagination: {pagination}")

        results = data.get("results") or []
        print(f"  [scraper] page {page} — {len(results)} results")

        if not results:
            break

        all_results.extend(results)

        pagination = data.get("pagination") or {}
        if not pagination.get("has_next", False):
            break

    print(f"  [scraper] {len(all_results)} total results across {api_calls} page(s)")
    return all_results, api_calls
