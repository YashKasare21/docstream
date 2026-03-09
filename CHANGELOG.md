# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffold with full package structure
- `DocStream` main class with `pdf_to_latex` and `latex_to_pdf` methods
- Three-stage pipeline: Extractor → Structurer → Renderer
- `PDFExtractor` using PyMuPDF for PDF parsing
- `LaTeXExtractor` for LaTeX source parsing
- `GeminiStructurer` for AI-powered content structuring via Gemini
- `GroqStructurer` for AI-powered content structuring via Groq
- `LuaRenderer` for template-based LaTeX generation
- `PDFRenderer` for LaTeX → PDF compilation
- Pydantic models: `DocumentAST`, `Section`, `Block`, `Table`, `Image`, `ConversionResult`
- Custom exception hierarchy: `DocstreamError`, `ExtractionError`, `StructuringError`, `RenderingError`, `ValidationError`
- Built-in Lua templates: `ieee`, `report`, `resume`
- Utility helpers for file validation, LaTeX sanitisation, text chunking
- Comprehensive test suite with shared pytest fixtures
- GitHub Actions CI workflow (pytest + ruff + mypy on push/PR)
- GitHub Actions publish workflow (auto-publish to PyPI on release tag)
- GitHub issue and PR templates
- MkDocs Material documentation site
- `Makefile` with `install`, `test`, `lint`, `format`, `typecheck`, `check`, `docs`, `clean` targets
- MIT License

## [0.1.0] - Unreleased

_Initial development release — not yet published to PyPI._

[Unreleased]: https://github.com/yourusername/docstream/compare/HEAD...HEAD
[0.1.0]: https://github.com/yourusername/docstream/releases/tag/v0.1.0
