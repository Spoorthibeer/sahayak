"""
FastAPI backend wrapping the existing (Day 1/2, already tested) agent so it
can be driven from a browser instead of only the terminal REPL.

This file does NOT reimplement any agent logic — it imports and calls
agent.get_client(), agent.start_chat(), agent.detect_language(), and
agent.run_agent() exactly as agent.py's own REPL loop does. See CLAUDE.md
for why each of those exists.

Voice (speech-to-text / text-to-speech) uses Sarvam AI (see /transcribe and
/speak below) — purpose-built for Indian languages, with free credits and no
card required, unlike Google Cloud's billing requirement. This replaced a
Google Cloud STT/TTS integration (which itself replaced an even earlier
browser-native SpeechRecognition/SpeechSynthesis version). See CLAUDE.md for
the full history. Google Cloud credentials/code are left in place, untested,
as a fallback until this swap is confirmed working in a real browser — not
yet removed.

Usage:
    uvicorn app:app --reload
    then open http://127.0.0.1:8000 in a browser
"""

import base64
import os
import time
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from google.genai import errors
from pydantic import BaseModel
from sarvamai import SarvamAI
from sarvamai.core.api_error import ApiError

import agent

app = FastAPI(title="Sahayak")

# Same language-name -> BCP-47 mapping used for Sarvam's STT/TTS language
# codes (Sarvam uses the same BCP-47 codes Google Cloud did for these 3).
_LANG_CODES = {"English": "en-IN", "Hindi": "hi-IN", "Telugu": "te-IN"}

# Sarvam client is created lazily and reused — same reasoning as agent.py's
# Gemini client: don't pay connection/auth setup cost per request. Sarvam
# uses one client for both STT and TTS (client.speech_to_text.transcribe /
# client.text_to_speech.convert), unlike Google Cloud's two separate clients.
_sarvam_client: Optional[SarvamAI] = None


def _get_sarvam_client() -> SarvamAI:
    global _sarvam_client
    if _sarvam_client is None:
        api_key = os.environ.get("SARVAM_API_KEY")
        if not api_key:
            raise RuntimeError("SARVAM_API_KEY is not set — check .env.")
        _sarvam_client = SarvamAI(api_subscription_key=api_key)
    return _sarvam_client

# session_id -> {"chat": <google.genai Chat>, "language": Optional[str]}
# In-memory only, per CLAUDE.md's explicit call: lost on server restart.
# Acceptable, deliberate limitation for a hackathon demo — no database needed
# for the MVP. One session_id maps to exactly one long-lived Chat object, so
# Day 2's conversation-memory fix (client.chats) carries over correctly
# instead of being undone by a fresh chat per request.
_sessions: dict[str, dict] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    # Manual language override toggle (see static/index.html's language
    # badge) — when set, takes priority over agent.detect_language() for
    # this and every subsequent turn until the customer changes/clears it
    # themselves; None means "keep auto-detecting," same as before.
    lang_override: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    language: str
    products: list
    # Structured UI signals, populated only when the agent actually asked
    # for them via a tool call THIS turn (see _extract_new_turn_signals) —
    # None/absent means "nothing to show," not "the frontend should guess."
    needs_input: Optional[dict] = None
    suggestions: Optional[list] = None
    # {"product_a_name", "product_b_name", "rows": [{"label","a","b"}, ...]}
    # when the agent called show_comparison() this turn (see Compare mode).
    comparison_table: Optional[dict] = None
    # Names of products (from this turn's `products`) whose fit_score result
    # this turn used the highest-confidence signal (order_history or
    # usual_size) — see _extract_high_confidence_matches for the
    # best-effort correlation logic and its known limitation.
    match_found_products: Optional[list] = None


