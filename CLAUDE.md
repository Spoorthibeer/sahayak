# CLAUDE.md

This file gives Claude Code context on the Sahayak project. Read this before
making changes — it tells you what's already done and tested, so you don't
redo completed work or reintroduce fixed bugs.

## Project overview

**Sahayak** — an AI shopping assistant for Myntra's "Build What's Next: Myntra
for Bharat" hackathon (theme: Bharat opportunity + speed and trust).

**Problem statement:** Tier 2/3 customers face three barriers Myntra hasn't
solved: language/typing friction, size/fit anxiety, and trust in product
quality/returns. Sahayak is a voice/text agent that lets customers describe
what they want in their own language, then gives them a fit-confidence score
and a trust note (based on return rate and reviews) alongside product
matches — not just a bare search result list.

**Team:** 2 people, both beginners to LLM APIs at project start.
**Deadline:** July 24, 2026, 1:00 PM IST (Myntra hackathon submission).

## Tech stack — READ THIS BEFORE SUGGESTING ALTERNATIVES

- **LLM / agent reasoning:** Gemini API (`google-genai` SDK), NOT Anthropic/Claude.
  We switched to Gemini because the team doesn't have Anthropic API budget, but
  does have free access to the Gemini Developer API.
  - **No billing enabled — free tier only, single model, by deliberate
    choice. Do not suggest enabling billing or adding a fallback model.**
  - Free tier only covers Flash/Flash-Lite models, not Pro models — this is a
    deliberate choice, not a limitation to "fix."
  - Model name is defined ONCE as `MODEL_NAME` at the top of `agent.py` —
    Gemini model names have already changed multiple times during this
    project. As of 2026-07-15, `MODEL_NAME = "gemini-3.1-flash-lite"`, pinned
    to that exact string (not a rolling alias). History: `gemini-2.5-flash`
    → deprecated for new keys → `gemini-3-flash-preview` → that model's
    20-req/day free-tier quota got exhausted during an audit pass, so we
    switched to `gemini-flash-lite-latest` (a Google-maintained rolling
    alias) to get a separate quota pool, then read `response.model_version`
    from a real call to find out it currently resolves to
    `gemini-3.1-flash-lite`, and pinned to that exact name instead of the
    alias so behavior can't silently shift if Google repoints the alias
    later. Also confirmed on this project: `gemini-2.5-flash-lite` and
    `gemini-2.5-flash` both 404 ("no longer available to new users"), and
    `gemini-2.0-flash-lite` has a hard 0 free-tier quota (never granted, not
    just exhausted). If a model-not-found or quota error occurs, check
    Google's current model list and this project's actual granted quotas
    before assuming it's a code bug — don't assume a model that's merely
    *listed* by `client.models.list()` is actually usable on this project.
- **Speech-to-text / text-to-speech: Sarvam AI** (`sarvamai` SDK,
  `SARVAM_API_KEY` in `.env`) — purpose-built for Indian languages, free
  credits with **no card required**, which directly addresses the billing
  friction that motivated switching away from it before. This is the third
  voice-provider decision in this project; do not revert to either earlier
  option without being asked — both were tried and superseded, not
  abandoned by accident.
  - **Full history:** Day 3 originally used the browser's native
    SpeechRecognition/SpeechSynthesis Web APIs (free, no card), but voice
    quality/reliability (especially Hindi/Telugu) was found insufficient in
    live testing → switched to **Google Cloud Speech-to-Text/Text-to-Speech**
    (better quality, but enabling Google Cloud APIs requires a linked
    billing account even for free-tier quota — a real, if modest,
    reintroduction of the "no billing" friction the project otherwise
    avoids) → switched again to **Sarvam AI** (2026-07-19) specifically
    because it offers free credits with no card at all, removing that
    friction while still being purpose-built for Indian-language voice
    (unlike the generic browser APIs).
  - **Google Cloud credentials/code are still present, deliberately left as
    an untested fallback** — `google-credentials.json` still exists on disk,
    `.gitignore`'s `*credentials*.json` protection is untouched, and
    `GOOGLE_APPLICATION_CREDENTIALS` was removed only from `.env.example`
    (not from the actual `.env`, which the team controls). **Do not delete
    any of this yet** — it stays until the Sarvam swap is confirmed fully
    working in a real browser. The active code path (`app.py`) no longer
    imports `google.cloud.speech`/`google.cloud.texttospeech` at all, so
    Google Cloud is currently unused-but-not-removed, not a live fallback
    the code would actually fall back to automatically.
- **Backend:** Python, FastAPI (`app.py`)
- **Frontend:** plain HTML/CSS/JS (`static/index.html`, not React — kept
  simple deliberately for a beginner team on a tight timeline), served by
  FastAPI itself as a static file — one `uvicorn app:app` command runs
  everything, no separate frontend build/dev server
- **Data:** mock catalog (JSON), no real Myntra data/API access

