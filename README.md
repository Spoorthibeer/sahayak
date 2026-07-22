# Sahayak

An AI shopping assistant built for Myntra's "Build What's Next: Myntra for Bharat" hackathon — helping Tier 2/3 customers find the right product, the right size, and buy with confidence, by voice or text, in their own language.

**Team:** NovaPair — G. Narayanamma Institute of Technology and Science
**Theme:** Bharat Opportunity + Speed & Trust

---

## The problem

Fashion e-commerce has one of the highest return rates of any online retail category, and fit/sizing issues are consistently cited as the single biggest driver of those returns. For a first-time customer in Tier 2/3 India, this is compounded further: they can't try clothes on before buying, they aren't always confident an online size will match their body, they aren't sure a product will look and feel like its photo, and many are more comfortable speaking than typing — and not always in English.

## What Sahayak does

- **Talk to it, don't search it.** Customers describe what they want in plain English, Hindi, or Telugu — by voice or text — and Sahayak reasons through the request using Google's Gemini API with function-calling, not a scripted flow.
- **A fit-confidence system that adapts to what the customer actually knows.** Order history first, then usual size, then a visual size chart, then a comparison to a garment the customer already owns — falling back to an honest, clearly-labeled estimate only as a last resort.
- **Trust, at the moment it matters.** Every sizing recommendation comes with a return-policy reassurance in the same message, alongside real product ratings where available.
- **Real Myntra product data**, sourced and manually verified, alongside clearly-distinguished mock data for products without a real match — never presented as more certain than it is.
- **A full interactive UI** — voice with live waveform and barge-in, a tappable size poll, product comparison, a wishlist, and a full product detail page.

## Tech stack

| Layer | Technology |
|---|---|
| AI reasoning / agent | Google Gemini API (function-calling) |
| Voice (speech-to-text & text-to-speech) | Sarvam AI |
| Backend | Python, FastAPI |
| Frontend | Plain HTML / CSS / JavaScript |
| Product data | Real Myntra product data (photos, ratings) + realistic mock data |

## Architecture

```
Customer (voice/text)
   → Landing Page → Chat Assistant ⇄ Product Detail Page
      → FastAPI Backend (/chat, /transcribe, /speak, /api/product/{id})
         → Voice Layer (Sarvam AI)
         → Agent Orchestrator (Gemini API)
            → search_catalog()
            → fit_score() / trust_note() — fallback chain
               → Product Data (catalog.json, real_photos/, demand_log.json)
```

## Setup

```bash
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`) with:
```
GEMINI_API_KEY=your_key_here
SARVAM_API_KEY=your_key_here
```

Run:
```bash
uvicorn app:app --reload
```
Then open `http://127.0.0.1:8000` in Chrome.

## Third-party services and data disclosure

- **Google Gemini API** — agent reasoning and function-calling (free tier)
- **Sarvam AI** — Indian-language speech-to-text and text-to-speech
- **Real product photos and data** — sourced from a public Myntra product dataset (Kaggle/Hugging Face mirror), manually verified for correctness before use, used for educational/hackathon purposes
- All other libraries are listed in `requirements.txt`, standard open-source packages under their respective licenses

## Known limitations (MVP scope)

- Chat sessions are stored in memory and reset if the server restarts
- Product data is a mix of real and mock entries, clearly separated internally
- Voice quality depends on the Sarvam AI free tier's available credits

## Roadmap

- Full agentic checkout
- Additional Indian language support
- Feeding regional demand signals back to Myntra's merchandising and seller-onboarding
- AR/visual try-on (considered, out of scope for this MVP)