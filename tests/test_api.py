"""
Tests for the public docstream functional API:
  convert(), extract(), structure(), render(), __version__
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

import docstream
from docstream.models.document import (
    Block,
    BlockType,
    ConversionResult,
    DocumentAST,
    DocumentMetadata,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_blocks():
    return [
        Block(type=BlockType.TEXT, content="Hello world", page_number=0),
        Block(type=BlockType.TEXT, content="Second paragraph", page_number=1),
    ]


@pytest.fixture
def sample_ast():
    return DocumentAST(
        title="Test Doc",
        metadata=DocumentMetadata(title="Test Doc"),
    )


@pytest.fixture
def success_result(tmp_path):
    return ConversionResult(
        success=True,
        tex_path=tmp_path / "document.tex",
        pdf_path=tmp_path / "document.pdf",
        processing_time_seconds=0.5,
        template_used="report",
    )


# ---------------------------------------------------------------------------
# test_extract
# ---------------------------------------------------------------------------


class TestExtract:
    def test_returns_list(self, sample_blocks):
        with patch("docstream.PDFExtractor") as mock_extractor:
            mock_extractor.return_value.extract.return_value = sample_blocks
            result = docstream.extract("test.pdf")
        assert isinstance(result, list)

    def test_returns_correct_count(self, sample_blocks):
        with patch("docstream.PDFExtractor") as mock_extractor:
            mock_extractor.return_value.extract.return_value = sample_blocks
            result = docstream.extract("test.pdf")
        assert len(result) == 2

    def test_accepts_string_path(self, sample_blocks):
        with patch("docstream.PDFExtractor") as mock_extractor:
            mock_extractor.return_value.extract.return_value = sample_blocks
            docstream.extract("paper.pdf")
        mock_extractor.assert_called_once_with("paper.pdf")

    def test_accepts_path_object(self, sample_blocks, tmp_path):
        pdf = tmp_path / "test.pdf"
        with patch("docstream.PDFExtractor") as mock_extractor:
            mock_extractor.return_value.extract.return_value = sample_blocks
            docstream.extract(pdf)
        mock_extractor.assert_called_once_with(str(pdf))

    def test_propagates_extraction_error(self):
        from docstream.exceptions import ExtractionError

        with patch("docstream.PDFExtractor") as mock_extractor:
            mock_extractor.return_value.extract.side_effect = ExtractionError("bad file")
            with pytest.raises(ExtractionError):
                docstream.extract("bad.pdf")


# ---------------------------------------------------------------------------
# test_structure
# ---------------------------------------------------------------------------


class TestStructure:
    def test_returns_document_ast(self, sample_blocks, sample_ast):
        with patch("docstream.DocumentStructurer") as mock_structurer:
            mock_structurer.return_value.structure.return_value = sample_ast
            result = docstream.structure(sample_blocks)
        assert isinstance(result, DocumentAST)

    def test_uses_env_gemini_key(self, sample_blocks, sample_ast):
        with (
            patch("docstream.DocumentStructurer") as mock_structurer,
            patch.dict(
                os.environ, {"GEMINI_API_KEY": "env-gemini-key", "GROQ_API_KEY": "env-groq"}
            ),
        ):
            mock_structurer.return_value.structure.return_value = sample_ast
            docstream.structure(sample_blocks)
        call_kwargs = mock_structurer.call_args[1]
        assert call_kwargs["gemini_key"] == "env-gemini-key"

    def test_explicit_gemini_key_overrides_env(self, sample_blocks, sample_ast):
        with (
            patch("docstream.DocumentStructurer") as mock_structurer,
            patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}),
        ):
            mock_structurer.return_value.structure.return_value = sample_ast
            docstream.structure(sample_blocks, gemini_key="explicit-key")
        call_kwargs = mock_structurer.call_args[1]
        assert call_kwargs["gemini_key"] == "explicit-key"

    def test_groq_key_loaded_from_env(self, sample_blocks, sample_ast):
        with (
            patch("docstream.DocumentStructurer") as mock_structurer,
            patch.dict(os.environ, {"GEMINI_API_KEY": "g", "GROQ_API_KEY": "groq-env-key"}),
        ):
            mock_structurer.return_value.structure.return_value = sample_ast
            docstream.structure(sample_blocks)
        call_kwargs = mock_structurer.call_args[1]
        assert call_kwargs["groq_key"] == "groq-env-key"

    def test_explicit_groq_key_overrides_env(self, sample_blocks, sample_ast):
        with (
            patch("docstream.DocumentStructurer") as mock_structurer,
            patch.dict(os.environ, {"GROQ_API_KEY": "env-groq"}),
        ):
            mock_structurer.return_value.structure.return_value = sample_ast
            docstream.structure(sample_blocks, groq_key="explicit-groq")
        call_kwargs = mock_structurer.call_args[1]
        assert call_kwargs["groq_key"] == "explicit-groq"


# ---------------------------------------------------------------------------
# test_render
# ---------------------------------------------------------------------------


class TestRender:
    def test_returns_conversion_result(self, sample_ast, success_result, tmp_path):
        with patch("docstream.DocumentRenderer") as mock_renderer:
            mock_renderer.return_value.render.return_value = success_result
            result = docstream.render(sample_ast, output_dir=tmp_path)
        assert isinstance(result, ConversionResult)

    def test_default_template_is_report(self, sample_ast, success_result, tmp_path):
        with patch("docstream.DocumentRenderer") as mock_renderer:
            mock_renderer.return_value.render.return_value = success_result
            docstream.render(sample_ast, output_dir=tmp_path)
        mock_renderer.assert_called_once_with(template="report")

    def test_custom_template_is_forwarded(self, sample_ast, success_result, tmp_path):
        with patch("docstream.DocumentRenderer") as mock_renderer:
            mock_renderer.return_value.render.return_value = success_result
            docstream.render(sample_ast, template="ieee", output_dir=tmp_path)
        mock_renderer.assert_called_once_with(template="ieee")

    def test_accepts_string_output_dir(self, sample_ast, success_result, tmp_path):
        with patch("docstream.DocumentRenderer") as mock_renderer:
            mock_renderer.return_value.render.return_value = success_result
            result = docstream.render(sample_ast, output_dir=str(tmp_path))
        assert result.success is True

    def test_output_dir_passed_as_path(self, sample_ast, success_result, tmp_path):
        with patch("docstream.DocumentRenderer") as mock_renderer:
            mock_renderer.return_value.render.return_value = success_result
            docstream.render(sample_ast, output_dir=str(tmp_path))
        render_args = mock_renderer.return_value.render.call_args[0]
        assert isinstance(render_args[1], Path)


# ---------------------------------------------------------------------------
# test_convert
# ---------------------------------------------------------------------------


class TestConvert:
    def test_chains_all_three_stages(self, sample_blocks, sample_ast, success_result, tmp_path):
        with (
            patch("docstream.extract", return_value=sample_blocks) as mock_extract,
            patch("docstream.structure", return_value=sample_ast) as mock_structure,
            patch("docstream.render", return_value=success_result) as mock_render,
        ):
            docstream.convert("paper.pdf", template="ieee", output_dir=tmp_path)
        mock_extract.assert_called_once_with("paper.pdf")
        mock_structure.assert_called_once_with(sample_blocks)
        mock_render.assert_called_once_with(sample_ast, template="ieee", output_dir=Path(tmp_path))

    def test_returns_conversion_result(self, sample_blocks, sample_ast, success_result, tmp_path):
        with (
            patch("docstream.extract", return_value=sample_blocks),
            patch("docstream.structure", return_value=sample_ast),
            patch("docstream.render", return_value=success_result),
        ):
            result = docstream.convert("paper.pdf", output_dir=tmp_path)
        assert isinstance(result, ConversionResult)

    def test_default_template_report(self, sample_blocks, sample_ast, success_result, tmp_path):
        with (
            patch("docstream.extract", return_value=sample_blocks),
            patch("docstream.structure", return_value=sample_ast),
            patch("docstream.render", return_value=success_result) as mock_render,
        ):
            docstream.convert("paper.pdf", output_dir=tmp_path)
        assert mock_render.call_args[1]["template"] == "report"

    def test_output_dir_forwarded_as_path(
        self, sample_blocks, sample_ast, success_result, tmp_path
    ):
        with (
            patch("docstream.extract", return_value=sample_blocks),
            patch("docstream.structure", return_value=sample_ast),
            patch("docstream.render", return_value=success_result) as mock_render,
        ):
            docstream.convert("paper.pdf", output_dir=str(tmp_path))
        assert isinstance(mock_render.call_args[1]["output_dir"], Path)


# ---------------------------------------------------------------------------
# test___version__ and importability
# ---------------------------------------------------------------------------


class TestVersion:
    def test_version_is_string(self):
        assert isinstance(docstream.__version__, str)

    def test_version_value(self):
        assert docstream.__version__ == "0.1.0"

    def test_convert_is_callable(self):
        assert callable(docstream.convert)

    def test_extract_is_callable(self):
        assert callable(docstream.extract)

    def test_structure_is_callable(self):
        assert callable(docstream.structure)

    def test_render_is_callable(self):
        assert callable(docstream.render)

    def test_all_symbols_in___all__(self):
        for name in ("convert", "extract", "structure", "render", "__version__"):
            assert name in docstream.__all__
