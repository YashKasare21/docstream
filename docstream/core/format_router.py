"""
Format Router — detects input file type and routes to
the correct format handler for extraction.

Supports: PDF, DOCX, PPTX, images (JPG/PNG),
          Markdown, plain text (TXT)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from docstream import Block


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
        ".txt": "text",
    }

    def route(self, file_path: Path) -> str:
        """Detect format and return handler name.

        Args:
            file_path: Path to the input file.

        Returns:
            Handler name string (e.g. ``"pdf"``, ``"docx"``).

        Raises:
            ValueError: If the file extension is not supported.
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError

    def extract(self, file_path: Path) -> "List[Block]":
        """Route to the correct handler and return extracted blocks.

        Args:
            file_path: Path to the input file.

        Returns:
            List of ``Block`` objects extracted from the file.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError
