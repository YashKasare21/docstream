"""
Tests for the docstream CLI (docstream/cli.py).

All docstream API calls are mocked — tests cover argument parsing,
exit codes, output formatting, and error handling.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from docstream.cli import build_parser, main
from docstream.models.document import Block, BlockType, ConversionResult

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def success_result(tmp_path):
    return ConversionResult(
        success=True,
        tex_path=tmp_path / "document.tex",
        pdf_path=tmp_path / "document.pdf",
        processing_time_seconds=0.42,
        template_used="report",
    )


@pytest.fixture
def failed_result():
    return ConversionResult(
        success=False,
        error="xelatex: compilation failed",
        processing_time_seconds=0.1,
        template_used="report",
    )


@pytest.fixture
def sample_blocks():
    return [
        Block(type=BlockType.TEXT, content="Hello world", page_number=0),
        Block(type=BlockType.TEXT, content="Second block", page_number=1),
    ]


# ---------------------------------------------------------------------------
# test_version_flag
# ---------------------------------------------------------------------------


class TestVersionFlag:
    def test_version_exits_cleanly(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_short_version_flag(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["-V"])
        assert exc_info.value.code == 0

    def test_version_string_contains_docstream(self, capsys):
        with pytest.raises(SystemExit):
            main(["--version"])
        captured = capsys.readouterr()
        assert "docstream" in (captured.out + captured.err)

    def test_version_string_contains_version_number(self, capsys):
        with pytest.raises(SystemExit):
            main(["--version"])
        captured = capsys.readouterr()
        assert "0.2.0-dev" in (captured.out + captured.err)


# ---------------------------------------------------------------------------
# test_convert_command
# ---------------------------------------------------------------------------


class TestConvertCommand:
    def test_success_returns_zero(self, success_result, tmp_path):
        with patch("docstream.cli._with_progress", return_value=success_result):
            code = main(["convert", "paper.pdf", "--output", str(tmp_path)])
        assert code == 0

    def test_failure_result_returns_one(self, failed_result, tmp_path):
        with patch("docstream.cli._with_progress", return_value=failed_result):
            code = main(["convert", "paper.pdf", "--output", str(tmp_path)])
        assert code == 1

    def test_exception_returns_one(self, tmp_path):
        with patch("docstream.cli._with_progress", side_effect=RuntimeError("boom")):
            code = main(["convert", "paper.pdf", "--output", str(tmp_path)])
        assert code == 1

    def test_template_flag_long(self, success_result, tmp_path):
        with patch("docstream.cli._with_progress", return_value=success_result):
            code = main(["convert", "paper.pdf", "--template", "ieee", "--output", str(tmp_path)])
        assert code == 0

    def test_template_flag_short(self, success_result, tmp_path):
        with patch("docstream.cli._with_progress", return_value=success_result):
            code = main(["convert", "paper.pdf", "-t", "resume", "-o", str(tmp_path)])
        assert code == 0

    def test_output_printed_on_success(self, success_result, tmp_path, capsys):
        with patch("docstream.cli._with_progress", return_value=success_result):
            main(["convert", "paper.pdf", "--output", str(tmp_path)])
        captured = capsys.readouterr()
        assert "document.pdf" in captured.out or "document.tex" in captured.out


# ---------------------------------------------------------------------------
# test_extract_command
# ---------------------------------------------------------------------------


class TestExtractCommand:
    def test_success_returns_zero(self, sample_blocks):
        with patch("docstream.cli._with_progress", return_value=sample_blocks):
            code = main(["extract", "paper.pdf"])
        assert code == 0

    def test_exception_returns_one(self):
        with patch("docstream.cli._with_progress", side_effect=RuntimeError("fail")):
            code = main(["extract", "paper.pdf"])
        assert code == 1

    def test_saves_json_file(self, sample_blocks, tmp_path):
        out_file = tmp_path / "blocks.json"
        with patch("docstream.cli._with_progress", return_value=sample_blocks):
            code = main(["extract", "paper.pdf", "--output", str(out_file)])
        assert code == 0
        assert out_file.exists()

    def test_json_file_is_valid_list(self, sample_blocks, tmp_path):
        out_file = tmp_path / "blocks.json"
        with patch("docstream.cli._with_progress", return_value=sample_blocks):
            main(["extract", "paper.pdf", "--output", str(out_file)])
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 2

    def test_prints_to_stdout_without_output_flag(self, sample_blocks, capsys):
        with patch("docstream.cli._with_progress", return_value=sample_blocks):
            main(["extract", "paper.pdf"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)

    def test_short_output_flag(self, sample_blocks, tmp_path):
        out_file = tmp_path / "out.json"
        with patch("docstream.cli._with_progress", return_value=sample_blocks):
            code = main(["extract", "paper.pdf", "-o", str(out_file)])
        assert code == 0


# ---------------------------------------------------------------------------
# test_templates_list
# ---------------------------------------------------------------------------


class TestTemplatesList:
    def test_returns_zero(self):
        code = main(["templates", "list"])
        assert code == 0

    def test_output_contains_report(self, capsys):
        main(["templates", "list"])
        assert "report" in capsys.readouterr().out

    def test_output_contains_ieee(self, capsys):
        main(["templates", "list"])
        assert "ieee" in capsys.readouterr().out

    def test_output_contains_resume(self, capsys):
        main(["templates", "list"])
        assert "resume" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# test_no_command_prints_help
# ---------------------------------------------------------------------------


class TestNoCommand:
    def test_no_args_returns_zero(self):
        code = main([])
        assert code == 0

    def test_help_flag_exits_cleanly(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# test_build_parser (unit tests for parser)
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_returns_argument_parser(self):
        import argparse

        assert isinstance(build_parser(), argparse.ArgumentParser)

    def test_convert_default_template_is_report(self):
        args = build_parser().parse_args(["convert", "f.pdf"])
        assert args.template == "report"

    def test_convert_default_output_is_out(self):
        args = build_parser().parse_args(["convert", "f.pdf"])
        assert args.output == "./out"

    def test_convert_template_choices(self):
        for tpl in ("report", "ieee", "resume"):
            args = build_parser().parse_args(["convert", "f.pdf", "--template", tpl])
            assert args.template == tpl

    def test_extract_output_defaults_to_none(self):
        args = build_parser().parse_args(["extract", "f.pdf"])
        assert args.output is None

    def test_templates_list_subcommand_parsed(self):
        args = build_parser().parse_args(["templates", "list"])
        assert args.templates_command == "list"
