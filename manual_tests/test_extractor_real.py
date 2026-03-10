"""Stage 1 — Extractor isolated real-world test."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from docstream.core.extractor import PDFExtractor

OUT_DIR = Path("test_outputs/extractor")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Use PDFs from test_pdfs/ directory
pdfs = {
    "digital": "test_pdfs/attention_paper.pdf",
    "ieee": "test_pdfs/resnet_ieee.pdf",
    "scanned": "test_pdfs/scanned_test.pdf",
}

PASS = 0
FAIL = 0

for name, path in pdfs.items():
    if not Path(path).exists():
        print(f"SKIP {name} — file not found: {path}")
        continue

    print(f"\n{'='*50}")
    print(f"Testing: {name} ({path})")
    try:
        extractor = PDFExtractor(path)
        blocks = extractor.extract()

        page_nums = [b.page_number for b in blocks if b.page_number]
        max_page = max(page_nums) if page_nums else 0
        table_count = sum(1 for b in blocks if b.type == "table")
        bold_count = sum(1 for b in blocks if getattr(b, "is_bold", False))
        has_content = all(b.content for b in blocks[:10])

        print(f"  Blocks extracted: {len(blocks)}")
        print(f"  Pages: {max_page}")
        print(f"  Tables: {table_count}")
        print(f"  Bold blocks: {bold_count}")
        print(f"  First 10 blocks have content: {has_content}")

        # Save blocks for inspection
        out = OUT_DIR / f"{name}_blocks.json"
        with open(out, "w") as f:
            json.dump([b.model_dump() for b in blocks], f, indent=2, default=str)
        print(f"  Saved to: {out}")

        assert len(blocks) > 0, "No blocks extracted"
        assert has_content, "Empty blocks found"
        print(f"  PASSED")
        PASS += 1

    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        FAIL += 1

print(f"\n{'='*50}")
print(f"EXTRACTOR RESULTS: {PASS} passed | {FAIL} failed")
print(f"{'='*50}")
sys.exit(1 if FAIL > 0 else 0)
