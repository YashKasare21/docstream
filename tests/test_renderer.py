"""
Tests for Phase-3 DocumentRenderer.

All subprocess calls (pandoc, xelatex) are mocked so tests run
without a real TeX installation and finish in milliseconds.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docstream.core.renderer import DocumentRenderer
from docstream.exceptions import RenderingError
from docstream.models.document import DocumentAST, DocumentMetadata, Section

# ---------------------------------------------------------------------------
# Shared fixtures & helpers
# ---------------------------------------------------------------------------

FAKE_TEX = "\\documentclass{article}\\begin{document}Hello world\\end{document}"


@pytest.fixture
def simple_ast():
    """Minimal DocumentAST with one section — used by all renderer tests."""
    meta = DocumentMetadata(title="Test Document", author="Test Author")
    section = Section(
        heading="Introduction",
        level=1,
        content=["This is a test paragraph.", "Second paragraph of the introduction."],
    )
    return DocumentAST(
        title="Test Document",
        authors=["Test Author"],
        metadata=meta,
        sections=[section],
    )


def _make_subprocess_mock(
    xelatex_fail: bool = False,
    xelatex_log_content: str | None = None,
    pandoc_fail: bool = False,
):
    """Return a callable suitable for use as subprocess.run side_effect."""

    def _run(cmd, **kwargs):  # noqa: ANN001
        if not cmd:
            return MagicMock(returncode=0)
        prog = cmd[0]

        # ---- pandoc --version (init check) --------------------------------
        if prog == "pandoc" and len(cmd) > 1 and cmd[1] == "--version":
            return MagicMock(returncode=0, stdout="pandoc 3.1.3", stderr="")

        # ---- pandoc JSON → LaTeX conversion --------------------------------
        if prog == "pandoc":
            if pandoc_fail:
                return MagicMock(returncode=1, stdout="", stderr="pandoc: fatal error")
            return MagicMock(returncode=0, stdout=FAKE_TEX, stderr="")

        # ---- xelatex -------------------------------------------------------
        if prog == "xelatex":
            cwd = kwargs.get("cwd", ".")
            if xelatex_log_content:
                Path(cwd, "document.log").write_text(xelatex_log_content, encoding="utf-8")
            if xelatex_fail:
                return MagicMock(returncode=1, stdout="", stderr="xelatex: compilation failed")
            # Success: create a fake PDF so _compile_latex finds the file
            Path(cwd, "document.pdf").write_bytes(b"%PDF-1.4 fake-pdf-content")
            return MagicMock(returncode=0, stdout="", stderr="")

        return MagicMock(returncode=0)

    return _run


# ---------------------------------------------------------------------------
# test_render_report_template
# ---------------------------------------------------------------------------


class TestRenderReportTemplate:
    """DocumentRenderer with 'report' template — success path."""

    def test_success_is_true(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("report")
            result = renderer.render(simple_ast, tmp_path)
        assert result.success is True

    def test_template_used_is_report(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("report")
            result = renderer.render(simple_ast, tmp_path)
        assert result.template_used == "report"

    def test_tex_path_is_set_and_has_correct_suffix(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("report")
            result = renderer.render(simple_ast, tmp_path)
        assert result.tex_path is not None
        assert Path(result.tex_path).suffix == ".tex"

    def test_pdf_path_is_set_and_has_correct_suffix(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("report")
            result = renderer.render(simple_ast, tmp_path)
        assert result.pdf_path is not None
        assert Path(result.pdf_path).suffix == ".pdf"

    def test_processing_time_is_non_negative(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("report")
            result = renderer.render(simple_ast, tmp_path)
        assert result.processing_time_seconds >= 0.0

    def test_error_field_is_none_on_success(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("report")
            result = renderer.render(simple_ast, tmp_path)
        assert result.error is None


# ---------------------------------------------------------------------------
# test_render_ieee_template
# ---------------------------------------------------------------------------


class TestRenderIeeeTemplate:
    """DocumentRenderer with 'ieee' template — success path."""

    def test_success_is_true(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("ieee")
            result = renderer.render(simple_ast, tmp_path)
        assert result.success is True

    def test_template_used_is_ieee(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("ieee")
            result = renderer.render(simple_ast, tmp_path)
        assert result.template_used == "ieee"

    def test_unknown_template_raises_value_error(self):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            with pytest.raises(ValueError, match="Unknown template"):
                DocumentRenderer("nonexistent_template")

    def test_all_three_valid_templates_accepted(self):
        for tpl in ("report", "ieee", "resume"):
            with patch("subprocess.run", side_effect=_make_subprocess_mock()):
                renderer = DocumentRenderer(tpl)
                assert renderer.template == tpl


# ---------------------------------------------------------------------------
# test_render_resume_template
# ---------------------------------------------------------------------------


class TestRenderResumeTemplate:
    """DocumentRenderer with 'resume' template — success path."""

    def test_success_is_true(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("resume")
            result = renderer.render(simple_ast, tmp_path)
        assert result.success is True

    def test_template_used_is_resume(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("resume")
            result = renderer.render(simple_ast, tmp_path)
        assert result.template_used == "resume"

    def test_output_dir_is_created(self, simple_ast, tmp_path):
        out_dir = tmp_path / "output" / "nested"
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("resume")
            result = renderer.render(simple_ast, out_dir)
        assert result.success is True
        assert out_dir.exists()


# ---------------------------------------------------------------------------
# test_latex_error_parsed_correctly
# ---------------------------------------------------------------------------


class TestLatexErrorParsedCorrectly:
    """xelatex failure → error is parsed from .log and surfaced."""

    def test_success_is_false_on_xelatex_failure(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock(xelatex_fail=True)):
            renderer = DocumentRenderer("report")
            result = renderer.render(simple_ast, tmp_path)
        assert result.success is False

    def test_error_field_is_populated(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock(xelatex_fail=True)):
            renderer = DocumentRenderer("report")
            result = renderer.render(simple_ast, tmp_path)
        assert result.error is not None
        assert len(result.error) > 0

    def test_log_bang_lines_appear_in_error(self, simple_ast, tmp_path):
        log = "! Undefined control sequence.\n! Emergency stop.\n"
        with patch(
            "subprocess.run",
            side_effect=_make_subprocess_mock(xelatex_fail=True, xelatex_log_content=log),
        ):
            renderer = DocumentRenderer("report")
            result = renderer.render(simple_ast, tmp_path)
        assert "Undefined control sequence" in result.error

    def test_template_used_still_recorded_on_failure(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock(xelatex_fail=True)):
            renderer = DocumentRenderer("report")
            result = renderer.render(simple_ast, tmp_path)
        assert result.template_used == "report"


# ---------------------------------------------------------------------------
# test_cleanup_on_failure
# ---------------------------------------------------------------------------


class TestCleanupOnFailure:
    """_cleanup is always called in finally — even when rendering fails."""

    def test_cleanup_called_on_xelatex_failure(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock(xelatex_fail=True)):
            renderer = DocumentRenderer("report")
            with patch.object(renderer, "_cleanup") as mock_cleanup:
                result = renderer.render(simple_ast, tmp_path)
        assert result.success is False
        assert mock_cleanup.call_count >= 1

    def test_cleanup_called_on_pandoc_failure(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock(pandoc_fail=True)):
            renderer = DocumentRenderer("report")
            with patch.object(renderer, "_cleanup") as mock_cleanup:
                result = renderer.render(simple_ast, tmp_path)
        assert result.success is False
        assert mock_cleanup.call_count >= 1

    def test_cleanup_called_on_success_too(self, simple_ast, tmp_path):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("report")
            with patch.object(renderer, "_cleanup") as mock_cleanup:
                result = renderer.render(simple_ast, tmp_path)
        assert result.success is True
        assert mock_cleanup.call_count >= 1


# ---------------------------------------------------------------------------
# test_pandoc_not_found_error
# ---------------------------------------------------------------------------


class TestPandocNotFoundError:
    """Missing pandoc binary raises RenderingError at __init__ time."""

    def test_raises_rendering_error(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("pandoc: not found")):
            with pytest.raises(RenderingError):
                DocumentRenderer("report")

    def test_error_message_mentions_pandoc_org(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            try:
                DocumentRenderer("report")
                pytest.fail("Expected RenderingError was not raised")
            except RenderingError as exc:
                assert "pandoc.org" in str(exc)

    def test_rendering_error_not_file_not_found_error(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            exc_caught = None
            try:
                DocumentRenderer("report")
            except RenderingError as exc:
                exc_caught = exc
        assert exc_caught is not None
        assert isinstance(exc_caught, RenderingError)


# ---------------------------------------------------------------------------
# Unit tests for _ast_to_pandoc_json
# ---------------------------------------------------------------------------


class TestAstToPandocJson:
    """Direct unit tests for the Pandoc JSON conversion helper."""

    def test_output_has_required_top_level_keys(self, simple_ast):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("report")
        pj = renderer._ast_to_pandoc_json(simple_ast)
        assert "pandoc-api-version" in pj
        assert "meta" in pj
        assert "blocks" in pj

    def test_blocks_are_non_empty_for_non_trivial_ast(self, simple_ast):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("report")
        pj = renderer._ast_to_pandoc_json(simple_ast)
        assert len(pj["blocks"]) > 0

    def test_header_block_present_for_section(self, simple_ast):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("report")
        pj = renderer._ast_to_pandoc_json(simple_ast)
        types = [b["t"] for b in pj["blocks"]]
        assert "Header" in types

    def test_title_in_meta(self, simple_ast):
        with patch("subprocess.run", side_effect=_make_subprocess_mock()):
            renderer = DocumentRenderer("report")
        pj = renderer._ast_to_pandoc_json(simple_ast)
        assert "title" in pj["meta"]
