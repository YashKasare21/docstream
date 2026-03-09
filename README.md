# DocStream

[![PyPI version](https://img.shields.io/pypi/v/docstream.svg)](https://pypi.org/project/docstream/)
[![CI](https://github.com/yourusername/docstream/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/docstream/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**DocStream** is a professional open-source document conversion library providing seamless bidirectional conversion between PDF and LaTeX formats, powered by AI models (Gemini & Groq) and a Lua template engine.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          DocStream Pipeline                          │
├─────────────────┬────────────────────┬───────────────────────────────┤
│   EXTRACTION    │    STRUCTURING     │          RENDERING            │
│                 │                    │                               │
│  PDF ─────────► │  Raw Content ────► │  DocumentAST ──────────────►  │
│  LaTeX ────────► │  (text/images/ │  (Gemini / Groq)  │  Lua Template  │ LaTeX / PDF │
│                 │   tables)          │                               │
│  [PyMuPDF]      │  [AI Models]       │  [ieee / report / resume.lua] │
└─────────────────┴────────────────────┴───────────────────────────────┘

Input                                                           Output
  │                                                               │
  ├── PDF  ──► PDFExtractor  ──► GeminiStructurer ──► LuaRenderer ──► LaTeX
  │                              GroqStructurer
  └── LaTeX ──► LaTeXExtractor ──► Structurer    ──► PDFRenderer  ──► PDF
```

---

## Features

- **Bidirectional**: PDF → LaTeX and LaTeX → PDF
- **AI-powered structuring**: Gemini 1.5 Pro and Groq (Llama 3) for intelligent document understanding
- **Template engine**: Lua-based templates (IEEE, Report, Resume) with full customisation support
- **Type-safe**: Pydantic v2 models throughout the entire pipeline
- **Production-ready error handling**: Granular exception hierarchy with automatic fallback between AI models
- **Extensible**: Drop in custom extractors, structurers, or Lua templates

---

## Installation

```bash
# Recommended: using uv
uv add docstream

# Or using pip
pip install docstream
```

### Environment setup

```bash
cp .env.example .env
# Edit .env and add your API keys:
#   GEMINI_API_KEY=...
#   GROQ_API_KEY=...
```

---

## Quick Start

```python
from docstream import DocStream, TemplateType

ds = DocStream()

# PDF → LaTeX
result = ds.pdf_to_latex("paper.pdf", template=TemplateType.IEEE)
result.save("paper.tex")

# LaTeX → PDF
result = ds.latex_to_pdf("report.tex", template=TemplateType.REPORT)
result.save("report.pdf")
```

### With custom configuration

```python
from docstream import DocStream, DocStreamConfig

config = DocStreamConfig(
    gemini_model="gemini-1.5-pro",
    groq_model="llama3-70b-8192",
    extraction_timeout=300,
)
ds = DocStream(config=config)
result = ds.pdf_to_latex("thesis.pdf")
```

### Error handling

```python
from docstream import DocStream
from docstream.exceptions import ExtractionError, StructuringError, RenderingError

ds = DocStream()
try:
    result = ds.pdf_to_latex("document.pdf")
except ExtractionError as e:
    print(f"Extraction failed: {e}")
except StructuringError as e:
    print(f"AI structuring failed: {e}")
except RenderingError as e:
    print(f"Template rendering failed: {e}")
```

---

## Project Structure

```
docstream/
├── docstream/
│   ├── core/
│   │   ├── extractor.py      ← PDF & LaTeX content extraction
│   │   ├── structurer.py     ← AI-powered (Gemini / Groq) structuring
│   │   └── renderer.py       ← Lua template rendering + PDF compilation
│   ├── templates/
│   │   ├── ieee.lua          ← IEEE conference/journal template
│   │   ├── report.lua        ← Technical report template
│   │   └── resume.lua        ← Professional resume template
│   ├── models/
│   │   └── document.py       ← Pydantic models (DocumentAST, Section, Block…)
│   ├── exceptions.py         ← Custom exception hierarchy
│   └── utils/helpers.py      ← File validation, LaTeX sanitisation, etc.
├── tests/                    ← pytest test suite
├── docs/                     ← MkDocs Material documentation
├── pyproject.toml            ← uv-managed, ruff + mypy configured
└── Makefile                  ← make install / test / lint / format / docs
```

---

## Development

```bash
# Install dev dependencies
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

# Serve docs locally
make docs-serve
```

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) and the full
[Contributing Guide](docs/contributing.md) for details on setup, code style,
testing requirements, and the PR process.

---

## License

[MIT](LICENSE) © 2024 Your Name
