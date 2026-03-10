# Contributing to DocStream

Thank you for your interest in contributing! This guide covers everything you need to go from zero to a merged pull request.

---

## Table of Contents

- [Development environment setup](#development-environment-setup)
- [Project structure](#project-structure)
- [Running tests](#running-tests)
- [Adding a new template](#adding-a-new-template)
- [Code style](#code-style)
- [Pull request checklist](#pull-request-checklist)

---

## Development Environment Setup

### Prerequisites

| Tool | Install |
|------|---------|
| Python 3.11+ | [python.org](https://www.python.org/downloads/) |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| pandoc | `sudo apt install pandoc` / `brew install pandoc` |
| texlive-xetex | `sudo apt install texlive-xetex texlive-fonts-recommended texlive-latex-extra` |
| tesseract | `sudo apt install tesseract-ocr` / `brew install tesseract` |

### Step-by-step setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/YashKasare21/docstream.git
cd docstream

# 2. Create and sync the virtual environment
uv venv
uv sync

# 3. Copy the example environment file
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY and GROQ_API_KEY

# 4. Verify everything works
make check
# Expected: lint + typecheck + 118 tests — all passing
```

---

## Project Structure

```
docstream/
├── core/
│   ├── extractor.py      ← PDFExtractor (PyMuPDF + Tesseract OCR)
│   ├── structurer.py     ← DocumentStructurer (Gemini Flash + Groq fallback)
│   └── renderer.py       ← DocumentRenderer (Pandoc Lua writer + XeLaTeX)
├── models/
│   └── document.py       ← Pydantic models (DocumentAST, Block, Section, …)
├── templates/
│   ├── report.lua        ← Pandoc Lua writer — technical report
│   ├── ieee.lua          ← Pandoc Lua writer — IEEE two-column
│   └── resume.lua        ← Pandoc Lua writer — résumé/CV
├── exceptions.py         ← Exception hierarchy
├── cli.py                ← argparse CLI entry point
└── __init__.py           ← Public API: convert, extract, structure, render
tests/
├── test_api.py
├── test_cli.py
├── test_extractor.py
├── test_renderer.py
└── test_structurer.py
```

---

## Running Tests

```bash
# Run full test suite
make test

# Run a single file
uv run pytest tests/test_extractor.py -v

# Run a single test
uv run pytest tests/test_extractor.py::TestPDFExtractor::test_extracts_text -v

# Run with coverage report
uv run pytest --cov=docstream --cov-report=term-missing

# Run tests inside Docker (matches CI environment exactly)
make docker-test
```

---

## Adding a New Template

Templates are Pandoc 3.x Lua custom writers. Here is the full process:

### 1. Create the Lua file

```bash
cp docstream/templates/report.lua docstream/templates/mytheme.lua
```

### 2. Edit the Lua writer

Every template must define a `Writer(doc, opts)` function that returns a LaTeX string. The minimum structure:

```lua
-- mytheme.lua — My custom DocStream template
local function preamble(meta)
  return table.concat({
    "\\documentclass[12pt,a4paper]{article}",
    "\\usepackage{fontspec}",
    -- add your packages here
    "\\begin{document}",
  }, "\n")
end

local function postamble()
  return "\\end{document}\n"
end

function Writer(doc, opts)
  local body = pandoc.write(doc, "latex", opts)
  local meta = doc.meta
  return preamble(meta) .. "\n" .. body .. "\n" .. postamble()
end
```

### 3. Register the template name

In `docstream/core/renderer.py`, add your template to the valid templates set:

```python
_VALID_TEMPLATES: set[str] = {"report", "ieee", "resume", "mytheme"}
```

### 4. Add a test

In `tests/test_renderer.py`, add a parametrize entry:

```python
@pytest.mark.parametrize("template", ["report", "ieee", "resume", "mytheme"])
def test_all_templates_render(template, sample_ast, tmp_path):
    ...
```

### 5. Verify

```bash
make test
uv run docstream templates list  # should now show "mytheme"
```

---

## Code Style

DocStream uses `ruff` for linting and formatting.

```bash
# Check for issues
make lint

# Auto-fix all fixable issues
make format
```

Key rules enforced:
- **E/W** — pycodestyle errors and warnings
- **F** — pyflakes (unused imports, undefined names)
- **I** — isort (import order)
- **N** — pep8-naming (snake_case functions, PascalCase classes)
- **UP** — pyupgrade (modern Python syntax)

Line length limit: **100 characters** (enforced by formatter, not by error).

---

## Pull Request Checklist

Before opening a PR, confirm every item:

- [ ] `make lint` passes with zero warnings
- [ ] `make typecheck` passes (mypy strict=false)
- [ ] `make test` passes — **118+ tests, 0 failures**
- [ ] New code has tests (aim for > 90% coverage on changed files)
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] Docstrings added for any new public function or class
- [ ] PR title follows: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, or `chore:` prefix
- [ ] Branch targets `dev`, not `main` directly

---

## Branch Naming

```
feat/short-description     ← new feature
fix/short-description      ← bug fix
docs/short-description     ← documentation only
refactor/short-description ← internal cleanup
```

---

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions. This project follows the [Contributor Covenant](https://www.contributor-covenant.org/).
