"""List available Gemini models."""

import os
import warnings

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(m.name)
