"""Stage 2 — Structurer isolated real-world test."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from docstream.core.extractor import PDFExtractor
from docstream.core.structurer import DocumentStructurer

OUT_DIR = Path("test_outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

pdf_path = "test_pdfs/attention_paper.pdf"

print("Extracting blocks...")
blocks = PDFExtractor(pdf_path).extract()
print(f"Got {len(blocks)} blocks")

gemini_key = os.environ.get("GEMINI_API_KEY", "")
groq_key = os.environ.get("GROQ_API_KEY", "")

print(f"\nStructuring (Gemini key: {'present' if gemini_key else 'MISSING'}, "
      f"Groq key: {'present' if groq_key else 'MISSING'})...")

try:
    structurer = DocumentStructurer(gemini_key=gemini_key, groq_key=groq_key)
    ast = structurer.structure(blocks)

    print(f"  Title: {ast.title}")
    print(f"  Authors: {ast.authors}")
    print(f"  Sections: {len(ast.sections)}")
    if ast.abstract:
        print(f"  Abstract: {ast.abstract[:100]}...")
    else:
        print(f"  Abstract: None")

    for i, sec in enumerate(ast.sections[:5]):
        print(f"  Section {i+1}: [{sec.level}] {sec.heading}")

    # Save full AST
    out = OUT_DIR / "ast_output.json"
    with open(out, "w") as f:
        json.dump(ast.model_dump(), f, indent=2, default=str)
    print(f"\n  Saved to: {out}")
    print("  PASSED")

except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    sys.exit(1)
