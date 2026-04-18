"""
PDF Handler — wraps existing PDFExtractor.
Handles both digital and scanned PDFs via Tesseract OCR.
"""

from __future__ import annotations

from pathlib import Path

from docstream.core.extractor import PDFExtractor
from docstream.models.document import Block


class PDFHandler:
    """Extract blocks from PDF files using the existing ``PDFExtractor``.

    Handles both digital (text-layer) PDFs and scanned PDFs.
    Scanned documents are routed through Tesseract OCR automatically
    by the underlying ``PDFExtractor``.
    """

    def extract(self, file_path: Path) -> list[Block]:
        """Extract blocks from a PDF file.

        Args:
            file_path: Path to the ``.pdf`` file.

        Returns:
            List of ``Block`` objects with text, type, and metadata.

        Raises:
            ExtractionError: If the file cannot be read or parsed.
        """
        extractor = PDFExtractor(file_path)
        return extractor.extract()
