import os
import time
import httpx

_HOST = "zillow-property-data1.p.rapidapi.com"
_BASE = f"https://{_HOST}"
_HEADERS = {
    "x-rapidapi-host": _HOST,
    "x-rapidapi-key": os.environ["RAPIDAPI_KEY_APILOW"],
    "Content-Type": "application/json",
}

# "for_rent" matches Zillow's for-rent section.
# If the API returns 0 results, verify the correct type value
# (alternatives to try: "rent", "rental", "for-rent").
_SEARCH    = "Las Vegas, NV"
_TYPE      = "for_rent"
_MAX_ITEMS = 100

_POLL_INTERVAL = 5    # seconds between GET polls
_POLL_TIMEOUT  = 120  # max seconds to wait for job completion


def _submit_job() -> tuple[str, list[dict]]:
    """
    POST /v1/properties — submit batch search job.
    Returns (job_id, early_results).
    early_results is populated if the API returns results synchronously in the POST.
    """
    payload = {
        "search": _SEARCH,
        "type": _TYPE,
        "max_items": _MAX_ITEMS,
    }
    print(f"  [apilow] POST /v1/properties — search={_SEARCH!r} type={_TYPE!r} max_items={_MAX_ITEMS}")
    resp = httpx.post(
        f"{_BASE}/v1/properties",
        headers=_HEADERS,
        json=payload,
        timeout=30,
    )
    print(f"  [apilow] POST HTTP {resp.status_code}")
    if not resp.is_success:
        print(f"  [apilow] POST error body: {resp.text[:800]}")
        resp.raise_for_status()

    data = resp.json()
    print(f"  [apilow] POST response keys: {list(data.keys())}")
    print(f"  [apilow] POST status={data.get('status')!r}")

    job_id = str(data.get("job_id") or data.get("id") or "").strip()
    if not job_id:
        raise ValueError(f"No job_id in POST response — full response: {data}")

    print(f"  [apilow] job_id={job_id!r}")

    # Handle synchronous response (job already complete in POST body)
    early_results: list[dict] = []
    if data.get("status") == "complete":
        early_results = data.get("results", [])
        print(f"  [apilow] POST returned results immediately ({len(early_results)} items)")

    return job_id, early_results


def _poll_for_results(job_id: str) -> tuple[list[dict], int]:
    """
    GET /v1/properties?job_id=... — poll until status=='complete'.
    Returns (results, number_of_get_calls).
    """
    deadline = time.time() + _POLL_TIMEOUT
    poll_count = 0

    while time.time() < deadline:
        poll_count += 1
        print(f"  [apilow] GET poll #{poll_count} — job_id={job_id!r}")
        resp = httpx.get(
            f"{_BASE}/v1/properties",
            headers=_HEADERS,
            params={"job_id": job_id},
            timeout=30,
        )
        print(f"  [apilow] GET HTTP {resp.status_code}")
        if not resp.is_success:
            print(f"  [apilow] GET error body: {resp.text[:800]}")
            resp.raise_for_status()

        data = resp.json()
        status = data.get("status", "")
        results_so_far = len(data.get("results", []))
        errors_so_far  = len(data.get("errors", []))
        print(f"  [apilow] status={status!r}  results={results_so_far}  errors={errors_so_far}")

        if status == "complete":
            results = data.get("results", [])
            for err in data.get("errors", []):
                print(f"  [apilow] error item: {err}")
            return results, poll_count

        if status in ("failed", "error"):
            raise RuntimeError(f"APIllow job {job_id!r} ended with status={status!r}")

        print(f"  [apilow] waiting {_POLL_INTERVAL}s before next poll…")
        time.sleep(_POLL_INTERVAL)

    raise TimeoutError(f"APIllow job {job_id!r} did not complete within {_POLL_TIMEOUT}s")


def search_rentals() -> tuple[list[dict], int]:
    """
    Submit a batch job and return results with API call count.
    Returns (property_dicts, total_api_calls_used).

    Minimum 2 calls per run (1 POST + 1 GET); more if the job is slow to process.
    """
    job_id, early_results = _submit_job()
    api_calls = 1  # POST

    if early_results:
        all_results = early_results
    else:
        all_results, get_count = _poll_for_results(job_id)
        api_calls += get_count

    # Unwrap nested 'property' object from each result record
    properties: list[dict] = []
    for r in all_results:
        if r.get("success") and r.get("property"):
            properties.append(r["property"])
        elif not r.get("success"):
            print(f"  [apilow] failed result: {r.get('error', '?')}  url={r.get('url', '')}")

    print(f"  [apilow] {len(properties)}/{len(all_results)} results were successful")
    print(f"  [apilow] total API calls this run: {api_calls} (budget: 50/month)")
    return properties, api_calls
