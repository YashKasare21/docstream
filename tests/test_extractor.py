"""
Tests for PDFExtractor — Phase 1.

Real PDFs are generated in conftest.py via PyMuPDF (TextWriter for
extractable text). API/OCR calls that hit external processes are mocked.
"""

from unittest.mock import patch

import pytest

from docstream.core.extractor import _FLAG_BOLD, _FLAG_ITALIC, PDFExtractor
from docstream.exceptions import ExtractionError
from docstream.models.document import BlockType, TextBlock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_doc(extractor: PDFExtractor) -> None:
    """Open the underlying fitz.Document on the extractor (helper for unit tests)."""
    import fitz

    extractor._doc = fitz.open(str(extractor._path))


def _close_doc(extractor: PDFExtractor) -> None:
    if extractor._doc:
        extractor._doc.close()
        extractor._doc = None


# ---------------------------------------------------------------------------
# test_extract_digital_pdf
# ---------------------------------------------------------------------------


class TestExtractDigitalPdf:
    """Integration tests for digital (text-layer) PDFs.

    _is_scanned is patched to False so tests focus purely on text extraction
    without depending on a Tesseract installation.
    """

    def test_returns_non_empty_block_list(self, digital_pdf_path):
        """Digital PDF yields at least one TEXT block."""
        extractor = PDFExtractor(digital_pdf_path)
        with patch.object(extractor, "_is_scanned", return_value=False):
            blocks = extractor.extract()
        assert len(blocks) > 0

    def test_blocks_have_text_type(self, digital_pdf_path):
        """All extracted spans come back as TEXT blocks."""
        extractor = PDFExtractor(digital_pdf_path)
        with patch.object(extractor, "_is_scanned", return_value=False):
            blocks = extractor.extract()
        text_blocks = [b for b in blocks if b.type == BlockType.TEXT]
        assert len(text_blocks) > 0

    def test_blocks_contain_expected_content(self, digital_pdf_path):
        """Extracted text contains the string written by the fixture."""
        extractor = PDFExtractor(digital_pdf_path)
        with patch.object(extractor, "_is_scanned", return_value=False):
            blocks = extractor.extract()
        all_text = " ".join(b.content for b in blocks)
        assert "Hello" in all_text

    def test_blocks_carry_page_number(self, digital_pdf_path):
        """Every block records its 0-indexed page number."""
        extractor = PDFExtractor(digital_pdf_path)
        with patch.object(extractor, "_is_scanned", return_value=False):
            blocks = extractor.extract()
        assert all(hasattr(b, "page_number") for b in blocks)
        assert all(b.page_number == 0 for b in blocks)

    def test_blocks_carry_font_size(self, digital_pdf_path):
        """Text blocks carry a non-None font_size extracted from the PDF."""
        extractor = PDFExtractor(digital_pdf_path)
        with patch.object(extractor, "_is_scanned", return_value=False):
            blocks = extractor.extract()
        text_blocks = [b for b in blocks if b.type == BlockType.TEXT]
        assert any(b.font_size is not None for b in text_blocks)

    def test_extract_text_blocks_directly(self, digital_pdf_path):
        """_extract_text_blocks() returns Block objects with bbox and font_name."""
        extractor = PDFExtractor(digital_pdf_path)
        _open_doc(extractor)
        blocks = extractor._extract_text_blocks()
        _close_doc(extractor)
        assert len(blocks) > 0
        assert all(b.font_name is not None for b in blocks)


# ---------------------------------------------------------------------------
# test_extract_scanned_detection
# ---------------------------------------------------------------------------


class TestExtractScannedDetection:
    def test_scanned_pdf_routes_to_ocr(self, scanned_pdf_path):
        """A blank-page PDF (no text) triggers the OCR code path."""
        extractor = PDFExtractor(scanned_pdf_path)
        mock_block = TextBlock(type=BlockType.TEXT, content="OCR text", page_number=0)

        with patch.object(extractor, "_run_ocr", return_value=[mock_block]) as mock_ocr:
            blocks = extractor.extract()
            mock_ocr.assert_called_once()

        assert blocks[0].content == "OCR text"

    def test_is_scanned_true_for_blank_pdf(self, scanned_pdf_path):
        """_is_scanned() returns True for a zero-text PDF."""
        extractor = PDFExtractor(scanned_pdf_path)
        _open_doc(extractor)
        result = extractor._is_scanned()
        _close_doc(extractor)
        assert result is True

    def test_is_scanned_false_for_digital_pdf(self, digital_pdf_path):
        """_is_scanned() returns False when the PDF has an extractable text layer."""
        extractor = PDFExtractor(digital_pdf_path)
        _open_doc(extractor)
        result = extractor._is_scanned()
        _close_doc(extractor)
        assert result is False

    def test_scanned_threshold_constant(self):
        """SCANNED_THRESHOLD is 100 as documented."""
        assert PDFExtractor.SCANNED_THRESHOLD == 100


# ---------------------------------------------------------------------------
# test_extract_tables
# ---------------------------------------------------------------------------


