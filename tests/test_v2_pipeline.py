"""Tests for the v2 PDF to LaTeX pipeline."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import fitz


# ─── Fixtures ───────────────────────────────────────────

@pytest.fixture
def minimal_pdf(tmp_path) -> Path:
    """Create a minimal digital PDF for testing."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Test Paper Title\n\n"
        "Abstract\n\n"
        "This is the abstract of the test paper.\n\n"
        "1. Introduction\n\n"
        "This is the introduction section.\n\n"
        "2. Methods\n\n"
        "These are the methods used.\n\n"
        "3. Results\n\n"
        "These are the results obtained.\n\n"
        "4. Conclusion\n\n"
        "This is the conclusion.",
        fontsize=12,
    )
    path = tmp_path / "test.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def sample_document() -> dict:
    """Sample structured document dict."""
    return {
        "title": "Test Paper Title",
        "metadata": {
            "author": "Test Author",
            "page_count": 1,
            "is_scanned": False,
        },
        "structure": [
            {"type": "heading", "text": "Test Paper Title",
             "level": 1, "page": 1},
            {"type": "paragraph",
             "text": "This is the abstract.", "page": 1},
            {"type": "heading", "text": "Introduction",
             "level": 2, "page": 1},
            {"type": "paragraph",
             "text": "This is the introduction.", "page": 1},
            {"type": "heading", "text": "Conclusion",
             "level": 2, "page": 1},
            {"type": "paragraph",
             "text": "This is the conclusion.", "page": 1},
        ],
        "full_text": "Test Paper Title\nThis is the abstract...",
        "body_font_size": 12.0,
    }


VALID_LATEX = r"""
\documentclass[12pt, a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\begin{document}
\title{Test Title}
\author{Test Author}
\date{\today}
\maketitle
\begin{abstract}
Test abstract.
\end{abstract}
\section{Introduction}
Test introduction.
\end{document}
"""


# ─── Extractor tests ───────────────────────────────────

class TestExtractorV2:
    """Tests for the v2 PDF extractor."""

    def test_extract_returns_dict(self, minimal_pdf):
        """Extraction should return a dictionary."""
        from docstream.core.extractor_v2 import extract_structured
        result = extract_structured(minimal_pdf)
        assert isinstance(result, dict)

    def test_extract_has_required_keys(self, minimal_pdf):
        """Result dict must contain all expected keys."""
        from docstream.core.extractor_v2 import extract_structured
        result = extract_structured(minimal_pdf)
        assert "title" in result
        assert "structure" in result
        assert "full_text" in result
        assert "metadata" in result

    def test_extract_detects_headings(self, minimal_pdf):
        """Extractor should detect paragraph blocks from PDF text."""
        from docstream.core.extractor_v2 import extract_structured
        result = extract_structured(minimal_pdf)
        types = [b["type"] for b in result["structure"]]
        assert "paragraph" in types

    def test_extract_full_text_not_empty(self, minimal_pdf):
        """Full text should contain meaningful content."""
        from docstream.core.extractor_v2 import extract_structured
        result = extract_structured(minimal_pdf)
        assert len(result["full_text"]) > 50

    def test_extract_raises_on_missing_file(self):
        """Missing file should raise ExtractionError."""
        from docstream.core.extractor_v2 import extract_structured
        from docstream.exceptions import ExtractionError
        with pytest.raises(ExtractionError):
            extract_structured("/nonexistent/file.pdf")

    def test_table_to_markdown_basic(self):
        """Basic table data should convert to markdown format."""
        from docstream.core.extractor_v2 import _table_to_markdown
        table = [["H1", "H2"], ["v1", "v2"], ["v3", "v4"]]
        result = _table_to_markdown(table)
        assert "H1" in result
        assert "H2" in result
        assert "|" in result

    def test_table_to_markdown_empty(self):
        """Empty tables should return empty string."""
        from docstream.core.extractor_v2 import _table_to_markdown
        assert _table_to_markdown([]) == ""
        assert _table_to_markdown([[]]) == ""

    def test_heading_level_estimation(self):
        """Font size ratios should map to correct heading levels."""
        from docstream.core.extractor_v2 import _estimate_heading_level
        assert _estimate_heading_level(24.0, 12.0) == 1
        assert _estimate_heading_level(16.0, 12.0) == 2
        assert _estimate_heading_level(13.0, 12.0) == 3


# ─── Generator tests ───────────────────────────────────

