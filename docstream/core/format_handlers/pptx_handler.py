"""
PPTX Handler — extracts content from PowerPoint files.
Uses python-pptx to extract slide titles, body text,
speaker notes, and table content.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from docstream import Block


class PPTXHandler:
    """Extract blocks from ``.pptx`` PowerPoint presentations.

    Processes each slide in order, extracting the title,
    body text shapes, speaker notes, and any table shapes
    using ``python-pptx``.
    """

    def extract(self, file_path: Path) -> "List[Block]":
        """Extract blocks from a ``.pptx`` file.

        Args:
            file_path: Path to the ``.pptx`` file.

        Returns:
            List of ``Block`` objects — one per slide element
            (title, body, notes, table rows).

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError
