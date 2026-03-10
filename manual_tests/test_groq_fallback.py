"""Step 6 — Groq fallback test."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from docstream.core.extractor import PDFExtractor
from docstream.core.structurer import DocumentStructurer
from docstream.exceptions import StructuringError

pdf_path = "test_pdfs/attention_paper.pdf"
blocks = PDFExtractor(pdf_path).extract()
print(f"Extracted {len(blocks)} blocks\n")

PASS = 0
FAIL = 0

# Test 1: Groq only (invalid Gemini key forces fallback)
print("Test 1: Groq-only mode (invalid Gemini key)...")
try:
    structurer = DocumentStructurer(
        gemini_key="invalid_key_to_force_fallback",
        groq_key=os.getenv("GROQ_API_KEY"),
    )
    ast = structurer.structure(blocks)
    print(f"  PASSED — Groq fallback works, title: {ast.title}")
    PASS += 1
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    FAIL += 1

# Test 2: Both keys invalid (should raise clean StructuringError)
print("\nTest 2: Both keys invalid (expect clean error)...")
try:
    structurer = DocumentStructurer(gemini_key="bad_key", groq_key="bad_key")
    ast = structurer.structure(blocks)
    print(f"  FAILED — should have raised an error")
    FAIL += 1
except StructuringError as e:
    print(f"  PASSED — Clean StructuringError: {str(e)[:80]}...")
    PASS += 1
except Exception as e:
    print(f"  FAILED — Wrong exception type: {type(e).__name__}: {e}")
    FAIL += 1

# Test 3: No keys at all
print("\nTest 3: No keys at all (expect immediate clean error)...")
try:
    structurer = DocumentStructurer(gemini_key="", groq_key="")
    ast = structurer.structure(blocks)
    print(f"  FAILED — should have raised an error")
    FAIL += 1
except StructuringError as e:
    print(f"  PASSED — Clean StructuringError: {str(e)[:80]}...")
    PASS += 1
except Exception as e:
    print(f"  FAILED — Wrong exception type: {type(e).__name__}: {e}")
    FAIL += 1

print(f"\n{'='*50}")
print(f"FALLBACK RESULTS: {PASS} passed | {FAIL} failed")
print(f"{'='*50}")
sys.exit(1 if FAIL > 0 else 0)
