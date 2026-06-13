"""
Raw staging layer — saves API responses as dated JSON files in etl/raw/.
These files are .gitignored and never pushed to the repo.

Usage:
    from raw_store import save_raw, load_latest_raw

    save_raw("realty", results)   # writes etl/raw/realty_2026-06-13.json
    rows = load_latest_raw("realty")
"""

import json
import os
from datetime import date
from glob import glob

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")


def save_raw(source: str, data: list[dict]) -> str:
    """Persist raw API results. Returns the file path written."""
    os.makedirs(RAW_DIR, exist_ok=True)
    today = date.today().isoformat()
    path = os.path.join(RAW_DIR, f"{source}_{today}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def load_latest_raw(source: str) -> list[dict]:
    """Load the most-recently-written raw file for a given source."""
    pattern = os.path.join(RAW_DIR, f"{source}_*.json")
    files = sorted(glob(pattern))
    if not files:
        return []
    with open(files[-1]) as f:
        return json.load(f)
