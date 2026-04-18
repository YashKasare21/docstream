"""
Plain Text Handler — processes TXT files.
Splits by paragraphs, detects potential headings by
heuristics (short lines, ALL CAPS, numbered sections).
"""

from __future__ import annotations

import re
from pathlib import Path

from docstream.exceptions import ExtractionError
from docstream.models.document import Block, BlockType

# Matches "1. Intro", "1.1 Background", "Chapter 3", "Section 2.4", etc.
_NUMBERED_SECTION_RE = re.compile(
    r"^(\d+(\.\d+)*\.?\s+.+|Chapter\s+\d+|Section\s+\d+(\.\d+)*)",
    re.IGNORECASE,
)


def _is_heading(paragraph: str) -> bool:
    """Return True if the paragraph looks like a heading."""
    stripped = paragraph.strip()
    if not stripped:
        return False

    # ALL CAPS and short enough to be a title
    if stripped.isupper() and len(stripped) < 80:
        return True

    # Numbered section marker
    if _NUMBERED_SECTION_RE.match(stripped):
        return True

    # Single short line that doesn't end with sentence-ending punctuation
    # (sentences like "This is intro text." should stay as TEXT)
    lines = stripped.splitlines()
    if len(lines) == 1 and len(stripped) < 60 and not stripped.endswith((".", "!", "?", ":", ";")):
        return True

    return False


class TextHandler:
    """Parse plain ``.txt`` files into structured blocks.

    Splits content on blank lines to identify paragraphs, then applies
    heuristics to promote short lines, ALL-CAPS text, or numbered
    section markers to heading blocks.

    Falls back from UTF-8 to latin-1 encoding automatically.
    """

    def extract(self, file_path: Path) -> list[Block]:
        """Extract blocks from a plain-text file.

        Args:
            file_path: Path to the ``.txt`` file.

        Returns:
            List of ``Block`` objects with headings detected by heuristic.

        Raises:
            ExtractionError: If the file cannot be read.
        """
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = file_path.read_text(encoding="latin-1")
            except Exception as exc:
                raise ExtractionError(f"Could not read text file: {file_path.name}") from exc

        raw_paragraphs = text.split("\n\n")
        blocks: list[Block] = []

        for para in raw_paragraphs:
            content = para.strip()
            if len(content) < 3:
                continue

            if _is_heading(content):
                blocks.append(
                    Block(
                        type=BlockType.HEADING,
                        content=content,
                        page_number=1,
                        font_size=18.0,
                        is_bold=True,
                        bbox=(0.0, 0.0, 0.0, 0.0),
                    )
                )
            else:
                blocks.append(
                    Block(
                        type=BlockType.TEXT,
                        content=content,
                        page_number=1,
                        font_size=12.0,
                        bbox=(0.0, 0.0, 0.0, 0.0),
                    )
                )

        return blocks
