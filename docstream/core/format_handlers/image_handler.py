"""
Image Handler — extracts text from JPG/PNG files.
Uses Tesseract OCR via pytesseract.
Preprocesses image for better OCR accuracy.
"""

from __future__ import annotations

from pathlib import Path

from docstream.exceptions import ExtractionError
from docstream.models.document import Block, BlockType


class ImageHandler:
    """Extract text from ``.jpg`` / ``.png`` images via Tesseract OCR.

    Applies image pre-processing (grayscale, optional upscaling)
    using Pillow before passing to ``pytesseract`` for improved accuracy.
    """

    def extract(self, file_path: Path) -> list[Block]:
        """Extract blocks from an image file.

        Args:
            file_path: Path to the ``.jpg`` or ``.png`` image.

        Returns:
            List of ``Block`` objects containing OCR-extracted text.

        Raises:
            ExtractionError: If the image cannot be opened or OCR yields
                             fewer than 20 characters.
        """
        try:
            from PIL import Image, UnidentifiedImageError  # Pillow
        except ImportError as exc:
            raise ExtractionError(
                "Pillow is required for image extraction. "
                "Install with: pip install Pillow"
            ) from exc

        try:
            import pytesseract
        except ImportError as exc:
            raise ExtractionError(
                "pytesseract is required for image extraction. "
                "Install with: pip install pytesseract"
            ) from exc

        # Open image
        try:
            img = Image.open(file_path)
        except Exception as exc:
            raise ExtractionError(
                "Could not open image file. "
                "Supported formats: JPG, PNG."
            ) from exc

        # Pre-process: grayscale
        img = img.convert("L")

        # Upscale if too small for reliable OCR
        width, height = img.size
        if width < 1000:
            scale = 1000 / width
            img = img.resize(
                (1000, int(height * scale)),
                Image.LANCZOS,
            )

        # Run OCR
        text: str = pytesseract.image_to_string(img, lang="eng")

        if len(text.strip()) < 20:
            raise ExtractionError(
                "Could not extract text from image. "
                "The image may be too low resolution or contain no text."
            )

        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 3]

        return [
            Block(
                type=BlockType.TEXT,
                content=para,
                page_number=1,
                font_size=12.0,
                is_bold=False,
                is_italic=False,
                bbox=(0.0, 0.0, 0.0, 0.0),
            )
            for para in paragraphs
        ]
