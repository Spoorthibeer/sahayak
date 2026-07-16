"""
FastAPI backend wrapping the existing (Day 1/2, already tested) agent so it
can be driven from a browser instead of only the terminal REPL.

This file does NOT reimplement any agent logic — it imports and calls
agent.get_client(), agent.start_chat(), agent.detect_language(), and
agent.run_agent() exactly as agent.py's own REPL loop does. See CLAUDE.md
for why each of those exists.

Voice (speech-to-text / text-to-speech) uses Google Cloud Speech-to-Text and
Text-to-Speech (see /transcribe and /speak below). This replaced an earlier
Day 3 version that used only the browser's native SpeechRecognition/
SpeechSynthesis — that was dropped because voice quality/reliability was
insufficient in live testing. See CLAUDE.md for the full history and the
GOOGLE_APPLICATION_CREDENTIALS setup this requires.

Usage:
    uvicorn app:app --reload
    then open http://127.0.0.1:8000 in a browser
"""

from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import speech, texttospeech
from google.genai import errors
from pydantic import BaseModel

import agent

app = FastAPI(title="Sahayak")

# Same language-name -> BCP-47 mapping the frontend uses for
# SpeechRecognition/SpeechSynthesis, reused here for Google Cloud STT/TTS so
# there's one single source of truth for the mapping (kept in sync manually
# with static/index.html's LANG_CODES since JS and Python can't literally
# share a constant).
_LANG_CODES = {"English": "en-IN", "Hindi": "hi-IN", "Telugu": "te-IN"}

# Google Cloud clients are created lazily and reused — same reasoning as
# agent.py's Gemini client: don't pay connection/auth setup cost per request.
_speech_client: Optional[speech.SpeechClient] = None
_tts_client: Optional[texttospeech.TextToSpeechClient] = None


def _get_speech_client() -> speech.SpeechClient:
    global _speech_client
    if _speech_client is None:
        _speech_client = speech.SpeechClient()
    return _speech_client


def _get_tts_client() -> texttospeech.TextToSpeechClient:
    global _tts_client
    if _tts_client is None:
        _tts_client = texttospeech.TextToSpeechClient()
    return _tts_client

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


class ChatResponse(BaseModel):
    reply: str
    language: str
    products: list


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


def _extract_products(chat) -> list:
    """Pulls the most recent search_catalog results out of the chat's own
    history so the frontend can render product cards, without agent.py
    having to change what run_agent() returns. The google-genai SDK stores
    each tool's return value as {"result": <return value>} on the
    function_response part of that turn's history (see
    google.genai._extra_utils.get_function_response_parts).
    """
    history = chat.get_history(curated=True)
    for content in reversed(history):
        if not content.parts:
            continue
        for part in content.parts:
            fr = part.function_response
            if fr and fr.name == "search_catalog" and fr.response:
                return fr.response.get("result", [])
    return []


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    message = req.message.strip()
    if not message:
        return ChatResponse(reply="Please type or say something.", language="English", products=[])

    session = _get_session(req.session_id)

    # Same language-persistence rule as agent.py's REPL loop: only switch the
    # session's established language on a clear signal; an ambiguous message
    # (e.g. just "500") inherits whatever language the conversation is
    # already in, instead of resetting to English.
    signal = agent.detect_language(message)
    session["language"] = signal or session["language"] or "English"

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

    products = _extract_products(session["chat"])
    return ChatResponse(reply=reply_text, language=session["language"], products=products)


class TranscribeResponse(BaseModel):
    text: str


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio data received.")

    # Explicit per-request language hints, not open-ended auto-detection:
    # Sahayak only supports English/Hindi/Telugu, so giving the recognizer a
    # closed 3-language candidate set (one primary + alternatives) is both
    # more accurate than unconstrained auto-detect across all of Google's
    # supported languages, and directly matches this product's actual scope.
    # There's no per-request language parameter from the frontend (the
    # /transcribe contract is just "audio in, text out"), so this same
    # 3-language set is used on every call rather than trying to guess a
    # hint from the still-unknown conversation state.
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        language_code="en-IN",
        alternative_language_codes=["hi-IN", "te-IN"],
    )
    recognition_audio = speech.RecognitionAudio(content=audio_bytes)

    try:
        response = _get_speech_client().recognize(config=config, audio=recognition_audio)
    except GoogleAPICallError as e:
        raise HTTPException(status_code=502, detail=f"Speech-to-Text request failed: {e}")

    if not response.results:
        return TranscribeResponse(text="")

    text = " ".join(result.alternatives[0].transcript for result in response.results)
    return TranscribeResponse(text=text.strip())


class SpeakRequest(BaseModel):
    text: str
    lang: str


@app.post("/speak")
def speak(req: SpeakRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text to speak.")

    language_code = _LANG_CODES.get(req.lang, "en-IN")
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    try:
        tts_response = _get_tts_client().synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
    except GoogleAPICallError as e:
        raise HTTPException(status_code=502, detail=f"Text-to-Speech request failed: {e}")

    return Response(content=tts_response.audio_content, media_type="audio/mpeg")


# Mounted last and at "/" so it acts as a catch-all for static files
# (index.html etc.) without shadowing the /chat route defined above.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
