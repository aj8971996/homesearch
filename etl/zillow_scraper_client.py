import os
import httpx

_HOST = "zillow-com-live-data-scraper-api.p.rapidapi.com"
_BASE = f"https://{_HOST}"
_HEADERS = {
    "x-rapidapi-host": _HOST,
    "x-rapidapi-key": os.environ["RAPIDAPI_KEY_ZILLOW_SCRAPER"],
    "Content-Type": "application/json",
}

# Summerlin / NW Las Vegas agents known to list for-rent properties.
# Full list will be enabled next month once API quota resets.
# Remaining agents to add: Robert Adams Broker, Sam Beard
AGENT_URLS = [
    "https://www.zillow.com/profile/Ehren%20Alessi%20CEO",
    "https://www.zillow.com/profile/AltGroupRE",
]

_PAGE_CAP = 4  # max pages per agent — 2 agents × 4 pages = 8 calls max


def search_rentals() -> tuple[list[dict], int]:
    """
    GET /agentForRentProperties — fetch for-rent listings for each agent.
    Returns (all_raw_results, api_calls_made).
    Dedup and property filtering are handled in the ETL layer.
    """
    all_results: list[dict] = []
    api_calls = 0

    for agent_url in AGENT_URLS:
        agent_slug = agent_url.split("/profile/")[-1]
        print(f"\n  [scraper] agent: {agent_slug}")

        for page in range(1, _PAGE_CAP + 1):
            print(f"  [scraper] GET /agentForRentProperties page {page}")
            resp = httpx.get(
                f"{_BASE}/agentForRentProperties",
                headers=_HEADERS,
                params={"url": agent_url, "page": page},
                timeout=30,
            )
            api_calls += 1
            print(f"  [scraper] HTTP {resp.status_code}")

            if not resp.is_success:
                print(f"  [scraper] error body: {resp.text[:600]}")
                resp.raise_for_status()

            data = resp.json()

            if page == 1:
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

    print(f"\n  [scraper] {len(all_results)} total results across {api_calls} call(s)")
    return all_results, api_calls
