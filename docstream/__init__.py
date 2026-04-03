"""
Docstream — PDF to LaTeX conversion library.

Simple 3-step pipeline:
1. Extract structured text from PDF
2. AI generates LaTeX from template skeleton
3. XeLaTeX compiles to PDF

Basic usage:
    import docstream
    result = docstream.convert("paper.pdf", template="ieee")
    print(result.tex_path)   # Path to .tex file
    print(result.pdf_path)   # Path to .pdf file
"""

from __future__ import annotations

__version__ = "0.2.0"
__all__ = ["convert", "extract", "generate", "ConversionResult"]

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConversionResult:
    """Result of a PDF conversion operation."""

    def __init__(
        self,
        success: bool,
        tex_path: Path | None = None,
        pdf_path: Path | None = None,
        error: str | None = None,
        processing_time: float = 0.0,
        template_used: str = "",
    ):
        """Initialize conversion result.

        Args:
            success: Whether the conversion succeeded
            tex_path: Path to the generated .tex file
            pdf_path: Path to the generated .pdf file
            error: Error message if conversion failed
            processing_time: Total processing time in seconds
            template_used: Name of the template used
        """
        self.success = success
        self.tex_path = tex_path
        self.pdf_path = pdf_path
        self.error = error
        self.processing_time = processing_time
        self.template_used = template_used

    def __repr__(self) -> str:
        """Return string representation of conversion result."""
        if self.success:
            return (
                f"ConversionResult(success=True, "
                f"template={self.template_used!r}, "
                f"pdf={self.pdf_path})"
            )
        return f"ConversionResult(success=False, error={self.error!r})"


def convert(
    pdf_path: str | Path,
    template: str = "report",
    output_dir: str | Path = "./docstream_output",
    ai_provider=None,
) -> ConversionResult:
    """
    Convert a PDF to LaTeX and PDF.

    This is the main entry point for Docstream.

    Pipeline:
    1. Extract structured text from PDF using PyMuPDF
    2. AI fills LaTeX template skeleton with content
    3. XeLaTeX compiles LaTeX to PDF

    Args:
        pdf_path: Path to the input PDF file
        template: 'report' or 'ieee' (default: 'report')
        output_dir: Directory for output files
        ai_provider: Optional custom AI provider chain

    Returns:
        ConversionResult with tex_path and pdf_path on success

    Example:
        result = docstream.convert("paper.pdf", template="ieee")
        if result.success:
            print(f"LaTeX: {result.tex_path}")
            print(f"PDF: {result.pdf_path}")
    """
    import time
    from docstream.core.extractor_v2 import extract_structured
    from docstream.core.generator import generate_latex
    from docstream.core.compiler import compile_latex
    from docstream.exceptions import DocstreamError

    start_time = time.time()
    output_dir = Path(output_dir)

    try:
        # Step 1: Extract
        logger.info(f"Step 1/3: Extracting from {Path(pdf_path).name}")
        document = extract_structured(pdf_path)
        logger.info(
            f"Extracted {len(document['structure'])} blocks"
        )

        # Step 2: Generate LaTeX
        logger.info(f"Step 2/3: Generating LaTeX ({template} template)")
        latex = generate_latex(document, template, ai_provider)
        logger.info(f"Generated {len(latex)} chars of LaTeX")

        # Step 3: Compile
        logger.info("Step 3/3: Compiling with XeLaTeX")
        tex_path, pdf_path_out = compile_latex(
            latex, output_dir
        )

        processing_time = round(time.time() - start_time, 1)
        logger.info(f"Conversion complete in {processing_time}s")

        return ConversionResult(
            success=True,
            tex_path=tex_path,
            pdf_path=pdf_path_out,
            processing_time=processing_time,
            template_used=template,
        )

    except DocstreamError as e:
        processing_time = round(time.time() - start_time, 1)
        logger.error(f"Conversion failed: {e}")
        return ConversionResult(
            success=False,
            error=str(e),
            processing_time=processing_time,
            template_used=template,
        )

    except Exception as e:
        processing_time = round(time.time() - start_time, 1)
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return ConversionResult(
            success=False,
            error=f"Unexpected error: {e}",
            processing_time=processing_time,
            template_used=template,
        )


def extract(pdf_path: str | Path) -> dict:
    """
    Extract structured content from a PDF.

    Returns raw structured document dict.
    Useful for inspecting extraction quality before converting.
    """
    from docstream.core.extractor_v2 import extract_structured
    return extract_structured(pdf_path)


def generate(
    document: dict,
    template: str = "report",
    ai_provider=None,
) -> str:
    """
    Generate LaTeX from extracted document content.

    Returns complete LaTeX string.
    Useful for inspecting AI output before compiling.
    """
    from docstream.core.generator import generate_latex
    return generate_latex(document, template, ai_provider)
