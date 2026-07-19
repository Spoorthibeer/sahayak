"""
Day 2 task (refined in the sizing/fit-feature pass, see CLAUDE.md): fit-
confidence and trust-signal tools. These are simple rule-based functions (no
ML needed for the MVP) that Gemini calls after search_catalog returns
products, to give the customer practical buying advice instead of just a
bare product list.
"""

from typing import Optional

# Mock customer profile — hardcoded for the MVP demo.
# On the real app this would come from the customer's account/order history.
#
# Only past_orders is ever read silently (no need to ask the customer, same
# as a real "logged in" account). height_cm/weight_kg/usual_size/
# build_description are intentionally NOT read from here by fit_score —
# they're kept only as historical/mock-data shape from earlier passes and are
# no longer wired to any fit_score parameter at all (the sizing-refinement
# pass retired the raw height/weight and build-description signals — see
# CLAUDE.md). Sizing signals beyond order history are deliberately sourced
# fresh from the conversation each time (fit_score's own parameters) instead,
# so a genuinely new customer (no history) can still be simulated/tested.
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


# Broad category grouping for the visual size chart — "tops vs bottoms" is
# enough granularity for the MVP (don't over-engineer this). Categories not
# in either group (e.g. "sneakers") have no sensible height/weight-based
# clothing size, so the chart is just not offered for them.
_TOPS_CATEGORIES = {"shirt", "kurta", "t-shirt", "jacket", "dress", "saree", "ethnic set"}
_BOTTOMS_CATEGORIES = {"jeans", "trousers"}


def _category_group(category: str) -> Optional[str]:
    if category in _TOPS_CATEGORIES:
        return "tops"
    if category in _BOTTOMS_CATEGORIES:
        return "bottoms"
    return None


# Simple static weight -> size chart, used to BUILD the customer-facing
# visual size chart (see size_chart() below) — not to silently compute a
# size from raw numbers anymore (that was the pre-refinement design; the
# customer now sees this same data as a real table and tells us which row
# matches them, see CLAUDE.md). Weight is the primary axis; height is called
# out separately as a one-line note rather than a second table dimension,
# since it only nudges the result for notably tall frames.
_WEIGHT_SIZE_BANDS = {
    "tops": [(54, "S"), (68, "M"), (82, "L"), (96, "XL"), (999, "XXL")],
    "bottoms": [(54, "S"), (70, "M"), (85, "L"), (100, "XL"), (999, "XXL")],
}


def size_chart(category: str) -> Optional[dict]:
    """Returns structured height/weight -> size chart data for `category`,
    for showing the customer an actual visual table they can read and match
    themselves against (see agent.py's request_size_chart() tool, which
    wraps this). Returns None if the category has no sensible clothing size
    chart (e.g. footwear/accessories) — callers should treat that as "the
    chart isn't applicable here" and fall back to another signal.
    """
    group = _category_group(category)
    if not group:
        return None
    rows = []
    prev_max = 0
    for max_weight, size in _WEIGHT_SIZE_BANDS[group]:
        weight_range = f"Above {prev_max} kg" if max_weight >= 999 else f"{prev_max + 1}–{max_weight} kg"
        rows.append({"size": size, "weight_range": weight_range})
        prev_max = max_weight
    return {
        "category_group": group,
        "rows": rows,
        "height_note": "If you're taller than about 180cm, consider sizing up for length.",
    }


# Standardized output format (sizing-refinement pass): every fit_score
# message, regardless of which signal produced it, is built from the same
# three parts — (1) an actionable, relative recommendation tied to a
# reference size the customer already knows, (2) an honestly-worded
# confidence sentence that varies by signal strength, (3) a constant return-
# policy sentence, always appended. Part (3) deliberately does NOT vary with
# a product's return_rate — that's trust_note's job (see its docstring); this
# sentence is only ever about the return PROCESS itself, so it never
# contradicts a separately-stated trust caution.
_REFERENCE_PHRASES = {
    "order_history": "your usual size",
    "usual_size": "your usual size",
    "size_chart": "your size-chart match",
    "garment_comparison": "the size on that tag",
}

_CONFIDENCE_SENTENCES = {
    "order_history": "I'm fairly confident about this, since it matches what's worked for you before.",
    "usual_size": "I'm fairly confident about this, based on the size you told me.",
    "size_chart": "This is my best estimate, based on the size chart.",
    "garment_comparison": "This is my best estimate, based on comparing it to that garment.",
}

_RETURN_POLICY_SENTENCE = (
    "And if it doesn't work out, returns are easy — pickup from your home "
    "within 7 days for a full refund."
)


