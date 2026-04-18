"""
Tests for the public docstream v2 API:
  convert(), extract(), generate(), ConversionResult, __version__
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import docstream
from docstream import ConversionResult

# ---------------------------------------------------------------------------
# Shared mock return values
# ---------------------------------------------------------------------------

SAMPLE_DOCUMENT = {
    "title": "Test Paper",
    "metadata": {"page_count": 1, "is_scanned": False},
    "structure": [
        {"type": "heading", "text": "Introduction", "level": 1, "page": 1},
        {"type": "paragraph", "text": "Test paragraph.", "page": 1},
    ],
    "full_text": "Introduction\nTest paragraph.",
    "body_font_size": 12.0,
    "images": [],
}

SAMPLE_LATEX = (
    r"\documentclass{article}"
    r"\begin{document}"
    r"\section{Introduction}Test paragraph.\end{document}"
)


# ---------------------------------------------------------------------------
# test_extract
# ---------------------------------------------------------------------------


class TestExtract:
    def test_returns_dict(self):
        with patch(
            "docstream.core.extractor_v2.extract_structured",
            return_value=SAMPLE_DOCUMENT,
        ):
            result = docstream.extract("test.pdf")
        assert isinstance(result, dict)

    def test_returns_document_with_structure_key(self):
        with patch(
            "docstream.core.extractor_v2.extract_structured",
            return_value=SAMPLE_DOCUMENT,
        ):
            result = docstream.extract("test.pdf")
        assert "structure" in result

    def test_accepts_string_path(self):
        with patch(
            "docstream.core.extractor_v2.extract_structured",
            return_value=SAMPLE_DOCUMENT,
        ) as mock_extract:
            docstream.extract("paper.pdf")
        mock_extract.assert_called_once()

    def test_accepts_path_object(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        with patch(
            "docstream.core.extractor_v2.extract_structured",
            return_value=SAMPLE_DOCUMENT,
        ) as mock_extract:
            docstream.extract(pdf)
        mock_extract.assert_called_once()

    def test_propagates_extraction_error(self):
        from docstream.exceptions import ExtractionError

        with patch(
            "docstream.core.extractor_v2.extract_structured",
            side_effect=ExtractionError("bad file"),
        ):
            with pytest.raises(ExtractionError):
                docstream.extract("bad.pdf")


# ---------------------------------------------------------------------------
# test_generate
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_returns_string(self):
        with patch(
            "docstream.core.generator.generate_latex",
            return_value=SAMPLE_LATEX,
        ):
            result = docstream.generate(SAMPLE_DOCUMENT, template="report")
        assert isinstance(result, str)

    def test_returns_non_empty_latex(self):
        with patch(
            "docstream.core.generator.generate_latex",
            return_value=SAMPLE_LATEX,
        ):
            result = docstream.generate(SAMPLE_DOCUMENT, template="report")
        assert len(result) > 0

    def test_default_template_is_report(self):
        with patch(
            "docstream.core.generator.generate_latex",
            return_value=SAMPLE_LATEX,
        ) as mock_gen:
            docstream.generate(SAMPLE_DOCUMENT)
        args = mock_gen.call_args
        assert args[0][1] == "report"

    def test_ieee_template_forwarded(self):
        with patch(
            "docstream.core.generator.generate_latex",
            return_value=SAMPLE_LATEX,
        ) as mock_gen:
            docstream.generate(SAMPLE_DOCUMENT, template="ieee")
        args = mock_gen.call_args
        assert args[0][1] == "ieee"

    def test_custom_ai_provider_forwarded(self):
        mock_provider = MagicMock()
        with patch(
            "docstream.core.generator.generate_latex",
            return_value=SAMPLE_LATEX,
        ) as mock_gen:
            docstream.generate(SAMPLE_DOCUMENT, ai_provider=mock_provider)
        args = mock_gen.call_args
        assert args[0][2] is mock_provider


# ---------------------------------------------------------------------------
# test_convert
# ---------------------------------------------------------------------------


class TestConvert:
    def _patch_pipeline(self, tmp_path):
        """Context manager that patches all 3 pipeline stages."""
        tex = tmp_path / "document.tex"
        pdf = tmp_path / "document.pdf"
        tex.write_text(SAMPLE_LATEX)
        pdf.write_bytes(b"%PDF-1.4")
        return (
            patch(
                "docstream.core.extractor_v2.extract_structured",
                return_value=SAMPLE_DOCUMENT,
            ),
            patch(
                "docstream.core.generator.generate_latex",
                return_value=SAMPLE_LATEX,
            ),
            patch(
                "docstream.core.compiler.compile_latex",
                return_value=(tex, pdf),
            ),
        )

    def test_returns_conversion_result(self, tmp_path):
        p1, p2, p3 = self._patch_pipeline(tmp_path)
        with p1, p2, p3:
            result = docstream.convert("paper.pdf", output_dir=tmp_path)
        assert isinstance(result, ConversionResult)

    def test_success_is_true_on_happy_path(self, tmp_path):
        p1, p2, p3 = self._patch_pipeline(tmp_path)
        with p1, p2, p3:
            result = docstream.convert("paper.pdf", output_dir=tmp_path)
        assert result.success is True

    def test_default_template_is_report(self, tmp_path):
        p1, p2, p3 = self._patch_pipeline(tmp_path)
        with p1, p2, p3:
            result = docstream.convert("paper.pdf", output_dir=tmp_path)
        assert result.template_used == "report"

    def test_ieee_template_forwarded(self, tmp_path):
        p1, p2, p3 = self._patch_pipeline(tmp_path)
        with p1, p2, p3:
            result = docstream.convert("paper.pdf", template="ieee", output_dir=tmp_path)
        assert result.template_used == "ieee"

    def test_tex_path_set(self, tmp_path):
        p1, p2, p3 = self._patch_pipeline(tmp_path)
        with p1, p2, p3:
            result = docstream.convert("paper.pdf", output_dir=tmp_path)
        assert result.tex_path is not None
        assert Path(result.tex_path).suffix == ".tex"

    def test_pdf_path_set(self, tmp_path):
        p1, p2, p3 = self._patch_pipeline(tmp_path)
        with p1, p2, p3:
            result = docstream.convert("paper.pdf", output_dir=tmp_path)
        assert result.pdf_path is not None
        assert Path(result.pdf_path).suffix == ".pdf"

    def test_processing_time_is_non_negative(self, tmp_path):
        p1, p2, p3 = self._patch_pipeline(tmp_path)
        with p1, p2, p3:
            result = docstream.convert("paper.pdf", output_dir=tmp_path)
        assert result.processing_time >= 0.0

    def test_error_is_none_on_success(self, tmp_path):
        p1, p2, p3 = self._patch_pipeline(tmp_path)
        with p1, p2, p3:
            result = docstream.convert("paper.pdf", output_dir=tmp_path)
        assert result.error is None

    def test_success_false_on_extraction_error(self, tmp_path):
        from docstream.exceptions import ExtractionError

        with patch(
            "docstream.core.extractor_v2.extract_structured",
            side_effect=ExtractionError("missing file"),
        ):
            result = docstream.convert("missing.pdf", output_dir=tmp_path)
        assert result.success is False
        assert result.error is not None

    def test_accepts_string_output_dir(self, tmp_path):
        p1, p2, p3 = self._patch_pipeline(tmp_path)
        with p1, p2, p3:
            result = docstream.convert("paper.pdf", output_dir=str(tmp_path))
        assert result.success is True


# ---------------------------------------------------------------------------
# test_ConversionResult
# ---------------------------------------------------------------------------


class TestConversionResult:
    def test_success_field(self):
        r = ConversionResult(success=True)
        assert r.success is True

    def test_error_field_none_by_default(self):
        r = ConversionResult(success=True)
        assert r.error is None

    def test_template_used_empty_by_default(self):
        r = ConversionResult(success=True)
        assert r.template_used == ""

    def test_repr_success(self, tmp_path):
        r = ConversionResult(
            success=True,
            template_used="report",
            pdf_path=tmp_path / "doc.pdf",
        )
        assert "True" in repr(r)

    def test_repr_failure(self):
        r = ConversionResult(success=False, error="something failed")
        assert "False" in repr(r)


# ---------------------------------------------------------------------------
# test___version__ and importability
# ---------------------------------------------------------------------------


class TestVersion:
    def test_version_is_string(self):
        assert isinstance(docstream.__version__, str)

    def test_version_value(self):
        assert docstream.__version__ == "0.2.0"

    def test_convert_is_callable(self):
        assert callable(docstream.convert)

    def test_extract_is_callable(self):
        assert callable(docstream.extract)

    def test_generate_is_callable(self):
        assert callable(docstream.generate)

    def test_conversion_result_in___all__(self):
        assert "ConversionResult" in docstream.__all__

    def test_all_symbols_in___all__(self):
        for name in ("convert", "extract", "generate", "ConversionResult"):
            assert name in docstream.__all__