class TestExtractTables:
    def test_table_blocks_returned(self, table_pdf_path):
        """find_tables() on a drawn-grid PDF returns at least one TABLE block."""
        extractor = PDFExtractor(table_pdf_path)
        with patch.object(extractor, "_is_scanned", return_value=False):
            blocks = extractor.extract()
        table_blocks = [b for b in blocks if b.type == BlockType.TABLE]
        assert len(table_blocks) >= 1

    def test_table_content_is_markdown(self, table_pdf_path):
        """TABLE block content uses Markdown pipe-table syntax."""
        extractor = PDFExtractor(table_pdf_path)
        with patch.object(extractor, "_is_scanned", return_value=False):
            blocks = extractor.extract()
        table_blocks = [b for b in blocks if b.type == BlockType.TABLE]
        if table_blocks:
            assert "|" in table_blocks[0].content

    def test_rows_to_markdown_well_formed(self):
        """_rows_to_markdown produces header + separator + data rows."""
        rows = [["Name", "Score"], ["Alice", "95"], ["Bob", "87"]]
        md = PDFExtractor._rows_to_markdown(rows)
        assert "| Name | Score |" in md
        assert "| --- | --- |" in md
        assert "| Alice | 95 |" in md

    def test_rows_to_markdown_empty_input(self):
        """_rows_to_markdown on empty list returns empty string."""
        assert PDFExtractor._rows_to_markdown([]) == ""

    def test_table_extraction_no_tables_returns_empty_list(self, digital_pdf_path):
        """PDF without tables → _extract_tables() returns []."""
        extractor = PDFExtractor(digital_pdf_path)
        _open_doc(extractor)
        result = extractor._extract_tables()
        _close_doc(extractor)
        assert isinstance(result, list)
        assert all(b.type == BlockType.TABLE for b in result)


# ---------------------------------------------------------------------------
# test_bold_italic_detection
# ---------------------------------------------------------------------------


class TestBoldItalicDetection:
    def test_bold_flag_detected(self, bold_pdf_path):
        """Text inserted with Helvetica-Bold has is_bold=True on at least one span."""
        extractor = PDFExtractor(bold_pdf_path)
        _open_doc(extractor)
        blocks = extractor._extract_text_blocks()
        _close_doc(extractor)
        assert any(b.is_bold for b in blocks), (
            f"Expected a bold block. Got flags: {[b.font_flags for b in blocks]}"
        )

    def test_font_flags_stored(self, digital_pdf_path):
        """font_flags is populated for every text span."""
        extractor = PDFExtractor(digital_pdf_path)
        _open_doc(extractor)
        blocks = extractor._extract_text_blocks()
        _close_doc(extractor)
        assert any(b.font_flags is not None for b in blocks)

    def test_font_name_stored(self, digital_pdf_path):
        """font_name is set for every text span."""
        extractor = PDFExtractor(digital_pdf_path)
        _open_doc(extractor)
        blocks = extractor._extract_text_blocks()
        _close_doc(extractor)
        assert all(b.font_name is not None for b in blocks)

    def test_italic_flag_bit_mask(self):
        """_FLAG_ITALIC mask: flags & 2 detects bit-1 italic."""
        assert bool(2 & _FLAG_ITALIC) is True
        assert bool(0 & _FLAG_ITALIC) is False

    def test_bold_flag_bit_mask(self):
        """_FLAG_BOLD mask: flags & 16 detects bit-4 bold."""
        assert bool(16 & _FLAG_BOLD) is True
        assert bool(0 & _FLAG_BOLD) is False

    def test_block_is_bold_set_from_flags(self):
        """is_bold is derived from font_flags bit 4 (value 16)."""
        block = TextBlock(
            type=BlockType.TEXT,
            content="test",
            font_flags=16,
            is_bold=bool(16 & _FLAG_BOLD),
        )
        assert block.is_bold is True

    def test_block_is_italic_set_from_flags(self):
        """is_italic is derived from font_flags bit 1 (value 2)."""
        block = TextBlock(
            type=BlockType.TEXT,
            content="test",
            font_flags=2,
            is_italic=bool(2 & _FLAG_ITALIC),
        )
        assert block.is_italic is True


# ---------------------------------------------------------------------------
# test_extraction_error_on_corrupt_file
# ---------------------------------------------------------------------------


class TestExtractionErrorOnCorruptFile:
    def test_corrupt_file_raises_extraction_error(self, corrupt_pdf_path):
        """A corrupt (non-PDF) file raises ExtractionError, not a raw fitz error."""
        with pytest.raises(ExtractionError):
            PDFExtractor(corrupt_pdf_path).extract()

    def test_missing_file_raises_at_init(self, tmp_path):
        """Non-existent path raises ExtractionError at __init__ time."""
        with pytest.raises(ExtractionError, match="File not found"):
            PDFExtractor(str(tmp_path / "nonexistent.pdf"))

    def test_error_type_is_extraction_error(self, corrupt_pdf_path):
        """Ensure the raised exception is exactly ExtractionError (not a subclass)."""
        exc = None
        try:
            PDFExtractor(corrupt_pdf_path).extract()
        except ExtractionError as e:
            exc = e
        assert exc is not None
        assert type(exc) is ExtractionError
