"""
DocStream: Professional Document Conversion Library

DocStream provides seamless bidirectional conversion between PDF and LaTeX formats
with AI-powered content extraction and template-based rendering.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

__version__ = "0.2.0-dev"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__license__ = "MIT"

# Core classes
from docstream.core.docstream import DocStream, DocStreamConfig

# Phase 1-3 core classes — imported here so patch("docstream.X") works in tests
from docstream.core.extractor import PDFExtractor
from docstream.core.renderer import DocumentRenderer, TemplateInfo, TemplateType
from docstream.core.structurer import DocumentStructurer

# Exceptions
from docstream.exceptions import (
    AIUnavailableError,
    DocstreamError,
    ExtractionError,
    RenderingError,
    StructuringError,
    ValidationError,
)

# Models
from docstream.models.document import (
    Block,
    BlockType,
    ConversionResult,
    DocumentAST,
    DocumentMetadata,
    DocumentType,
    Image,
    ListType,
    Section,
    SemanticChunk,
    SemanticDocument,
    Table,
)


def _load_env() -> None:
    """Load .env file if present (silent if python-dotenv is missing)."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Public functional API
# ---------------------------------------------------------------------------


def extract(path: str | Path) -> list[Block]:
    """Extract raw content blocks from any supported document format.

    Supports: PDF, DOCX, PPTX, JPG, PNG, MD, TXT.

    Args:
        path: Path to the input file (str or Path).

    Returns:
        List of Block objects with text, font metadata, bounding boxes, etc.

    Raises:
        ExtractionError: If the file cannot be read, parsed, or the
                         format is not supported.
    """
    _load_env()
    from docstream.core.format_router import FormatRouter

    router = FormatRouter()
    return router.extract(Path(path))


def analyze(
    blocks_or_path: list[Block] | str | Path,
    ai_provider: object | None = None,
) -> SemanticDocument:
    """Semantically analyze a document.

    Accepts either pre-extracted blocks or a file path (which will be
    extracted automatically before analysis).

    Args:
        blocks_or_path: ``List[Block]`` from ``extract()`` **or** a file path
                        (str or Path) to any supported format.
        ai_provider:    Optional ``AIProviderChain`` instance. A new chain is
                        built automatically from environment variables if not
                        supplied.

    Returns:
        ``SemanticDocument`` with document type, chunks, and metadata.

    Raises:
        ExtractionError:    If the file cannot be read or format is unsupported.
        StructuringError:   If the AI response is malformed.
        AIUnavailableError: If no AI providers are available.
    """
    _load_env()
    from docstream.core.format_router import FormatRouter
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    if not isinstance(blocks_or_path, list):
        blocks_or_path = FormatRouter().extract(Path(blocks_or_path))

    return SemanticAnalyzer(ai_provider).analyze(blocks_or_path)


def supported_formats() -> list[str]:
    """Return all supported input file extensions.

    Returns:
        List of extension strings, e.g. ``['.pdf', '.docx', ...]``.
    """
    from docstream.core.format_router import FormatRouter

    return FormatRouter.supported_extensions()


def structure(
    blocks: list[Block],
    gemini_key: str | None = None,
    groq_key: str | None = None,
) -> DocumentAST:
    """Structure raw blocks into a DocumentAST using AI.

    API keys are loaded from GEMINI_API_KEY / GROQ_API_KEY environment
    variables automatically when not supplied explicitly.

    Args:
        blocks: List of Block objects (output of ``extract()``).
        gemini_key: Google Gemini API key (overrides env).
        groq_key:   Groq API key (overrides env).

    Returns:
        DocumentAST representing the fully structured document.

    Raises:
        StructuringError: If all AI providers fail.
    """
    _load_env()
    gk = gemini_key or os.environ.get("GEMINI_API_KEY", "")
    rk = groq_key or os.environ.get("GROQ_API_KEY")
    structurer = DocumentStructurer(gemini_key=gk, groq_key=rk)
    return structurer.structure(blocks)


def render(
    ast: DocumentAST,
    template: str = "report",
    output_dir: str | Path = "./out",
) -> ConversionResult:
    """Render a DocumentAST to ``.tex`` and ``.pdf`` via Pandoc + XeLaTeX.

    Args:
        ast:        DocumentAST to render.
        template:   Template name — ``"report"``, ``"ieee"``, or ``"resume"``.
        output_dir: Directory for output files (created if absent).

    Returns:
        ConversionResult with ``tex_path``, ``pdf_path``, and timing info.

    Raises:
        RenderingError: If Pandoc or XeLaTeX compilation fails.
        ValueError:     If *template* is not one of the built-in names.
    """
    renderer = DocumentRenderer(template=template)
    return renderer.render(ast, Path(output_dir))


def convert(
    path: str | Path,
    template: str = "report",
    output_dir: str | Path = "./out",
) -> ConversionResult:
    """Convert a PDF to structured LaTeX + PDF in one call.

    Internally chains: ``extract()`` → ``structure()`` → ``render()``.

    Args:
        path:       Path to the input PDF file.
        template:   Output template — ``"report"``, ``"ieee"``, or ``"resume"``.
        output_dir: Directory for output files (default: ``"./out"``).

    Returns:
        ConversionResult with ``tex_path``, ``pdf_path``, and timing info.

    Example::

        from docstream import convert
        result = convert("paper.pdf", template="ieee", output_dir="./out")
        print(result.pdf_path)
    """
    blocks = extract(path)
    ast = structure(blocks)
    return render(ast, template=template, output_dir=Path(output_dir))


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

__all__ = [
    # Version
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    # Functional API
    "analyze",
    "convert",
    "extract",
    "structure",
    "render",
    "supported_formats",
    # Core classes
    "DocStream",
    "DocStreamConfig",
    "PDFExtractor",
    "DocumentStructurer",
    "DocumentRenderer",
    # Data models
    "DocumentAST",
    "DocumentMetadata",
    "Section",
    "Block",
    "Table",
    "Image",
    "ConversionResult",
    "BlockType",
    "ListType",
    # Template system
    "TemplateType",
    "TemplateInfo",
    # v2 semantic models
    "DocumentType",
    "SemanticChunk",
    "SemanticDocument",
    # Exceptions
    "AIUnavailableError",
    "DocstreamError",
    "ExtractionError",
    "StructuringError",
    "RenderingError",
    "ValidationError",
]

# Package metadata
PACKAGE_NAME = "docstream"
DESCRIPTION = "Professional document conversion library (PDF ↔ LaTeX)"
URL = "https://github.com/YashKasare21/docstream"

logging.getLogger(__name__).addHandler(logging.NullHandler())
