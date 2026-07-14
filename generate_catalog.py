"""
Day 1 task: generate a mock product catalog for the hackathon MVP.
Run this once to create data/catalog.json.

Usage:
    python generate_catalog.py
"""

import json
import random
import uuid

CATEGORIES = ["shirt", "kurta", "jeans", "saree", "t-shirt", "dress",
              "trousers", "jacket", "ethnic set", "sneakers"]
OCCASIONS = ["office", "wedding", "casual", "festive", "party", "everyday"]
REGIONS = ["Patna", "Belgaum", "Vizag", "Coimbatore", "Lucknow", "Nagpur"]
FIT_NOTES = ["runs small", "true to size", "runs large"]

BASE_NAMES = {
    "shirt": ["Cotton Formal Shirt", "Checked Casual Shirt", "Linen Shirt"],
    "kurta": ["Printed Cotton Kurta", "Embroidered Kurta", "Festive Silk Kurta"],
    "jeans": ["Slim Fit Jeans", "Straight Fit Jeans", "Stretchable Jeans"],
    "saree": ["Cotton Handloom Saree", "Silk Blend Saree", "Printed Georgette Saree"],
    "t-shirt": ["Graphic Tee", "Plain Cotton Tee", "Polo T-Shirt"],
    "dress": ["A-Line Dress", "Wrap Dress", "Maxi Dress"],
    "trousers": ["Formal Trousers", "Chinos", "Cargo Pants"],
    "jacket": ["Denim Jacket", "Bomber Jacket", "Quilted Jacket"],
    "ethnic set": ["Kurta Pajama Set", "Sharara Set", "Anarkali Set"],
    "sneakers": ["Casual Sneakers", "Running Shoes", "Canvas Shoes"],
}


def make_product():
    category = random.choice(CATEGORIES)
    name = random.choice(BASE_NAMES[category])
    price = random.choice([399, 499, 599, 699, 799, 899, 999, 1299, 1499, 1999])
    occasion = random.choice(OCCASIONS)
    region_tag = random.choice(REGIONS)
    fit_notes = random.choice(FIT_NOTES)
    return_rate = round(random.uniform(0.03, 0.25), 2)  # 3%-25% return rate
    review_count = random.randint(5, 500)
    review_avg = round(random.uniform(3.2, 4.8), 1)

    return {
        "product_id": str(uuid.uuid4())[:8],
        "name": name,
        "category": category,
        "price": price,
        "occasion": occasion,
        "region_tag": region_tag,
        "fit_notes": fit_notes,
        "return_rate": return_rate,
        "review_summary": f"{review_avg}/5 average from {review_count} reviews",
    }


def main(n=250):
    catalog = [make_product() for _ in range(n)]
    with open("data/catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"Generated {n} products -> data/catalog.json")


if __name__ == "__main__":
    main()
