"""
Markdown Handler — parses Markdown files.
Uses mistune to parse headings, paragraphs, code blocks,
tables, and lists into Block objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from docstream import Block


class MarkdownHandler:
    """Parse ``.md`` Markdown files into structured blocks.

    Uses ``mistune`` (v3) to tokenize the Markdown AST and converts
    each node type (heading, paragraph, code_block, table, list)
    into a corresponding ``Block`` object.
    """

    def extract(self, file_path: Path) -> "List[Block]":
        """Extract blocks from a Markdown file.

        Args:
            file_path: Path to the ``.md`` file.

        Returns:
            List of ``Block`` objects mapped from Markdown AST nodes.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError
