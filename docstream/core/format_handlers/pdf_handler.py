"""
PDF Handler — wraps existing PDFExtractor.
Handles both digital and scanned PDFs via Tesseract OCR.
"""

from __future__ import annotations

from pathlib import Path

from docstream.core.extractor_v2 import extract_structured
from docstream.models.document import Block, BlockType


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
        doc = extract_structured(str(file_path))
        blocks = []
        for item in doc.get("structure", []):
            if item.get("type") == "heading":
                block_type = BlockType.HEADING
            elif item.get("type") == "table":
                block_type = BlockType.TABLE
            else:
                block_type = BlockType.TEXT
            blocks.append(
                Block(
                    type=block_type,
                    content=item.get("text", ""),
                    metadata={"page": item.get("page", 1)},
                )
            )
        return blocks