def _get_session(session_id: str) -> dict:
    """Returns the existing session for session_id, creating one (with a
    fresh Chat) the first time this session_id is seen. A missing or unknown
    session_id is not an error — it just starts a new conversation, which
    matches how a browser tab that lost its session_id (e.g. after a server
    restart) should behave rather than crashing.
    """
    if session_id not in _sessions:
        client = agent.get_client()
        _sessions[session_id] = {
            # Keep a strong reference to `client`, not just the Chat it
            # creates: google.genai.Client closes its underlying HTTP
            # transport in __del__ when garbage collected, and a local
            # variable that goes out of scope here is fair game for GC.
            # Without this, the first request on a session works and every
            # later one on the same session_id 500s with "Cannot send a
            # request, as the client has been closed" — found live while
            # testing this exact endpoint.
            "client": client,
            "chat": agent.start_chat(client),
            "language": None,
        }
    return _sessions[session_id]


def _extract_products(chat, history_before: int) -> list:
    """Pulls THIS turn's search_catalog results out of the chat's own
    history so the frontend can render product cards, without agent.py
    having to change what run_agent() returns. The google-genai SDK stores
    each tool's return value as {"result": <return value>} on the
    function_response part of that turn's history (see
    google.genai._extra_utils.get_function_response_parts).

    A prior version scanned the WHOLE history in reverse for the most
    recent search_catalog call from anywhere in the conversation — that
    meant the same product cards kept reappearing on every later reply,
    even ones with nothing to do with products (same class of bug already
    fixed for needs_input/suggestions via _extract_new_turn_signals; see
    CLAUDE.md). Scoping to new_history only (this turn) means products is
    genuinely empty on any turn that didn't call search_catalog.
    """
    new_history = chat.get_history(curated=True)[history_before:]
    for content in reversed(new_history):
        if not content.parts:
            continue
        for part in content.parts:
            fr = part.function_response
            if fr and fr.name == "search_catalog" and fr.response:
                return fr.response.get("result", [])
    return []


def _extract_new_turn_signals(chat, history_before: int):
    """Looks for request_size_poll()/request_size_chart()/suggest_follow_ups()
    tool calls made during THIS turn only — not anywhere earlier in the
    conversation. Unlike _extract_products() (which deliberately re-shows the
    last known search results even on turns that didn't search again), a
    stale size poll/chart or suggestion set reappearing on an unrelated later
    reply would be a real bug, not a convenience. history_before is the
    curated-history length captured just before this turn's run_agent()
    call, since chat.get_history() always covers the whole conversation.
    """
    new_history = chat.get_history(curated=True)[history_before:]
    needs_input = None
    suggestions = None
    for content in new_history:
        if not content.parts:
            continue
        for part in content.parts:
            fr = part.function_response
            if not fr or not fr.response:
                continue
            if fr.name == "request_size_poll":
                result = fr.response.get("result") or {}
                needs_input = {"type": "size_poll", "options": result.get("options", [])}
            elif fr.name == "request_size_chart":
                result = fr.response.get("result") or {}
                if result.get("applicable"):
                    needs_input = {
                        "type": "size_chart",
                        "rows": result.get("rows", []),
                        "height_note": result.get("height_note", ""),
                    }
            elif fr.name == "suggest_follow_ups":
                result = fr.response.get("result") or {}
                suggestions = result.get("suggestions")
    return needs_input, suggestions


def _extract_comparison_table(chat, history_before: int) -> Optional[dict]:
    """Looks for a show_comparison() tool call made during THIS turn only
    (see agent.py) — same turn-scoped pattern as _extract_new_turn_signals,
    kept separate since a comparison table is its own response field, not
    part of needs_input.
    """
    new_history = chat.get_history(curated=True)[history_before:]
    for content in new_history:
        if not content.parts:
            continue
        for part in content.parts:
            fr = part.function_response
            if fr and fr.name == "show_comparison" and fr.response:
                return fr.response.get("result")
    return None


# signal_used values fit_score can return that represent its two STRONGEST
# signals (real order history or a directly self-reported usual size) — see
# tools.py's fit_score docstring for the full 5-signal priority chain.
_HIGH_CONFIDENCE_SIGNALS = {"order_history", "usual_size"}