def _sized_message(baseline_size: str, fit_notes: str, signal_used: str, category: str) -> dict:
    reference = _REFERENCE_PHRASES[signal_used]
    if fit_notes == "runs small":
        suggested = _adjacent_size(baseline_size, 1)
        lead = f"This {category} runs small — if {reference} is {baseline_size}, size up to {suggested} for a perfect fit."
    elif fit_notes == "runs large":
        suggested = _adjacent_size(baseline_size, -1)
        lead = f"This {category} runs large — if {reference} is {baseline_size}, size down to {suggested} for a perfect fit."
    else:
        lead = f"This {category} fits true to size — if {reference} is {baseline_size}, stick with {baseline_size} for a great fit."

    message = f"{lead} {_CONFIDENCE_SENTENCES[signal_used]} {_RETURN_POLICY_SENTENCE}"
    return {"message": message, "signal_used": signal_used}


def fit_score(
    fit_notes: str,
    category: str,
    usual_size: Optional[str] = None,
    chart_matched_size: Optional[str] = None,
    garment_size: Optional[str] = None,
) -> dict:
    """Returns a plain-language, personalized fit-confidence message for a
    product, using the best available sizing signal for this customer. This
    is the core "will this actually fit me" reassurance for customers who
    can't try clothes on before buying — the message ALWAYS states an
    actionable size recommendation, an honest confidence level, and the
    return policy, no matter which signal below produced it.

    Call this after search_catalog, using the fit_notes and category values
    from a product you want to give the customer advice about.

    This function checks signals in priority order automatically — always
    pass whatever you already know about the customer from this
    conversation, even if you're unsure it will end up being used:
      1. The customer's real order/return history for this category (no
          input needed from you — read automatically; a returned item is
          not trusted as a sizing signal).
      2. usual_size, if the customer has told you their usual clothing size.
      3. chart_matched_size, if the customer has looked at the visual size
          chart (see request_size_chart()) and told you which row/size
          matches them.
      4. garment_size, if the customer checked the size tag on a piece of
          clothing they own that already fits them well and told you that
          size instead.
      5. If none of the above is available, an honest generic message based
          on fit_notes alone, with no personal signal.

    Only ask the customer for usual_size / the size chart / a garment
    comparison if they don't already have order history for this category
    and haven't already told you earlier in this conversation — see the
    system instruction for the order to ask in, one question at a time.

    Args:
        fit_notes: the product's fit_notes field, one of
            "runs small", "true to size", "runs large"
        category: the product's category field, e.g. "shirt", "jeans"
        usual_size: the customer's self-reported usual clothing size, one of
            "XS", "S", "M", "L", "XL", "XXL", if they've told you
        chart_matched_size: the size the customer identified after reading
            the visual size chart (e.g. "the M row matches me"), one of
            "XS", "S", "M", "L", "XL", "XXL", if they've told you
        garment_size: the size printed on the tag of an owned garment the
            customer said already fits them well, one of "XS", "S", "M",
            "L", "XL", "XXL", if they've told you

    Returns:
        A dict with "message" (the text to relay to the customer, in your
        own words — it already includes the confidence level and return
        policy, so don't drop those when paraphrasing) and "signal_used"
        (which signal actually produced this answer: "order_history",
        "usual_size", "size_chart", "garment_comparison", or "generic" — for
        your awareness, not necessarily to repeat to the customer verbatim).
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
        return _sized_message(past_order["size_ordered"], fit_notes, "order_history", category)

    # (b) Self-reported usual size.
    if usual_size and usual_size.strip().upper() in _SIZE_ORDER:
        return _sized_message(usual_size.strip().upper(), fit_notes, "usual_size", category)

    # (c) Visual size-chart match — the customer read the chart themselves
    # and told us which row/size fits them.
    if chart_matched_size and chart_matched_size.strip().upper() in _SIZE_ORDER:
        return _sized_message(chart_matched_size.strip().upper(), fit_notes, "size_chart", category)

    # (d) Owned-garment comparison — the size tag on something that already
    # fits them well.
    if garment_size and garment_size.strip().upper() in _SIZE_ORDER:
        return _sized_message(garment_size.strip().upper(), fit_notes, "garment_comparison", category)

    # (e) Generic fit_notes alone — true last resort. Honest that this is a
    # rough guess with no personal signal behind it. Still always includes
    # the return policy — the return-buying-wrong-thing fear applies just as
    # much here as anywhere else in the chain.
    return {
        "message": (
            f"This {category} {fit_description}, based on what other buyers generally found. "
            f"This is just a rough guess, since I don't have your sizing info yet. "
            f"{_RETURN_POLICY_SENTENCE}"
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
    print(fit_score("runs small", "shirt"))                                        # (a) order history
    print(fit_score("runs large", "jeans"))                                        # past order returned -> falls through
    print(fit_score("runs small", "kurta", usual_size="L"))                        # (b) usual size
    print(fit_score("runs large", "kurta", chart_matched_size="M"))                # (c) size chart
    print(fit_score("true to size", "kurta", garment_size="L"))                    # (d) garment comparison
    print(fit_score("true to size", "kurta"))                                      # (e) generic, no signal
    print(size_chart("kurta"))
    print(size_chart("sneakers"))                                                  # None, not a clothing category
    print(trust_note(0.05, "4.1/5 average from 173 reviews"))
    print(trust_note(0.20, "3.6/5 average from 377 reviews"))
