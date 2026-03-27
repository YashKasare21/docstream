"""
Plain Text Handler — processes TXT files.
Splits by paragraphs, detects potential headings by
heuristics (short lines, ALL CAPS, numbered sections).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from docstream import Block


class TextHandler:
    """Parse plain ``.txt`` files into structured blocks.

    Splits content on blank lines to identify paragraphs, then applies
    heuristics to promote short lines, ALL-CAPS text, or numbered
    section markers (e.g. ``1.``, ``1.1``) to heading blocks.
    """

    def extract(self, file_path: Path) -> "List[Block]":
        """Extract blocks from a plain-text file.

        Args:
            file_path: Path to the ``.txt`` file.

        Returns:
            List of ``Block`` objects with headings detected by heuristic.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError
