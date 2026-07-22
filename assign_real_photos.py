"""
One-time script: assigns real product photos (already sourced, verified,
and committed at data/real_photos/, see manifest.json) to our mock catalog
products, by category. Updates data/catalog.json in place, adding
"image_path", "gender", and "colour" fields to each product whose category
has at least one real photo available.

Not part of the running app — run manually, once, whenever the catalog or
the real_photos set changes.

Usage:
    python assign_real_photos.py

Matching key: manifest.json's top-level keys are category names (matching
our catalog's own category strings exactly, e.g. "ethnic set" with a
space) mapping to a list of {filename, gender, colour, ...} entries.
Multiple catalog products in the same category reuse the same small set of
real photos (round-robin, for some visual variety) when there are fewer
real photos than products in that category — this is expected and fine,
not a bug.

Gender field (2026-07-22 pass): our mock catalog (generate_catalog.py) has
no gender concept of its own — a product's "gender" is set to whatever
gender its assigned real photo actually is, straight from the manifest.
This is deliberate, not an approximation: it guarantees a product's photo
and its gender label can never disagree (there's no separate "pick a
gender" step that could drift from "pick a photo"), and it gives a
realistic-enough gender spread per category since manifest.json's own
photos already span Men/Women/Girls/Unisex per category (checked directly
before writing this — e.g. shirt has 10 Men + 2 Women, jeans has 3 Men + 8
Women; kurta/saree/ethnic set are 100% Women in this photo set, so those
categories end up all "Women" — genuinely no Men-labeled photos exist for
them in data/real_photos/, not an oversight).
"""

import json
from collections import defaultdict

MANIFEST_PATH = "data/real_photos/manifest.json"
CATALOG_PATH = "data/catalog.json"
PHOTOS_DIR = "data/real_photos"


def main():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)

    category_cursor = defaultdict(int)  # round-robins through each category's photos
    before_counts = defaultdict(lambda: [0, 0])  # category -> [had_photo, no_photo], before this run
    after_counts = defaultdict(lambda: [0, 0])
    gender_counts = defaultdict(lambda: defaultdict(int))  # category -> {gender: count}

    for product in catalog:
        cat = product.get("category")
        had_photo_before = bool(product.get("image_path"))
        before_counts[cat][0 if had_photo_before else 1] += 1

        photos = manifest.get(cat)
        if photos:
            chosen = photos[category_cursor[cat] % len(photos)]
            category_cursor[cat] += 1
            product["image_path"] = f"{PHOTOS_DIR}/{chosen['filename']}"
            product["gender"] = chosen["gender"]
            if chosen.get("colour"):
                product["colour"] = chosen["colour"]
            gender_counts[cat][chosen["gender"]] += 1

        after_counts[cat][0 if product.get("image_path") else 1] += 1

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    total_photo = sum(v[0] for v in after_counts.values())
    total_icon = sum(v[1] for v in after_counts.values())

    print("Before this run:")
    for cat in sorted(before_counts):
        had, none = before_counts[cat]
        print(f"  {cat}: {had} real photo, {none} icon fallback")

    print()
    print("After this run (photo coverage + gender breakdown):")
    for cat in sorted(after_counts):
        had, none = after_counts[cat]
        genders = dict(gender_counts[cat])
        print(f"  {cat}: {had} real photo, {none} icon fallback, genders={genders}")

    print()
    print(f"Total: {total_photo}/{len(catalog)} products now have a real photo, {total_icon} still on the icon fallback.")


if __name__ == "__main__":
    main()