def _extract_high_confidence_matches(chat, history_before: int, products: list) -> list:
    """Best-effort correlation of this turn's high-confidence fit_score
    calls to specific products in this turn's `products` list, for the
    "Match found" animation. fit_score's signature deliberately isn't being
    changed to take a product identifier (the sizing fallback chain is out
    of scope for this pass), so there's no exact link between a fit_score
    call and which card it was about — this pairs each fit_score call with
    the function_call that immediately preceded its response (args include
    fit_notes/category) and matches that against the first not-yet-matched
    product with the same (fit_notes, category). Known limitation: if two
    shown products share identical fit_notes+category, only the first one
    is credited — documented in CLAUDE.md, not fixed here.
    """
    new_history = chat.get_history(curated=True)[history_before:]
    matched_names = []
    used_indices = set()
    pending_args = None
    for content in new_history:
        if not content.parts:
            continue
        for part in content.parts:
            fc = part.function_call
            if fc and fc.name == "fit_score":
                pending_args = fc.args or {}
                continue
            fr = part.function_response
            if fr and fr.name == "fit_score" and fr.response and pending_args is not None:
                result = fr.response.get("result") or {}
                if result.get("signal_used") in _HIGH_CONFIDENCE_SIGNALS:
                    fit_notes = pending_args.get("fit_notes")
                    category = pending_args.get("category")
                    for i, p in enumerate(products):
                        if i in used_indices:
                            continue
                        if p.get("fit_notes") == fit_notes and p.get("category") == category:
                            matched_names.append(p.get("name"))
                            used_indices.add(i)
                            break
                pending_args = None
    return matched_names


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    message = req.message.strip()
    if not message:
        return ChatResponse(reply="Please type or say something.", language="English", products=[])

    session = _get_session(req.session_id)

    if req.lang_override:
        # Manual override takes priority over auto-detection entirely,
        # every turn it's set — the customer explicitly corrected the
        # language, so detect_language() shouldn't second-guess them.
        session["language"] = req.lang_override
    else:
        # Text-based detection for every turn, voice-originated or typed — a
        # STT-authoritative variant of this was tried and reverted (see CLAUDE.md):
        # Google STT's own detected language for genuinely-Hindi audio came back
        # "en-in" in live testing (twice), which would have made voice replies
        # come back in the wrong language more often, not less. detect_language()
        # on the transcript text proved more reliable in both cases. Only switch
        # the session's established language on a clear signal; an ambiguous
        # message (e.g. just "500") inherits whatever language the conversation
        # is already in, instead of resetting to English.
        signal = agent.detect_language(message)
        session["language"] = signal or session["language"] or "English"

    # Captured before run_agent() so _extract_new_turn_signals can scope
    # itself to only what this turn added (see that function's docstring).
    history_before = len(session["chat"].get_history(curated=True))

    gemini_start = time.time()
    try:
        reply_text = agent.run_agent(session["chat"], message, session["language"])
    except errors.ServerError:
        return ChatResponse(
            reply="Sorry, Gemini's servers are overloaded right now. Please try again in a moment.",
            language=session["language"],
            products=[],
        )
    except errors.ClientError as e:
        return ChatResponse(
            reply=f"Something went wrong talking to Gemini and I can't recover automatically: {e}",
            language=session["language"],
            products=[],
        )

    print(f"[timing] /chat: agent.run_agent took {time.time() - gemini_start:.2f}s")
    products = _extract_products(session["chat"], history_before)
    needs_input, suggestions = _extract_new_turn_signals(session["chat"], history_before)
    comparison_table = _extract_comparison_table(session["chat"], history_before)
    match_found_products = _extract_high_confidence_matches(session["chat"], history_before, products)
    return ChatResponse(
        reply=reply_text,
        language=session["language"],
        products=products,
        needs_input=needs_input,
        suggestions=suggestions,
        comparison_table=comparison_table,
        match_found_products=match_found_products or None,
    )


