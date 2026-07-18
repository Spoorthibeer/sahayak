"""
Day 2 task: fit-confidence and trust-signal tools.
These are simple rule-based functions (no ML needed for the MVP) that
Gemini calls after search_catalog returns products, to give the customer
practical buying advice instead of just a bare product list.
"""

from typing import Optional

# Mock customer profile — hardcoded for the MVP demo.
# On the real app this would come from the customer's account/order history.
#
# Only past_orders is ever read silently (no need to ask the customer,
# same as a real "logged in" account). height_cm/weight_kg/usual_size/
# build_description are intentionally NOT read from here by fit_score, even
# though the shape matches — they're deliberately sourced fresh from the
# conversation (as fit_score's own parameters) instead. If fit_score fell
# back to this dict for those fields, every session would silently look like
# a customer with sizing info already on file, making it impossible for a
# genuinely new customer (no history) to be simulated/tested. See
# fit_score's docstring and CLAUDE.md for the full fallback chain.
CUSTOMER_PROFILE = {
    "height_cm": 170,
    "weight_kg": 65,
    "usual_size": None,
    "build_description": None,
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


# Broad category grouping for the height/weight size chart — "tops vs
# bottoms" is enough granularity for the MVP (task explicitly says not to
# over-engineer this). Categories not in either group (e.g. "sneakers") have
# no sensible height/weight-based clothing size, so the chart is just
# skipped for them.
_TOPS_CATEGORIES = {"shirt", "kurta", "t-shirt", "jacket", "dress", "saree", "ethnic set"}
_BOTTOMS_CATEGORIES = {"jeans", "trousers"}


def _category_group(category: str) -> Optional[str]:
    if category in _TOPS_CATEGORIES:
        return "tops"
    if category in _BOTTOMS_CATEGORIES:
        return "bottoms"
    return None


# Simple static height/weight -> size chart. Weight is the primary signal
# (dominant factor for garment sizing in a rough chart like this); height
# only nudges the result up one size for notably tall frames (>=180cm), to
# account for length. Deliberately coarse — this is a last-resort fallback
# signal, not a precise fit chart.
_WEIGHT_SIZE_BANDS = {
    "tops": [(54, "S"), (68, "M"), (82, "L"), (96, "XL"), (999, "XXL")],
    "bottoms": [(54, "S"), (70, "M"), (85, "L"), (100, "XL"), (999, "XXL")],
}


def _size_from_height_weight(height_cm: int, weight_kg: int, category_group: str) -> str:
    bands = _WEIGHT_SIZE_BANDS[category_group]
    size = next(s for max_weight, s in bands if weight_kg <= max_weight)
    if height_cm >= 180:
        size = _adjacent_size(size, 1)
    return size


# Last-resort qualitative signal, for a customer who can't answer a usual
# size or height/weight. Maps to a baseline the same way the other signals
# do, then gets adjusted by fit_notes just like everywhere else.
_BUILD_BASELINE_SIZE = {"slim": "S", "average": "M", "broad": "L"}


def _sized_message(baseline_size: str, fit_notes: str, fit_description: str,
                    signal_used: str, approximate: bool = False) -> dict:
    if fit_notes == "runs small":
        suggested = _adjacent_size(baseline_size, 1)
        advice = f"this item {fit_description}, so consider sizing up to {suggested}"
    elif fit_notes == "runs large":
        suggested = _adjacent_size(baseline_size, -1)
        advice = f"this item {fit_description}, so consider sizing down to {suggested}"
    else:
        advice = f"this item {fit_description}, so size {baseline_size} should work well"

    lead = {
        "order_history": f"You typically wear size {baseline_size} based on your past orders",
        "usual_size": f"Based on the usual size you gave me ({baseline_size})",
        "height_weight": f"Based on your height and weight, you're likely around size {baseline_size}",
        "build_description": f"Based on your build, you're likely around size {baseline_size}",
    }[signal_used]

    message = f"{lead}; {advice}."
    if approximate:
        message += " (This is a rough estimate — your usual size would give a more accurate fit.)"
    return {"message": message, "signal_used": signal_used}


def fit_score(
    fit_notes: str,
    category: str,
    usual_size: Optional[str] = None,
    height_cm: Optional[int] = None,
    weight_kg: Optional[int] = None,
    build_description: Optional[str] = None,
) -> dict:
    """Returns a plain-language, personalized fit-confidence message for a
    product, using the best available sizing signal for this customer.

    Call this after search_catalog, using the fit_notes and category values
    from a product you want to give the customer advice about.

    This function checks signals in priority order automatically — always
    pass whatever you already know about the customer from this
    conversation, even if you're unsure it will end up being used:
      1. The customer's real order/return history for this category (no
          input needed from you — read automatically; a returned item is
          not trusted as a sizing signal).
      2. usual_size, if the customer has told you their usual clothing size.
      3. height_cm + weight_kg together, if the customer has given you both
          (mapped to a size via a general chart — meaningful for clothing
          only, not footwear).
      4. build_description, if the customer described their build instead.
      5. If none of the above is available, an honest generic message based
          on fit_notes alone, with no personal signal.

    Only ask the customer for usual_size / height+weight / build_description
    if they don't already have order history for this category and haven't
    already told you earlier in this conversation — see the system
    instruction for the order to ask in, one question at a time.

    Args:
        fit_notes: the product's fit_notes field, one of
            "runs small", "true to size", "runs large"
        category: the product's category field, e.g. "shirt", "jeans"
        usual_size: the customer's self-reported usual clothing size, one of
            "XS", "S", "M", "L", "XL", "XXL", if they've told you
        height_cm: the customer's height in centimeters, if they've told you
        weight_kg: the customer's weight in kilograms, if they've told you
        build_description: the customer's self-described build, one of
            "slim", "average", "broad", if they've told you — translate
            phrases like "clothes usually fit me loose" to "slim" and
            "clothes usually fit tight" to "broad"

    Returns:
        A dict with "message" (the text to relay to the customer, in your
        own words) and "signal_used" (which signal actually produced this
        answer: "order_history", "usual_size", "height_weight",
        "build_description", or "generic" — for your awareness, not
        necessarily to repeat to the customer verbatim).
    """
    fit_descriptions = {
        "runs small": "tends to run small",
        "true to size": "fits true to size",
        "runs large": "tends to run large",
    }
    fit_description = fit_descriptions.get(fit_notes)
    if fit_description is None:
        return {"message": "No fit information is available for this item.", "signal_used": "none"}

    # (a) Real order/return history — strongest signal, checked first no
    # matter what else was passed in. Only trust a KEPT past order as a
    # sizing signal; a returned item suggests that size guess was wrong.
    past_order = next(
        (
            o for o in CUSTOMER_PROFILE["past_orders"]
            if o["category"] == category and o["kept"]
        ),
        None,
    )
    if past_order is not None:
        return _sized_message(past_order["size_ordered"], fit_notes, fit_description, "order_history")

    # (b) Self-reported usual size.
    if usual_size and usual_size.strip().upper() in _SIZE_ORDER:
        return _sized_message(usual_size.strip().upper(), fit_notes, fit_description, "usual_size")

    # (c) Self-reported height/weight, via the general size chart — only
    # meaningful for categories that map to a tops/bottoms group.
    group = _category_group(category)
    if height_cm and weight_kg and group:
        estimated_size = _size_from_height_weight(height_cm, weight_kg, group)
        return _sized_message(estimated_size, fit_notes, fit_description, "height_weight", approximate=True)

    # (d) Qualitative build description — last-resort personal signal.
    baseline_size = _BUILD_BASELINE_SIZE.get((build_description or "").strip().lower())
    if baseline_size:
        return _sized_message(baseline_size, fit_notes, fit_description, "build_description", approximate=True)

    # (e) Generic fit_notes alone — true last resort. Honest that this is a
    # rough guess with no personal signal behind it.
    return {
        "message": (
            f"Since I don't have your sizing info yet, here's what other buyers "
            f"generally found — this item {fit_description}."
        ),
        "signal_used": "generic",
    }


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
    # Quick standalone check — one call per fallback-chain path
    print(fit_score("runs small", "shirt"))                                   # (a) order history
    print(fit_score("runs large", "jeans"))                                   # past order returned -> falls through
    print(fit_score("runs small", "kurta", usual_size="L"))                   # (b) usual size
    print(fit_score("runs large", "kurta", height_cm=182, weight_kg=90))      # (c) height/weight chart
    print(fit_score("true to size", "kurta", build_description="slim"))       # (d) build description
    print(fit_score("true to size", "kurta"))                                 # (e) generic, no signal
    print(trust_note(0.05, "4.1/5 average from 173 reviews"))
    print(trust_note(0.20, "3.6/5 average from 377 reviews"))
