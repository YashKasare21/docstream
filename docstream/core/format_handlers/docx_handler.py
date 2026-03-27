"""
DOCX Handler — extracts content from Word documents.
Uses python-docx to extract paragraphs, headings, tables.
Preserves heading hierarchy and table structure.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from docstream import Block


class DOCXHandler:
    """Extract blocks from ``.docx`` Word documents.

    Preserves heading levels (Heading 1–6), paragraph text,
    and table content using ``python-docx``.
    """

    def extract(self, file_path: Path) -> "List[Block]":
        """Extract blocks from a ``.docx`` file.

        Args:
            file_path: Path to the ``.docx`` file.

        Returns:
            List of ``Block`` objects preserving heading hierarchy
            and table structure.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError
