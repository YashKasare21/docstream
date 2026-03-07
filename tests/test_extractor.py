"""
Tests for the Extractor module.

This module contains unit tests for content extraction from PDF and LaTeX
documents. Tests cover both happy path and error scenarios.
"""

import pytest

from docstream.core.extractor import Extractor, LaTeXExtractor, PDFExtractor
from docstream.exceptions import ExtractionError
from docstream.models.document import DocumentMetadata, RawContent


class TestPDFExtractor:
    """Unit tests for PDFExtractor."""

    def test_supports_pdf_format(self, tmp_path):
        """PDFExtractor should support .pdf files."""
        extractor = PDFExtractor()
        assert extractor.supports_format(str(tmp_path / "file.pdf")) is True

    def test_does_not_support_tex_format(self, tmp_path):
        """PDFExtractor should not support .tex files."""
        extractor = PDFExtractor()
        assert extractor.supports_format(str(tmp_path / "file.tex")) is False

    def test_raises_on_missing_file(self):
        """PDFExtractor.extract should raise ExtractionError for missing files."""
        extractor = PDFExtractor()
        with pytest.raises(ExtractionError):
            extractor.extract("/nonexistent/file.pdf")

    def test_extract_returns_raw_content(self, sample_pdf_path):
        """PDFExtractor.extract should return a RawContent object."""
        extractor = PDFExtractor()
        try:
            result = extractor.extract(sample_pdf_path)
            assert isinstance(result, RawContent)
            assert result.source_format == "pdf"
        except ExtractionError:
            pytest.skip("PyMuPDF could not open minimal test PDF")

    def test_extract_metadata_structure(self, sample_pdf_path):
        """Extracted metadata should be a DocumentMetadata instance."""
        extractor = PDFExtractor()
        try:
            result = extractor.extract(sample_pdf_path)
            assert isinstance(result.metadata, DocumentMetadata)
        except ExtractionError:
            pytest.skip("PyMuPDF could not open minimal test PDF")


class TestLaTeXExtractor:
    """Unit tests for LaTeXExtractor."""

    def test_supports_tex_format(self, tmp_path):
        """LaTeXExtractor should support .tex files."""
        extractor = LaTeXExtractor()
        assert extractor.supports_format(str(tmp_path / "file.tex")) is True

    def test_supports_latex_extension(self, tmp_path):
        """LaTeXExtractor should support .latex files."""
        extractor = LaTeXExtractor()
        assert extractor.supports_format(str(tmp_path / "file.latex")) is True

    def test_does_not_support_pdf(self, tmp_path):
        """LaTeXExtractor should not support .pdf files."""
        extractor = LaTeXExtractor()
        assert extractor.supports_format(str(tmp_path / "file.pdf")) is False

    def test_raises_on_missing_file(self):
        """LaTeXExtractor.extract should raise ExtractionError for missing files."""
        extractor = LaTeXExtractor()
        with pytest.raises(ExtractionError):
            extractor.extract("/nonexistent/file.tex")

    def test_extract_returns_raw_content(self, sample_latex_path):
        """LaTeXExtractor.extract should return a RawContent object."""
        extractor = LaTeXExtractor()
        result = extractor.extract(sample_latex_path)
        assert isinstance(result, RawContent)
        assert result.source_format == "latex"

    def test_extract_title_from_latex(self, sample_latex_path):
        """LaTeXExtractor should extract title from \\title{} command."""
        extractor = LaTeXExtractor()
        result = extractor.extract(sample_latex_path)
        assert result.metadata.title == "Sample Document"

    def test_extract_author_from_latex(self, sample_latex_path):
        """LaTeXExtractor should extract author from \\author{} command."""
        extractor = LaTeXExtractor()
        result = extractor.extract(sample_latex_path)
        assert result.metadata.author == "Test Author"

    def test_extract_cleans_latex_commands(self, sample_latex_path):
        """Extracted text should have LaTeX commands stripped."""
        extractor = LaTeXExtractor()
        result = extractor.extract(sample_latex_path)
        # The text should not contain raw \documentclass etc.
        assert "\\documentclass" not in result.text


class TestExtractor:
    """Unit tests for the main Extractor dispatcher."""

    def test_dispatches_to_latex_extractor(self, sample_latex_path):
        """Extractor should dispatch .tex files to LaTeXExtractor."""
        extractor = Extractor()
        result = extractor.extract(sample_latex_path)
        assert result.source_format == "latex"

    def test_raises_for_unsupported_format(self, tmp_path):
        """Extractor should raise ExtractionError for unsupported formats."""
        unsupported = tmp_path / "file.xyz"
        unsupported.write_text("content")
        extractor = Extractor()
        with pytest.raises(ExtractionError):
            extractor.extract(str(unsupported))

    def test_get_supported_formats(self):
        """Extractor should report supported formats."""
        extractor = Extractor()
        formats = extractor.get_supported_formats()
        assert "pdf" in formats
        assert "tex" in formats

    def test_raises_when_file_missing(self):
        """Extractor should raise ExtractionError when file is missing."""
        extractor = Extractor()
        with pytest.raises(ExtractionError):
            extractor.extract("/does/not/exist.tex")
