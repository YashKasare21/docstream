"""
DocStream — conversion demo
===========================

This script downloads a real open-access paper from arXiv, converts it with
all three built-in templates, and prints a timing summary.

It is intentionally verbose so portfolio viewers can follow each step of the
DocStream pipeline without reading the library source.

Usage
-----
    # Install dependencies first
    pip install docstream requests

    # Set API keys in .env or as environment variables
    export GEMINI_API_KEY=your-key-here

    # Run
    python examples/convert_example.py

What it does
------------
1.  Downloads a freely available arXiv PDF (~400 KB) into a temp directory.
2.  Runs the three-stage DocStream pipeline for each template:
        Extract  →  Structure  →  Render
3.  Prints a timing breakdown for every stage and template.
4.  Saves all outputs under ./out/demo/.
"""

from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path

# ── 0. Optional early check ────────────────────────────────────────────────────
# Give the user a clear message if the API key is missing before we import
# the heavy libraries.
if not os.environ.get("GEMINI_API_KEY") and not Path(".env").exists():
    print(
        "ERROR: GEMINI_API_KEY not set.\n"
        "  Create a .env file with GEMINI_API_KEY=<your-key>\n"
        "  or export GEMINI_API_KEY=<your-key> in your shell.",
        file=sys.stderr,
    )
    sys.exit(1)

# ── 1. Imports ─────────────────────────────────────────────────────────────────
import docstream
from docstream.exceptions import DocstreamError

# ── 2. Configuration ───────────────────────────────────────────────────────────
# arXiv "Attention Is All You Need" — the original Transformer paper.
# This is a freely available open-access PDF (~3 MB).
ARXIV_PDF_URL = "https://arxiv.org/pdf/1706.03762"
ARXIV_PDF_NAME = "attention_is_all_you_need.pdf"

# Templates to demonstrate — all three built-in styles.
TEMPLATES = ["report", "ieee", "resume"]

# Output directory — all generated .tex and .pdf files go here.
OUTPUT_DIR = Path("./out/demo")

# ── 3. Helper utilities ────────────────────────────────────────────────────────


def _hr(char: str = "─", width: int = 60) -> str:
    """Return a horizontal rule of the given width."""
    return char * width


def _download_pdf(url: str, dest: Path) -> None:
    """Download *url* to *dest*, skipping if the file already exists."""
    if dest.exists():
        print(f"  [cache] {dest.name} already downloaded — skipping.")
        return

    print(f"  Downloading {dest.name} …", end=" ", flush=True)
    t0 = time.perf_counter()
    urllib.request.urlretrieve(url, dest)  # noqa: S310 — URL is hardcoded/safe here
    elapsed = time.perf_counter() - t0
    size_kb = dest.stat().st_size // 1024
    print(f"done ({size_kb} KB in {elapsed:.1f}s)")


# ── 4. Main demo ───────────────────────────────────────────────────────────────


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Download the sample PDF ───────────────────────────────────────
    print(_hr("═"))
    print("  DocStream — Conversion Demo")
    print(_hr("═"))
    print()
    print("Step 1 — Download sample PDF")
    print(_hr())

    pdf_path = OUTPUT_DIR / ARXIV_PDF_NAME
    _download_pdf(ARXIV_PDF_URL, pdf_path)

    # ── Step 2: Extract blocks (once, shared across all templates) ────────────
    print()
    print("Step 2 — Extract content from PDF")
    print(_hr())

    t_extract_start = time.perf_counter()
    blocks = docstream.extract(pdf_path)
    t_extract = time.perf_counter() - t_extract_start

    print(f"  Extracted {len(blocks)} blocks in {t_extract:.2f}s")

    # Show a preview of the first three blocks so portfolio viewers can see
    # what raw extracted content looks like before AI structuring.
    print()
    print("  Preview of first 3 blocks:")
    for i, block in enumerate(blocks[:3], 1):
        preview = block.content[:80].replace("\n", " ")
        print(f"    [{i}] type={block.type.value!s:<8} p{block.page_number}  {preview!r}")

    # ── Step 3: Structure the document (once, AI call) ────────────────────────
    print()
    print("Step 3 — Structure document with Gemini Flash")
    print(_hr())

    t_structure_start = time.perf_counter()
    ast = docstream.structure(blocks)
    t_structure = time.perf_counter() - t_structure_start

    print(f"  Title    : {ast.title}")
    print(f"  Authors  : {', '.join(ast.metadata.authors or [])}")
    print(f"  Sections : {len(ast.sections)}")
    print(f"  Time     : {t_structure:.2f}s")

    # ── Step 4: Render with each template ─────────────────────────────────────
    print()
    print("Step 4 — Render with all three templates")
    print(_hr())

    # Collect timing results for the final summary table.
    results: list[dict] = []

    for template in TEMPLATES:
        template_out = OUTPUT_DIR / template
        template_out.mkdir(exist_ok=True)

        print(f"  [{template}] rendering …", end=" ", flush=True)
        t_render_start = time.perf_counter()

        try:
            result = docstream.render(ast, template=template, output_dir=template_out)
            t_render = time.perf_counter() - t_render_start

            if result.success:
                print(f"✓ ({t_render:.2f}s)")
                results.append(
                    {
                        "template": template,
                        "status": "✓",
                        "tex": result.tex_path,
                        "pdf": result.pdf_path,
                        "render_time": t_render,
                    }
                )
            else:
                print(f"✗ — {result.error}")
                results.append(
                    {
                        "template": template,
                        "status": "✗",
                        "error": result.error,
                        "render_time": t_render,
                    }
                )

        except DocstreamError as exc:
            t_render = time.perf_counter() - t_render_start
            print(f"✗ — {exc}")
            results.append(
                {
                    "template": template,
                    "status": "✗",
                    "error": str(exc),
                    "render_time": t_render,
                }
            )

    # ── Step 5: Print summary ──────────────────────────────────────────────────
    t_total = t_extract + t_structure + sum(r["render_time"] for r in results)

    print()
    print(_hr("═"))
    print("  Summary")
    print(_hr("═"))
    print(f"  Extract   {t_extract:>6.2f}s  ({len(blocks)} blocks)")
    print(f"  Structure {t_structure:>6.2f}s  (Gemini Flash)")

    for r in results:
        status = r["status"]
        tpl = r["template"]
        rt = r["render_time"]
        if status == "✓":
            print(f"  Render [{tpl:<6}] {rt:>5.2f}s  → {r['pdf']}")
        else:
            print(f"  Render [{tpl:<6}] {rt:>5.2f}s  ✗ {r.get('error', '')}")

    print(_hr())
    print(f"  Total  {t_total:>7.2f}s")
    print(_hr("═"))


if __name__ == "__main__":
    main()
