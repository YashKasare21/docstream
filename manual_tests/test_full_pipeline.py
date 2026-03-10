"""Step 3 — Full pipeline integration tests."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import docstream

test_cases = [
    ("digital_report", "test_pdfs/attention_paper.pdf", "report"),
    ("digital_ieee", "test_pdfs/attention_paper.pdf", "ieee"),
    ("digital_resume", "test_pdfs/attention_paper.pdf", "resume"),
    ("ieee_report", "test_pdfs/resnet_ieee.pdf", "report"),
    ("scanned_report", "test_pdfs/scanned_test.pdf", "report"),
]

results = []

for name, pdf, template in test_cases:
    if not Path(pdf).exists():
        print(f"SKIP {name} — {pdf} not found")
        continue

    print(f"\nTesting {name} ({pdf} → {template})...")
    output_dir = Path(f"test_outputs/integration/{name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    start = time.time()
    try:
        result = docstream.convert(pdf, template=template, output_dir=str(output_dir))
        elapsed = time.time() - start

        status = "PASS" if result.success else "FAIL"
        print(f"  {status} | {elapsed:.1f}s | PDF: {result.pdf_path}")
        results.append((name, result.success, elapsed, result.error))

    except Exception as e:
        elapsed = time.time() - start
        print(f"  EXCEPTION | {elapsed:.1f}s | {type(e).__name__}: {e}")
        results.append((name, False, elapsed, str(e)))

print(f"\n{'='*70}")
print(f"{'Test':<20} {'Status':<10} {'Time':<10} {'Error'}")
print(f"{'='*70}")
for name, success, elapsed, error in results:
    status = "PASS" if success else "FAIL"
    err = (error[:35] + "...") if error and len(error) > 35 else (error or "-")
    print(f"{name:<20} {status:<10} {elapsed:<10.1f} {err}")

passed = sum(1 for _, s, _, _ in results if s)
failed = sum(1 for _, s, _, _ in results if not s)
print(f"\nTOTAL: {passed} passed | {failed} failed")
sys.exit(1 if failed > 0 else 0)
