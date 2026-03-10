"""Stage 3 — Renderer isolated real-world test."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from docstream.core.extractor import PDFExtractor
from docstream.core.renderer import DocumentRenderer
from docstream.core.structurer import DocumentStructurer

pdf_path = "test_pdfs/attention_paper.pdf"

print("Extracting + structuring...")
blocks = PDFExtractor(pdf_path).extract()
gemini_key = os.environ.get("GEMINI_API_KEY", "")
groq_key = os.environ.get("GROQ_API_KEY", "")
ast = DocumentStructurer(gemini_key=gemini_key, groq_key=groq_key).structure(blocks)
print(f"AST ready: {ast.title} ({len(ast.sections)} sections)")

PASS = 0
FAIL = 0

for template in ["report", "ieee", "resume"]:
    print(f"\nRendering template: {template}")
    output_dir = Path(f"test_outputs/renderer/{template}")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        renderer = DocumentRenderer(template=template)
        result = renderer.render(ast, output_dir=output_dir)

        if result.success:
            print(f"  Success in {result.processing_time_seconds:.1f}s")
            print(f"  TEX: {result.tex_path} ({result.tex_path.stat().st_size} bytes)")
            print(f"  PDF: {result.pdf_path} ({result.pdf_path.stat().st_size} bytes)")
            PASS += 1
        else:
            print(f"  FAILED: {result.error}")
            FAIL += 1

    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")
        FAIL += 1

print(f"\n{'='*50}")
print(f"RENDERER RESULTS: {PASS} passed | {FAIL} failed")
print(f"{'='*50}")
sys.exit(1 if FAIL > 0 else 0)
