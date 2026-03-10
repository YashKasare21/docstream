# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.1.0] - 2024-03-07

### Added

#### Core Pipeline
- Three-stage PDF → LaTeX + PDF pipeline: **Extraction → Structuring → Rendering**
- `PDFExtractor` using PyMuPDF for high-fidelity text extraction with font metadata (size, bold, italic), bounding boxes, and page numbers
- Scanned PDF fallback: automatic Tesseract OCR when extracted text is below 100 characters per page
- Table detection via PyMuPDF `find_tables()` with Markdown serialisation
- `DocumentStructurer` using **Gemini 1.5 Flash** (primary) with **Groq Llama-3** fallback and exponential-backoff retry (2 attempts per provider)
- `DocumentRenderer` using **Pandoc** JSON pipeline + **XeLaTeX** two-pass compilation for cross-references
- LaTeX log parsing for actionable error messages on compilation failure

#### Templates
- `report.lua` — Academic report (article class, 1-inch margins, lmodern serif)
- `ieee.lua` — IEEE two-column conference format (IEEEtran class)
- `resume.lua` — Clean résumé (compact margins, no section numbers)

#### Public API (Phase 4)
- `docstream.extract(path)` → `list[Block]`
- `docstream.structure(blocks, gemini_key, groq_key)` → `DocumentAST`
- `docstream.render(ast, template, output_dir)` → `ConversionResult`
- `docstream.convert(path, template, output_dir)` → `ConversionResult` (full pipeline in one call)
- Automatic API key loading from `.env` via `python-dotenv`
- Accept `str` or `Path` for all file path arguments

#### CLI
- `docstream convert <pdf> --template <name> --output <dir>`
- `docstream extract <pdf> --output <json>`
- `docstream templates list`
- `docstream --version`
- Threading-based progress spinner on stderr
- Exit code 0 on success, 1 on error

#### Data Models (Pydantic v2)
- `DocumentAST`, `DocumentMetadata`, `Section`, `Block`, `Table`, `Image`
- `ConversionResult` with `tex_path`, `pdf_path`, `template_used`, `processing_time_seconds`, `error`
- `BlockType`, `ListType` enums

#### Exceptions
- Full hierarchy: `DocstreamError` → `ExtractionError`, `StructuringError`, `RenderingError`, `ValidationError`, `APIError`, `TemplateError`, `CompilationError`, `FileError`, `TimeoutError`, `ModelError`

#### Docker
- `docker/Dockerfile.dev` — development image with all system tools
- `docker/Dockerfile.prod` — multi-stage production image, non-root user
- `docker-compose.yml` — api, worker, redis:7, postgres:16 with healthchecks
- `.dockerignore` — excludes `.git`, `.venv`, `__pycache__`, `tests/`, `docs/`
- `make docker-build`, `make docker-run`, `make docker-test`

#### Developer Experience
- `Makefile` with `install`, `test`, `lint`, `format`, `typecheck`, `check`, `docs`, `clean`, `docker-*` targets
- GitHub Actions CI (pytest + ruff + mypy on push/PR to `main` and `dev`)
- GitHub Actions PyPI publish workflow (triggered by release tag)
- 118 pytest tests across 5 test files
- MkDocs Material documentation site

---

[Unreleased]: https://github.com/YashKasare21/docstream/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YashKasare21/docstream/releases/tag/v0.1.0