class TestGenerator:
    """Tests for the LaTeX generator."""

    def test_valid_templates_accepted(self, sample_document):
        """Report template should produce LaTeX with documentclass."""
        from docstream.core.generator import generate_latex
        mock_ai = MagicMock()
        mock_ai.complete.return_value = VALID_LATEX
        result = generate_latex(sample_document, "report", mock_ai)
        assert "\\documentclass" in result

    def test_ieee_template_accepted(self, sample_document):
        """IEEE template should be accepted without error."""
        from docstream.core.generator import generate_latex
        mock_ai = MagicMock()
        mock_ai.complete.return_value = VALID_LATEX
        result = generate_latex(sample_document, "ieee", mock_ai)
        assert result  # Should not raise

    def test_invalid_template_raises(self, sample_document):
        """Invalid template name should raise TemplateError."""
        from docstream.core.generator import generate_latex
        from docstream.exceptions import TemplateError
        mock_ai = MagicMock()
        with pytest.raises(TemplateError):
            generate_latex(sample_document, "invalid", mock_ai)

    def test_extract_latex_strips_fences(self):
        """Markdown code fences should be stripped from AI response."""
        from docstream.core.generator import _extract_latex
        fenced = "```latex\n" + VALID_LATEX + "\n```"
        result = _extract_latex(fenced)
        assert "```" not in result
        assert "\\documentclass" in result

    def test_extract_latex_finds_documentclass(self):
        """LaTeX should be found even with preamble text."""
        from docstream.core.generator import _extract_latex
        with_preamble = "Here is the LaTeX:\n" + VALID_LATEX
        result = _extract_latex(with_preamble)
        assert result.startswith("\\documentclass")

    def test_ai_failure_raises_structuring_error(self, sample_document):
        """AI provider exception should raise StructuringError."""
        from docstream.core.generator import generate_latex
        from docstream.exceptions import StructuringError
        mock_ai = MagicMock()
        mock_ai.complete.side_effect = Exception("API down")
        with pytest.raises(StructuringError):
            generate_latex(sample_document, "report", mock_ai)

    def test_empty_ai_response_raises(self, sample_document):
        """Empty AI response should raise StructuringError."""
        from docstream.core.generator import generate_latex
        from docstream.exceptions import StructuringError
        mock_ai = MagicMock()
        mock_ai.complete.return_value = ""
        with pytest.raises(StructuringError):
            generate_latex(sample_document, "report", mock_ai)

    def test_prompt_contains_content(self, sample_document):
        """Built prompt should include document content."""
        from docstream.core.generator import _build_prompt
        from docstream.core.generator import _load_skeleton
        from docstream.core.generator import _load_instructions
        skeleton = _load_skeleton("report")
        instructions = _load_instructions("report")
        prompt = _build_prompt(
            sample_document, skeleton, instructions, "report"
        )
        assert "Test Paper Title" in prompt
        assert "Introduction" in prompt


# ─── Compiler tests ───────────────────────────────────

class TestCompiler:
    """Tests for the XeLaTeX compiler wrapper."""

    def test_xelatex_available_check(self):
        """Availability check should return a boolean."""
        from docstream.core.compiler import _xelatex_available
        result = _xelatex_available()
        assert isinstance(result, bool)

    def test_parse_log_errors_finds_fatal(self):
        """Fatal errors in log should be detected."""
        from docstream.core.compiler import _parse_log_errors
        log = "! Fatal error: something wrong\nNormal line\n"
        errors = _parse_log_errors(log)
        assert any("Fatal" in e for e in errors)

    def test_parse_log_errors_ignores_overfull(self):
        """Overfull hbox warnings should be filtered out."""
        from docstream.core.compiler import _parse_log_errors
        log = "Overfull \\hbox (10pt) in paragraph\n"
        errors = _parse_log_errors(log)
        assert len(errors) == 0

    @patch("docstream.core.compiler._xelatex_available")
    def test_raises_when_xelatex_missing(
        self, mock_available, tmp_path
    ):
        """Missing XeLaTeX should raise RenderingError."""
        from docstream.core.compiler import compile_latex
        from docstream.exceptions import RenderingError
        mock_available.return_value = False
        with pytest.raises(RenderingError, match="XeLaTeX"):
            compile_latex(VALID_LATEX, tmp_path)


# ─── Integration test ──────────────────────────────────

class TestPublicAPI:
    """Tests for the public docstream API."""

    def test_convert_returns_result(self, minimal_pdf, tmp_path):
        """convert() should return a ConversionResult."""
        import docstream
        mock_ai = MagicMock()
        mock_ai.complete.return_value = VALID_LATEX

        with patch("docstream.core.compiler._xelatex_available",
                   return_value=False):
            result = docstream.convert(
                minimal_pdf,
                template="report",
                output_dir=tmp_path,
                ai_provider=mock_ai,
            )

        # Should fail gracefully (no xelatex in test env)
        assert isinstance(result, docstream.ConversionResult)
        assert result.template_used == "report"

    def test_extract_returns_dict(self, minimal_pdf):
        """extract() should return a structured dict."""
        import docstream
        result = docstream.extract(minimal_pdf)
        assert isinstance(result, dict)
        assert "structure" in result

    def test_generate_returns_latex(self, sample_document):
        """generate() should return LaTeX string."""
        import docstream
        mock_ai = MagicMock()
        mock_ai.complete.return_value = VALID_LATEX
        result = docstream.generate(
            sample_document, "report", mock_ai
        )
        assert "\\documentclass" in result
