"""
Tests for all v2 format handlers and FormatRouter.

Uses unittest.mock throughout — no real files are read.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docstream.exceptions import ExtractionError
from docstream.models.document import Block, BlockType

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_block(block_type: BlockType, content: str = "test") -> Block:
    return Block(type=block_type, content=content)


# ─────────────────────────────────────────────────────────────────────────────
# 1. PDFHandler — delegates to PDFExtractor
# ─────────────────────────────────────────────────────────────────────────────


def test_pdf_handler_delegates_to_extractor():
    """PDFHandler.extract() should return blocks from extract_structured."""
    with patch("docstream.core.format_handlers.pdf_handler.extract_structured") as mock_extract:
        mock_extract.return_value = {
            "title": "Test",
            "metadata": {"page_count": 1, "is_scanned": False},
            "structure": [{"type": "text", "text": "Hello PDF", "page": 1}],
        }

        from docstream.core.format_handlers.pdf_handler import PDFHandler

        result = PDFHandler().extract(Path("doc.pdf"))

    assert len(result) == 1
    mock_extract.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 2. DOCXHandler — extracts paragraphs with correct types
# ─────────────────────────────────────────────────────────────────────────────


def _mock_para(text: str, style_name: str) -> MagicMock:
    para = MagicMock()
    para.text = text
    para.style.name = style_name
    para.runs = []
    return para


def test_docx_handler_extracts_paragraphs():
    """DOCXHandler returns blocks with correct BlockType for known styles."""
    mock_doc = MagicMock()
    mock_doc.paragraphs = [
        _mock_para("Introduction", "Heading 1"),
        _mock_para("Some body text here.", "Normal"),
        _mock_para("More body text.", "Normal"),
    ]
    mock_doc.tables = []

    with patch("docx.Document", return_value=mock_doc):
        from docstream.core.format_handlers.docx_handler import DOCXHandler

        blocks = DOCXHandler().extract(Path("doc.docx"))

    assert len(blocks) == 3
    assert blocks[0].type == BlockType.HEADING
    assert blocks[1].type == BlockType.TEXT
    assert blocks[2].type == BlockType.TEXT


# ─────────────────────────────────────────────────────────────────────────────
# 3. DOCXHandler — skips empty paragraphs
# ─────────────────────────────────────────────────────────────────────────────


def test_docx_handler_skips_empty_paragraphs():
    """DOCXHandler must not emit blocks for paragraphs with < 2 chars."""
    mock_doc = MagicMock()
    mock_doc.paragraphs = [
        _mock_para("", "Normal"),
        _mock_para(" ", "Normal"),
        _mock_para("Real content here.", "Normal"),
    ]
    mock_doc.tables = []

    with patch("docx.Document", return_value=mock_doc):
        from docstream.core.format_handlers.docx_handler import DOCXHandler

        blocks = DOCXHandler().extract(Path("doc.docx"))

    assert len(blocks) == 1
    assert blocks[0].content == "Real content here."


# ─────────────────────────────────────────────────────────────────────────────
# 4. DOCXHandler — extracts tables as Markdown
# ─────────────────────────────────────────────────────────────────────────────


def _mock_table(rows: list[list[str]]) -> MagicMock:
    table = MagicMock()
    mock_rows = []
    for row_data in rows:
        row = MagicMock()
        row.cells = [MagicMock(text=cell) for cell in row_data]
        mock_rows.append(row)
    table.rows = mock_rows
    return table


def test_docx_handler_extracts_tables():
    """DOCXHandler produces a TABLE block with Markdown content for each table."""
    mock_doc = MagicMock()
    mock_doc.paragraphs = []
    mock_doc.tables = [_mock_table([["Name", "Age"], ["Alice", "30"]])]

    with patch("docx.Document", return_value=mock_doc):
        from docstream.core.format_handlers.docx_handler import DOCXHandler

        blocks = DOCXHandler().extract(Path("doc.docx"))

    assert len(blocks) == 1
    assert blocks[0].type == BlockType.TABLE
    assert "Name" in blocks[0].content
    assert "Alice" in blocks[0].content
    assert "---" in blocks[0].content


# ─────────────────────────────────────────────────────────────────────────────
# 5. PPTXHandler — extracts slide titles and body text
# ─────────────────────────────────────────────────────────────────────────────


def _mock_slide(title_text: str, body_texts: list[str], slide_num: int) -> MagicMock:
    slide = MagicMock()

    # Title shape
    title_shape = MagicMock()
    title_shape.has_text_frame = True
    title_shape.text = title_text
    title_shape.has_table = False
    slide.shapes.title = title_shape

    # Body shapes
    body_shapes = []
    for text in body_texts:
        shape = MagicMock()
        shape.has_text_frame = True
        shape.has_table = False
        para = MagicMock()
        para.text = text
        shape.text_frame.paragraphs = [para]
        body_shapes.append(shape)

    slide.shapes.__iter__ = MagicMock(return_value=iter([title_shape] + body_shapes))

    # No speaker notes
    slide.notes_slide = None

    return slide


def test_pptx_handler_extracts_slides():
    """PPTXHandler returns 1 HEADING + N TEXT blocks per slide."""
    mock_prs = MagicMock()
    mock_prs.slides = [
        _mock_slide("Slide 1 Title", ["Bullet one"], 1),
        _mock_slide("Slide 2 Title", ["Bullet two"], 2),
    ]

    with patch("pptx.Presentation", return_value=mock_prs):
        from docstream.core.format_handlers.pptx_handler import PPTXHandler

        blocks = PPTXHandler().extract(Path("deck.pptx"))

    headings = [b for b in blocks if b.type == BlockType.HEADING]
    texts = [b for b in blocks if b.type == BlockType.TEXT]
    assert len(headings) == 2
    assert len(texts) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 6. ImageHandler — runs OCR and returns text blocks
# ─────────────────────────────────────────────────────────────────────────────


def test_image_handler_runs_ocr():
    """ImageHandler splits OCR output into paragraph blocks."""
    mock_img = MagicMock()
    mock_img.size = (1200, 800)
    mock_img.convert.return_value = mock_img

    with (
        patch("PIL.Image.open", return_value=mock_img),
        patch(
            "pytesseract.image_to_string",
            return_value="Hello World\n\nSecond paragraph",
        ),
    ):
        from docstream.core.format_handlers.image_handler import ImageHandler

        blocks = ImageHandler().extract(Path("scan.png"))

    assert len(blocks) == 2
    assert all(b.type == BlockType.TEXT for b in blocks)
    assert blocks[0].content == "Hello World"
    assert blocks[1].content == "Second paragraph"


# ─────────────────────────────────────────────────────────────────────────────
# 7. ImageHandler — raises ExtractionError on empty OCR
# ─────────────────────────────────────────────────────────────────────────────


def test_image_handler_raises_on_empty_ocr():
    """ImageHandler raises ExtractionError when OCR yields < 20 chars."""
    mock_img = MagicMock()
    mock_img.size = (1200, 800)
    mock_img.convert.return_value = mock_img

    with (
        patch("PIL.Image.open", return_value=mock_img),
        patch("pytesseract.image_to_string", return_value=""),
        pytest.raises(ExtractionError),
    ):
        from docstream.core.format_handlers.image_handler import ImageHandler

        ImageHandler().extract(Path("blank.png"))


# ─────────────────────────────────────────────────────────────────────────────
# 8. MarkdownHandler — detects headings and plain text
# ─────────────────────────────────────────────────────────────────────────────


def test_markdown_handler_detects_headings(tmp_path: Path):
    """MarkdownHandler maps # lines to HEADING and plain lines to TEXT."""
    md_file = tmp_path / "doc.md"
    md_file.write_text(
        "# Title\n\nSome text\n\n## Section\n\nMore text",
        encoding="utf-8",
    )

    from docstream.core.format_handlers.markdown_handler import MarkdownHandler

    blocks = MarkdownHandler().extract(md_file)

    headings = [b for b in blocks if b.type == BlockType.HEADING]
    texts = [b for b in blocks if b.type == BlockType.TEXT]
    assert len(headings) == 2
    assert len(texts) == 2
    assert headings[0].content == "Title"
    assert headings[1].content == "Section"


