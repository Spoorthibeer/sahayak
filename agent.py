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
from tools import fit_score, trust_note

load_dotenv()

MODEL_NAME = "gemini-3.1-flash-lite"  # pinned exact model (was resolved from the
# "gemini-flash-lite-latest" rolling alias via response.model_version on
# 2026-07-15) — pinned so behavior can't silently shift mid-hackathon if
# Google repoints the alias to a different underlying model

SYSTEM_INSTRUCTION = """You are Sahayak, a helpful shopping assistant for Myntra
customers in Tier 2/3 India. Customers may write in Hindi, English, or a mix
of both — always reply in the same language they used.

When a customer describes what they're looking for, use search_catalog to
find matching products. For each relevant product you mention, also call
fit_score (using that product's fit_notes and category) and trust_note
(using its return_rate and review_summary) so you can give practical buying
advice, not just a bare list of products.

You have access to the full conversation so far — don't re-ask for details
the customer already gave you earlier in this conversation.

If the customer's request is missing an important detail (like budget or
category), ask ONE short clarifying question before searching.

Never state a specific product's name, price, fit information, trust/return
information, or stock availability unless it came directly from a
search_catalog, fit_score, or trust_note call you made earlier in this same
turn. If search_catalog returns no matching products, say so honestly instead
of inventing one.

Keep your replies short and conversational, like a helpful shopkeeper.
"""


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
        tools=[search_catalog, fit_score, trust_note],
        system_instruction=turn_instruction,
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_level="LOW"),
        # search_catalog can return 5 products, and the agent may call
        # fit_score + trust_note for each one (1 + 5*2 = 11 calls) — one over
        # the SDK's default cap of 10, which would silently drop the final
        # text turn (response.text becomes None) instead of erroring.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=15
        ),
    )

    delay_seconds = 2
    for attempt in range(1, max_retries + 1):
        try:
            response = chat.send_message(user_message, config=config)
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
