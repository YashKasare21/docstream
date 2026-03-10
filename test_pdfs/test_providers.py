"""Quick diagnostic for Gemini and Groq API providers."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# --- Gemini ---
print("=== Gemini Test ===")
key = os.environ.get("GEMINI_API_KEY", "")
print(f"Key present: {bool(key)} (len={len(key)})")
try:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        import google.generativeai as genai

    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    resp = model.generate_content('Return only this JSON: {"test": true}')
    print(f"OK: {resp.text[:100]}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

# --- Groq old model ---
print("\n=== Groq (llama-3.1-70b-versatile) ===")
groq_key = os.environ.get("GROQ_API_KEY", "")
print(f"Key present: {bool(groq_key)} (len={len(groq_key)})")
try:
    from groq import Groq

    client = Groq(api_key=groq_key)
    resp = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[{"role": "user", "content": 'Return JSON: {"test": true}'}],
        max_tokens=50,
    )
    print(f"OK: {resp.choices[0].message.content[:60]}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

# --- Groq new model ---
print("\n=== Groq (llama-3.3-70b-versatile) ===")
try:
    from groq import Groq

    client = Groq(api_key=groq_key)
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": 'Return JSON: {"test": true}'}],
        max_tokens=50,
    )
    print(f"OK: {resp.choices[0].message.content[:60]}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
