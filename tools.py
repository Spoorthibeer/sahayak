"""
Day 2 task: fit-confidence and trust-signal tools.
These are simple rule-based functions (no ML needed for the MVP) that
Gemini calls after search_catalog returns products, to give the customer
practical buying advice instead of just a bare product list.
"""

# Mock customer profile — hardcoded for the MVP demo.
# On the real app this would come from the customer's account/order history.
CUSTOMER_PROFILE = {
    "height_cm": 170,
    "weight_kg": 65,
    "past_orders": [
        {"category": "shirt", "size_ordered": "M", "kept": True},
        {"category": "jeans", "size_ordered": "L", "kept": False},
    ],
}


_SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


def _adjacent_size(size: str, step: int) -> str:
    """Returns the size one step up (step=1) or down (step=-1) from `size`
    in _SIZE_ORDER. Falls back to returning `size` unchanged if it's not a
    recognized letter size (e.g. a numeric jeans size)."""
    if size not in _SIZE_ORDER:
        return size
    idx = _SIZE_ORDER.index(size)
    idx = max(0, min(len(_SIZE_ORDER) - 1, idx + step))
    return _SIZE_ORDER[idx]


def fit_score(fit_notes: str, category: str) -> str:
    """Returns a plain-language, personalized fit-confidence message for a
    product, combining the product's fit_notes with the customer's own
    order history for that category (CUSTOMER_PROFILE) where available.

    Call this after search_catalog, using the fit_notes and category values
    from a product you want to give the customer advice about.

    Args:
        fit_notes: the product's fit_notes field, one of
            "runs small", "true to size", "runs large"
        category: the product's category field, e.g. "shirt", "jeans"
    """
    fit_descriptions = {
        "runs small": "tends to run small",
        "true to size": "fits true to size",
        "runs large": "tends to run large",
    }
    fit_description = fit_descriptions.get(fit_notes)
    if fit_description is None:
        return "No fit information is available for this item."

    # Only trust a past order as a sizing signal if the customer actually
    # kept it — a returned item suggests that size guess was wrong.
    past_order = next(
        (
            o for o in CUSTOMER_PROFILE["past_orders"]
            if o["category"] == category and o["kept"]
        ),
        None,
    )
    if past_order is None:
        return f"This {fit_description} — consider sizing up or down accordingly."

    usual_size = past_order["size_ordered"]
    if fit_notes == "runs small":
        suggested_size = _adjacent_size(usual_size, 1)
        return (
            f"You typically wear size {usual_size} based on your past orders; "
            f"this item {fit_description}, so consider sizing up to {suggested_size}."
        )
    if fit_notes == "runs large":
        suggested_size = _adjacent_size(usual_size, -1)
        return (
            f"You typically wear size {usual_size} based on your past orders; "
            f"this item {fit_description}, so consider sizing down to {suggested_size}."
        )
    return (
        f"You typically wear size {usual_size} based on your past orders; "
        f"this item {fit_description}, so size {usual_size} should work well."
    )


def trust_note(return_rate: float, review_summary: str) -> str:
    """Returns a plain-language trust note for a product.

    Call this after search_catalog, using the return_rate and
    review_summary values from a product you want to give the customer
    advice about.

    Args:
        return_rate: the product's return_rate field, a number between 0 and 1
        review_summary: the product's review_summary field, e.g. "4.1/5 average from 173 reviews"
    """
    if return_rate < 0.08:
        trust_level = "a very low return rate — highly trusted by buyers"
    elif return_rate < 0.15:
        trust_level = "a moderate return rate — generally trusted"
    else:
        trust_level = "a higher return rate — worth double-checking size and fit before buying"

    return f"{review_summary}, with {trust_level}."


if __name__ == "__main__":
    # Quick standalone check
    print(fit_score("runs small", "shirt"))   # kept past order -> personalized
    print(fit_score("runs large", "jeans"))   # past order was returned -> generic fallback
    print(fit_score("true to size", "kurta")) # no past order at all -> generic fallback
    print(trust_note(0.05, "4.1/5 average from 173 reviews"))
    print(trust_note(0.20, "3.6/5 average from 377 reviews"))
