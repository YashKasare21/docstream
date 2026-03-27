"""
Tests for QualityChecker and QualityReport.

All subprocess calls (xelatex) are mocked — no real compilation.
"""

from __future__ import annotations

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from docstream.models.document import QualityReport

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

MINIMAL_VALID_LATEX = r"""
\documentclass{article}
\usepackage{fontenc}
\usepackage{inputenc}
\begin{document}
\title{Test Document}
\section{Introduction}
This is a test document with sufficient content to pass
quality checks. It contains multiple sentences and words
to ensure the content length threshold is met properly.
The document has proper structure and formatting throughout.
\end{document}
"""

BROKEN_LATEX = r"""
\documentclass{article}
\begin{document}
\begin{itemize}
Missing end for itemize — this environment is never closed.
The document has enough content here to not trigger the empty
document check, but it will fail environment balance check.
\end{document}
"""

# ---------------------------------------------------------------------------
# 1. Valid latex passes static analysis
# ---------------------------------------------------------------------------


def test_valid_latex_passes_static():
    from docstream.core.quality_checker import QualityChecker

    checker = QualityChecker()
    errors, warnings = checker._static_analysis(MINIMAL_VALID_LATEX, "report")
    assert errors == []


# ---------------------------------------------------------------------------
# 2. Missing \documentclass is an error
# ---------------------------------------------------------------------------


def test_missing_documentclass_fails():
    from docstream.core.quality_checker import QualityChecker

    latex = MINIMAL_VALID_LATEX.replace(r"\documentclass{article}", "")
    errors, _ = QualityChecker()._static_analysis(latex, "report")

    assert any(r"\documentclass" in e for e in errors)


# ---------------------------------------------------------------------------
# 3. Missing \begin{document} is an error
# ---------------------------------------------------------------------------


def test_missing_begin_document_fails():
    from docstream.core.quality_checker import QualityChecker

    latex = MINIMAL_VALID_LATEX.replace(r"\begin{document}", "")
    errors, _ = QualityChecker()._static_analysis(latex, "report")

    assert errors  # at least one error


# ---------------------------------------------------------------------------
# 4. Unbalanced environment is detected
# ---------------------------------------------------------------------------


def test_unbalanced_environments_detected():
    from docstream.core.quality_checker import QualityChecker

    errors = QualityChecker()._check_balanced_environments(BROKEN_LATEX)

    assert any("itemize" in e for e in errors)


# ---------------------------------------------------------------------------
# 5. Balanced environments in valid LaTeX produce no errors
# ---------------------------------------------------------------------------


def test_balanced_environments_pass():
    from docstream.core.quality_checker import QualityChecker

    errors = QualityChecker()._check_balanced_environments(MINIMAL_VALID_LATEX)
    assert errors == []


# ---------------------------------------------------------------------------
# 6. Unmatched dollar sign is detected
# ---------------------------------------------------------------------------


