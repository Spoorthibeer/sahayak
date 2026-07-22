"""
Day 2 task: the agent itself.
This is where search_catalog, fit_score, and trust_note become Gemini
"tools" — Gemini decides which ones to call, in what order, based on
what the customer asks.

Setup:
    Put GEMINI_API_KEY=your_key_here in a .env file in this directory
    (see .env.example) — it's loaded automatically via python-dotenv, no
    need to set it manually in every new terminal session.

Usage:
    python agent.py
    (then type queries; type 'quit' to exit)
"""

import os
import re
import time
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from catalog import search_catalog
from tools import fit_score, size_chart, trust_note

load_dotenv()

MODEL_NAME = "gemini-3.1-flash-lite"  # pinned exact model (was resolved from the
# "gemini-flash-lite-latest" rolling alias via response.model_version on
# 2026-07-15) — pinned so behavior can't silently shift mid-hackathon if
# Google repoints the alias to a different underlying model

SYSTEM_INSTRUCTION = """You are Sahayak, a helpful shopping assistant for Myntra
customers in Tier 2/3 India. Customers may write in Hindi, English, or a mix
of both — always reply in the same language they used.

CRITICAL: every single turn must end with real, non-empty conversational
text for the customer to read — never end a turn with only a tool call and
no message. If you call request_size_poll(), request_size_chart(),
show_comparison(), or suggest_follow_ups(), always write the actual
sentence(s) that go along with that call in the same turn (the question
you're asking, or the summary you're giving) — the tool call only adds UI
elements alongside your words, it is never a substitute for them.

When a customer describes what they're looking for, use search_catalog to
find matching products. For each relevant product you mention, also call
fit_score (using that product's fit_notes and category) and trust_note
(using its return_rate and review_summary) so you can give practical buying
advice, not just a bare list of products.

GENDER FILTER — READ CAREFULLY, this is a common mistake: the moment the
customer states their OWN gender ("I'm a woman", "as a man...") or who
they're shopping for ("for my husband", "kids' sizes"), you MUST pass
search_catalog's gender parameter ("Men", "Women", "Girls", or "Boys") on
THAT search AND every later search_catalog call for the rest of this
conversation — including follow-up searches for a different category later
on, even though they don't repeat their gender. Example: customer says
"I'm a woman, show me jackets" → call search_catalog(category="jacket",
gender="Women"). Two turns later they say "show me jeans too" (no gender
mentioned again) → still call search_catalog(category="jeans",
gender="Women"), because they already told you. Never claim in your reply
that results are filtered for a gender (e.g. "here are some women's
jeans") unless you actually passed that gender to search_catalog THIS
call — check your own tool call before writing that sentence. If a
gender-filtered search comes back empty, say so honestly (e.g. "I don't
have men's kurtas in this catalog, only women's") rather than showing an
unrelated product just to have something to show.

Whenever you call fit_score, also pass any sizing info the customer has
already told you earlier in this conversation — usual_size,
chart_matched_size, or garment_size — even if you're not sure it'll be
used. fit_score always prefers the customer's real order history over
these, so it's always safe to pass what you know.

fit_score's returned message already contains the full standard format —
an actionable, relative size recommendation, an honest confidence sentence,
and the return policy. Relay it faithfully in your own voice; you may
lightly rephrase it, but never drop the confidence phrasing or the return-
policy sentence, and never invent a different return policy.

Only ask a sizing follow-up question (see below) once the customer has
clearly settled on ONE specific product — they named it, said "that one" /
"the first one" / similar, or otherwise confirmed interest in a single
item. While they're still browsing or comparing multiple options you've
shown them, do NOT interrupt with a sizing question — just give the best
fit/trust advice you can with whatever signal is already available, and
keep helping them browse.

Once the customer HAS settled on a specific product, if fit_score's result
for it has "signal_used": "generic" (meaning it had to guess from fit_notes
alone, with no personal signal), that's your cue to gather one — in this
order, stopping as soon as they give you something usable, and asking only
ONE question at a time:
  1. Ask for their usual clothing size. When you ask this specific
     question, ALSO call request_size_poll() in the same turn (in addition
     to your normal reply text) so the interface can show tappable size
     buttons — still phrase the question naturally in your reply,
     request_size_poll() just adds the buttons alongside it. If they answer
     this, pass it to fit_score as usual_size next time.
  2. If they say they don't know their usual size, call request_size_chart()
     (passing that product's category) in the same turn as your reply, and
     ask them to look at the chart and tell you which row/size matches
     them — e.g. "no worries — here's a quick size chart, let me know which
     row matches you best." If request_size_chart() returns
     {"applicable": false}, there's no sensible chart for that category
     (e.g. footwear) — skip straight to step 3 instead. Once they tell you
     which size/row matches them, pass it to fit_score as
     chart_matched_size next time.
  3. If they say the chart doesn't help either (they're not sure of their
     height/weight, or the chart wasn't applicable), ask them to check the
     size tag on a piece of clothing they already own that fits them
     well — e.g. "no worries — check the tag on a shirt that already fits
     you well, what size does it say?" (no tool call for this one). Pass
     their answer to fit_score as garment_size next time.
Never ask a step they've already answered earlier this conversation, and
never ask more than one of these in the same reply. Only call
request_size_poll() alongside step 1's question and only call
request_size_chart() alongside step 2's question — never call either one
when you're actually asking the step-3 owned-garment question, and never
call both tools in the same turn.

STYLE PREFERENCE (ask once per conversation): the first time in this
conversation you're about to show product search results, also ask a quick
one-time style question in the same reply — e.g. "Quick one, so I can
point out better matches — do you tend to like bold, statement pieces or
subtle, understated ones?" Check the conversation history first — never
ask this again once they've answered. Once you know their preference, each
product has a style_tag field ("bold" or "subtle") from search_catalog —
when showing results afterward, softly mention/prioritize items that match
their stated preference in your phrasing (e.g. "the first one here is
bold, matching what you told me"), without hiding other good options or
forcing a mention onto every single product.

PROACTIVE BETTER-DEAL NUDGE: when search_catalog returns multiple
candidates and one is a clearly better price/rating trade-off than
another (meaningfully cheaper AND at least as well-reviewed, or notably
better-reviewed at a similar price), proactively point it out — e.g. "By
the way, this one's ₹200 cheaper and rated higher too." Only do this when
the comparison is genuinely clear-cut from the data you have; don't force
one onto every reply or invent a comparison when nothing actually stands
out — this should feel occasional and attentive, not constant.

COMPARE MODE: if the customer asks to compare two specific products
they've already seen in this conversation (including a message like
"Compare the X and the Y", which is what tapping the "Compare" button on
two different product cards sends), make sure you have that turn's
fit_score and trust_note results for both (call them again this turn if
you haven't already), then call show_comparison with both products' name,
price, fit_notes, and return_rate, in addition to a short conversational
reply summarizing the difference. Only call show_comparison when exactly
two specific already-seen products are being compared — not for a general
"what's the difference" question with no specific products named.

After a reply where you've just shown the customer product results, call
suggest_follow_ups with 2-3 short, specific next messages the customer
might actually want to tap next — genuinely based on what you just showed
them (e.g. only suggest "show cheaper options" if a realistically cheaper
option exists; suggest something about trust/fit/other sizes only if that's
relevant to what you showed). Vary these across turns based on context —
don't suggest the same three things every time.

OUTFIT COMPLETION: once the customer has settled on one specific product,
consider including ONE suggestion for a complementary category among your
suggest_follow_ups, using this mapping: shirt/t-shirt -> trousers or jeans;
kurta -> an ethnic set or ethnic bottoms; jeans/trousers -> a shirt or
t-shirt; dress -> a jacket; jacket -> jeans or a t-shirt; ethnic
set/saree/sneakers -> no natural pairing in this catalog, skip it. Only
include it when it's genuinely relevant to what they just settled on, not
every single time.

You have access to the full conversation so far — don't re-ask for details
the customer already gave you earlier in this conversation.

If the customer's request is missing an important detail (like budget or
category), ask ONE short clarifying question before searching.

Never state a specific product's name, price, fit information, trust/return
information, or stock availability unless it came directly from a
search_catalog, fit_score, or trust_note call you made earlier in this same
turn. If search_catalog returns no matching products, say so honestly instead
of inventing one.

Keep your replies short and conversational, like a helpful shopkeeper. You
may use simple markdown (**bold**, numbered or bulleted lists) where it
genuinely helps readability — the interface renders it properly and also
handles converting it for voice, so don't avoid it, but don't overuse it
either.
"""


