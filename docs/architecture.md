# Architecture

DocStream implements a strict three-stage pipeline — **Extract → Structure → Render** — where each stage has a single responsibility, a typed input/output contract, and is independently testable.

---

## Pipeline Overview

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                         DocStream Pipeline                              │
  ├──────────────────┬───────────────────────────┬────────────────────────-─┤
  │   STAGE 1        │   STAGE 2                 │   STAGE 3               │
  │   EXTRACTION     │   STRUCTURING             │   RENDERING             │
  │                  │                           │                         │
  │  PDF file        │  List[Block]              │  DocumentAST            │
  │     │            │       │                   │       │                 │
  │     ▼            │       ▼                   │       ▼                 │
  │  PDFExtractor    │  DocumentStructurer        │  DocumentRenderer      │
  │  (PyMuPDF)       │  (Gemini Flash)            │  (Pandoc + XeLaTeX)   │
  │     │            │  (Groq fallback)           │       │                │
  │     │  font size │       │  JSON → AST        │       │  Lua writer    │
  │     │  bold/ital │       │  validation        │       │  2-pass LaTeX  │
  │     │  bbox      │       │                   │       │                 │
  │     ▼            │       ▼                   │       ▼                 │
  │  List[Block]     │  DocumentAST              │  .tex + .pdf            │
  └──────────────────┴───────────────────────────┴─────────────────────────┘
```

Data flows through the pipeline as strongly-typed Pydantic models:

```
PDF → [Block, Block, ...] → DocumentAST → ConversionResult(tex_path, pdf_path)
```

---

## Stage 1 — Extraction

**File:** `docstream/core/extractor.py`  
**Class:** `PDFExtractor`  
**Input:** PDF file path  
**Output:** `list[Block]`

### What it does

`PDFExtractor` opens the PDF with PyMuPDF (`fitz`) and iterates over every page. For each page it calls `page.get_text("dict")` which returns a rich JSON structure containing every text span with:

- font name and size
- bold / italic flags derived from font name heuristics
- bounding box coordinates (x0, y0, x1, y1)
- page number

Spans within the same block are concatenated into a single `Block` object. Blocks shorter than 3 characters are discarded as noise.

### OCR fallback

If the total extracted text for a page is under 100 characters (indicating a scanned/image-only page), the page is rendered to a PIL `Image` at 300 DPI and passed to `pytesseract.image_to_string()`. The OCR result is returned as a plain-text Block.

### Table detection

PyMuPDF's `page.find_tables()` is called on every page. Each detected table is converted to a Markdown string (header row + `---` separator + data rows) and stored as a `BlockType.TABLE` block.

---

## Stage 2 — Structuring

**File:** `docstream/core/structurer.py`  
**Class:** `DocumentStructurer`  
**Input:** `list[Block]`  
**Output:** `DocumentAST`

### What it does

The structurer serialises the blocks to JSON and sends them to an AI model with a system prompt asking for a structured document hierarchy (title, sections, subsections, metadata). The model responds with a JSON object that is validated against the `DocumentAST` Pydantic schema.

### Provider chain

```
Attempt 1 → Gemini 1.5 Flash   (fast, cheap, 1M context window)
    ↓ fails
Attempt 2 → Gemini 1.5 Flash   (retry with backoff)
    ↓ fails
Attempt 3 → Groq Llama-3 70B   (fast inference, good fallback)
    ↓ fails
Attempt 4 → Groq Llama-3 70B   (retry with backoff)
    ↓ fails
