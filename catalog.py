"""
Day 1 task: plain Python catalog search + regional demand logging.
No AI involved yet — this gets wired in as a Gemini "tool" on Day 2.

Usage (as a standalone test):
    python catalog.py
"""

import json
import os
from datetime import datetime, timezone

CATALOG_PATH = "data/catalog.json"
DEMAND_LOG_PATH = "data/demand_log.json"


def _load_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def search_catalog(filters: dict) -> list:
    """
    filters can include any of: category, max_price, min_price, occasion,
    region_tag. Only the filters you pass in are applied.
    Example: search_catalog({"category": "shirt", "max_price": 800})
    """
    catalog = _load_catalog()
    results = catalog

    if "category" in filters:
        results = [p for p in results if p["category"] == filters["category"]]
    if "max_price" in filters:
        results = [p for p in results if p["price"] <= filters["max_price"]]
    if "min_price" in filters:
        results = [p for p in results if p["price"] >= filters["min_price"]]
    if "occasion" in filters:
        results = [p for p in results if p["occasion"] == filters["occasion"]]
    if "region_tag" in filters:
        results = [p for p in results if p["region_tag"] == filters["region_tag"]]

    log_query(filters, filters.get("region_tag", "unknown"))
    return results[:5]  # keep responses short for the agent to summarize


def log_query(filters: dict, region_tag: str = "unknown"):
    """
    Appends every search to a demand log — this is the 'regional demand
    capture' feature: a record of what customers are actually asking for,
    by region, that Myntra's merchandising side could act on.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "filters": filters,
        "region_tag": region_tag,
    }

    if os.path.exists(DEMAND_LOG_PATH):
        with open(DEMAND_LOG_PATH, "r", encoding="utf-8") as f:
            log = json.load(f)
    else:
        log = []

    log.append(entry)

    with open(DEMAND_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Day 1 end-of-day check — run this file directly to confirm everything works
    results = search_catalog({"category": "shirt", "max_price": 800})
    print(f"Found {len(results)} matching products:")
    for p in results:
        print(f"  - {p['name']} | Rs.{p['price']} | fit: {p['fit_notes']} | {p['review_summary']}")
    print("\nCheck data/demand_log.json — it should now have one entry.")
