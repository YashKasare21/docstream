"""
Format Router — detects input file type and routes to
the correct format handler for extraction.

Supports: PDF, DOCX, PPTX, images (JPG/PNG),
          Markdown, plain text (TXT)
"""

from __future__ import annotations

from pathlib import Path

from docstream.exceptions import ExtractionError
from docstream.models.document import Block


class FormatRouter:
    """Detect input format and dispatch to the appropriate handler."""

    SUPPORTED_FORMATS: dict[str, str] = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".pptx": "pptx",
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".md": "markdown",
        ".markdown": "markdown",
        ".txt": "text",
    }

    @property
    def _handlers(self) -> dict[str, type]:
        """Lazy-import handlers to avoid heavy top-level imports."""
        from docstream.core.format_handlers.docx_handler import DOCXHandler
        from docstream.core.format_handlers.image_handler import ImageHandler
        from docstream.core.format_handlers.markdown_handler import MarkdownHandler
        from docstream.core.format_handlers.pdf_handler import PDFHandler
        from docstream.core.format_handlers.pptx_handler import PPTXHandler
        from docstream.core.format_handlers.text_handler import TextHandler

        return {
            "pdf": PDFHandler,
            "docx": DOCXHandler,
            "pptx": PPTXHandler,
            "image": ImageHandler,
            "markdown": MarkdownHandler,
            "text": TextHandler,
        }

    def route(self, file_path: Path) -> str:
        """Detect format and return handler name.

        Args:
            file_path: Path to the input file.

        Returns:
            Handler name string (e.g. ``"pdf"``, ``"docx"``).

        Raises:
            ExtractionError: If the file extension is not supported.
        """
        suffix = Path(file_path).suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise ExtractionError(
                f"Unsupported file format: '{suffix}'. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS.keys())}"
            )
        return self.SUPPORTED_FORMATS[suffix]

    def extract(self, file_path: Path) -> list[Block]:
        """Route file to the correct handler and return extracted blocks.

        Args:
            file_path: Path to the input file.

        Returns:
            List of ``Block`` objects extracted from the file.

        Raises:
            ExtractionError: If the file is missing, unsupported, or
                             yields no extractable content.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ExtractionError(f"File not found: {file_path}")

        format_name = self.route(file_path)
        handler_class = self._handlers[format_name]
        handler = handler_class()

        blocks = handler.extract(file_path)

        if not blocks:
            raise ExtractionError(
                f"No content could be extracted from '{file_path.name}'. "
                "The file may be empty or corrupted."
            )

        return blocks

    @classmethod
    def supported_extensions(cls) -> list[str]:
        """Return all supported file extensions."""
        return list(cls.SUPPORTED_FORMATS.keys())

    @classmethod
    def is_supported(cls, file_path: Path) -> bool:
        """Return True if the file extension is supported."""
        return Path(file_path).suffix.lower() in cls.SUPPORTED_FORMATS