# ─────────────────────────────────────────────────────────────────────────────
# 9. MarkdownHandler — handles code blocks
# ─────────────────────────────────────────────────────────────────────────────


def test_markdown_handler_handles_code_blocks(tmp_path: Path):
    """MarkdownHandler wraps fenced code blocks as CODE blocks."""
    md_file = tmp_path / "code.md"
    md_file.write_text(
        "# Example\n\n```python\nprint('hello')\n```\n",
        encoding="utf-8",
    )

    from docstream.core.format_handlers.markdown_handler import MarkdownHandler

    blocks = MarkdownHandler().extract(md_file)

    code_blocks = [b for b in blocks if b.type == BlockType.CODE]
    assert len(code_blocks) == 1
    assert "print" in code_blocks[0].content


# ─────────────────────────────────────────────────────────────────────────────
# 10. TextHandler — promotes ALL CAPS paragraphs to headings
# ─────────────────────────────────────────────────────────────────────────────


def test_text_handler_detects_all_caps_headings(tmp_path: Path):
    """TextHandler promotes ALL CAPS paragraphs to HEADING blocks."""
    txt_file = tmp_path / "doc.txt"
    txt_file.write_text(
        "INTRODUCTION\n\nThis is the intro text.",
        encoding="utf-8",
    )

    from docstream.core.format_handlers.text_handler import TextHandler

    blocks = TextHandler().extract(txt_file)

    assert blocks[0].type == BlockType.HEADING
    assert blocks[0].content == "INTRODUCTION"
    assert blocks[1].type == BlockType.TEXT