def request_size_poll() -> dict:
    """Call this when (and only when) you are asking the customer for their
    usual clothing size, per the sizing-question rules in your
    instructions — i.e. only once they've settled on a specific product and
    you have no other sizing signal for them yet. This does not replace
    your normal reply text; still ask the question naturally in your reply.
    Calling this additionally tells the interface to show tappable size
    buttons (XS through XXL) alongside your question, so the customer can
    tap instead of typing.

    Returns:
        Confirmation that the poll was requested (for your own bookkeeping
        only — no need to mention this call to the customer).
    """
    return {"requested": True, "options": ["S", "M", "L", "XL", "XXL"]}


def request_size_chart(category: str) -> dict:
    """Call this when (and only when) you are showing the customer the
    visual size chart, per the sizing-question rules in your instructions —
    i.e. the customer just told you they don't know their usual clothing
    size, and you have no other sizing signal for them yet. This does not
    replace your normal reply text; still ask the question naturally in
    your reply (e.g. "here's a quick size chart — let me know which row
    matches you"). Calling this additionally tells the interface to render
    the chart rows as an actual table alongside your question, so the
    customer can read it and match themselves to a row instead of you
    silently computing a size from raw numbers.

    Args:
        category: the current product's category field, e.g. "shirt", "jeans"

    Returns:
        {"applicable": True, "rows": [...], "height_note": "..."} if a chart
        exists for this category, or {"applicable": False} if it doesn't
        (e.g. footwear/accessories) — in that case, don't mention a chart at
        all; go straight to asking about an owned-garment comparison instead.
    """
    chart = size_chart(category)
    if chart is None:
        return {"applicable": False}
    return {"applicable": True, "rows": chart["rows"], "height_note": chart["height_note"]}


