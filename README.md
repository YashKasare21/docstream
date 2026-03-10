# DocStream

[![CI](https://github.com/YashKasare21/docstream/actions/workflows/ci.yml/badge.svg)](https://github.com/YashKasare21/docstream/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**DocStream** is a professional open-source document conversion library that turns any PDF into structured LaTeX + PDF output — powered by AI (Gemini & Groq) and Pandoc Lua templates.

---

## How It Works

DocStream uses a **3-stage pipeline**:

```
Stage 1 — EXTRACTION        Stage 2 — STRUCTURING       Stage 3 — RENDERING
─────────────────────       ──────────────────────       ───────────────────────────
                                                         
  PDF file                    List[Block]                  DocumentAST
     │                             │                            │
     ▼                             ▼                            ▼
  PDFExtractor               DocumentStructurer          DocumentRenderer
  (PyMuPDF)                  (Gemini Flash)              (Pandoc + XeLaTeX)
     │                       (Groq fallback)                    │
     │  font metadata,            │                             │  Lua writer
     │  bounding boxes,           │  JSON → AST                │  (report/ieee/resume)
     │  tables, OCR               │  validation                 │
     ▼                             ▼                            ▼
  List[Block]               DocumentAST                  .tex  +  .pdf
```

**Stage 1 — Extraction** (`PDFExtractor`)
- Reads each PDF page with PyMuPDF
- Extracts text blocks with font size, bold/italic flags, bounding boxes, and page numbers
- Detects scanned PDFs (< 100 chars) and falls back to Tesseract OCR
- Detects tables with `find_tables()` and converts them to Markdown

**Stage 2 — Structuring** (`DocumentStructurer`)
- Sends extracted blocks to Gemini 1.5 Flash (primary) or Groq Llama-3 (fallback)
- Parses the AI JSON response into a validated `DocumentAST`
- Retries with exponential backoff (2 retries per provider)

**Stage 3 — Rendering** (`DocumentRenderer`)
- Converts `DocumentAST` to Pandoc JSON format
- Runs `pandoc -f json -t <template.lua>` to generate LaTeX
- Compiles with `xelatex -interaction=nonstopmode` (twice for cross-references)
- Parses `.log` for `!` error lines and surfaces them clearly

---

## Architecture

```
docstream/
├── docstream/
│   ├── __init__.py           ← Public API: convert(), extract(), structure(), render()
│   ├── cli.py                ← CLI entry point (argparse)
│   ├── core/
│   │   ├── extractor.py      ← PDFExtractor (PyMuPDF + Tesseract OCR fallback)
│   │   ├── structurer.py     ← DocumentStructurer (Gemini Flash + Groq fallback)
│   │   └── renderer.py       ← DocumentRenderer (Pandoc + XeLaTeX)
│   ├── templates/
│   │   ├── report.lua        ← Pandoc Lua writer: academic report
│   │   ├── ieee.lua          ← Pandoc Lua writer: IEEE two-column
│   │   └── resume.lua        ← Pandoc Lua writer: compact resume
│   ├── models/
│   │   └── document.py       ← Pydantic models (DocumentAST, Block, ConversionResult…)
│   └── exceptions.py         ← Exception hierarchy
├── tests/                    ← pytest suite (64 tests)
├── pyproject.toml            ← uv-managed, ruff + mypy configured
└── Makefile                  ← make install / test / lint / docs
```

---

## Installation

```bash
# Recommended: using uv
uv add docstream

# Or using pip
pip install docstream
```

### System dependencies

```bash
# Pandoc (required for LaTeX generation)
sudo apt install pandoc -y

# XeLaTeX (required for PDF compilation)
sudo apt install texlive-xetex texlive-latex-extra texlive-fonts-recommended -y

# Tesseract (optional — only needed for scanned PDFs)
sudo apt install tesseract-ocr -y
```

### API keys

```bash
cp .env.example .env
# Edit .env:
#   GEMINI_API_KEY=your-gemini-key
#   GROQ_API_KEY=your-groq-key   (optional fallback)
```

---

## Python API

### One-liner conversion

```python
from docstream import convert

result = convert("paper.pdf", template="ieee", output_dir="./out")
print(result.pdf_path)   # ./out/document.pdf
print(result.tex_path)   # ./out/document.tex
```

### Step-by-step pipeline

```python
from docstream import extract, structure, render

# Stage 1 — extract raw blocks from PDF
blocks = extract("paper.pdf")
print(f"Extracted {len(blocks)} blocks")

# Stage 2 — structure blocks into an AST with AI
ast = structure(blocks)
print(f"Title: {ast.title}, Sections: {len(ast.sections)}")

# Stage 3 — render AST to LaTeX + PDF
result = render(ast, template="report", output_dir="./out")
if result.success:
    print(f"PDF saved to {result.pdf_path}")
else:
    print(f"Rendering failed: {result.error}")
```

### With explicit API keys

```python
from docstream import extract, structure

blocks = extract("paper.pdf")
ast = structure(blocks, gemini_key="your-key", groq_key="your-groq-key")
```

### Error handling

```python
from docstream import convert
from docstream.exceptions import ExtractionError, StructuringError, RenderingError

try:
    result = convert("document.pdf", template="report")
except ExtractionError as e:
    print(f"Could not read PDF: {e}")
except StructuringError as e:
    print(f"AI structuring failed: {e}")
except RenderingError as e:
    print(f"LaTeX compilation failed: {e}")
```

### Available templates

| Name     | Description                                  |
|----------|----------------------------------------------|
| `report` | Academic report — article class, 1in margins |
| `ieee`   | IEEE two-column conference format             |
| `resume` | Clean resume — compact, no section numbers   |

---

## CLI

### Convert a PDF

```bash
# Full pipeline: PDF → LaTeX + PDF
docstream convert paper.pdf --template ieee --output ./out

# Short flags
docstream convert paper.pdf -t report -o ./output
```

### Extract raw blocks

```bash
# Print extracted blocks as JSON to stdout
docstream extract paper.pdf

# Save to file
docstream extract paper.pdf --output blocks.json
```

### List templates

```bash
docstream templates list
```

### Version

```bash
docstream --version
```

---

## Development

```bash
# Install all dependencies
make install

# Run tests
make test

# Lint + format check
make lint

# Auto-fix formatting
make format

# Type check
make typecheck

# All checks at once
make check
```

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, code style, and PR process.

---

## License

[MIT](LICENSE) © 2024 DocStream Contributors
