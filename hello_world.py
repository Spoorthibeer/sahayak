"""
Day 1 check: confirms your Gemini API key works.
Run this AFTER setting GEMINI_API_KEY in your .env file (or as an
environment variable directly).

Usage:
    export GEMINI_API_KEY="your_key_here"   # or load from .env, see below
    python hello_world.py
"""

import os
from google import genai

# Reads GEMINI_API_KEY from the environment automatically if you don't
# pass api_key explicitly — but being explicit here so it's obvious
# what's happening for Day 1 learning purposes.
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise SystemExit(
        "GEMINI_API_KEY is not set. Get a free key at aistudio.google.com "
        "and run: export GEMINI_API_KEY='your_key_here'"
    )

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Say hello in Hindi and English, in one short sentence each.",
)

print("Gemini says:")
print(response.text)
