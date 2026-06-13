import os
import httpx

_HOST = "zillow-com-live-data-scraper-api.p.rapidapi.com"
_BASE = f"https://{_HOST}"
_HEADERS = {
    "x-rapidapi-host": _HOST,
    "x-rapidapi-key": os.environ["RAPIDAPI_KEY_ZILLOW_SCRAPER"],
    "Content-Type": "application/json",
}

# Location slug format: "city-state" (e.g. "las-vegas-nv").
# All 6 target zip codes are in Las Vegas; zip filtering is done client-side.
_LOCATION = "las-vegas-nv"
_PAGE_CAP  = 3  # max pages per run to stay within quota


def search_rentals() -> tuple[list[dict], int]:
    """
    GET /bylocation — fetch for-rent listings page by page.
    Returns (all_raw_results, api_calls_made).
    Filters are applied server-side where supported; zip-code filtering is done
    in the ETL layer since the API does not accept zip-code constraints.
    """
    all_results: list[dict] = []
    api_calls = 0

    for page in range(1, _PAGE_CAP + 1):
        print(f"  [scraper] GET /bylocation page {page}")
        resp = httpx.get(
            f"{_BASE}/bylocation",
            headers=_HEADERS,
            params={
                "location":  _LOCATION,
                "listType":  "for-rent",
                "beds":      3,
                "baths":     2,
                "maxPrice":  2500,
                "minSqft":   1300,
                "page":      page,
            },
            timeout=30,
        )
        api_calls += 1
        print(f"  [scraper] HTTP {resp.status_code}")

        if not resp.is_success:
            print(f"  [scraper] error body: {resp.text[:600]}")
            resp.raise_for_status()

        data = resp.json()

        # Log top-level structure on first page so field-name changes surface in CI logs
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
        has_next = pagination.get("has_next", False)
        if not has_next:
            break

    print(f"  [scraper] {len(all_results)} total results across {api_calls} page(s)")
    return all_results, api_calls
