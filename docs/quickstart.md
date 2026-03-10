# Quick Start

Get DocStream running in under 5 minutes.

---

## Install

```bash
pip install docstream
```

Or with uv (recommended):

```bash
uv add docstream
```

**System dependencies** (required for PDF rendering):

=== "Ubuntu / Debian"
    ```bash
    sudo apt install pandoc texlive-xetex texlive-fonts-recommended \
                     texlive-latex-extra tesseract-ocr
    ```

=== "macOS"
    ```bash
    brew install pandoc tesseract
    brew install --cask mactex
    ```

=== "Docker"
    ```bash
    # All system deps pre-installed
    docker pull ghcr.io/yashkasare21/docstream:latest
    ```

---

## Set Up API Keys

DocStream uses Gemini 1.5 Flash for document structuring, with Groq as a fallback.

1. Get a free Gemini key at [aistudio.google.com](https://aistudio.google.com/)
2. Optionally get a Groq key at [console.groq.com](https://console.groq.com/) (fallback)

Create a `.env` file in your project root:

```env
GEMINI_API_KEY=your-gemini-api-key-here
GROQ_API_KEY=your-groq-api-key-here   # optional
```

DocStream loads these automatically — no extra setup needed.

---

## Convert Your First PDF

### CLI

```bash
docstream convert paper.pdf --template report --output ./out
```

Expected output:

```
✓ Extracted 42 blocks from paper.pdf
✓ Structured document with Gemini Flash (1.8s)
✓ Rendered with template: report
──────────────────────────────────────────
  LaTeX  ./out/paper.tex
  PDF    ./out/paper.pdf
  Time   4.2s
```

### Python API

```python
import docstream

result = docstream.convert("paper.pdf", template="report", output_dir="./out")

print(result.pdf_path)          # ./out/paper.pdf
print(result.tex_path)          # ./out/paper.tex
print(result.processing_time_seconds)  # 4.2
print(result.success)           # True
```

---

## Switch Templates

Three templates are built in:

| Template | Use case | Document class |
|----------|----------|----------------|
| `report` | Technical reports, theses | `article` — serif, 1in margins |
| `ieee` | Conference papers | `IEEEtran` — two-column, 10pt |
| `resume` | CVs and résumés | `article` — compact, 0.6in margins |

```bash
# CLI
docstream convert paper.pdf --template ieee
docstream convert cv.pdf    --template resume

# Python
result = docstream.convert("paper.pdf", template="ieee")
```

List all available templates:

```bash
docstream templates list
```

---

## Use the Python API Step by Step

The `convert()` function is a convenience wrapper. You can also call each stage individually:

### Stage 1 — Extract

```python
import docstream

# Returns List[Block] — each block has content, font_size, is_bold, page_number
blocks = docstream.extract("paper.pdf")

print(f"Extracted {len(blocks)} blocks")
for block in blocks[:3]:
    print(f"  [{block.type}] p{block.page_number}: {block.content[:60]}")
```

### Stage 2 — Structure

```python
from docstream.models.document import DocumentAST

# Sends blocks to Gemini Flash → returns a typed DocumentAST
ast: DocumentAST = docstream.structure(blocks)

print(f"Title: {ast.title}")
print(f"Authors: {ast.metadata.authors}")
print(f"Sections: {[s.title for s in ast.sections]}")
```

You can also pass keys explicitly (they override the `.env` values):

```python
ast = docstream.structure(
    blocks,
    gemini_key="my-gemini-key",
    groq_key="my-groq-key",
)
```

### Stage 3 — Render

```python
from pathlib import Path

result = docstream.render(ast, template="ieee", output_dir=Path("./out"))

if result.success:
    print(f"PDF saved to {result.pdf_path}")
else:
    print(f"Render failed: {result.error}")
```

---

## Error Handling

All DocStream errors inherit from `DocstreamError`:

```python
from docstream.exceptions import (
    DocstreamError,
    ExtractionError,
    StructuringError,
    RenderingError,
)

try:
    result = docstream.convert("paper.pdf")
except ExtractionError as e:
    print(f"Could not read PDF: {e}")
except StructuringError as e:
    print(f"AI structuring failed: {e}")
except RenderingError as e:
    print(f"LaTeX compilation failed: {e}")
except DocstreamError as e:
    print(f"Unexpected error: {e}")
```

---

## Next Steps

- **[Architecture](architecture.md)** — understand the 3-stage pipeline in depth
- **[Templates](templates.md)** — customise or create new Lua templates
- **[Self-Hosting](self-hosting.md)** — run DocStream in Docker
- **[API Reference](api-reference.md)** — full function signatures and types
- **[Contributing](contributing.md)** — add features, fix bugs, write templates