raises StructuringError
```

Retry delay: 2 seconds between attempts within the same provider.

### Why AI for structuring?

Heuristic-based structuring (comparing font sizes to detect headings) breaks on the enormous variety of PDF formatting. AI models generalise across all fonts, layouts, and document types without any per-document tuning.

---

## Stage 3 — Rendering

**File:** `docstream/core/renderer.py`  
**Class:** `DocumentRenderer`  
**Input:** `DocumentAST`, output directory  
**Output:** `ConversionResult`

### What it does

1. **Pandoc JSON** — `DocumentAST` is serialised to Pandoc's native JSON format (blocks, inlines, metadata).
2. **Pandoc + Lua writer** — `pandoc -f json -t <template.lua>` converts the JSON to LaTeX. The Lua writer has full control over the LaTeX preamble (document class, packages, margins).
3. **XeLaTeX compilation** — `xelatex -interaction=nonstopmode` is run twice in a temporary directory. Two passes are required so `\tableofcontents` and cross-references resolve correctly.
4. **Log parsing** — The `.log` file is scanned for lines starting with `!` (LaTeX errors). The first error is surfaced in `ConversionResult.error`.
5. **Copy outputs** — `document.tex` and `document.pdf` are copied to the user-specified output directory.

### Why XeLaTeX instead of pdfLaTeX?

XeLaTeX supports Unicode natively and can use system fonts via `fontspec`. This matters for documents containing non-ASCII characters, author names, or specialised mathematical symbols. pdfLaTeX requires explicit encoding declarations that are fragile for AI-generated content.

---

## Data Models

```
DocumentAST
├── title: str
├── metadata: DocumentMetadata
│   ├── title, authors, abstract, keywords
│   └── date, document_type, language
├── sections: List[Section]
│   ├── title, level (1-6), content: str
│   └── subsections: List[Section]  (recursive)
├── blocks: List[Block]
│   ├── type: BlockType  (TEXT, HEADING, LIST, TABLE, CODE, IMAGE)
│   ├── content: str
│   ├── page_number: int
│   ├── font_size, is_bold, is_italic
│   └── bbox: tuple[float, float, float, float]
├── tables: List[Table]
└── images: List[Image]
```

---

## Template System

Templates are **Pandoc 3.x Lua custom writers** — standalone `.lua` files that receive the full Pandoc AST and return a LaTeX string.

```
docstream/templates/
├── report.lua   ← article class, 1-inch margins, lmodern serif
├── ieee.lua     ← IEEEtran class, two-column, 10pt
└── resume.lua   ← article class, compact 0.6in margins, no section numbers
```

Each template defines a `Writer(doc, opts)` function. It processes the Pandoc AST's `doc.blocks` list, dispatching on block type (`Para`, `Header`, `BulletList`, `CodeBlock`, etc.) and emitting the corresponding LaTeX commands.

### Adding a new template

1. Copy `docstream/templates/report.lua` to `docstream/templates/mytheme.lua`
2. Modify the `Writer()` function and the preamble
3. Add `"mytheme"` to `_VALID_TEMPLATES` in `docstream/core/renderer.py`
4. Use it: `docstream convert paper.pdf --template mytheme`

---

## Technology Choices and Rationale

### PyMuPDF over pdfminer.six

| | PyMuPDF | pdfminer.six |
|---|---|---|
| Speed | ~10× faster | Slower |
| Font metadata | Full (size, flags, bbox) | Limited |
| Table detection | Built-in `find_tables()` | None |
| Image extraction | Yes | No |
| Maintenance | Active | Slow |

PyMuPDF's `get_text("dict")` gives per-span font metadata in one call. pdfminer requires building a layout analysis tree and manually walking it to recover the same information.

### Gemini Flash over GPT-4

| | Gemini 1.5 Flash | GPT-4o |
|---|---|---|
| Context window | 1,000,000 tokens | 128,000 tokens |
| Speed | ~2s | ~8s |
| Cost | $0.075 / 1M tokens | $5 / 1M tokens |
| Long PDFs | Handles entire document | Requires chunking |

A 300-page academic paper is ~300,000 tokens. GPT-4o cannot handle it in one call; Gemini Flash can. Groq is used as a fallback because it offers sub-second inference for smaller documents.

### Pandoc over jinja2 templating

Pandoc's Lua writer receives the full AST — not raw text. This means the template has access to structured information (is this a heading? what level?) rather than doing regex parsing on a string. It also means the same `.lua` file works for any input format Pandoc supports, not just DocStream.

### Pydantic v2 over dataclasses

Pydantic v2 provides runtime validation, JSON serialisation/deserialisation, and IDE autocompletion in one package. The AI model's JSON response is validated directly against the `DocumentAST` schema — invalid responses raise `ValidationError` immediately rather than causing confusing errors downstream.

---

## Error Flow

```
extract()
  └── ExtractionError   ← file not found, corrupted PDF, Tesseract failure

structure()
  └── StructuringError  ← all AI providers failed after retries

render()
  ├── RenderingError    ← Pandoc not found, Lua writer error
  └── RenderingError    ← xelatex compilation failed (log message included)
```

All exceptions inherit from `DocstreamError(Exception)` so a single `except DocstreamError` catches everything.