def show_comparison(
    product_a_name: str,
    product_a_price: int,
    product_a_fit_notes: str,
    product_a_return_rate: float,
    product_b_name: str,
    product_b_price: int,
    product_b_fit_notes: str,
    product_b_return_rate: float,
) -> dict:
    """Call this when (and only when) the customer wants to compare two
    specific products they've already seen in this conversation, per the
    compare-mode rules in your instructions. Use the exact values you
    already have from this conversation's earlier search_catalog/fit_score/
    trust_note calls for each product — don't re-search or guess. This does
    not replace your normal reply text; still summarize the difference
    naturally in your reply. Calling this additionally tells the interface
    to render a real side-by-side comparison table.

    Args:
        product_a_name: the first product's name field
        product_a_price: the first product's price field
        product_a_fit_notes: the first product's fit_notes field
        product_a_return_rate: the first product's return_rate field
        product_b_name: the second product's name field
        product_b_price: the second product's price field
        product_b_fit_notes: the second product's fit_notes field
        product_b_return_rate: the second product's return_rate field
    """
    return {
        "product_a_name": product_a_name,
        "product_b_name": product_b_name,
        "rows": [
            {"label": "Price", "a": f"₹{product_a_price}", "b": f"₹{product_b_price}"},
            {"label": "Fit", "a": product_a_fit_notes, "b": product_b_fit_notes},
            {
                "label": "Return rate",
                "a": f"{round(product_a_return_rate * 100)}%",
                "b": f"{round(product_b_return_rate * 100)}%",
            },
        ],
    }


def suggest_follow_ups(suggestions: list[str]) -> dict:
    """Call this after a reply that shows the customer product results, to
    offer 2-3 short, specific, tappable follow-up messages related to what
    you just showed them. Write each one exactly as the CUSTOMER would say
    it (e.g. "Show cheaper options"), not as an instruction to yourself.
    Base these on what's actually relevant to what you just showed — don't
    suggest the same three things every time; vary them with context (e.g.
    don't suggest "cheaper options" if everything shown is already the
    cheapest available in that category).

    Args:
        suggestions: 2 to 3 short suggested next messages, each roughly
            2-6 words
    """
    return {"suggestions": suggestions}


# Rule-based language detection (no ML, matches fit_score/trust_note's style).
# Customers write Hindi and Telugu both in native script AND romanized/Latin
# script (e.g. "office ke liye shirt, budget 800 tak"), which script-only
# detection would miss — so Latin-script text also gets checked against a
# small list of common romanized markers before falling back to English.
_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
_TELUGU_SCRIPT_RE = re.compile(r"[ఀ-౿]")

_HINDI_MARKERS = {
    "ke", "ka", "ki", "hai", "chahiye", "kaisa", "kaisi", "acha", "accha",
    "paisa", "rupaye", "tak", "liye", "mujhe", "kya", "kitna", "kitne",
}
_TELUGU_MARKERS = {
    "naku", "kavali", "kosam", "bagundi", "chala", "adi", "idi", "kani",
    "cheppu", "kuda", "lo", "meeru", "nenu",
}


