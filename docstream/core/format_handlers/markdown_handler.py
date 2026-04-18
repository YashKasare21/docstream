"""
Markdown Handler — parses Markdown files.
Processes headings, paragraphs, code blocks, tables, lists,
and blockquotes into Block objects line-by-line.
"""

from __future__ import annotations

import re
from pathlib import Path

from docstream.exceptions import ExtractionError
from docstream.models.document import Block, BlockType

# Heading pattern → (prefix_regex, font_size)
_HEADING_LEVELS = [
    (re.compile(r"^#{4}\s+(.+)$"), 14.0),  # ####
    (re.compile(r"^#{3}\s+(.+)$"), 16.0),  # ###
    (re.compile(r"^#{2}\s+(.+)$"), 20.0),  # ##
    (re.compile(r"^#\s+(.+)$"), 24.0),     # #
]

_LIST_RE = re.compile(r"^[-*+]\s+(.+)$|^(\d+)\.\s+(.+)$")
_BLOCKQUOTE_RE = re.compile(r"^>\s*(.*)$")
_TABLE_LINE_RE = re.compile(r"^\|.+\|$")
_CODE_FENCE_RE = re.compile(r"^```(.*)$")


class MarkdownHandler:
    """Parse ``.md`` Markdown files into structured blocks.

    Processes the file line-by-line, accumulating code blocks and
    table blocks, and mapping all other element types to ``Block``
    objects with appropriate ``BlockType`` and font sizes.
    """

    def extract(self, file_path: Path) -> list[Block]:
        """Extract blocks from a Markdown file.

        Args:
            file_path: Path to the ``.md`` file.

        Returns:
            List of ``Block`` objects mapped from Markdown elements.

        Raises:
            ExtractionError: If the file cannot be read as UTF-8.
        """
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ExtractionError(
                "Could not read Markdown file. "
                "Please ensure the file is UTF-8 encoded."
            ) from exc

        blocks: list[Block] = []
        lines = text.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i]

            # ── Code fence ────────────────────────────────────────────────
            m = _CODE_FENCE_RE.match(line)
            if m:
                lang = m.group(1).strip()
                code_lines: list[str] = []
                i += 1
                while i < len(lines) and not _CODE_FENCE_RE.match(lines[i]):
                    code_lines.append(lines[i])
                    i += 1
                # consume closing fence
                i += 1
                content = "\n".join(code_lines)
                if content.strip():
                    blocks.append(
                        Block(
                            type=BlockType.CODE,
                            content=content,
                            page_number=1,
                            font_size=12.0,
                            metadata={"language": lang} if lang else {},
                            bbox=(0.0, 0.0, 0.0, 0.0),
                        )
                    )
                continue

            # ── Table (accumulate consecutive table lines) ─────────────────
            if _TABLE_LINE_RE.match(line):
                table_lines: list[str] = []
                while i < len(lines) and _TABLE_LINE_RE.match(lines[i]):
                    table_lines.append(lines[i])
                    i += 1
                blocks.append(
                    Block(
                        type=BlockType.TABLE,
                        content="\n".join(table_lines),
                        page_number=1,
                        font_size=12.0,
                        bbox=(0.0, 0.0, 0.0, 0.0),
                    )
                )
                continue

            # ── Headings ──────────────────────────────────────────────────
            matched_heading = False
            for pattern, font_size in _HEADING_LEVELS:
                hm = pattern.match(line)
                if hm:
                    content = hm.group(1).strip()
                    if content:
                        blocks.append(
                            Block(
                                type=BlockType.HEADING,
                                content=content,
                                page_number=1,
                                font_size=font_size,
                                is_bold=True,
                                bbox=(0.0, 0.0, 0.0, 0.0),
                            )
                        )
                    matched_heading = True
                    break
            if matched_heading:
                i += 1
                continue

            # ── Blockquote ────────────────────────────────────────────────
            bm = _BLOCKQUOTE_RE.match(line)
            if bm:
                content = bm.group(1).strip()
                if content:
                    blocks.append(
                        Block(
                            type=BlockType.TEXT,
                            content=content,
                            page_number=1,
                            font_size=12.0,
                            is_italic=True,
                            bbox=(0.0, 0.0, 0.0, 0.0),
                        )
                    )
                i += 1
                continue

            # ── List item ─────────────────────────────────────────────────
            lm = _LIST_RE.match(line)
            if lm:
                # group(1) for bullet, group(3) for numbered
                content = (lm.group(1) or lm.group(3) or "").strip()
                if content:
                    blocks.append(
                        Block(
                            type=BlockType.LIST,
                            content=content,
                            page_number=1,
                            font_size=12.0,
                            bbox=(0.0, 0.0, 0.0, 0.0),
                        )
                    )
                i += 1
                continue

            # ── Empty line ────────────────────────────────────────────────
            if not line.strip():
                i += 1
                continue

            # ── Plain paragraph ───────────────────────────────────────────
            content = line.strip()
            if content:
                blocks.append(
                    Block(
                        type=BlockType.TEXT,
                        content=content,
                        page_number=1,
                        font_size=12.0,
                        bbox=(0.0, 0.0, 0.0, 0.0),
                    )
                )
            i += 1

        return blocks