# ─────────────────────────────────────────────────────────────────────────────
# 11. FormatRouter — routes extensions to correct format names
# ─────────────────────────────────────────────────────────────────────────────


def test_format_router_routes_correctly():
    """FormatRouter.route() returns the correct handler name per extension."""
    from docstream.core.format_router import FormatRouter

    router = FormatRouter()
    assert router.route(Path("doc.pdf")) == "pdf"
    assert router.route(Path("doc.docx")) == "docx"
    assert router.route(Path("deck.pptx")) == "pptx"
    assert router.route(Path("scan.jpg")) == "image"
    assert router.route(Path("scan.jpeg")) == "image"
    assert router.route(Path("photo.png")) == "image"
    assert router.route(Path("readme.md")) == "markdown"
    assert router.route(Path("notes.txt")) == "text"


# ─────────────────────────────────────────────────────────────────────────────
# 12. FormatRouter — raises on unsupported extension
# ─────────────────────────────────────────────────────────────────────────────


def test_format_router_raises_on_unsupported():
    """FormatRouter raises ExtractionError for unknown file extensions."""
    from docstream.core.format_router import FormatRouter

    with pytest.raises(ExtractionError):
        FormatRouter().route(Path("file.xyz"))


# ─────────────────────────────────────────────────────────────────────────────
# 13. FormatRouter — raises on missing file
# ─────────────────────────────────────────────────────────────────────────────


def test_format_router_raises_on_missing_file():
    """FormatRouter.extract() raises ExtractionError if file does not exist."""
    from docstream.core.format_router import FormatRouter

    with pytest.raises(ExtractionError):
        FormatRouter().extract(Path("/nonexistent/path/file.pdf"))


# ─────────────────────────────────────────────────────────────────────────────
# 14. Public API — docstream.extract() uses FormatRouter
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_public_api_uses_extractor():
    """docstream.extract() delegates to extract_structured()."""
    sample_doc = {
        "title": "Test",
        "structure": [{"type": "paragraph", "text": "API block", "page": 1}],
        "full_text": "API block",
        "images": [],
    }

    with patch(
        "docstream.core.extractor_v2.extract_structured",
        return_value=sample_doc,
    ) as mock_extract:
        import docstream

        result = docstream.extract("test.pdf")

    mock_extract.assert_called_once()
    assert result == sample_doc
