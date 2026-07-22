"""
Catalog search + regional demand logging.
Day 2: search_catalog() is now written so Gemini can call it directly as a
tool — it needs typed parameters (not a generic dict) for the SDK to build
a schema from it automatically.

Usage (as a standalone test):
    python catalog.py
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

CATALOG_PATH = "data/catalog.json"
DEMAND_LOG_PATH = "data/demand_log.json"


def _load_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_product_by_id(product_id: str) -> Optional[dict]:
    """Returns the single catalog product with this product_id, or None if
    no product has it. Used by app.py's GET /api/product/{product_id} for
    the product detail page — reuses the exact same catalog data
    search_catalog reads from, no separate data source.
    """
    for product in _load_catalog():
        if product["product_id"] == product_id:
            return product
    return None


def search_catalog(
    category: Optional[str] = None,
    max_price: Optional[int] = None,
    min_price: Optional[int] = None,
    occasion: Optional[str] = None,
    region_tag: Optional[str] = None,
    gender: Optional[str] = None,
) -> list:
    """Searches the product catalog and returns up to 5 matching products.

    Use this whenever the customer is looking for a product. Only pass the
    filters the customer actually mentioned — leave the rest unset.

    Args:
        category: product type, e.g. "shirt", "kurta", "jeans", "saree",
            "t-shirt", "dress", "trousers", "jacket", "ethnic set", "sneakers"
        max_price: highest price in rupees the customer is willing to pay
        min_price: lowest price in rupees, if the customer mentioned one
        occasion: e.g. "office", "wedding", "casual", "festive", "party", "everyday"
        region_tag: customer's city/region, if known
        gender: who the product is for, one of "Men", "Women", "Girls",
            "Boys" — pass this whenever the customer has stated a gender
            preference, including on later searches this same conversation
            after they first mentioned it, not just the turn they said it.
            Products tagged "Unisex" always match regardless of this filter.
            Not every category has options for every gender (e.g. this
            catalog's kurta/saree/ethnic set items are all "Women" — if a
            search with a gender filter comes back empty, say so honestly
            rather than showing an unrelated product.
    """
    catalog = _load_catalog()
    results = catalog

    if category:
        results = [p for p in results if p["category"] == category]
    if max_price:
        results = [p for p in results if p["price"] <= max_price]
    if min_price:
        results = [p for p in results if p["price"] >= min_price]
    if occasion:
        results = [p for p in results if p["occasion"] == occasion]
    if region_tag:
        results = [p for p in results if p["region_tag"] == region_tag]
    if gender:
        gender_lower = gender.lower()
        results = [
            p for p in results
            if p.get("gender", "").lower() in (gender_lower, "unisex")
        ]

    filters_used = {
        k: v for k, v in {
            "category": category, "max_price": max_price, "min_price": min_price,
            "occasion": occasion, "region_tag": region_tag, "gender": gender,
        }.items() if v is not None
    }
    log_query(filters_used, region_tag or "unknown")
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
    # Quick standalone check — run this file directly to confirm everything works
    results = search_catalog(category="shirt", max_price=800)
    print(f"Found {len(results)} matching products:")
    for p in results:
        print(f"  - {p['name']} | Rs.{p['price']} | fit: {p['fit_notes']} | {p['review_summary']}")
    print("\nCheck data/demand_log.json — it should now have a new entry.")