class TranscribeResponse(BaseModel):
    text: str


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio data received.")

    # Auto-detection, not an explicit language hint: Sarvam's transcribe()
    # takes a single language_code (unlike Google STT's primary +
    # alternatives candidate list) — there's no way to hand it a closed
    # 3-language set the way the Google integration did. The choices are
    # either (a) pre-guess ONE specific language before the customer has
    # said anything, which would degrade accuracy for the other two
    # languages whenever the guess is wrong, or (b) language_code="unknown",
    # which asks Sarvam's saarika:v2.5 model to auto-detect. (b) is the
    # closer equivalent to the previous design's intent and was the only
    # reasonable choice available in this SDK, so that's what's used. This
    # doesn't reintroduce the STT-authority bug from the Google Cloud pass
    # (CLAUDE.md gotcha) — /transcribe's contract is still just "audio in,
    # text out"; the detected language is not read or trusted anywhere,
    # agent.detect_language() on the resulting text remains the sole
    # authority for the /chat turn's reply language, unchanged.
    input_audio_codec = "webm"  # matches MediaRecorder's audio/webm;codecs=opus

    stt_start = time.time()
    try:
        response = _get_sarvam_client().speech_to_text.transcribe(
            file=("recording.webm", audio_bytes, "audio/webm"),
            model="saarika:v2.5",
            language_code="unknown",
            input_audio_codec=input_audio_codec,
        )
    except ApiError as e:
        raise HTTPException(status_code=502, detail=f"Speech-to-Text request failed: {e}")
    print(f"[timing] /transcribe: Speech-to-Text call took {time.time() - stt_start:.2f}s")

    return TranscribeResponse(text=(response.transcript or "").strip())


class SpeakRequest(BaseModel):
    text: str
    lang: str


@app.post("/speak")
def speak(req: SpeakRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text to speak.")

    language_code = _LANG_CODES.get(req.lang, "en-IN")

    tts_start = time.time()
    try:
        tts_response = _get_sarvam_client().text_to_speech.convert(
            text=text,
            target_language_code=language_code,
            model="bulbul:v3",
            # "shubh" is bulbul:v3's own documented default speaker; picked
            # as the one reasonable default rather than leaving it unset,
            # so the choice is explicit and doesn't silently change if
            # Sarvam ever changes the model's default.
            speaker="shubh",
            output_audio_codec="mp3",
        )
    except ApiError as e:
        raise HTTPException(status_code=502, detail=f"Text-to-Speech request failed: {e}")
    print(f"[timing] /speak: Text-to-Speech call took {time.time() - tts_start:.2f}s")

    # Sarvam returns base64-encoded audio string(s), one per input text (we
    # only ever send one) — must be decoded before it's valid audio bytes.
    audio_bytes = base64.b64decode(tts_response.audios[0])
    return Response(content=audio_bytes, media_type="audio/mpeg")


# Landing page pass (2026-07-19): "/" now serves the new landing page
# (static/home.html) instead of the chat UI directly; the chat UI itself
# was relocated to static/assistant.html, served at "/assistant". Both are
# explicit routes rather than relying on StaticFiles(html=True)'s
# automatic "index.html at /" behavior, since we now need TWO specific
# HTML entry points instead of one. Neither page has any separate CSS/JS
# asset files (everything is inline, same single-file convention as
# before), so no asset-serving mount is needed for now — if either page
# ever gains external assets (e.g. real product photos, once a usable
# source dataset exists — see CLAUDE.md's "Product photo attempt" note),
# mount StaticFiles at a namespaced path (e.g. "/static") rather than "/",
# to avoid shadowing these two routes or the API routes above.
@app.get("/", include_in_schema=False)
def home_page():
    return FileResponse("static/home.html")


@app.get("/assistant", include_in_schema=False)
def assistant_page():
    return FileResponse("static/assistant.html")