def test_unmatched_dollar_sign_detected():
    from docstream.core.quality_checker import QualityChecker

    latex = MINIMAL_VALID_LATEX + "\nThis has $unclosed math mode."
    errors, _ = QualityChecker()._static_analysis(latex, "report")

    assert any("$" in e or "math" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# 7. Empty / command-only document fails
# ---------------------------------------------------------------------------


def test_empty_document_fails():
    from docstream.core.quality_checker import QualityChecker

    latex = r"\documentclass{article}" + "\n" + r"\begin{document}" + "\n" + r"\end{document}"
    errors, _ = QualityChecker()._static_analysis(latex, "report")

    assert any("empty" in e.lower() or "content" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# 8. Professional check warns about missing sections for ieee
# ---------------------------------------------------------------------------


def test_professional_check_warns_no_sections():
    from docstream.core.quality_checker import QualityChecker

    latex = r"""
\documentclass{article}
\begin{document}
\title{Paper}
\maketitle
\author{Someone}
No sections here at all, just plain text content that fills words.
\end{document}
"""
    _, warnings = QualityChecker()._professional_check(latex, "ieee")

    assert any("section" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# 9. Professional check warns about missing \author for ieee
# ---------------------------------------------------------------------------


def test_professional_check_warns_missing_author_ieee():
    from docstream.core.quality_checker import QualityChecker

    latex = r"""
\documentclass{article}
\begin{document}
\title{Paper}
\maketitle
\section{Introduction}
Content here.
\end{document}
"""
    _, warnings = QualityChecker()._professional_check(latex, "ieee")

    assert any("author" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# 10. Professional check warns about lorem ipsum placeholder
# ---------------------------------------------------------------------------


def test_professional_check_warns_lorem_ipsum():
    from docstream.core.quality_checker import QualityChecker

    latex = MINIMAL_VALID_LATEX + "\nlorem ipsum dolor sit amet"
    _, warnings = QualityChecker()._professional_check(latex, "report")

    assert any("lorem ipsum" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# 11. Professional check warns about TODO markers
# ---------------------------------------------------------------------------


def test_professional_check_warns_todo_markers():
    from docstream.core.quality_checker import QualityChecker

    latex = MINIMAL_VALID_LATEX + "\n% TODO: fix this section"
    _, warnings = QualityChecker()._professional_check(latex, "report")

    assert any("todo" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# 12. Compile check — success with mocked subprocess
# ---------------------------------------------------------------------------


def test_compile_check_success_mocked(tmp_path):
    from docstream.core.quality_checker import QualityChecker

    def fake_run(cmd, **kwargs):
        # Create a fake PDF so success=True
        out_dir = kwargs.get("cwd") or str(tmp_path)
        # find -output-directory argument
        if "-output-directory" in cmd:
            idx = cmd.index("-output-directory")
            out_dir = cmd[idx + 1]
        pdf = os.path.join(out_dir, "document.pdf")
        open(pdf, "wb").close()
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fake_run):
        checker = QualityChecker()
        errors, warnings, log, success = checker._compile_check(MINIMAL_VALID_LATEX)

    assert success is True
    assert errors == []


# ---------------------------------------------------------------------------
# 13. Compile check — parses errors from log
# ---------------------------------------------------------------------------


def test_compile_check_parses_errors_from_log(tmp_path):
    from docstream.core.quality_checker import QualityChecker

    error_line = "! LaTeX Error: Something went badly wrong."

    def fake_run(cmd, **kwargs):
        if "-output-directory" in cmd:
            idx = cmd.index("-output-directory")
            out_dir = cmd[idx + 1]
        else:
            out_dir = str(tmp_path)
        log_path = os.path.join(out_dir, "document.log")
        with open(log_path, "w") as fh:
            fh.write(error_line + "\n")
        # No PDF produced
        return MagicMock(returncode=1)

    with patch("subprocess.run", side_effect=fake_run):
        errors, _, _, success = QualityChecker()._compile_check(MINIMAL_VALID_LATEX)

    assert not success
    assert any("LaTeX Error" in e for e in errors)


# ---------------------------------------------------------------------------
# 14. Compile check — timeout produces blocking error
# ---------------------------------------------------------------------------


def test_compile_check_handles_timeout():
    from docstream.core.quality_checker import QualityChecker

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("xelatex", 60)):
        errors, _, _, success = QualityChecker()._compile_check(MINIMAL_VALID_LATEX)

    assert not success
    assert any("[BLOCKING]" in e for e in errors)


# ---------------------------------------------------------------------------
# 15. Compile check — FileNotFoundError (xelatex missing)
# ---------------------------------------------------------------------------


def test_compile_check_handles_xelatex_not_found():
    from docstream.core.quality_checker import QualityChecker

    with patch("subprocess.run", side_effect=FileNotFoundError):
        errors, _, _, success = QualityChecker()._compile_check(MINIMAL_VALID_LATEX)

    assert not success
    assert any("xelatex not found" in e for e in errors)


# ---------------------------------------------------------------------------
# 16. Overall score calculation (0.6 × technical + 0.4 × professional)
# ---------------------------------------------------------------------------


def test_overall_score_calculation():
    report = QualityReport(
        technical_score=1.0,
        professional_score=0.8,
    )
    computed = round(0.6 * report.technical_score + 0.4 * report.professional_score, 2)
    assert computed == pytest.approx(0.92)


# ---------------------------------------------------------------------------
# 17. passed=True when overall_score >= 0.6 and no blocking errors
# ---------------------------------------------------------------------------


def test_passed_threshold():
    from docstream.core.quality_checker import QualityChecker

    checker = QualityChecker()
    # Build a report manually via check() with skip_compilation=True
    report = checker.check(MINIMAL_VALID_LATEX, "report", skip_compilation=True)

    assert report.overall_score >= 0.6
    assert report.passed is True


# ---------------------------------------------------------------------------
# 18. passed=False when overall_score < 0.6
# ---------------------------------------------------------------------------


def test_failed_threshold():
    # Many static errors → low score → passed=False
    from docstream.core.quality_checker import QualityChecker

    # A document missing all required commands + unbalanced envs
    bad_latex = "hello world this is not latex at all just some random text here"
    report = QualityChecker().check(bad_latex, "report", skip_compilation=True)

    assert report.passed is False


# ---------------------------------------------------------------------------
# 19. skip_compilation prevents subprocess calls
# ---------------------------------------------------------------------------


def test_skip_compilation_flag():
    from docstream.core.quality_checker import QualityChecker

    with patch("subprocess.run") as mock_run:
        QualityChecker().check(MINIMAL_VALID_LATEX, "report", skip_compilation=True)

    mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# 20. Public API check_quality returns QualityReport
# ---------------------------------------------------------------------------


def test_public_api_check_quality():
    import docstream

    with patch(
        "docstream.core.quality_checker.QualityChecker.check",
        return_value=QualityReport(
            technical_score=1.0,
            professional_score=1.0,
            overall_score=1.0,
            passed=True,
        ),
    ) as mock_check:
        result = docstream.check_quality(MINIMAL_VALID_LATEX, "report")

    assert isinstance(result, QualityReport)
    mock_check.assert_called_once_with(MINIMAL_VALID_LATEX, "report", False)
