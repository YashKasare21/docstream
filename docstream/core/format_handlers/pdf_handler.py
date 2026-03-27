"""
PDF Handler — wraps existing PDFExtractor.
Handles both digital and scanned PDFs via Tesseract OCR.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from docstream import Block


class PDFHandler:
    """Extract blocks from PDF files using the existing ``PDFExtractor``.

    Handles both digital (text-layer) PDFs and scanned PDFs.
    Scanned documents are routed through Tesseract OCR automatically.
    """

    def extract(self, file_path: Path) -> "List[Block]":
        """Extract blocks from a PDF file.

        Args:
            file_path: Path to the ``.pdf`` file.

        Returns:
            List of ``Block`` objects with text, type, and metadata.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError
