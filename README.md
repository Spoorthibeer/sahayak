# Sahayak — Day 1 scaffold

AI vernacular shopping agent for Myntra's Bharat hackathon.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your real keys, then load them
into your shell before running anything:

```bash
cp .env.example .env
# edit .env with your real keys, then:
export $(cat .env | xargs)      # Linux/Mac quick-load; use a library like
                                 # python-dotenv later if this gets tedious
```

- **Gemini API key** — free, no credit card, at https://aistudio.google.com
- **OpenAI API key** (for Whisper, added on Day 3) — https://platform.openai.com
- **Google Cloud credentials** (for TTS, added on Day 3) — enable the
  Text-to-Speech API in a Google Cloud project, create a service account,
  download its JSON key

## Day 1 — run these in order

```bash
python hello_world.py        # confirms your Gemini key works
python generate_catalog.py   # creates data/catalog.json (250 mock products)
python catalog.py            # tests search_catalog() + log_query(), prints results
```

If all three run without errors, Day 1 is done. `data/demand_log.json` should
now exist with at least one entry.

## What's here so far

| File | Purpose |
|---|---|
| `hello_world.py` | Confirms the Gemini API key works |
| `generate_catalog.py` | Generates the mock product catalog |
| `catalog.py` | `search_catalog()` and `log_query()` — becomes a Gemini tool on Day 2 |
| `data/catalog.json` | The mock catalog (generated, not hand-written) |
| `data/demand_log.json` | Regional demand log (generated as searches happen) |

## Coming next (Day 2)

`agent.py` — wraps `search_catalog` as a Gemini function-calling tool, plus
`fit_score()` and `trust_note()` as two more tools, and the full agent loop.
