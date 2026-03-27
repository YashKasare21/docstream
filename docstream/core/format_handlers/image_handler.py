"""
Image Handler — extracts text from JPG/PNG files.
Uses Tesseract OCR via pytesseract.
Preprocesses image for better OCR accuracy.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from docstream import Block


class ImageHandler:
    """Extract text from ``.jpg`` / ``.png`` images via Tesseract OCR.

    Applies image pre-processing (grayscale, denoising, thresholding)
    using Pillow before passing to ``pytesseract`` for improved accuracy.
    """

    def extract(self, file_path: Path) -> "List[Block]":
        """Extract blocks from an image file.

        Args:
            file_path: Path to the ``.jpg`` or ``.png`` image.

        Returns:
            List of ``Block`` objects containing OCR-extracted text.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError
