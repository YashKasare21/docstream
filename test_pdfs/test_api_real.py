"""Real-world Python API integration test for DocStream."""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import docstream

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  PASSED: {name} {detail}")
        PASS += 1
    else:
        print(f"  FAILED: {name} {detail}")
        FAIL += 1


# ── Test 1: Extract ──────────────────────────────────────────────
print("\n=== Test 1: docstream.extract() ===")
try:
    blocks = docstream.extract("attention_paper.pdf")
    check("extract returns list", isinstance(blocks, list))
    check("extract non-empty", len(blocks) > 0, f"({len(blocks)} blocks)")
    check("block has content", hasattr(blocks[0], "content") and blocks[0].content)
    check("block has type", hasattr(blocks[0], "type"))
except Exception as e:
    check("extract", False, str(e))

# ── Test 2: Structure ────────────────────────────────────────────
print("\n=== Test 2: docstream.structure() ===")
try:
    ast = docstream.structure(blocks)
    check("structure returns DocumentAST", type(ast).__name__ == "DocumentAST")
    check("has title", bool(ast.title), f"('{ast.title[:50]}...')" if ast.title else "")
    check("has sections", len(ast.sections) > 0, f"({len(ast.sections)} sections)")
except Exception as e:
    check("structure", False, str(e))

# ── Test 3: Render with report template ──────────────────────────
print("\n=== Test 3: docstream.render() — report ===")
try:
    result = docstream.render(ast, template="report", output_dir="./api_test_out/report")
    check("render success", result.success, result.error or "")
    if result.success:
        check("tex exists", result.tex_path and result.tex_path.exists())
        check("pdf exists", result.pdf_path and result.pdf_path.exists())
        check("time recorded", result.processing_time_seconds > 0,
              f"({result.processing_time_seconds:.2f}s)")
except Exception as e:
    check("render report", False, str(e))

# ── Test 4: Render with ieee template ────────────────────────────
print("\n=== Test 4: docstream.render() — ieee ===")
try:
    result = docstream.render(ast, template="ieee", output_dir="./api_test_out/ieee")
    check("render ieee success", result.success, result.error or "")
except Exception as e:
    check("render ieee", False, str(e))

# ── Test 5: Render with resume template ──────────────────────────
print("\n=== Test 5: docstream.render() — resume ===")
try:
    result = docstream.render(ast, template="resume", output_dir="./api_test_out/resume")
    check("render resume success", result.success, result.error or "")
except Exception as e:
    check("render resume", False, str(e))

# ── Test 6: Full convert() pipeline ─────────────────────────────
print("\n=== Test 6: docstream.convert() — full pipeline ===")
try:
    t0 = time.time()
    result = docstream.convert(
        "attention_paper.pdf",
        template="report",
        output_dir="./api_test_out/full",
    )
    elapsed = time.time() - t0
    check("convert success", result.success, result.error or "")
    if result.success:
        check("convert pdf exists", result.pdf_path and result.pdf_path.exists())
        check("convert time", elapsed > 0, f"({elapsed:.1f}s total)")
except Exception as e:
    check("convert", False, str(e))

# ── Test 7: version ──────────────────────────────────────────────
print("\n=== Test 7: docstream.__version__ ===")
check("version string", docstream.__version__ == "0.1.0", docstream.__version__)

# ── Summary ──────────────────────────────────────────────────────
print(f"\n{'='*54}")
print(f"  API RESULTS: {PASS} passed | {FAIL} failed")
print(f"{'='*54}")
sys.exit(1 if FAIL > 0 else 0)