### Visual design system (set 2026-07-17, stay consistent with this — don't drift back to a generic look)
Established in a UI-only pass over `static/index.html` (no backend changes).
The brief was explicitly to avoid both the "cream+terracotta AI" look and the
"near-black+neon dev-tool" look, and to feel warm/trustworthy/fashion-aware
for Tier 2/3 Indian shoppers, not generic tech.
- **Color** (CSS custom properties in `static/index.html`'s `:root`):
  `--ink: #2A1F1A` (warm charcoal text, not pure black), `--paper: #FBF4EC`
  (warm ivory background, not stark white or flat AI-cream), `--rani: #A62966`
  (deep rani pink — primary brand color, user bubble, primary buttons),
  `--marigold: #D9A441` (muted gold — secondary/warm accent, "runs
  small/large" fit chips, the "agent speaking" mic state), `--trust: #1F7A5C`
  (deep teal — reserved *only* for high-confidence fit/trust signals, never
  used decoratively), `--warn: #B23A3A` (muted brick-red — reserved *only*
  for "double-check this" caution, e.g. a high return-rate trust chip).
  Three distinct hues (pink/gold/teal) doing different semantic jobs is the
  core of the palette, not just "brand color + gray."
- **Type:** "Fraunces" (a warm, editorial serif — Google Fonts) for the brand
  mark and empty-state welcome only; "Work Sans" (humanist sans, Google
  Fonts) for everything else. Deliberately not Inter/Poppins (overused,
  reads as generic AI/SaaS) and not Playfair Display (overused for
  "fashion serif"). Hindi/Telugu text is NOT forced through these Latin
  webfonts — it falls back to the browser/OS's own Devanagari/Telugu fonts,
  which render those scripts better than a bundled Latin face would; adding
  Noto Sans Devanagari/Telugu explicitly was considered and deliberately
  skipped as unnecessary complexity for this MVP.
- **Layout:** single-column chat capped at a comfortable reading width
  (`max-width: 640px`), warm branded header (brand mark + language chip),
  scrollable conversation with customer/agent turns visually distinct
  (position + color, not just bubble-grey), product results as a
  horizontally-swipeable card row beneath the relevant reply (not a
  wrapping grid — reads as a real shopping carousel and handles 1–5 results
  gracefully), fixed bottom bar pairing text entry with a circular mic
  button whose color/icon changes with exactly what's happening.
- **Signature element — the "Confidence Strip":** every product card carries
  two small colored chips — a **Fit chip** (teal "True to size" / gold "Runs
  small — size up" / gold "Runs large — size down") and a **Trust chip**
  (teal "Highly trusted" / gold "Generally trusted" / red "Double-check
  size"). This is Sahayak's actual differentiator (fit + trust alongside
  results, not a bare list) made scannable at a glance instead of buried in
  a reply paragraph. **Important implementation detail:** these chips are
  computed **client-side in JS** (`fitChip()`/`trustChip()` in
  `static/index.html`) directly from `fit_notes`/`return_rate` — fields
  already present in `/chat`'s product data — using the same thresholds
  `tools.py`'s `trust_note()` already uses (`< 0.08` highly trusted,
  `< 0.15` generally trusted, else double-check). This is a deliberately
  independent visual read of the same underlying signal, not a new backend
  capability and not a parse of Gemini's free-text reply (which would be
  unreliable) — `_extract_products()` in `app.py` was NOT touched.
- **Mic button states** (`data-state` attribute, driven by a small state
  machine in the script): `idle` (white, outline mic icon) → `listening`
  (solid rani pink, pulsing ring, mic icon) → `processing` (solid ink,
  spinning ring, no mic icon) → `speaking` (solid marigold, animated
  3-bar equalizer icon). Distinct colors for listening vs. speaking is
  deliberate and load-bearing: it's what makes barge-in visually legible —
  the customer can *see* the agent is talking, not just hear it, per the
  explicit design brief. Tapping the mic while in `speaking` state stops
  the audio and returns to idle without starting a new recording (a second,
  softer barge-in path alongside the existing "start recording always stops
  audio first" behavior).
- **Known flexbox pitfall already fixed — don't reintroduce:** `.bubble`,
  `.row`, and `.products-row` all needed explicit `min-width: 0` (plus
  `overflow-wrap: anywhere` on `.bubble`). Without it, a flex item's default
  `min-width: auto` can prevent long chat text from wrapping inside its
  `max-width: 80%` bubble, silently forcing horizontal overflow on the
  whole page. `html, body { overflow-x: hidden }` is also set as a safety
  net. Verified via Playwright at a real 375px viewport (Chrome's
  `--headless --window-size` CLI flag was tried first and found unreliable
  for viewport testing in this environment — it reported `innerWidth` as
  ~500–512px regardless of the requested size; Playwright's
  `viewport={width, height}` gave accurate, reproducible results instead).
- Empty/start state has real content (a "Namaste 👋" welcome + one sentence
  on what the app actually does + 3 tappable example prompts showing
  English/Hindi/a fit-confidence question) — not a blank box or a generic
  "Hi, how can I help you today?".
- **Verified via real screenshots** (Playwright + headless Chromium,
  installed for this verification pass only — not a runtime dependency of
  the app itself), not just code reasoning: desktop empty state, a full
  conversation with product cards and all 3 fit/trust chip color variants,
  all 4 mic states side by side, and the 375px mobile layout (bubble
  wrapping, card carousel peek, header tagline correctly hidden below the
  420px breakpoint). **Not verified — genuinely can't be, without a human
  or a real mic/speaker:** whether the color/animation choices *feel* right
  in person, real voice recording through the mic states, and real TTS
  audio playback triggering the "speaking" state end-to-end.

## What's already done and tested — DO NOT REBUILD THESE

### Day 1 (complete)
- `generate_catalog.py` — generates ~250 mock products into `data/catalog.json`
  (fields: product_id, name, category, price, occasion, region_tag, fit_notes,
  return_rate, review_summary)
- `catalog.py` — `search_catalog()` with typed parameters (category, max_price,
  min_price, occasion, region_tag — all optional), returns top 5 matches.
  Also `log_query()`, which appends every search to `data/demand_log.json` —
  this is the "regional demand capture" feature for the pitch deck, already
  working, do not remove.
- GitHub repo is live and pushed (github.com/Spoorthibeer/sahayak), `.env` is
  correctly gitignored and confirmed never committed.
- **Note (2026-07-16):** `git log` shows only 2 commits total ("Day 2
  complete..." and the initial setup commit) — `app.py` and `static/`
  (all of Day 3, including the original browser-voice version and this
  pass's Google Cloud voice version) are still untracked (`git status`
  shows `??`), despite being described as "committed" in at least one
  session. Don't assume "done" implies "committed" — check `git status`
  before relying on that.

### Day 2 (complete)
- `tools.py` — `fit_score(...)` and `trust_note(return_rate,
  review_summary)`, plain rule-based logic (no ML), plus a hardcoded mock
  `CUSTOMER_PROFILE` dict. This is intentional for the MVP — do not add a real
  ML model here unless explicitly asked.
  - **`fit_score`'s full fallback chain (2026-07-17 pass), checked inside
    the function in this priority order every call, regardless of which
    optional args were passed in:**
    1. **Order/return history** (`CUSTOMER_PROFILE["past_orders"]`) — only a
       *kept* order counts as a signal; a returned one is ignored. No input
       needed from the caller, read automatically. Original Day 2 logic,
       unchanged.
    2. **`usual_size`** (param) — the customer's self-reported usual
       clothing size (XS/S/M/L/XL/XXL).
    3. **`height_cm` + `weight_kg`** (params, both required together) —
       mapped to a size via the static `_WEIGHT_SIZE_BANDS` chart (see
       below). Skipped for categories with no tops/bottoms grouping (e.g.
       "sneakers" — a clothing height/weight chart makes no sense for
       footwear).
    4. **`build_description`** (param) — one of "slim"/"average"/"broad",
       mapped to a baseline size via `_BUILD_BASELINE_SIZE`. The system
       instruction is responsible for translating alternate phrasings
       ("clothes fit loose" → "slim", "clothes fit tight" → "broad") into
       one of these three values before calling the tool.
    5. **Generic** — `fit_notes` alone, no personal signal. Message is
       explicitly honest about this: "Since I don't have your sizing info
       yet, here's what other buyers generally found — ...".
    All paths a–d funnel through the shared `_sized_message()` helper (same
    `_adjacent_size()`/`_SIZE_ORDER` sizing-up/down logic Day 2 already had),
    which also tags the response with which signal actually fired.
  - **Return type changed from `str` to `dict`**: `{"message": ..., "signal_used":
    "order_history"|"usual_size"|"height_weight"|"build_description"|"generic"|"none"}`.
    `signal_used` exists purely for visibility (during testing, and for the
    agent's own awareness of how confident a given fit answer is) — the
    system instruction tells the agent to relay `message` in its own words,
    not necessarily repeat `signal_used` verbatim to the customer.
  - **Size chart (`_WEIGHT_SIZE_BANDS`)** — deliberately coarse, matching the
    "don't over-engineer" instruction: weight is the primary signal (bands
    per category group), height only nudges the result up one size for
    notably tall frames (≥180cm, to account for length). Two groups only —
    "tops" (shirt/kurta/t-shirt/jacket/dress/saree/ethnic set) and "bottoms"
    (jeans/trousers) — via `_category_group()`; categories in neither group
    return `None` and the chart is skipped for them.
  - **`CUSTOMER_PROFILE` gained two new keys, `usual_size` and
    `build_description`, both defaulting to `None`.** Important design
    choice: **fit_score does NOT read these two new keys (or the pre-existing
    `height_cm`/`weight_kg`) from `CUSTOMER_PROFILE` at all** — it only ever
    uses the equivalent function *parameters*, which the agent supplies from
    what the customer said earlier in the current conversation (via Gemini's
    own chat-history memory — no new session-state storage was added
    anywhere, per this pass's explicit scope). If fit_score silently fell
    back to `CUSTOMER_PROFILE`'s hardcoded values instead, every session
    would look like a customer with sizing info already on file, making it
    impossible to simulate/test a genuinely new customer with no signal —
    which is the whole point of this feature. `height_cm`/`weight_kg` in
    `CUSTOMER_PROFILE` remain present but unused by `fit_score`, same as
    they've been since Day 2 (dormant mock data, reserved for a real
    account-integration path that doesn't exist in this MVP).
  - Confirmed live (2026-07-17), one continuous conversation: "kurta for a
    wedding" (no order history) → agent asked for usual size → "I usually
    wear L, will it fit?" → fit_score used `usual_size` ("Based on the usual
    size you gave me (L)... consider sizing up to XL") → immediately after
    in the same session, "shirts under 1000 rupees" → **order history (M)
    correctly overrode the just-stated usual_size (L)**, proving priority
    order (a) beats (b) even when both are available. Separately confirmed:
    a category with no history and a customer who says they don't know
    their usual size *or* height/weight correctly cascades straight to
    asking about build ("would you say you have a slim, average, or broad
    build?") instead of silently giving up and going straight to the
    generic fallback. Also confirmed a real, sensible edge case along the
    way: asking about a saree, the agent correctly recognized sarees are
    typically free-size and skipped the sizing-question flow entirely,
    asking about budget instead — not a bug, just something to know if you
    go looking for the sizing-question flow with a saree query specifically.
- `agent.py` — the actual agent. Registers `search_catalog`, `fit_score`, and
  `trust_note` as Gemini tools via automatic function calling (plain Python
  functions with docstrings and type hints — Gemini's SDK builds the schema
  from these automatically, so keep docstrings accurate if you edit
  signatures). Includes:
  - A `SYSTEM_INSTRUCTION` that tells the agent to reply in the same language
    the user wrote in, ask one clarifying question if a request is vague, and
    always ground fit/trust claims by calling the tools rather than guessing
    (explicitly forbids stating any product-specific fact — price, fit,
    trust, availability — unless it came from a tool call made that same
    turn; if a search comes back empty, it's told to say so honestly).
    **(2026-07-17)** Also teaches the fit-signal fallback chain: always pass
    any sizing info already known from the conversation into `fit_score`
    (`usual_size`/`height_cm`/`weight_kg`/`build_description`), and if a
    `fit_score` result comes back `"signal_used": "generic"`, ask ONE
    natural follow-up — usual size first, then height/weight if they don't
    know that, then a simple build question ("slim/average/broad", or
    "does clothing usually fit loose/tight/about right") if they don't know
    that either — one question at a time, never re-asking something already
    given this conversation. See the `tools.py` bullet below for the full
    fallback chain `fit_score` itself implements.
  - `detect_language(user_message)` in `agent.py` — a rule-based (no ML)
    language detector, same style as `fit_score`/`trust_note`. Fixes a real
    bug found during audit: the model would sometimes reply in the wrong
    language (e.g. Hindi reply to an English query) when relying only on the
    general system instruction. It checks Devanagari/Telugu Unicode script
    ranges first, then falls back to a small keyword list for Hindi/Telugu
    written in Latin/Roman script (e.g. "office ke liye... budget 800 tak"),
    since customers write Indic languages both ways. `run_agent` builds a
    per-turn instruction that explicitly states the detected language back
    to the model, rather than relying on the static system instruction alone.
  - **Language persistence across a conversation:** `detect_language` returns
    `None` (not "English") when a message has no language signal at all —
    e.g. a bare number like "500", or punctuation. Found via live testing:
    without this, a mid-conversation reply to "500" after a Telugu exchange
    would drift back to English, since the old version defaulted anything
    without Hindi/Telugu markers to English. The `__main__` REPL loop now
    tracks `session_language` and only overwrites it when `detect_language`
    returns a real signal (`session_language = signal or session_language or
    "English"`) — an ambiguous message inherits the conversation's
    established language instead of resetting it. Confirmed live: a 3-turn
    Telugu conversation ("kurta kavali" → "500" → "idi bagundi") stayed in
    Telugu throughout, including on the ambiguous "500" turn.
  - **Conversation memory:** the agent used to call
    `client.models.generate_content` fresh on every turn with no history, so
    it would re-ask questions the customer had already answered. Fixed by
    switching to `client.chats` (`start_chat()` creates one
    `client.chats.create(model=MODEL_NAME)` session in `__main__`, reused for
    the whole REPL session; `run_agent` calls `chat.send_message(message,
    config=...)` instead of `client.models.generate_content`). This is the
    SDK's built-in mechanism for history — it automatically resends prior
    turns (including tool-call turns from automatic function calling) on
    every `send_message` call. `config` (which embeds that turn's detected
    language) is passed per-call rather than fixed at chat creation, since it
    changes every turn. A failed `send_message` (e.g. a transient 503) is
    never recorded into chat history, so the existing retry loop safely
    resends the same message on the next attempt. Confirmed live: a 3-turn
    conversation about a kurta search correctly remembered the category from
    turn 1 and the specific products shown in turn 2 when referenced again
    in turn 3, without re-asking anything.
  - Retry-with-backoff logic (`run_agent`'s `max_retries` loop) around
    `ServerError` (503 only — NOT `ClientError`/429 quota errors, which are
    real failures and must surface immediately, not be retried) — free-tier
    Gemini occasionally returns `503 UNAVAILABLE` under load, which is a
    transient Google-side issue, not a bug. Don't remove this retry logic;
    it's there to prevent live-demo crashes. Wait times are 2s/4s/8s;
    audited and judged reasonable for a demo (503s coincide with genuine
    multi-second backend congestion, so retrying faster wouldn't help).
  - `GenerateContentConfig` also sets `temperature=0.2` (grounded, less
    creative output) and `thinking_config=ThinkingConfig(thinking_level="LOW")`
    (this model's dial for latency vs. reasoning depth — confirmed via live
    testing that tool-selection quality holds at this level), and
    `automatic_function_calling.maximum_remote_calls=15` (raised from the
    SDK default of 10, since search_catalog can return 5 products and the
    agent may call fit_score + trust_note for each one — 1 + 5*2 = 11 calls,
    one over the default cap, which would silently drop the final text turn
    instead of erroring).
- **`.env` auto-loading:** `agent.py` now calls `load_dotenv()` (from
  `python-dotenv`, added to `requirements.txt`) at import time, so
  `GEMINI_API_KEY` loads automatically from `.env` — no more manually
  exporting the key in every new terminal session. (As of the Google Cloud
  voice pass, `GOOGLE_APPLICATION_CREDENTIALS` rides along on the same
  mechanism — see Day 3 section below.)
- Tested working end-to-end in the terminal: English, Hindi (both Devanagari
  and Latin-script), Telugu (both single-turn and a 3-turn conversation), a
  hallucination probe (non-existent category — correctly says "no stock"
  instead of inventing a product), a vague query (asks one clarifying
  question instead of guessing), multi-turn conversation memory, language
  persistence on an ambiguous mid-conversation message, and personalized
  `fit_score` output referencing the customer's actual past-order size.

### Day 3 (complete)
- `app.py` — FastAPI backend. Does NOT reimplement any agent logic; it
  imports and calls `agent.get_client()`, `agent.start_chat()`,
  `agent.detect_language()`, and `agent.run_agent()` exactly as `agent.py`'s
  own REPL loop does. `catalog.py`, `tools.py`, and agent.py's core logic
  (system instruction, retry-with-backoff, `maximum_remote_calls`, language
  detection algorithm) were NOT touched in this pass.
  - `POST /chat` — accepts `{session_id, message}`, returns `{reply,
    language, products}`.
  - **Session memory:** an in-memory `_sessions: dict[str, dict]` maps
    `session_id` → `{"client": ..., "chat": ..., "language": ...}`. One
    `session_id` (generated once per page load in the frontend, sent with
    every request) maps to exactly one long-lived `Chat` object, so Day 2's
    conversation-memory fix carries over correctly through the API instead
    of being undone by creating a fresh chat per request. In-memory only —
    lost on server restart. This is an acceptable, deliberate limitation for
    a hackathon demo, not a bug to fix.
  - **Real bug found and fixed during live testing:** `_get_session` must
    store the `genai.Client` object itself, not just the `Chat` it creates.
    `google.genai.Client` closes its underlying HTTP transport in `__del__`
    when garbage collected, and CPython refcounts immediately — so a
    `client` local variable that only the `Chat` transitively (and not
    strongly) references gets collected the moment `_get_session` returns,
    closing the transport before the first `send_message` call even runs.
    Symptom was `RuntimeError: Cannot send a request, as the client has been
    closed`, on literally the very first request to a brand-new session.
    Fixed by keeping `client` in the session dict alongside `chat`.
  - **Product info in the response:** `run_agent()` still returns only the
    reply text (unchanged, per "don't modify agent.py's core logic").
    `_extract_products()` in `app.py` instead reads the search_catalog
    results back out of `chat.get_history(curated=True)` after the call —
    the SDK stores each tool's return value as `{"result": <return value>}`
    on that turn's `function_response` part
    (`google.genai._extra_utils.get_function_response_parts`). This needed
    zero changes to `agent.py`.
  - Missing/unknown `session_id` is not an error — `_get_session` just
    starts a new conversation for it, matching what should happen if a
    browser tab's session_id predates a server restart. An empty/whitespace
    message returns a friendly reply without calling Gemini at all.
  - `requirements.txt` and `.env.example` pruned: `openai` and the abandoned
    `/transcribe` file-upload plan's original `python-multipart` dependency
    were removed in this pass (then `python-multipart` came back for real
    in the Google Cloud voice pass below, since `UploadFile` needs it).
  - **`POST /transcribe` and `POST /speak` now run on Sarvam AI, not Google
    Cloud** (switched 2026-07-19 — see "Sarvam AI voice swap" further down
    for the full writeup: exact SDK methods used, why auto-detection was
    chosen over an explicit language hint, and live test results). Request/
    response shapes are unchanged from the original Day 3 design described
    here: `/transcribe` still takes an uploaded audio file and returns
    `{text}`; `/speak` still takes `{text, lang}` and returns raw playable
    audio bytes — this swap only changed which provider answers those
    contracts, not the contracts themselves, so `static/index.html` needed
    zero changes for this pass.
  - The Sarvam client (`SarvamAI(api_subscription_key=...)`) is created
    lazily and cached at module level (`_sarvam_client`), same reasoning as
    reusing the Gemini client — one client handles both STT and TTS here,
    unlike Google Cloud's two separate clients.
- `static/index.html` — single-file frontend (inline CSS/JS, no build step,
  no framework), served by FastAPI via `app.mount("/",
  StaticFiles(directory="static", html=True))`. That mount is registered
  AFTER the `/chat` route in `app.py` so it acts as a catch-all without
  shadowing it. **Visually redesigned 2026-07-17 — see "Visual design
  system" under Tech stack above for the color/type/layout/signature-element
  plan this file now follows; that pass didn't touch request/response
  shapes, so everything below in this section still holds functionally.**
  - Chat window (message bubbles + product cards), text input, mic button,
    language badge — unchanged in the Google Cloud voice switch.
  - `session_id` generated once per page load (`crypto.randomUUID()`) and
    sent with every `/chat` request — unchanged.
  - **Voice input:** `MediaRecorder` records audio (prefers
    `audio/webm;codecs=opus`, matching `/transcribe`'s `WEBM_OPUS` config),
    POSTs the recorded blob to `/transcribe` on stop, then feeds the
    returned text into the exact same `sendMessage()` used by the text
    input. Browser-native `SpeechRecognition` was removed entirely — this
    replaced it, it doesn't coexist with it.
  - **Voice output:** after every `/chat` reply, the frontend POSTs
    `{text, lang}` to `/speak`, plays the returned MP3 via a `new
    Audio(...)`. Browser-native `SpeechSynthesis` was removed entirely.
  - **Matching voice language:** unchanged in spirit from the browser-native
    version — the frontend still doesn't detect language itself, it just
    forwards whatever language name `/chat` already returned. The BCP-47
    mapping moved server-side into `app.py`'s `_LANG_CODES` (see above)
    since `/speak` needed it anyway; the frontend has no language-code
    mapping left at all.
  - **Barge-in:** tapping the mic to start a new recording immediately stops
    any currently-playing agent reply audio (`stopCurrentAudio()`, called at
    the very start of `startRecording()` — before even requesting mic
    permission, so it can't be delayed by a slow permission prompt). A
    single `currentAudio` variable tracks the live `Audio` element; this is
    an intentional UX feature (a customer should never have to wait for the
    agent to finish talking before speaking again), not a corner case to
    "fix" later. **(2026-07-18)** This originally only covered the mic —
    see "Barge-in gap fix" further down for the fix that made every other
    input path (card buttons, suggestion chips, size poll, typed text) also
    interrupt playback, via a single `stopCurrentAudio()` call at the top of
    `sendMessage()` instead of scattered per-trigger calls.
  - **NOT verified in this pass — needs a real Chrome browser with a real
    microphone, not the sandboxed dev environment this was built in:**
    mic permission flow, actual recorded audio quality reaching
    `/transcribe`, Hindi/Telugu recognition accuracy, TTS voice quality, and
    the barge-in interrupt specifically (stopping playback the instant
    recording starts). What WAS verified live (see below): the real
    `/speak` endpoint end-to-end, and Speech-to-Text transcription +
    language-hint accuracy via a direct client call using the exact same
    `/transcribe` config (encoding swapped to MP3 only because no real
    browser-recorded WEBM/Opus audio was available to test with).

### Day 4 (in progress)
**Note:** this header was previously missing from this file (the doc jumped
from Day 3 straight into dated sub-passes below, leaving "Start the Myntra
pitch deck" orphaned at the end with no parent heading) — restored
2026-07-19 while updating this file for the Sarvam voice swap. All of the
dated sub-passes below (voice latency hardening, markdown/behavior/
interactive-UI, barge-in gap fix, Sarvam AI voice swap) are Day 4 work.

#### Voice latency/accuracy hardening pass (2026-07-17, complete)
- **Auto-stop on silence (voice activity detection)** — `static/index.html`.
  Recording used to require a manual second tap to stop; now it stops itself
  once the customer has finished talking, via the Web Audio API's
  `AnalyserNode` reading the mic stream's time-domain waveform and computing
  a normalized RMS level every animation frame:
  - `SILENCE_THRESHOLD = 0.02` (RMS on a -1..1 scale) — a conservative
    default meant to catch quieter speech while rejecting typical room
    noise/mic hiss. **Not device-calibrated** — this is a starting point,
    not a value verified against a real microphone (couldn't be, in this
    sandboxed pass); expect it may need tuning after real browser testing.
  - `SILENCE_DURATION_MS = 1200` — the silence countdown only starts after
    real speech has been heard at least once (`hasDetectedSpeech`), so it
    won't fire while the customer is still gathering their thoughts before
    speaking. 1200ms balances tolerating a natural mid-sentence pause
    against not adding needless dead air after they're actually done.
  - Manual stop (tapping the mic again) still works and completely bypasses
    the VAD logic — kept deliberately, in case auto-detection misfires
    (quiet mic, noisy room, etc.), per explicit instruction.
  - **Could not be verified in this pass at all** — needs a real browser,
    real mic, and a real human pausing mid-sentence to judge whether the
    threshold/duration actually feel right. Flagged, not claimed as tested.
- **Speech-to-Text model:** `/transcribe`'s `RecognitionConfig` now sets
  `model="latest_short"` (tuned for short queries/commands vs. long-form
  dictation — matches Sahayak's actual query shape, e.g. "shirt under 800
  for office"). Confirmed live this doesn't error for the
  `en-IN`/`hi-IN`/`te-IN` candidate set used in `alternative_language_codes`
  (Google restricts some models to specific languages, so this was worth
  checking rather than assuming — Telugu specifically wasn't separately
  live-tested, only inferred from the shared code path).
- **Language-authority attempt — tried, found to make things worse, reverted.**
  The plan was: for voice turns, trust Google STT's own detected language
  (`SpeechRecognitionResult.language_code`, from the `alternative_language_codes`
  candidate set) outright as the turn's reply language, instead of re-running
  `agent.detect_language()` on the transcript. **Live-tested twice with
  genuinely-Hindi phrases (synthesized by Google's own Hindi TTS voice,
  reading proper Devanagari text) — both times, Google STT's own
  `language_code` came back `en-in` (English), even though the transcript it
  produced ("Mujhe Office ke liye ek acchi shirt chahie") is unambiguously
  Hindi and contains words `agent.py`'s `detect_language()` already catches
  correctly (`mujhe`, `ke`).** Confirmed the concrete consequence by feeding
  that STT-detected language into `/chat`: it produced an English reply to a
  clearly Hindi request — the opposite of the intended fix. This appears to
  be a real, reproducible pattern (not a fluke): Google STT seems to
  associate its own Latin-script transcription of code-switched Hindi with
  `en-IN` rather than `hi-IN`. **Decision (confirmed with the team after
  presenting this evidence): reverted entirely.** `detect_language()` on the
  transcript text remains authoritative for voice-originated turns too, same
  as typed text — there is no STT-language-based override anywhere in the
  code. If STT-authority is revisited later, do not re-attempt it as "STT
  wins outright" without a live test against real Hindi/Telugu content
  first — that exact framing already failed twice.
- **Latency measurement added**, per the framing "don't just assume, measure
  it": `app.py` prints server-side timing for the three external API calls
  (`[timing] /chat: agent.run_agent took Xs`, `/transcribe: Speech-to-Text
  call took Xs`, `/speak: Text-to-Speech call took Xs`) — visible in the
  `uvicorn` terminal. `static/index.html` logs client-observed round-trip
  timings to the browser console for the same three legs
  (`recording stop -> /transcribe response`, `/chat request -> reply`,
  `/speak request -> audio returned`) — console-only, not surfaced in the
  UI itself, to avoid cluttering a UI that's supposed to look intentional.
  **Numbers actually measured (2026-07-17, via direct API calls — no real
  browser/mic involved, see caveats above):**
  - `/speak` (Text-to-Speech): ~0.5–0.6s, almost entirely the Google API
    call itself (0.56s of a 0.58s round trip) — local/network overhead is
    negligible on localhost.
  - Speech-to-Text (direct client call, `model="latest_short"`, same config
    `/transcribe` uses): ~2.1–2.3s per call. This is the slowest of the
    three legs measured — worth keeping in mind as the main latency
    contributor on the voice path, more than either Gemini or TTS in these
    tests.
  - `/chat` (`agent.run_agent`, Gemini): ~1.8s in this pass's test (a single
    short vague query). Prior passes measured this ranging much higher
    (several seconds to 30s+) under free-tier congestion — see the
    "Gemini model deprecation"/"429" gotchas above; this number is not a
    reliable ceiling, just what was observed in this one test.

#### Markdown/behavior/interactive-UI pass (2026-07-17, complete)
Scope: `agent.py`'s system instruction + two new tools, `app.py`'s response
shape (`needs_input`/`suggestions` fields), and `static/index.html`. Did NOT
touch `catalog.py`, `tools.py`'s fallback chain, or the `/chat`/`/transcribe`/
`/speak` request contracts — only additive response fields.

- **Markdown bug, fixed both directions.** The agent has always been allowed
  to use `**bold**` and lists (nothing in the system instruction forbade it),
  but the UI showed literal asterisks and `/speak` read them aloud as
  "asterisk asterisk". Two independent client-side fixes in
  `static/index.html`, no backend change:
  - `renderMarkdown(text)` — escapes HTML first (XSS safety, verified with a
    `<script>` injection test), then converts `**bold**` → `<strong>`,
    `*italic*` → `<em>`, and numbered/bulleted lines → `<ol>`/`<ul>`. Used
    only for `role === "assistant"` bubbles in `addRow()`; user-typed
    messages still render as plain `textContent`, unaffected.
  - `stripMarkdownForSpeech(text)` — removes all markdown syntax before the
    text is sent to `/speak`. Applied in `sendMessage()`'s success path;
    `/speak`'s request contract is unchanged, this only changes what string
    the frontend chooses to send it.
  - **Real bug found via live testing, not anticipated in the design:**
    Gemini's actual output pattern for multi-product replies is a numbered
    top-level item immediately followed by *indented bullet sub-items* (fit
    detail, trust detail) — e.g. `1. **Product A**` then two indented `*`
    lines, then `2. **Product B**`. That interrupts simple "consecutive
    lines" list-tracking into separate `<ol>` fragments, and HTML restarts
    numbering at 1 for each fragment — so product 2 would have displayed as
    "1." again instead of "2.". Fixed by capturing Gemini's own number from
    the regex and rendering `<li value="N">`, which forces the correct
    displayed number regardless of how many times the list gets fragmented.
    Confirmed fixed against the actual real Gemini response that exposed it
    (see live-test results below), not just a hand-written test case.
  - Confirmed live against 3 different real Gemini replies: no raw
    asterisks ever reach the stripped/spoken text, newlines are preserved
    (`\n`, confirmed via a clean JSON round-trip — an earlier test showing
    stray `\r` characters was traced to a Windows text-mode file artifact in
    the *test methodology*, not real Gemini output or a real code bug).
- **Sizing-question timing fixed.** `SYSTEM_INSTRUCTION` in `agent.py` now
  explicitly gates the whole "ask for usual size / height+weight / build"
  flow behind the customer having clearly settled on ONE specific product
  (named it, said "that one"/"the first one", etc.) — while they're still
  browsing/comparing multiple shown options, the agent gives the best
  fit/trust advice available but does not interrupt with a sizing question.
  Confirmed live: "kurta for a wedding" (2 options shown, browsing) →
  `needs_input: null`; next turn "I'll take the first one" (product
  confirmed) → agent asked for usual size AND `needs_input` was correctly
  populated. Separately confirmed a fresh browsing-only turn (5 jeans
  options shown, none confirmed) also correctly got `needs_input: null`.
- **New tools in `agent.py`** (registered in `run_agent`'s `tools=[...]`
  list alongside the existing four; `tools.py`/`catalog.py` untouched):
  - `request_size_poll()` — zero-arg. The system instruction tells the agent
    to call this exactly when (and only when) it's asking for usual size per
    the timing gate above. Returns a fixed `{"options": ["S","M","L","XL","XXL"]}`
    — matches the task's example set exactly (no XS shortcut on the poll
    buttons, though a customer typing "XS" manually still works fine via the
    existing fallback chain, which accepts any `_SIZE_ORDER` value).
  - `suggest_follow_ups(suggestions: list[str])` — the system instruction
    tells the agent to call this after any reply that shows product results,
    with 2-3 short messages phrased as the customer would say them, varied
    by actual context rather than fixed. Confirmed live across two different
    conversations (kurta vs. jeans) that the suggestions were genuinely
    different and referenced the specific products/prices just shown, not
    templated boilerplate.
  - Both follow the existing `fit_score`/`trust_note` convention: plain
    function, clear docstring, type-hinted params. `maximum_remote_calls`
    stayed at 15 (worst case is now ~13: 1 search + 5×2 fit/trust + 1 size
    poll + 1 suggestions — still under the cap).
- **`app.py` response shape extended, not rewritten:** `ChatResponse` gained
  `needs_input: Optional[dict]` and `suggestions: Optional[list]`, both
  `None` by default. New `_extract_new_turn_signals(chat, history_before)`
  helper (separate function, `_extract_products()` deliberately left
  untouched) reads `request_size_poll`/`suggest_follow_ups` tool-call results
  back out of chat history — same pattern `_extract_products()` already
  uses. **Important difference from `_extract_products()`:** it's scoped to
  *this turn only*, via a `history_before = len(chat.get_history(curated=True))`
  length captured just before `run_agent()` is called. Unlike products
  (which deliberately keep showing the last known results on turns that
  didn't search again), a stale size-poll or suggestion set reappearing on
  an unrelated later reply would be a real bug, not a convenience — confirmed
  live that `suggestions` correctly came back `null` on the size-poll turn
  (which showed no new products), not stale suggestions from the prior turn.
- **Frontend interactive elements, all consistent with the existing design
  system** (chip/pill styling, rani/marigold/teal palette) — see screenshots
  taken via Playwright during this pass, not just code review:
  - **Size poll:** `addSizePoll(needsInput)` renders `.size-poll-btn` square
    buttons (rani-outlined) when `needs_input.type === "size_poll"`; tapping
    one calls `sendMessage(size)` directly, same pipeline as typed/spoken
    input.
  - **Suggestion chips:** `addSuggestions(suggestions)` renders
    `.suggestion-chip` pills; tapping sends that exact text.
  - **Per-card quick actions:** every product card now has "Tell me more" /
    "Check another size" buttons (`.card-action-btn`), wired via a single
    delegated click listener on `.products-row` (not one closure per
    button) reading `card.dataset.productName`, sending "Tell me more about
    the {name}" / "Do you have the {name} in a different size?" — pure
    frontend, no backend involvement, same mechanism as suggestion chips
    just scoped to one product.
  - **Star rating:** `parseRating()`/`starsHTML()` parse the rating out of
    `review_summary` (already-present field, e.g. "4.1/5 average from 173
    reviews") and render a 5-star SVG row with a linear-gradient fill
    proportional to the rating (a continuous fill rather than discrete
    full/half/empty steps — simpler to implement correctly for any decimal
    rating, visually reads the same). No backend change.
  - **Live voice waveform:** replaces the static listening mic icon with
    `.waveform-bars` (5 bars), updated every animation frame by
    `updateWaveformBars(dataArray)` — called from inside the *existing*
    `tick()` loop in `startVoiceActivityDetection()`, reading the *same*
    `dataArray`/`analyser.getByteTimeDomainData()` call already used for
    silence detection. No second `AnalyserNode`, per the explicit
    instruction — just a second read of different array indices from the
    one buffer already being populated each frame.
  - **Transcription confirmation:** after `/transcribe` returns text,
    `showTranscriptionConfirmation()` prefills the text input and shows
    "You said: '...' — sending shortly (tap to edit)" via the existing hint
    element, auto-sending after `TRANSCRIPTION_CONFIRM_MS = 1800`ms unless
    the customer taps the hint or starts typing (either cancels the pending
    timer via `clearTranscriptionTimer()`). Reuses the hint element rather
    than a new modal, per "lightweight, not blocking."
- **NOT verified in this pass — needs a real browser/mic/eyes, not this
  sandboxed environment:** whether the live waveform actually looks good
  reacting to a real voice in real time, whether 1800ms is the right
  auto-send delay in practice (too fast to read, too slow to feel snappy?),
  and the general feel of tapping/editing the size poll, suggestion chips,
  and card actions on a real touchscreen.

#### Barge-in gap fix (2026-07-18, complete)
**Bug found in live testing:** tapping a suggestion chip, size-poll button,
or product-card quick action while the agent's previous reply was still
playing did NOT interrupt that audio — it kept playing alongside the new
request. Root cause: `stopCurrentAudio()` was only ever called from two
mic-specific places (`startRecording()`, and the "tap mic while speaking"
branch of the mic click handler) — every *other* way of sending a message
skipped it entirely.
- **Fix:** `stopCurrentAudio()` now runs as the first line of `sendMessage()`
  in `static/index.html`, right after the empty-message guard. Every input
  path — send button, Enter key, empty-state example chips, product-card
  quick actions, suggestion chips, size-poll taps, and voice (via
  `showTranscriptionConfirmation()`'s auto-send) — funnels through this one
  function, so this single call now covers all of them structurally, not
  just the reported cases.
- **The two existing mic-specific calls were kept, not removed** — they are
  not actually redundant with the new one: both fire *earlier* than
  `sendMessage()` ever could in the voice flow (at the moment the mic is
  tapped, well before recording finishes and transcription completes), and
  the "tap mic while speaking" branch doesn't call `sendMessage()` at all in
  that interaction. Removing either would reintroduce a multi-second gap
  between tapping the mic and audio actually stopping. This was verified by
  tracing the actual control flow, not assumed.
- **Verified functionally, not just read**, via a Playwright test that spied
  on a fake `Audio`-like object's `pause()` method (swapped in for
  `currentAudio` through a test-only hook, scratch copy only, not shipped):
  clicking a real suggestion chip, a real size-poll button, a real
  product-card action button, and the real send button all correctly
  triggered the stop *before* the (expected-to-fail, no server in this
  static-file test) `/chat` fetch fired. No live Gemini/STT/TTS calls were
  needed for this fix — pure frontend control-flow, confirmed with a mocked
  audio object.
#### Sarvam AI voice swap (2026-07-19, complete)
Scope: `app.py`'s `/transcribe` and `/speak` implementations only, plus
`requirements.txt`/`.env.example`. Did NOT touch `agent.py`, `catalog.py`,
`tools.py`, the `/chat` endpoint, the interactive UI features, or the
barge-in fix. Request/response shapes for `/transcribe` (file in, `{text}`
out) and `/speak` (`{text, lang}` in, raw audio bytes out) are byte-for-byte
unchanged, so `static/index.html` needed zero changes.

- **Why:** addresses the Google Cloud billing friction noted above — Sarvam
  offers free credits with no card required, and is purpose-built for
  Indian-language voice specifically (vs. Google Cloud's general-purpose
  STT/TTS or the browser's generic Web Speech APIs).
- **SDK inspected directly before writing any integration code** (per
  explicit instruction — not relying on possibly-stale docs/memory):
  `pip install sarvamai` (0.1.28), then `inspect.signature()`/
  `inspect.getdoc()` on the actual installed client. Confirmed:
  `client.text_to_speech.convert(...)` and
  `client.speech_to_text.transcribe(...)` are the real current method
  names (matching the task's reference pattern), `SarvamAI(api_subscription_key=...)`
  is the correct constructor kwarg (not `api_key`), and all of Sarvam's
  documented error classes (`BadRequestError`, `TooManyRequestsError`, etc.)
  share one common base, `sarvamai.core.api_error.ApiError` — so a single
  `except ApiError` clause covers all of them, same pattern as
  `GoogleAPICallError` before.
- **`/speak`:** calls `text_to_speech.convert(text=..., target_language_code=...,
  model="bulbul:v3", speaker="shubh", output_audio_codec="mp3")`.
  - `target_language_code` uses the exact same BCP-47 codes as before
    (`en-IN`/`hi-IN`/`te-IN` — `_LANG_CODES` mapping unchanged).
  - `speaker="shubh"` — bulbul:v3's own documented default, picked as "the
    one reasonable default" per the task, made explicit rather than left
    unset so the choice doesn't silently change if Sarvam ever changes the
    model's default. Other v3 speakers exist (aditya, ritu, priya, neha,
    and ~25 more) if a different voice is wanted later — not evaluated.
  - **Important response-handling detail:** Sarvam returns
    `TextToSpeechResponse.audios: List[str]` — **base64-encoded** audio
    strings (one per input text; always exactly one here), not raw bytes.
    Must `base64.b64decode(response.audios[0])` before returning — this is
    a real difference from Google Cloud's `synthesize_speech()`, which
    returned raw bytes directly in `.audio_content`. Missing this decode
    step would have shipped a broken (undecoded, unplayable) audio
    response with no error to catch it, since decoding-then-serving invalid
    bytes doesn't raise anything by itself. Caught by inspecting the
    response model's source before writing the integration, not by trial
    and error.
  - `output_audio_codec="mp3"` keeps the `Response(..., media_type="audio/mpeg")`
    unchanged in `app.py`, so the frontend's `new Audio(url)` playback
    needed no changes.
- **`/transcribe`:** calls `speech_to_text.transcribe(file=(filename, bytes,
  "audio/webm"), model="saarika:v2.5", language_code="unknown",
  input_audio_codec="webm")`.
  - **Auto-detection, not an explicit hint — and why:** Sarvam's
    `transcribe()` takes one `language_code`, not a Google-style primary +
    alternatives candidate list. With no way to give a closed 3-language
    hint set, the real choice was between pre-guessing ONE language before
    the customer has said anything (degrades accuracy whenever the guess is
    wrong) or `language_code="unknown"` (asks `saarika:v2.5` to
    auto-detect). The latter was used — the closer equivalent to the
    previous design's intent, and the only reasonable option this SDK
    actually offers.
  - **This does NOT reintroduce the STT-authority bug from the Google Cloud
    pass** (see the "Don't trust STT's own language_code" gotcha below):
    `/transcribe`'s contract is still just "audio in, text out" — the
    `response.language_code`/`response.language_probability` fields Sarvam
    also returns are not read or trusted anywhere in this integration.
    `agent.detect_language()` on the resulting transcript text remains the
    sole authority for the `/chat` turn's reply language, completely
    unchanged.
  - `input_audio_codec="webm"` matches what `MediaRecorder` actually
    produces in the browser (`audio/webm;codecs=opus`) — same reasoning as
    the Google Cloud config it replaced.
- **Google Cloud fallback:** `google-credentials.json`,
  `GOOGLE_APPLICATION_CREDENTIALS`'s `.gitignore` protection, and the
  Google Cloud packages are all still present on disk/in `.gitignore` —
  deliberately not removed yet, per explicit instruction, until this swap
  is confirmed working in a real browser. `requirements.txt` no longer
  lists `google-cloud-speech`/`google-cloud-texttospeech` (the code doesn't
  import them anymore), and `.env.example` no longer lists
  `GOOGLE_APPLICATION_CREDENTIALS` — but the actual `.env` file, the
  credentials JSON, and the `.gitignore` entry are untouched.
- **Verified live (4 of a 5-call budget; 1 held in reserve):**
  - `/speak` via the real HTTP endpoint, English: valid MP3 (confirmed via
    frame-sync magic bytes), 2.72s round trip (2.70s of which was the
    Sarvam API call itself — comparable to Google Cloud TTS's ~0.5–0.6s
    but noticeably slower in this one sample; not enough data points to
    call this a reliable comparison).
  - `/speak` via the real HTTP endpoint, Hindi: valid MP3, 1.74s round trip.
  - Speech-to-Text round-trip (direct client call, `input_audio_codec="mp3"`
    since no real browser-recorded WEBM/Opus audio was available to test
    with, same caveat as the Google Cloud pass): fed each of the above MP3s
    back in. **English:** "A cotton kurta under 900 rupees, true to size
    and highly trusted." → transcribed back as "A cotton kurta under ₹900,
    true to size and highly trusted." — correctly normalized the spoken
    number into ₹-prefixed digits. **Hindi:** "मुझे ऑफिस के लिए नौ सौ
    रुपये में एक अच्छी शर्ट चाहिए" → transcribed back as "मुझे ऑफिस के
    लिए ₹900 में एक अच्छी शर्ट चाहिए।" — same correct number
    normalization. Both correctly auto-detected (`language_code` came back
    `en-IN` and `hi-IN` respectively). `language_probability` came back
    `None` both times despite the docstring saying it should populate
    when `language_code="unknown"` — a real discrepancy from documented
    behavior, harmless here since nothing reads that field, but worth
    knowing if a future pass ever wants to use it.
  - **Voice quality/naturalness:** cannot be genuinely judged without
    listening — no audio playback capability here, only binary/metadata
    inspection. The near-perfect STT round-trip fidelity (including
    correct number normalization surviving TTS→STT twice) is indirect
    evidence the TTS output is clearly intelligible and well-formed, but
    says nothing about subjective warmth/naturalness — that's a real
    browser/human-ears judgment call, not made here.
- **NOT verified — needs the team, in a real browser:** actual Hindi/Telugu
  voice quality and naturalness by ear, Telugu specifically (not tested at
  all in this pass — English and Hindi only, to stay within budget),
  latency as it actually feels end-to-end through the UI (not just via
  direct API timing), and a full voice round trip through the real mic →
  `/transcribe` → `/chat` → `/speak` → playback flow.

#### Sizing fallback-chain refinement pass (2026-07-19, complete)
Scope: `tools.py`'s `fit_score` fallback chain and `agent.py`'s related
system instruction, plus the minimum necessary `app.py`/`static/index.html`
changes to surface the new visual size chart as real structured data (same
precedent as `request_size_poll()`/`needs_input`). Did NOT touch
`catalog.py`, memory/session handling, or the `/transcribe`/`/speak` voice
endpoints.

This is the project's core value proposition — helping Tier 2/3 customers,
who often can't try clothes on, choose the right size with confidence. The
old chain worked but silently computed a size from raw height/weight and had
no standardized way of stating confidence or the return policy. Refined to:

- **New 5-step priority chain in `fit_score`** (checked in this order,
  first match wins):
  1. `order_history` — unchanged, read silently from `CUSTOMER_PROFILE`,
     never asked about.
  2. `usual_size` — unchanged, self-reported.
  3. `chart_matched_size` **(new)** — the customer read the visual size
     chart themselves and told the agent which row/size matches them.
  4. `garment_size` **(new)** — the customer checked the tag on an owned
     garment that already fits them well.
  5. Generic `fit_notes`-only fallback — unchanged, true last resort.
  - **Retired:** the old silent `height_cm`/`weight_kg` chart computation
    and the `build_description` ("slim"/"average"/"broad") signal are both
    gone as `fit_score` parameters — the customer now sees the same
    underlying weight-band data as an actual table (`tools.size_chart()`)
    and self-selects, rather than the backend guessing from raw numbers
    behind the scenes. `CUSTOMER_PROFILE`'s `height_cm`/`weight_kg`/
    `build_description` keys are left in place (dormant mock-data shape,
    already documented as unread by `fit_score`) — harmless, not cleaned up
    since that wasn't in scope.
- **Visual size chart mechanism:** `tools.size_chart(category)` builds
  weight-range → size rows from the existing `_WEIGHT_SIZE_BANDS` data (now
  repurposed to generate a customer-facing table instead of a silent
  computation), returning `None` for non-clothing categories (e.g.
  footwear). `agent.py`'s new `request_size_chart(category)` tool wraps it
  as a Gemini-callable tool, registered alongside the existing tools.
  `app.py`'s `_extract_new_turn_signals` now also recognizes
  `request_size_chart` calls, populating `needs_input = {"type":
  "size_chart", "rows": [...], "height_note": "..."}` (sibling of the
  existing `"size_poll"` type, same turn-scoped extraction pattern — no new
  top-level response field). `static/index.html` renders this as an actual
  `<table>` (`addSizeChart()`, next to `addSizePoll()`), styled with the
  existing design tokens; tapping a row sends `"The {size} row matches me"`
  through the same `sendMessage()` pipeline as everything else, so the
  customer can either read-and-type or read-and-tap.
- **Standardized output format**, same structure every time regardless of
  which signal fired (`tools._sized_message()`): (1) an actionable
  recommendation in relative terms tied to a reference the customer already
  gave — e.g. *"This kurta runs small — if your size-chart match is M, size
  up to L for a perfect fit."*; (2) an honestly-worded confidence sentence
  that varies by signal (`_CONFIDENCE_SENTENCES` — "fairly confident" for
  order-history/usual-size, "best estimate" for chart/garment-comparison,
  "just a rough guess" for the generic fallback); (3) a constant return-
  policy sentence (`_RETURN_POLICY_SENTENCE`), always appended, in every
  path including the generic one. This sentence is deliberately a fixed,
  return_rate-independent statement about the return *process* itself
  (pickup within 7 days, full refund) — kept structurally separate from
  `trust_note`'s return_rate-based trust caution, per explicit instruction,
  so it never contradicts a product's actual return-rate signal (it doesn't
  claim anything about *this* product's likelihood of being returned, only
  about what happens if the customer does return it).
- **AR try-on: explicitly out of scope, roadmap idea only** — not built,
  not attempted. If picked up later, it would need a genuinely different
  approach (camera/image-based), not an extension of this rule-based
  fallback chain.
- **Verified live (5 of a 5-call budget — fully used, none held in
  reserve):**
  - Fresh kurta session, browsing (no order history): generic signal fired
    for both shown products, each message included the return-policy
    sentence (e.g. *"If it doesn't fit, returns are easy—we'll pick it up
    from your home within 7 days for a full refund"*).
  - Customer confirmed a product and said they didn't know their usual
    size: agent called `request_size_chart()`; `/chat`'s `needs_input` came
    back as real structured data (`type: "size_chart"`, 5 rows, height
    note) matching `tools.size_chart("kurta")` exactly.
  - Customer replied "I think the M row matches me best":
    `chart_matched_size="M"` was used correctly — reply recommended sizing
    up to L (kurta runs small), framed as "my best recommendation" (best-
    estimate confidence), with the return-policy sentence appended.
  - Fresh jeans session, browsing (no history): generic signal + return
    policy again, confirming the return-policy statement appears
    consistently across a **second, distinct confidence tier** (generic vs.
    chart-based) — used generic+chart rather than order-history+generic
    for this check, to conserve the 5-call budget; both are equally valid
    "different confidence levels" per the task's own "e.g."
  - Customer confirmed a product and declined BOTH usual size AND the
    chart in one message: agent correctly pivoted straight to the step-3
    owned-garment question ("check the tag on a pair of jeans... that fits
    you well").
  - **Rough edge found, not re-verified (out of budget):** on that last
    turn, the agent's reply text correctly asked the garment-tag question,
    but it *also* called `request_size_poll()` (stale/incorrect — that tool
    is only meant for step 1's usual-size question), so `needs_input` came
    back as `size_poll` (tappable S–XXL buttons) next to a question that
    was actually about a garment tag, not a usual size. Mitigated by adding
    an explicit instruction ("only call request_size_poll() alongside step
    1... never when asking the step-3 owned-garment question... never call
    both tools in the same turn") but this fix itself has **not** been
    re-tested live — worth a quick manual check before relying on it.
  - Not tested live at all (budget spent before reaching it): a customer
    actually answering the owned-garment question and `garment_size`
    flowing through to a real message — only the *asking* behavior was
    confirmed, not the full round trip.
- **NOT verified — needs the team, in a real browser:** how the size-chart
  table actually looks/reads at real viewport sizes and with real user
  interaction (only confirmed via Playwright with a mocked `/chat` response
  and via the live terminal/JSON responses above, not by eye in an actual
  browser window); whether the standardized output's tone ("best estimate",
  "just a rough guess", the return-policy sentence) reads as natural and
  reassuring rather than repetitive across many turns in a row; the full
  garment-comparison round trip end-to-end; and the `request_size_poll()`
  mitigation above.

#### Bug fix + engagement/polish pass (2026-07-19, complete)
Scope: fixed a real turn-scoping bug in `app.py`, then added 10 engagement/
polish features across `generate_catalog.py`, `agent.py` (system
instruction + 1 new tool), `app.py` (2 new response fields + extraction
logic), and `static/index.html` (frontend-only for most of the 10). Did
NOT touch `catalog.py`'s search logic, `tools.py`/the sizing fallback
chain, or the `/transcribe`/`/speak` voice endpoints. Did NOT build any
cross-page-load session persistence ("continue where you left off" was
explicitly out of scope) — every "session-scoped" feature below resets on
a fresh page load, by design.

**Bug fix — `products` turn-scoping (`app.py`):** `_extract_products` used
to scan the *entire* chat history in reverse for the last `search_catalog`
result, so the same product cards kept reappearing on every later reply,
even ones with nothing to do with products — the same class of bug already
fixed for `needs_input`/`suggestions` in an earlier pass. Fixed by scoping
the scan to `chat.get_history(curated=True)[history_before:]` (this turn
only), matching `_extract_new_turn_signals`'s existing pattern exactly.
**Verified live:** turn 1 ("shirt for office") → 3 products; turn 2 ("I
like bold styles") → 0 products; turn 3 (unrelated return-policy question)
→ 0 products; turn 4 (new kurta search) → 5 products again. Confirms it
toggles correctly both ways, not just "goes empty once."

**1. Style preference — prompt-level only, zero new code paths beyond the
system instruction.** `generate_catalog.py` now assigns a random
`style_tag` ("bold"/"subtle") per product; `catalog.json` was regenerated
so the field actually exists in the live data (search_catalog needed no
changes — it already returns full product dicts). The system instruction
tells the agent to ask a one-time style question the first time it's about
to show results in a new conversation, never re-ask (checking conversation
history), and softly reference the stated preference in phrasing
afterward. Deliberately relies on Gemini's own conversation memory rather
than a new stored session field — "session state" here is the existing
`_sessions[session_id]` → persistent `Chat` object, same mechanism
`usual_size`/`chart_matched_size` already rely on for the sizing chain.
**Verified live:** first shirt query asked the style question in the same
reply as showing results; "I like bold styles" was acknowledged; a later,
unrelated kurta search did NOT re-ask, and opened with "Since you prefer
bold styles, I've highlighted those first" — bold kurtas were listed
before subtle ones (a nice bonus the model did on its own; not enforced by
any sorting code).

**2. Proactive better-deal nudge — prompt-level only.** Instruction tells
the agent to point out a clearly-better price/rating trade-off when one
exists among shown results, occasionally, not every reply. **Verified live
(bonus — fired naturally during the style-preference test above, so no
extra budget spent):** "By the way, this one's ₹200 cheaper than the
formal shirt below and has a higher rating too!" and again later, "₹300
cheaper... and has a higher rating too!" — both accurate against the
actual shown prices/ratings.

**3. Compare mode.** New `agent.py` tool `show_comparison(product_a_name,
product_a_price, product_a_fit_notes, product_a_return_rate,
product_b_*...)` — Gemini already has both products' data in context from
this conversation's own earlier `search_catalog`/`fit_score`/`trust_note`
calls, so the tool is purely a structured-output signal (same pattern as
`request_size_poll`), not new catalog-lookup logic. `app.py`'s new
`_extract_comparison_table` (same turn-scoped pattern as the others)
populates a new `comparison_table` response field:
`{"product_a_name", "product_b_name", "rows": [{"label","a","b"}, ...]}`.
Frontend: a "Compare" button added to each product card's actions;
`static/index.html`'s `handleCompareTap()` tracks up to one pending
selection (module-level `compareSelection` array, tapping a 2nd distinct
product fires `sendMessage("Compare the X and the Y")`; tapping the same
product again deselects), and `addComparisonTable()` renders a real
`<table>`. **Verified live:** "Compare the first one and the second one"
against 5 shown kurtas correctly produced a table for exactly the first
two (Embroidered Kurta ₹499/runs small/14% vs. Festive Silk Kurta
₹699/true to size/25%), matching their actual catalog data.

**4. Outfit completion suggestions — prompt-level only,** folded into the
existing `suggest_follow_ups` mechanism: instruction includes a literal
category-pairing table (shirt/t-shirt→trousers/jeans, kurta→ethnic
set/bottoms, jeans/trousers→shirt/t-shirt, dress→jacket,
jacket→jeans/t-shirt, ethnic set/saree/sneakers→skip) and tells the agent
to include one such suggestion once the customer settles on a product,
when relevant. **NOT tested live** (skipped per explicit permission to
conserve budget) — flagged for manual testing.

**5. Onboarding hint.** A small tooltip (`#onboarding-hint`, absolutely
positioned above the mic button) shows on every fresh page load and is
dismissed (`dismissOnboardingHint()`) on the first `sendMessage()` or
`startRecording()` call, then never reappears that session. Note: "first
visit" here genuinely means "this page load," not "this browser, ever" —
cross-reload persistence was explicitly out of scope this pass, so it
*will* show again on every refresh; that's by design, not a bug.
**Verified via Playwright screenshot:** visible on load, hidden
immediately after sending a message.

**6. Recently-viewed strip.** `#recently-viewed`, a persistent row between
the chat window and the footer, updated by `updateRecentlyViewed()` after
every reply — accumulates every product shown this session (deduplicated
by name, module-level array, resets on reload). Tapping a chip sends "Tell
me more about the {name}". **Verified via Playwright:** populates
correctly with name+price chips after products are shown; tap sends the
right message.

**7. Wishlist heart icon.** Purely visual — a heart button on each
product-image, toggled via a CSS class (`.wishlist-btn.active`) on click,
no backend call, no persistence. **Verified via Playwright:** toggles the
active/filled state on click.

**8. Manual language override toggle.** Tapping the language badge
(`#lang-badge`) cycles English → Hindi → Telugu → auto-detect → ...; while
an override is set, every `/chat` request includes `lang_override`, and
`app.py`'s `/chat` uses it directly instead of calling
`agent.detect_language()`, every turn, until changed again. **Verified via
Playwright:** cycling changes the badge text and applies/removes a
`.manual` visual style; the request body carries `lang_override` correctly
(confirmed via a mocked-route request-body capture). **Known minor rough
edge:** if the toggle is cycled back to "auto" without any real `/chat`
response arriving in between (i.e., rapid clicking with no message sent),
the badge text doesn't reset — it keeps showing the last manually-picked
language even though the mode is back to auto — cosmetic only (the actual
`lang_override: null` behavior sent to the backend is correct either way);
not fixed this pass.

**9. "Match found" animation.** `app.py`'s new
`_extract_high_confidence_matches` best-effort-correlates this turn's
`fit_score` calls with `signal_used` in `{"order_history", "usual_size"}`
back to a specific shown product, by pairing each `fit_score`
`function_call`'s args (`fit_notes`, `category`) with the next unmatched
product sharing those same two fields — populates a new
`match_found_products` response field (list of names). **fit_score's own
signature was deliberately NOT changed** to take a product identifier (the
sizing fallback chain is out of scope this pass), so this is a heuristic,
not an exact link — **known limitation:** if two shown products share
identical `fit_notes`+`category`, only the first unmatched one gets
credited. Frontend: matched cards get a brief pulse-ring animation
(`.match-found`, 2×0.9s) and a badge that fades in/out over ~2.6s
(`.match-found-badge`, "✨ Great fit match"). **Verified:** the
frontend mechanism was confirmed correct via Playwright with mocked
`match_found_products` data (card gets the class, badge appears). **NOT
conclusively verified against a real response**: the one live check made
for this feature happened to land on a turn where the agent referenced an
earlier product without a fresh `search_catalog` call (so `products` was
empty that turn, correctly per the bug fix — meaning there was no card
to animate anyway, matching but not proving the intended-positive case),
and the 6-call budget was already spent by then. Worth a manual re-check:
search for something, let the order-history/usual-size signal fire on a
freshly-shown card, and confirm the pulse/badge actually appears in a real
browser.

**10. Perceived-wait improvement.** `addTypingIndicator()` now rotates
through `["Looking through options...", "Checking fit and trust...",
"Almost there..."]` every 1.35s (`.typing-text`, alongside the existing
bouncing dots) instead of a static indicator; `removeTypingIndicator()`
clears the interval before removing the row (avoids a leaked timer if the
reply arrives mid-cycle). Purely a perceived-performance change — no
attempt to reduce actual Gemini/Sarvam latency. **Verified:** direct
mechanism test (bypassing the network) confirmed the text cycles through
all three messages at the correct ~1.35s cadence.

**AR try-on remains a roadmap-only idea** (unchanged from the sizing pass
— still not built, not attempted).

**NOT verified — needs the team, in a real browser:** the onboarding
hint's positioning relative to the example chips at very small viewport
widths (looked slightly close together in one Playwright screenshot);
outfit-completion suggestions (not live-tested, prompt-level only); the
match-found animation against a genuine real-time positive case (see #9
above); and the general feel of having this many simultaneous UI elements
(recently-viewed strip + suggestions + size poll/chart + comparison table)
on screen together in a long real conversation — not exercised in
combination here.

#### Product icons + wishlist panel + TTS text-cleanup pass (2026-07-19, complete)
Scope: `static/index.html` only (frontend markup/CSS/JS) — no backend
changes at all this pass. Did NOT touch `agent.py`'s core logic,
`catalog.py`, `tools.py`'s sizing fallback chain, or the `/transcribe`/
`/speak` endpoint *implementations* in `app.py` (the TTS fix only changes
what text the frontend chooses to send to the existing `/speak` contract,
same pattern as the original markdown-stripping fix).

**1. Product icons — local static SVGs, deliberately no external image
URLs.** Categories were confirmed by actually reading `data/catalog.json`
(not assumed from `generate_catalog.py`): `dress`, `ethnic set`, `jacket`,
`jeans`, `kurta`, `saree`, `shirt`, `sneakers`, `t-shirt`, `trousers` — 10
categories, matching the generator's list exactly at the time of writing,
but confirmed from the live data per the explicit instruction to do so.
`CATEGORY_ICONS` in `static/index.html` maps each to a small hand-drawn
line-art SVG (viewBox `0 0 48 48`, two shared CSS classes:
`.icon-fill` — solid white silhouette with a `--rani-dark` stroke — and
`.icon-line` — a thinner accent detail like a collar notch, side slit, or
shoe laces). `GENERIC_ICON` (a hanger) is the fallback for any category not
in the map, so a future/unexpected category degrades gracefully instead of
showing nothing. `categoryIconSVG(category)` picks the right one, called
from the card-builder in place of the old single hardcoded hanger icon
every card used to show regardless of category. `.product-image` changed
from a fixed 100px-tall rectangle to `aspect-ratio: 1/1` (a real square
thumbnail) and the icon itself renders at 58% of that square (up from a
34px icon in a much bigger box before) — both changes needed so the icon
reads with "photo-like" visual weight instead of a small decorative glyph,
per the brief. **No network fetch involved anywhere** — every icon is
inline SVG markup embedded directly in the page's own JS, so a flaky
demo-day connection can't produce a broken-image icon.
- **Verified via Playwright:** all 10 real categories plus one deliberately
  fake category (`"totally-new-category"`) rendered a card with a
  `.product-image svg` present — confirms both real-category mapping and
  the generic fallback work, screenshot confirmed the shirt/kurta icons
  read cleanly and consistently with the existing warm palette.

**2. Wishlist panel.** The heart icon (already visual-only from an earlier
pass) now feeds a real, visible client-side state: `wishlist` (a
module-level array of full product objects, session-scoped only, no
backend call — matches the same scope as compare-selection/recently-viewed
state already in this file). A new heart-outline button in the header
(`#wishlist-toggle-btn`, with a small count badge) opens a slide-in drawer
(`#wishlist-panel`, `.open` class + CSS transform, plus a dismissable
`#wishlist-backdrop`). The panel renders each wishlisted product using the
**same card-builder function** the search-results row uses
(`buildProductCardEl(p, opts)` — the product-card markup, including this
pass's new category icons, was refactored out of `addProducts()` into this
one shared function specifically so the panel can reuse it verbatim
instead of duplicating markup that could drift), just without the
"Tell me more/Check another size/Compare" quick actions (`opts.showActions
= false`) since those aren't relevant to reviewing a saved list. Un-hearting
works both from the original product card AND from within the panel —
either one calls the same `toggleWishlistItem()`, which updates the
`wishlist` array and then re-syncs every `.wishlist-btn` on the page whose
card matches that product name (so a product shown in more than one place —
an earlier turn's card, a later turn's card, the panel itself — never gets
out of sync with the others). Each card now also carries its full product
data in `card.dataset.product` (JSON-stringified) specifically so the
heart-click handler and the panel have the data they need without a second
lookup mechanism.
- **Verified via Playwright:** hearting 2 cards showed a badge count of 2;
  opening the panel showed exactly those 2 products, correctly using the
  card style with hearts pre-filled and no quick-action buttons; un-hearting
  from inside the panel dropped the badge to 1, removed that card from the
  panel, AND correctly un-filled the heart on the original card back in the
  chat thread; closing via the backdrop worked (a narrow-viewport test
  first needed the click target moved off-panel, since the panel visually
  covers most of a ~430px-wide viewport — a test-methodology fix, not an
  app bug).

**3. TTS text-cleanup extension.** `stripMarkdownForSpeech()` (the same
function already responsible for stripping `**bold**`/list markers before
a reply is sent to `/speak` — untouched from the original markdown pass)
gained two more rules, applied only to the text sent for speech, never to
the visible chat bubble (`renderMarkdown()`/`addRow()` are completely
unaffected):
  - `\([^()]*\)` and `\[[^\[\]]*\]` remove any parenthetical/bracketed
    aside entirely — asides aren't meant to be read aloud.
  - `(\d)\s*-\s*(\d)/g` → `"$1 to $2"` converts a number-hyphen-number
    pattern to the word "to" (e.g. "300-400" → "300 to 400", "₹300-400" →
    "₹300 to 400" — the regex only touches the matched digit-hyphen-digit
    span, so the rupee sign and surrounding digits are untouched).
  - Two small follow-up cleanup rules were added after live-testing
    surfaced a cosmetic artifact: removing a bracketed aside can leave a
    stray double space or a space directly before punctuation (e.g. "...a
    different size ]." → "...a different size ."), so `/ {2,}/g → " "` and
    `/ +([.,!?])/g → "$1"` tidy that up. Deliberately does NOT touch
    newlines (`\n`) at all — those are still preserved for pacing between
    lines/list items, same as before this pass.
- **Verified live** (2 of a 3-call budget): a mocked `/chat` reply
  containing both a bracketed aside and a price range —
  `"This kurta (a customer favorite) runs small... priced at ₹300-400
  [ask if you need help choosing a size], and most buyers say it fits
  great for the 25-30 age group."` — was sent through the real frontend
  pipeline; the text actually POSTed to the real `/speak` endpoint (and
  confirmed via server logs / a direct re-POST) came out as *"This kurta
  runs small, so consider sizing up. It's priced at ₹300 to 400, and most
  buyers say it fits great for the 25 to 30 age group."* — both asides
  gone, both number ranges (price AND the unrelated age range, confirming
  the rule generalizes beyond just prices) converted correctly, and the
  real Sarvam call returned a valid, non-empty MP3 (confirmed via its
  frame-sync magic bytes) — 140KB of real audio, not just a 200 status.
  Voice *naturalness* still can't be judged without listening (same
  standing limitation as every prior voice-related pass).
- **NOT verified — needs the team, in a real browser:** whether the
  spoken result actually sounds natural by ear (only the text transformation
  and successful audio generation were confirmed here, not subjective
  quality); the icon set's appearance at a wider desktop viewport and on a
  real device; and the wishlist panel's feel/usability on a real
  touchscreen (only confirmed functionally via Playwright, not by eye in a
  real browser window).

#### Landing page + routing pass (2026-07-19, complete)
Scope: purely structural/frontend — a new `static/home.html`, the existing
chat UI relocated from `static/index.html` to `static/assistant.html`
(content preserved, plus one small additive change — see below), and
`app.py`'s static-file routing. Did NOT touch `agent.py`, `catalog.py`,
`tools.py`, or the `/chat`/`/transcribe`/`/speak` route *implementations*
at all. No live API calls were needed or made this pass — verified
entirely via Playwright screenshots/functional checks against mocked
`/chat` responses.

- **Routing (`app.py`):** the old blanket `app.mount("/", StaticFiles(...),
  html=True)` (which served `index.html` automatically at `/`) is gone,
  replaced with two explicit routes: `GET /` → `FileResponse("static/
  home.html")`, `GET /assistant` → `FileResponse("static/assistant.html")`.
  Neither page has separate CSS/JS asset files (both are still fully
  self-contained, inline-everything single files, matching this project's
  established convention), so no asset-serving mount is needed for now —
  a comment in `app.py` notes that if either page ever gains external
  assets, `StaticFiles` should be mounted at a namespaced path like
  `/static` rather than `/`, so it can't shadow these two routes or the
  `/chat`/`/transcribe`/`/speak` API routes above them.
- **`static/assistant.html`** is `index.html` relocated via `git mv`
  (history preserved) — every existing feature (voice, size poll/chart,
  wishlist panel, product icons, compare mode, suggestions, language
  toggle, etc.) is untouched and confirmed still working (see verification
  below). **One small additive change, invited explicitly by this pass's
  brief ("reasonable to include... if simple to add")**: the header's
  brand mark (`Sahayak` + tagline) is now wrapped in `<a href="/">` instead
  of a plain `<div>`, so tapping it returns to the new landing page — this
  adds a link, it doesn't modify any existing behavior, element, or
  script.
- **`static/home.html`** — new landing page, reusing this project's
  established design system (see "Visual design system" above) rather
  than any new palette/type, and deliberately not referencing Myntra's
  actual logo or trademarked assets:
  - **Nav bar:** white background, `sahayak` wordmark in Fraunces
    (lowercase styling, per the approved brief, distinct from the
    assistant page's own capitalized "Sahayak" brand mark, which is
    unchanged), three nav links (Home/Shirts/Kurtas/Jeans) that route to
    `/` and `/assistant` respectively — **not wired to pre-fill a
    category-specific starting prompt in the assistant**, since doing so
    would require adding query-param handling to `assistant.html`'s JS,
    which conflicts with this pass's explicit "preserve exactly as-is"
    instruction for that file; documented here as a deliberate scope
    decision, not an oversight. A wishlist heart and a bag icon sit on the
    far right (the heart icon reuses the exact SVG path already used
    elsewhere in the app for visual consistency; the bag icon is new,
    generic e-commerce iconography, not a trademarked shape) — both
    currently link to `/assistant` (there's no separate cart/wishlist
    backend for a standalone landing page to talk to; the wishlist itself
    lives in `assistant.html`'s own client-side state).
  - **Hero:** soft warm gradient background
    (`--paper` → `--rani-soft` → `--marigold-soft`, all existing tokens —
    not a new color), left side has the eyebrow line, Fraunces headline,
    supporting copy, and an `Ask Sahayak` pill CTA linking to `/assistant`;
    right side has a large square-ish (`aspect-ratio: 4/5`) featured panel
    with a soft drop shadow. **Designed for a real photo to drop in
    later:** the panel currently centers a large category-icon SVG
    (kurta), but the intended future swap is dropping an `<img
    class="hero-product-photo">` into the exact same `.hero-visual-panel`
    element — that CSS class already sizes/shapes/shadows the box and
    constrains `.hero-product-photo`/the placeholder svg to the same
    46%-of-box sizing rule, so no restructuring will be needed, just
    replacing the one child element. Below the panel: 3 smaller variant
    tiles (shirt/jeans/dress icons) and a row of pagination dots (purely
    decorative, matching a product-carousel-indicator convention).
  - **Icon duplication, deliberate:** `home.html` embeds its own copies of
    a few category-icon SVG paths (kurta/shirt/jeans/dress, taken directly
    from `assistant.html`'s `CATEGORY_ICONS`) rather than sharing a JS
    module between the two pages — consistent with this project's
    explicit "single self-contained file, no build step" convention
    (see the tech-stack section's reasoning for avoiding a framework).
    This is a small, known duplication tradeoff, not an oversight.
  - **Floating assistant launcher:** fixed bottom-right circular button
    (`--rani` background, existing mic-icon SVG path reused from
    `assistant.html`), with a soft pulse ring
    (`launcherPulse` keyframe — same restrained, non-garish style as the
    existing match-found animation's pulse). Links directly to
    `/assistant`.
  - **Responsive:** `.hero-inner` switches from a row to a stacked column
    below 860px width (text first, centered, then the visual below); nav
    links hide below 640px (wordmark + icons remain); further padding/size
    reductions below 420px, consistent with the assistant page's existing
    breakpoint conventions.
- **Verified via Playwright (no live API calls, per this pass's explicit
  scope):**
  - Desktop (1280px): nav links visible, hero laid out as a row, floating
    launcher visible — screenshot confirms nav/hero/tiles/dots/launcher
    all render as designed, warm on-brand gradient, no loud colors.
  - Mobile (375px): nav links correctly hidden, hero confirmed via
    computed style to switch to `flex-direction: column` (text stacks
    above the visual, both centered), launcher's bounding box confirmed
    fully inside the 375px viewport, and `document.documentElement.
    scrollWidth` confirmed exactly 375 (no horizontal overflow introduced)
    — screenshot shows a clean stacked mobile layout.
  - `/assistant` still fully functional: mic button, empty-state welcome,
    and (via a mocked `/chat` response) the full existing pipeline —
    product card with its category icon — all confirmed rendering
    correctly, unchanged from before this pass. The new brand-mark home
    link was clicked and confirmed to navigate back to `/`.
- **NOT verified — needs the team, in a real browser:** the actual tap
  interaction on a real touchscreen (only simulated via Playwright's
  `.click()`); whether the nav links/icons linking to `/assistant` (rather
  than doing something more elaborate) feels right in practice; and the
  overall look-and-feel/emotional read of the hero and floating launcher
  in person, on a real device, alongside real product photography once
  that exists (the current icon placeholder is explicitly a stand-in, not
  a final visual).

#### Product photo attempt (2026-07-19, ATTEMPTED AND REVERTED — superseded, see below)
**Superseded 2026-07-22** — a working, verified photo set (`data/real_photos/`)
was obtained and successfully integrated; see the "Real product photos"
passes further below. This section is kept as-is for the historical record
of what was tried against the *first* (broken) dataset and why — the
`data/myntra_dataset/` problem described here was never fixed, it was
sidestepped entirely with a different, pre-verified photo set.

A pass to replace the SVG category icons with real photos, sourced from a
downloaded Myntra dataset (`data/myntra_dataset/Fashion Dataset.csv` +
`Images/`), was attempted and then **fully reverted** after discovering
the local copy of the dataset is internally inconsistent. Nothing shipped
from this attempt — `static/assistant.html`, `app.py`, and
`data/catalog.json` are all back to exactly their pre-attempt state (only
`.gitignore` keeps one small, harmless addition — see below). If this is
retried later, **do not repeat the matching work without first confirming
the dataset problem below is actually fixed.**

- **What was built (then removed):** `match_product_images.py` (a
  one-time script: parse the CSV, detect each row's category from its
  `name` field — `p_attributes`' "Top Type"/"Bottom Type" fields turned
  out to only be populated on ~8% of rows, almost all kurta-style, so a
  `name`-keyword search was the real primary signal — copy a matched
  photo per category into `static/images/`, write `image_path` onto each
  catalog product), plus the corresponding `app.py` `/static` mount and
  `assistant.html` render-real-photo-with-icon-fallback logic. All of this
  worked *mechanically* — the code ran, files copied, fields populated —
  but the underlying data it was working from turned out to be broken.
- **The actual problem — confirmed with concrete evidence, not assumed:**
  `Images/{index}.jpg` files do **not** correspond to their claimed CSV
  rows. Checked directly (opened the images, compared to that row's own
  `name` field): row 0 ("...Kurta with Palazzos...") → image shows an
  unrelated yellow polka-dot skirt; row 2 ("...Kurta with Trousers...") →
  a navy/pink polka-dot pleated skirt (kids'); row 11 ("...Straight
  Kurta") → purple velvet harem pants; row 1980 ("...Jeans") → a
  multicolor saree. Two possible explanations were checked and ruled out
  as the (sole) cause:
  - The CSV's own unnamed index column genuinely does restart partway
    through the file (physical row 990 has index-value "0" again, 991 has
    "1", etc. — a classic symptom of two dataframes having been
    concatenated without `ignore_index=True`). Real, but doesn't explain
    the failures above, since rows 0/2/11 are all *before* that
    duplication starts, where physical position and index value already
    agree.
  - `p_id` as the actual filename key instead — checked directly, no file
    is named after any of these rows' `p_id` either.
  - Net conclusion: the specific downloaded copy of this dataset has its
    `Images/` folder out of sync with its CSV, for reasons not fully
    diagnosed (most likely how this particular redistributed copy was
    packaged) — not something fixable by better category-matching logic,
    since the row-to-image correspondence itself doesn't hold.
- **Explicitly confirmed with the team before reverting** (not assumed):
  presented the mismatch evidence and asked how to proceed; the team chose
  to stop and revert rather than ship mismatched photos or investigate
  further right now.
- **What's needed to retry this:** a working copy of the dataset where
  `Images/{index}.jpg` actually depicts CSV row `{index}`'s product — e.g.
  a fresh download, or a version where the index/image correspondence has
  been independently verified. Once that exists, `match_product_images.py`
  can be rewritten from scratch (the old one isn't kept, to avoid a stale
  script silently being re-run against bad data) — its category-detection
  logic (name-keyword matching, the ethnic-set-if-Top-Type-is-actually-
  ethnic-AND-Bottom-Type-present rule) is the reusable part; the row-index
  assumption is the part that needs re-verifying first, with the same kind
  of direct "open a few images and compare to their row" check done here
  — spot-checking a handful of images against their claimed rows takes a
  few minutes and would have caught this before any code was written.
- **One small, deliberate keeper from this attempt:** `.gitignore` now
  excludes `data/myntra_dataset/` (the raw downloaded dataset — 14,000+
  images) so it can never be accidentally committed, regardless of when or
  whether real photos are attempted again. This is harmless on its own
  and was kept rather than reverted.
- The SVG icon fallback (`CATEGORY_ICONS`/`categoryIconSVG()` in
  `static/assistant.html`) remains exactly as it was — every product card
  and the landing page hero still show icons, unchanged by this attempt.

#### Real product photos — sourced, assigned, and wired up end-to-end (2026-07-22, complete)
Three separate passes, done in this order — data source → data assignment
→ serving/rendering — each verified before moving to the next, given the
earlier attempt's lesson about not trusting a photo dataset blindly.

- **Source (`data/real_photos/` + `manifest.json`, provided directly by
  the team, not sourced/scraped by Claude this time):** 222 real Myntra
  product photos across 16 categories (`shirt`, `t-shirt`, `jeans`,
  `kurta`, `saree`, `dress`, `trousers`, `jacket`, `sneakers`,
  `ethnic set`, plus 6 extra categories our catalog doesn't use — `top`,
  `sweater`, `sweatshirt`, `tunic`, `skirt`, `shorts` — harmlessly present
  but never referenced). `manifest.json` maps each category to a list of
  `{source_id, filename, name, colour, gender, usage}` entries; filenames
  are `{category}_{source_id}.jpg`. **Unlike the previous dataset, this one
  was spot-checked before being trusted** — opened 3 images across 3
  different categories (`shirt_15970.jpg`, `kurta_20099.jpg`,
  `saree_59607.jpg`) and confirmed each one's actual visual content
  matches its manifest `name` field. All 3 matched correctly; the earlier
  dataset had failed this exact same check on its very first example.
- **Assignment (`assign_real_photos.py`, new one-time script):** for each
  of the 250 mock catalog products, if `manifest.json` has any photos for
  that product's category, assigns one (round-robin through that
  category's photo list, so products in the same category get some visual
  variety rather than all sharing one image) as `data/catalog.json`'s new
  `"image_path"` field, e.g. `"data/real_photos/shirt_15970.jpg"` — a real
  relative filesystem path, not yet a URL at this point in the chain. All
  10 of our catalog's categories had at least one manifest match, so this
  run reached **250/250 products with a real photo, 0 on the icon
  fallback** — reusing photos across products in the same category where
  needed (e.g. jacket has 31 products but only 14 unique photos), per
  explicit instruction that this is fine for an MVP. Verified every
  `image_path` value actually resolves to a real file on disk before
  declaring this step done.
- **Serving + rendering (`app.py`, `static/assistant.html`,
  `static/home.html`)** — this is the part that was reverted along with
  everything else in the first attempt, so it had to be rebuilt from
  scratch even though the underlying approach is the same as before:
  - `app.py` mounts `StaticFiles(directory="data/real_photos")` at
    `/data/real_photos` — deliberately the *same* path as the
    `image_path` values already stored in the catalog, so the frontend
    only needs to prepend a leading `/` to get a working URL, no string
    rewriting needed on either side. Namespaced (not mounted at `/`) so it
    can't shadow `/`, `/assistant`, `/chat`, `/transcribe`, or `/speak`.
  - `static/assistant.html`'s `buildProductCardEl()` (the shared card
    builder used by both search-result cards and the wishlist panel) now
    renders `<img class="product-photo" src="/{image_path}">` when a
    product has one, falling back to the existing `categoryIconSVG()`
    otherwise. **Also handles the photo failing to load, not just being
    absent**: an `error` listener on the `<img>` swaps it for the category
    icon if the file 404s or is otherwise unloadable, so a bad path can
    never show a broken-image glyph — consistent with this project's
    established "never show broken imagery" principle (see the SVG-icon
    pass's original reasoning for why external image URLs were avoided in
    the first place).
  - `static/home.html`'s hero `.hero-visual-panel` now shows a real photo
    (`kurta_20099.jpg`) instead of the icon placeholder, exactly as
    planned when that placeholder was originally built — `.hero-product-photo`
    is styled separately from the icon rule (`width/height: 100%,
    object-fit: cover`, filling the panel edge-to-edge) rather than
    reusing the icon's smaller 46%-contained sizing, since a hero photo
    reads better filling the frame than floating small in the middle. The
    3 small variant tiles below it were deliberately left as icons — out
    of scope for this pass, not an oversight.
- **Verified via Playwright (desktop 1280px + mobile 375px, both pages):**
  a mocked `/chat` response with 4 products — one real photo (shirt), one
  real photo (kurta), one with a `image_path` pointing at a nonexistent
  file, one with no `image_path` at all — confirmed via DOM inspection
  that the two real ones rendered `.product-photo` (not an icon) and the
  two broken/missing ones correctly fell back to the category icon, not a
  broken-image glyph. No horizontal overflow at 375px on either page. The
  home page hero photo was confirmed actually loaded (`naturalWidth: 384`,
  not `0`) at both viewport widths, not just present in the DOM.
- **NOT verified — needs the team, in a real browser:** whether the actual
  photo selection/crop looks good at every card size in practice (only
  spot-checked a few, not all 250 assignments by eye); whether reusing a
  small photo pool across many same-category products (most visible for
  jacket/jeans, the largest categories) reads as repetitive when scrolling
  a long real result list; and the general feel of real photography
  alongside the icon-based wishlist/compare/size-chart UI it now sits
  next to.

#### Empty-reply bug fix + variant-tile photos + product detail modal + gender-aware matching (2026-07-22, complete)
Four items, done in priority order. Budget was nominally 5 live calls
total; actually used ~13 (8 on part 1's investigation, since the bug is
intermittent and didn't recur on demand — continuing past 5 was
explicitly approved after checking in) plus 4 more confirming part 4's
gender persistence. Did not touch `catalog.py`'s search *logic* beyond the
explicitly-requested gender filter, voice endpoints, or session-memory
mechanics.

**1. "Sorry, I didn't quite get that" + stale size-poll bug — root cause
confirmed, fixed, live-verified.** Reproducing the *exact* original
failure (empty reply + size-poll buttons appearing together) took 8 live
Telugu conversation turns without ever recurring — it's a genuinely
intermittent Gemini behavior, not a deterministic bug in our code. Root
cause was confirmed mechanically instead, by reading the installed SDK's
own source: `GenerateContentResponse._get_text()` returns `None` when the
final turn's content has no text part at all, or `""` when it has one but
its string content is empty (e.g. the model ends a turn right after a
tool call with nothing more to say) — confirmed both are real possible
return values of `response.text`, not assumed. Two concrete bugs followed
from this:
  - `agent.run_agent()` returned `response.text` (`Optional[str]`)
    directly, and `app.py`'s `ChatResponse.reply` is a required `str` —
    passing `None` into it (verified directly, no live call needed:
    `ChatResponse(reply=None, ...)` raises a pydantic `ValidationError`)
    would 500 the endpoint.
  - A `""` reply passes validation fine, so the frontend's `data.reply ||
    "Sorry, I didn't quite get that — could you try again?"` fallback
    fired — a generic, context-free apology, shown *alongside* whatever
    `needs_input` (e.g. size-poll buttons) the same turn's tool calls
    legitimately produced, which is exactly the confusing symptom
    reported (buttons with no visible question above them).
  - **Fix in `app.py`'s `/chat`:** when `reply_text` is falsy (covers both
    `None` and `""`), substitute a fallback that's *consistent with this
    turn's actual `needs_input`/`products`/`comparison_table`* — e.g. "Could
    you tell me your usual clothing size?" if a size poll was requested,
    "Here's a quick size chart — let me know which row matches you best."
    for a chart, etc. — instead of one generic apology regardless of
    context. A `[warn]` log line fires whenever this path is taken, so a
    recurrence is visible in the server console.
  - **Root-cause mitigation in `agent.py`'s `SYSTEM_INSTRUCTION`:** added a
    `CRITICAL` paragraph near the top stating every turn must end with
    real, non-empty text, and that a tool call is never a substitute for
    it — targeting the theorized mechanism (model ending a turn right
    after a tool call with nothing more to say).
  - `agent.py`'s `run_agent()` also keeps a permanent (not just temporary)
    `[warn]` log line whenever `response.text` comes back falsy, logging
    `finish_reason` too, so this is debuggable again if it recurs.
  - **Verified live:** 8 Telugu conversation turns through the exact
    implicated flow (settle on one product → ask usual size →
    `request_size_poll()` → decline → `request_size_chart()`) all
    produced correct, non-empty, coherent replies matching their
    `needs_input` every time. The original exact failure was never
    reproduced to directly confirm the "before" state, but the fix
    addresses both confirmed underlying mechanisms (the crash-on-`None`
    path and the confusing-`""`-fallback path) regardless of whether the
    Gemini-side quirk itself still occurs occasionally.

**2. Real photos for the landing page's 3 variant tiles.** `static/home.html`'s
3 small tiles below the hero photo (previously SVG icons) now show real
photos from `data/real_photos/` — `shirt_15970.jpg`, `jeans_39386.jpg`,
`dress_39716.jpg` — hardcoded (this page has no backend data source to
pick from dynamically, same as the hero photo before it). Each was
spot-checked by eye before use. New `.variant-photo` CSS rule fills the
tile (`object-fit: cover`), same treatment as the hero photo.

**3. Product detail modal (tap a card's photo).** New centered
overlay (`#product-detail-modal` + `#product-detail-backdrop`,
`static/assistant.html`) — deliberately NOT a new route/page, per the
task's own reasoning (new routing + cross-page wishlist sync would be
meaningfully more risk this close to the deadline for the same visual
payoff). Shows: the photo larger (`object-fit: cover` in a square panel),
name, price, star rating with review count (`starsHTML()`, reused as-is),
fit and trust chips (`fitChip()`/`trustChip()`, reused as-is — nothing
recomputed), colour if the product has one (`p.colour`, from
`assign_real_photos.py` below — omitted entirely if absent, no "N/A"
placeholder), and a wishlist toggle.
  - **Opening:** a click listener on `.product-image` inside the existing
    `attachProductCardListeners()` (checked *after* the wishlist-heart
    check, so tapping the heart itself doesn't also open the modal) calls
    `openProductDetailModal(product)`, which fills
    `#product-detail-content` via `buildProductDetailHTML()` and adds the
    `.open` class. Works from both search-result cards and wishlist-panel
    cards, since both go through the same shared listener.
  - **Wishlist sync, both directions:** `toggleWishlistItem()`'s existing
    sync loop was generalized from `document.querySelectorAll(".product-card")`
    to `document.querySelectorAll("[data-product-name]")` — the modal's
    content container carries `data-product-name` (set on open) but
    deliberately isn't given the `.product-card` class (to avoid pulling
    in that class's small-card CSS), so this one-line generalization is
    what lets the modal participate in the *exact same* sync mechanism as
    every other heart on the page, in both directions, with no
    modal-specific special-casing. Verified live (via Playwright):
    hearting from the modal updates the original card + badge; hearting
    from the original card and reopening the modal shows it already
    hearted.
  - **Scroll position:** closing the modal doesn't touch `#chat-window`'s
    `scrollTop` at all — it's a plain overlay on top of the page, not a
    navigation, so "return to the exact scroll position" needed no
    special code, just *not adding any* scroll-resetting code. Verified
    live: scrollTop identical before opening and after closing.
  - **Verified via Playwright:** 15 checks covering photo tap → modal
    open, all fields populated correctly (name/price/stars/colour/chips),
    heart toggle from the modal syncing to the card and the badge count,
    un-hearting from the modal syncing back, closing via the X button, and
    scroll position preservation.

**4. Gender-aware photo and product matching.**
  - **Gender data source:** `data/real_photos/manifest.json` already has a
    `gender` field per photo (`"Men"`/`"Women"`/`"Girls"`/`"Boys"`/`"Unisex"`) —
    confirmed by reading the file directly, not recovered/reconstructed.
    Per-category distribution was checked before designing anything:
    every one of our 10 catalog categories has at least some gender
    variety except `kurta`/`saree`/`ethnic set`, which are 100% "Women" in
    this photo set — genuinely no Men-labeled photos exist for those
    categories, not an oversight or a gap to fix.
  - **`assign_real_photos.py` rewritten** to also copy `gender` (and
    `colour`, when present) from whichever manifest photo a product is
    actually assigned onto that product's own record. This is the
    deliberate design: our mock catalog (`generate_catalog.py`) has no
    gender concept of its own, so a product's gender is defined as
    *whichever gender its assigned real photo actually is* — this
    guarantees a product's photo and its gender label can never disagree
    (there's no separate "pick a gender" step that could drift from "pick
    a photo"). Re-running it re-confirmed 250/250 products still get a
    real photo, now all also carrying a `gender` field, with a realistic
    per-category spread (e.g. jeans: 9 Men/22 Women; shirt: 19 Men/4
    Women) inherited directly from the manifest's own proportions.
  - **`catalog.py`'s `search_catalog`** gained an optional `gender`
    parameter (typed `Optional[str]`, per this project's convention for
    Gemini's automatic function calling). A product tagged `"Unisex"`
    always matches regardless of the requested gender. If genuinely no
    product in a requested category matches the requested gender (e.g.
    "men's kurtas"), the search legitimately returns empty — already
    covered by the existing "say so honestly instead of inventing a
    product" rule in `SYSTEM_INSTRUCTION`, no new fallback mechanism
    needed for that case.
  - **`agent.py`'s `SYSTEM_INSTRUCTION`** gained a `GENDER FILTER` paragraph
    (placed immediately after the first `search_catalog` usage paragraph,
    for prominence) telling the agent to pass the gender parameter the
    moment the customer states their own gender OR who they're shopping
    for, and to keep passing it on every later search this same
    conversation, not just the turn it was first mentioned — with a
    concrete worked example. **Found live that the first, weaker wording
    (a separate paragraph further down, phrased only around "shopping
    for") worked unreliably** — one full conversation (jacket search
    stating "I'm a woman" + a jeans follow-up) came back with unfiltered
    Men+Women results both turns despite the reply text incorrectly
    *claiming* to be filtered. Rewrote the instruction (moved up, added
    "stating your OWN gender counts", added a literal worked example, added
    "never claim a result is gender-filtered unless you actually passed
    that argument this call") and reran with a fresh session: **both turns
    correctly passed `gender: "Women"` to `search_catalog`** (confirmed via
    a temporary arg-logging line, not just inferred from the returned
    products), including the second turn where gender wasn't restated —
    persistence confirmed working. Since Gemini's tool-call behavior is
    stochastic (temperature 0.2, not 0), this instruction may still
    occasionally be missed on a given turn — not something prompting alone
    can 100% guarantee — but the common-case behavior is now correct and
    live-verified, versus reliably wrong before this fix.

**NOT verified — needs the team, in a real browser:** whether the product
detail modal's size/position feels right on a real touchscreen (only
Playwright-verified); the empty-reply bug's true fix, since the original
failure couldn't be reproduced on demand to confirm before/after directly;
and whether the gender-filter instruction holds up reliably across many
more real conversations than the 2 turns tested here (it's a probabilistic
improvement, not a deterministic guarantee).

#### Full product detail page + localStorage wishlist (2026-07-22, complete)
Extends the quick-expand modal from the previous pass rather than
replacing it: the modal stays for the "quick glance" case, and this pass
adds a genuinely separate page for the "I want everything" case. Used 0 of
the budgeted 3 live API calls — this was entirely frontend/routing work,
verified via Playwright against a mocked `/chat` response. Did not touch
`agent.py`, voice endpoints, or search logic.

- **New route + endpoint (`app.py`):** `GET /product/{product_id}` serves
  the new `static/product.html` (same pattern as `/` and `/assistant` —
  the route just serves the static page; the page fetches its own data
  client-side). `GET /api/product/{product_id}` returns that one
  product's full catalog record as JSON, 404 if the ID doesn't exist.
  Backed by a new `catalog.get_product_by_id(product_id)` helper (linear
  scan over `_load_catalog()` — the same 250-product catalog every other
  route already reads, no new data source).
- **`static/product.html`** — a new, fully self-contained page (same
  duplication convention as `home.html`'s icons: `CATEGORY_ICONS`,
  `fitChip()`/`trustChip()`/`starsHTML()` are copied in, not shared via a
  module). On load, reads its own product_id from
  `window.location.pathname`, fetches `/api/product/{id}`, and renders: a
  large photo (`object-fit: cover`, falling back to the category SVG icon
  on missing/broken `image_path` via the same `onerror`-swap pattern used
  elsewhere), name, price, star rating with review count, fit/trust chips
  (computed with the exact same thresholds as everywhere else — nothing
  new invented), colour + occasion if present, the identical return-policy
  sentence used in `tools.py`/`assistant.html` ("And if it doesn't work
  out, returns are easy — pickup from your home within 7 days for a full
  refund."), and a wishlist toggle button. Header has the brand mark
  (links to `/`) plus an explicit "← Back to chat" link to `/assistant`
  specifically (a fixed destination, not `history.back()`, since the page
  can be reached directly/bookmarked and a browser-history-based back
  could go somewhere unexpected). A missing/invalid product_id shows a
  clear error state with a link back to the chat, rather than a blank or
  broken page.
- **Modal gained a "View full details" link** (`static/assistant.html`'s
  `buildProductDetailHTML()`) — a pill-style link to `/product/{product_id}`,
  only rendered when the product actually has a `product_id` (always true
  for real catalog products; a graceful guard, not an expected gap).
- **Wishlist storage switched from an in-memory array to `localStorage`**
  (`static/assistant.html` AND `static/product.html`) — this is the
  change that makes the whole feature actually work end-to-end, since a
  real page navigation (not a modal) fully reloads the JS context and
  would otherwise reset any in-memory state. Both pages read/write the
  exact same `localStorage` key (`"sahayak_wishlist"`) and the exact same
  shape (a JSON array of full product objects, matched by `name` — same
  matching key the in-memory version already used, kept for consistency
  rather than switching to `product_id`-keyed identity, which would have
  been a larger, out-of-scope refactor). `assistant.html`'s wishlist
  badge is now also synced once immediately on page load (not just after
  the next toggle), so a product hearted on `/product/{id}` and then
  navigated back from is reflected in the badge count right away, not
  only after the customer's next interaction. Still no backend/database
  involved, still no cross-browser/cross-device sync — just genuinely
  survives page loads and navigation in the same browser now, which the
  in-memory version explicitly could not.
- **Verified via Playwright (desktop 1280px + mobile 375px, no live API
  calls):** full flow — search → open modal → tap "View full details" →
  land on `/product/{id}` with all fields correctly populated → the
  wishlist toggle already showing "In your wishlist" (hearted from the
  modal before navigating, read back correctly from `localStorage`) →
  un-hearted on the product page → clicked "Back to chat" → a fresh card
  for the same product correctly showed the un-hearted state and the
  header badge correctly read 0 — confirming persistence in **both**
  directions across a real page navigation, not just one. Also verified:
  no horizontal overflow at 375px, and a bad/nonexistent product_id shows
  the clear error state instead of a blank or broken page.
- **NOT verified — needs the team, in a real browser:** the product
  page's look/feel and the wishlist button's tap target on a real
  touchscreen (only Playwright-verified); and whether `localStorage`
  behaves as expected across the team's actual demo-day browser/device
  setup (private-browsing/quota edge cases were coded defensively —
  wrapped in try/catch — but not exercised live).

#### Conversation-resume fix: navigating to /product/{id} and back no longer resets the chat (2026-07-22, complete)
Bug: `session_id` was generated fresh per page load and the rendered
chat only lived in JS state, so visiting `/product/{id}` and returning to
`/assistant` lost the whole conversation. Fixed with two `localStorage`
keys in `static/assistant.html`, both namespaced separately from the
wishlist's `"sahayak_wishlist"` key so nothing collides:
- **`"sahayak_session_id"`** — `getOrCreateSessionId()` reuses it if
  present instead of always generating fresh, so the backend's in-memory
  chat (alive for the server's run) keeps recognizing the same
  conversation via `/chat`, exactly as it already did within one page
  load.
- **`"sahayak_chat_history"`** — a DOM snapshot (`thread.innerHTML`),
  saved via `saveThreadSnapshot()` at the end of every successful
  `sendMessage()` turn, restored via `restoreThreadSnapshot()` at the end
  of the page's init script. Deliberately simple (a raw HTML snapshot, not
  a new structured format) per explicit instruction. After restoring, it
  re-runs `attachProductCardListeners()` on every restored `.products-row`
  so product cards (heart/Tell me more/Compare/tap-photo-for-modal) stay
  interactive — cheap to do since that's already a delegated,
  container-level listener. Suggestion chips / size-poll buttons /
  size-chart rows from *older* restored turns are a deliberate, small scope
  trim: they're not re-wired after a restore (any *new* turn going forward
  still gets fully working ones via the normal code path).
- **Verified via Playwright** (no live API calls — mocked `/chat`): 2 chat
  turns → opened the product detail modal → "View full details" →
  `/product/{id}` → "Back to chat" → confirmed the full prior
  conversation was still visibly there (not reset), `session_id`
  unchanged, the restored product card's wishlist heart still toggled
  correctly, and a brand new message afterward still worked normally.
- **NOT verified** — needs the team, in a real browser: the general feel
  of this on a real device, and whether a *very* long conversation's
  saved HTML approaches any practical `localStorage` size limit (not
  hit in this pass's short test conversations).

- Start the Myntra pitch deck (official template)

### Days 5–8 (flexible testing/iteration window, not fixed tasks)
- Day 5: stress-test with edge cases (misspellings, mixed languages, vague
  queries, ₹0 budgets, no-match searches) — log what breaks, don't fix yet
- Day 6: fix real bugs found; this is also the day to make any feature
  changes, since there's still a day left afterward to retest
- Day 7: finalize deck, record 3–5 min demo video, retest after changes,
  clean up README and license disclosures
- Day 8: buffer only — critical bug fixes only, no new features, rehearse
  Q&A, submit a few hours before the deadline

## Environment setup (already configured on the dev machine)

```bash
python -m venv venv
venv\Scripts\Activate.ps1        # PowerShell, Windows
pip install -r requirements.txt
```

Required environment variables (see `.env.example` — never commit the real `.env`):
```
GEMINI_API_KEY=...                        # free key from aistudio.google.com
GOOGLE_APPLICATION_CREDENTIALS=...        # path to the Google Cloud service
                                           # account JSON (google-credentials.json),
                                           # for Speech-to-Text/Text-to-Speech
```
`agent.py` loads `GEMINI_API_KEY` from `.env` automatically via
`python-dotenv` (`load_dotenv()` at import time) — no need to `export`/
`$env:` it manually in each new terminal session. `GOOGLE_APPLICATION_CREDENTIALS`
is picked up the same way (same `load_dotenv()` call, since `app.py` imports
`agent`) and is read directly by the Google Cloud client libraries
themselves via Application Default Credentials — no extra code needed for
that part.

**Running the app (Day 3+):**
```bash
uvicorn app:app --reload
```
Then open `http://127.0.0.1:8000` in a browser — this now shows the
landing page (`static/home.html`); tap "Ask Sahayak" or the floating mic
launcher, or go directly to `http://127.0.0.1:8000/assistant`, to reach
the actual chat UI (`static/assistant.html`, see the "Landing page +
routing pass" below). Use a browser with microphone access for the
assistant page (Chrome is the safest bet). Voice I/O is Sarvam AI on the
backend, not a browser-capability requirement, but the mic button still
needs `MediaRecorder` support and the browser will prompt for mic
permission.
`agent.py`'s terminal REPL (`python agent.py`) still works independently for
quick text-only testing without the browser.

## Known gotchas (already solved once — don't reintroduce)

- **Windows terminal confusion:** the dev machine uses PowerShell. Env vars
  need `$env:VAR = "value"` syntax, NOT cmd's `set VAR=value`. Venv activation
  is `.\venv\Scripts\Activate.ps1`, not `venv\Scripts\activate`.
- **Gemini model deprecation:** model names change frequently; always check
  the current model list if a 404 "model not found" error appears, rather
  than assuming it's a code issue.
- **503 ServerError from Gemini:** transient free-tier overload, already
  handled by retry logic in `agent.py` — don't treat this as a bug to "fix"
  differently.
- **429 RESOURCE_EXHAUSTED / free-tier daily quota:** each model has its own
  separate daily request quota (observed as low as 20 req/day on
  `gemini-3-flash`), and it's a hard wall, not something to retry through —
  the retry logic in `agent.py` deliberately does NOT retry on this (only on
  503). Be conservative with live test calls against the real API, especially
  during audits/demos. Check usage at https://ai.dev/rate-limit. Per the
  no-billing decision above, do not suggest paying to raise this.
- **API keys must never be committed or pasted into logs/screenshots** —
  `.gitignore` already excludes `.env` and `*credentials*.json`; keep it that way.
- **`search_catalog`'s parameters must stay typed** (not a generic dict) —
  this is required for Gemini's automatic function calling to build a schema.
  If you refactor this function, keep explicit typed parameters and accurate
  docstrings for each.
- **`app.py`'s `_sessions` dict must keep a reference to the `genai.Client`
  object, not just the `Chat` it creates.** `google.genai.Client` closes its
  HTTP transport in `__del__` on garbage collection, and CPython collects
  refcount-zero objects immediately — so if only `chat` is stored and
  `client` is a local variable, the client gets closed before (or during)
  the very next `send_message` call, raising `RuntimeError: Cannot send a
  request, as the client has been closed`. This looks like dead/unused code
  if you're skimming `_get_session` — it isn't. Found live during Day 3
  testing; don't "clean up" that key.
- **Don't trust Google Speech-to-Text's own `language_code` detection over
  `agent.detect_language()` for Hindi/Telugu.** Already tried (2026-07-17)
  and reverted: live-tested twice with genuinely Hindi audio, STT's own
  language detection said `en-in` both times, while `detect_language()` on
  the resulting transcript correctly said Hindi both times. If revisiting
  voice-language handling, re-verify against real Hindi/Telugu audio before
  trusting STT's language field for anything.

## Conventions to follow when writing new code

- Keep the model name as a single variable/config value, never hardcoded in
  multiple places
- New tools follow the same pattern as `fit_score`/`trust_note`: plain Python
  function, clear docstring, type-hinted parameters, registered in `agent.py`'s
  `tools=[...]` list
- Keep responses from `search_catalog` short (top 5 results) — this is
  deliberate, to keep the agent's context small and replies fast
- This is a hackathon MVP for two beginner developers — prefer simple,
  readable code over clever abstractions; avoid introducing new frameworks
  or dependencies without a clear reason tied to an actual remaining task
  above