def detect_language(text: str) -> Optional[str]:
    """Best-effort detection of which of Sahayak's 3 supported languages
    (English, Hindi, Telugu) a customer's message is written in — including
    Hindi/Telugu written in Latin script, not just native script.

    Returns None if the message has no clear language signal at all (e.g.
    just a number like "500", or punctuation) — callers should treat that as
    "unchanged" and keep whatever language the conversation already
    established, rather than defaulting to English.
    """
    if _DEVANAGARI_RE.search(text):
        return "Hindi"
    if _TELUGU_SCRIPT_RE.search(text):
        return "Telugu"

    words = set(re.findall(r"[a-zA-Z]+", text.lower()))
    if words & _TELUGU_MARKERS:
        return "Telugu"
    if words & _HINDI_MARKERS:
        return "Hindi"
    if words:
        return "English"
    return None


def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit(
            "GEMINI_API_KEY is not set. Run: set GEMINI_API_KEY=your_key_here"
        )
    return genai.Client(api_key=api_key)


def start_chat(client):
    """Starts a Gemini chat session. Using client.chats (instead of calling
    client.models.generate_content per turn) is the SDK's built-in mechanism
    for conversation memory — it keeps a running history of user/model turns
    (including tool-call turns from automatic function calling) and resends
    it on every send_message call, so the agent doesn't forget earlier turns.
    We don't pass a fixed config here because the system instruction changes
    every turn (it embeds that turn's detected language); config is passed
    explicitly to send_message() instead, which overrides the default.
    """
    return client.chats.create(model=MODEL_NAME)


def run_agent(chat, user_message: str, language: str, max_retries: int = 3) -> str:
    turn_instruction = (
        f"{SYSTEM_INSTRUCTION}\n\n"
        f"The customer's message for this turn is in {language} "
        f"(it may be written in Latin/Roman script rather than native script). "
        f"Reply in {language}."
    )

    config = types.GenerateContentConfig(
        tools=[
            search_catalog, fit_score, trust_note,
            request_size_poll, request_size_chart, show_comparison, suggest_follow_ups,
        ],
        system_instruction=turn_instruction,
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_level="LOW"),
        # search_catalog can return 5 products, and the agent may call
        # fit_score + trust_note for each one (1 + 5*2 = 11 calls), plus up
        # to one each of request_size_poll(), request_size_chart(),
        # show_comparison(), and suggest_follow_ups() — up to 15 in the
        # worst case, still under this cap (raised from the SDK default of
        # 10, which would silently drop the final text turn —
        # response.text becomes None — instead of erroring).
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=18
        ),
    )

    delay_seconds = 2
    for attempt in range(1, max_retries + 1):
        try:
            response = chat.send_message(user_message, config=config)
            if not response.text:
                # response.text is Optional[str] — the SDK's own
                # GenerateContentResponse._get_text() returns None when the
                # final turn has no text part at all, or "" when it has one
                # but its content is an empty string (e.g. the model ended
                # a turn right after a tool call with nothing more to say).
                # Both cases are handled by app.py's /chat (falls back to a
                # reply tied to whatever needs_input/products this turn
                # produced, instead of showing a bare, unhelpful apology) —
                # this log line is what makes a recurrence of that visible
                # in the server console rather than silently swallowed.
                cand = response.candidates[0] if response.candidates else None
                print(
                    f"[warn] run_agent: response.text came back {response.text!r} "
                    f"(finish_reason={getattr(cand, 'finish_reason', None)!r})"
                )
            return response.text
        except errors.ServerError:
            # Free-tier Gemini occasionally returns 503 UNAVAILABLE under load —
            # transient and worth a short retry. Anything else (quota, auth,
            # bad request) is a real error and should propagate, not be hidden.
            # The failed attempt is never recorded into chat history, so
            # retrying just resends the same message safely.
            if attempt == max_retries:
                raise
            print(f"  (Gemini is temporarily overloaded, retrying in {delay_seconds}s...)")
            time.sleep(delay_seconds)
            delay_seconds *= 2


if __name__ == "__main__":
    client = get_client()
    chat = start_chat(client)
    session_language = None  # established once the first clear signal appears
    print("Sahayak is ready. Type your query (or 'quit' to exit).\n")

    while True:
        user_message = input("You: ").strip()
        if user_message.lower() in ("quit", "exit"):
            break
        if not user_message:
            continue

        # Only switch the session's language on a clear signal from this
        # message. An ambiguous message (e.g. just "500") has no signal —
        # detect_language returns None — so it inherits whatever language the
        # conversation already established, instead of resetting to English.
        signal = detect_language(user_message)
        session_language = signal or session_language or "English"

        try:
            reply = run_agent(chat, user_message, session_language)
        except errors.ServerError:
            print("Sahayak: Sorry, Gemini's servers are overloaded right now. Please try again in a moment.\n")
            continue
        except errors.ClientError as e:
            print(f"Sahayak: Something went wrong talking to Gemini and I can't recover automatically: {e}\n")
            continue

        print(f"Sahayak: {reply}\n")
