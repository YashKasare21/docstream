"""
Quality Checker — validates LaTeX output before delivery.

Two-phase checking:

Phase A — Static analysis (fast, no compilation):
  - documentclass / begin{document} / end{document} present
  - All begin{env} have a matching end{env}
  - Math mode ($...$) is not left open
  - Document has non-trivial content

Phase B — Compilation check (requires xelatex):
  - Compiles in a temp directory with xelatex
  - Parses the .log for errors and warnings
  - Verifies the PDF was produced

Phase A always runs. Phase B runs only when Phase A passes
and ``skip_compilation=False``.

Professional checks run unconditionally after Phase A/B.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
from collections import Counter

from docstream.models.document import QualityReport

logger = logging.getLogger(__name__)


class QualityChecker:
    """Validate a LaTeX document for technical and professional quality.

    Usage::

        qc = QualityChecker()
        report = qc.check(latex_str, "report", skip_compilation=True)
        if not report.passed:
            print(report.errors)
    """

    # Minimum commands every LaTeX document must have
    REQUIRED_COMMANDS: list[str] = [
        r"\documentclass",
        r"\begin{document}",
        r"\end{document}",
    ]

    # Packages that are expected (but not required) for each template
    TEMPLATE_REQUIRED_PACKAGES: dict[str, list[str]] = {
        "report": ["fontenc", "inputenc"],
        "ieee": ["cite", "amsmath"],
        "resume": ["geometry"],
        "altacv": ["fontawesome5", "paracol"],
        "moderncv": ["moderncv"],
    }

    # xelatex log patterns that indicate blocking errors
    LOG_ERROR_PATTERNS: list[str] = [
        r"! LaTeX Error:",
        r"! Undefined control sequence",
        r"! Emergency stop",
        r"! Missing",
        r"! Too many",
        r"! Runaway argument",
        r"! File .* not found",
        r"! I can't find file",
    ]

    # xelatex log patterns that indicate non-blocking warnings
    LOG_WARNING_PATTERNS: list[str] = [
        r"LaTeX Warning:",
        r"Overfull \\hbox",
        r"Underfull \\hbox",
        r"Citation .* undefined",
        r"Reference .* undefined",
    ]

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def check(
        self,
        latex_content: str,
        template: str,
        skip_compilation: bool = False,
    ) -> QualityReport:
        """Run the full two-phase quality check.

        Args:
            latex_content: Complete LaTeX document string.
            template: Template name used to generate the content.
            skip_compilation: If ``True``, skip xelatex and score as if
                              compilation would succeed (Phase A only).

        Returns:
            ``QualityReport`` with scores, errors, warnings, and log.
        """
        report = QualityReport()

        # ── Phase A: static analysis ──────────────────────────────────────
        static_errors, static_warnings = self._static_analysis(latex_content, template)
        report.errors.extend(static_errors)
        report.warnings.extend(static_warnings)

        # Technical score from static analysis
        report.technical_score = max(0.0, 1.0 - len(static_errors) * 0.3)

        # ── Phase B: compilation ──────────────────────────────────────────
        if not static_errors and not skip_compilation:
            compile_errors, compile_warnings, log, success = self._compile_check(latex_content)
            report.errors.extend(compile_errors)
            report.warnings.extend(compile_warnings)
            report.latex_log = log
            report.compiled_successfully = success

            if not success:
                report.technical_score = max(0.0, report.technical_score - 0.4)
        elif skip_compilation:
            # Optimistically mark compilation as passing when static passes
            report.compiled_successfully = not bool(static_errors)

        # ── Professional checks ───────────────────────────────────────────
        prof_errors, prof_warnings = self._professional_check(latex_content, template)
        report.errors.extend(prof_errors)
        report.warnings.extend(prof_warnings)

        prof_issues = len(prof_errors) + len(prof_warnings) * 0.3
        report.professional_score = max(0.0, 1.0 - prof_issues * 0.15)

        # ── Overall score & pass/fail ─────────────────────────────────────
        report.overall_score = round(
            0.6 * report.technical_score + 0.4 * report.professional_score,
            2,
        )
        report.passed = report.overall_score >= 0.6 and not any(
            "blocking" in e.lower() or "fatal" in e.lower() for e in report.errors
        )

        return report

    # -------------------------------------------------------------------------
    # Phase A — static analysis
    # -------------------------------------------------------------------------

    def _static_analysis(self, latex: str, template: str) -> tuple[list[str], list[str]]:
        """Fast checks that require no compilation.

        Returns:
            Tuple of (errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Required structural commands
        for cmd in self.REQUIRED_COMMANDS:
            if cmd not in latex:
                errors.append(f"Missing required command: {cmd}")

        # 2. Balanced \begin / \end environments
        errors.extend(self._check_balanced_environments(latex))

        # 3. Document has non-trivial content
        text_only = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})*", "", latex)
        text_only = re.sub(r"[%{}\[\]]", "", text_only)
        if len(text_only.strip()) < 50:
            errors.append(
                "Document appears to be empty or contains only LaTeX "
                "commands with no actual content."
            )

        # 4. \documentclass should be the first non-comment line
        lines = latex.strip().split("\n")
        first_content = next(
            (ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("%")),
            "",
        )
        if first_content and not first_content.startswith(r"\documentclass"):
            warnings.append(r"\documentclass should be the first command in the document.")

        # 5. Unmatched math-mode delimiter ($)
        # Count raw $ minus escaped \$
        dollar_count = latex.count("$") - latex.count(r"\$")
        if dollar_count % 2 != 0:
            errors.append("Unmatched $ — math mode may be unclosed. Check all $ signs are paired.")

        # 6. Template-specific package hints (non-blocking)
        for pkg in self.TEMPLATE_REQUIRED_PACKAGES.get(template, []):
            if pkg not in latex:
                warnings.append(
                    f"Template '{template}' typically requires package "
                    f"'{pkg}' but it was not found."
                )

        return errors, warnings

    def _check_balanced_environments(self, latex: str) -> list[str]:
        """Verify every \\begin{env} has a matching \\end{env}.

        Returns:
            List of error strings for mismatched environments.
        """
        errors: list[str] = []

        begins = re.findall(r"\\begin\{(\w+)\}", latex)
        ends = re.findall(r"\\end\{(\w+)\}", latex)

        begin_counts = Counter(begins)
        end_counts = Counter(ends)

        all_envs = set(begin_counts) | set(end_counts)
        for env in sorted(all_envs):
            b = begin_counts.get(env, 0)
            e = end_counts.get(env, 0)
            if b > e:
                errors.append(f"Unmatched \\begin{{{env}}}: {b} opens, {e} closes.")
            elif e > b:
                errors.append(f"Unmatched \\end{{{env}}}: {e} closes, {b} opens.")

        return errors

    # -------------------------------------------------------------------------
    # Phase B — compilation check
    # -------------------------------------------------------------------------

    def _compile_check(self, latex_content: str) -> tuple[list[str], list[str], str, bool]:
        """Compile with xelatex in a temp directory and parse the log.

        Returns:
            Tuple of (errors, warnings, log_text, success).
        """
        errors: list[str] = []
        warnings: list[str] = []
        log_text = ""
        success = False

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "document.tex")
            pdf_path = os.path.join(tmpdir, "document.pdf")
            log_path = os.path.join(tmpdir, "document.log")

            with open(tex_path, "w", encoding="utf-8") as fh:
                fh.write(latex_content)

            try:
                subprocess.run(
                    [
                        "xelatex",
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "-output-directory",
                        tmpdir,
                        tex_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=tmpdir,
                )

                if os.path.exists(log_path):
                    with open(log_path, encoding="utf-8", errors="replace") as fh:
                        log_text = fh.read()

                success = os.path.exists(pdf_path)

                # Parse log
                seen_errors: set[str] = set()
                seen_warnings: set[str] = set()
                for line in log_text.splitlines():
                    line_s = line.strip()[:200]
                    for pattern in self.LOG_ERROR_PATTERNS:
                        if re.search(pattern, line) and line_s not in seen_errors:
                            errors.append(line_s)
                            seen_errors.add(line_s)
                            break
                    else:
                        for pattern in self.LOG_WARNING_PATTERNS:
                            if re.search(pattern, line) and line_s not in seen_warnings:
                                warnings.append(line_s)
                                seen_warnings.add(line_s)
                                break

                warnings = warnings[:10]

            except subprocess.TimeoutExpired:
                errors.append("[BLOCKING] LaTeX compilation timed out after 60 seconds.")
            except FileNotFoundError:
                errors.append("xelatex not found. Install TeX Live: sudo apt install texlive-xetex")

        return errors, warnings, log_text, success

    # -------------------------------------------------------------------------
    # Professional checks
    # -------------------------------------------------------------------------

    def _professional_check(self, latex: str, template: str) -> tuple[list[str], list[str]]:
        """Soft quality checks — output works but may look poor.

        Returns:
            Tuple of (errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Minimal content word count
        text_only = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})*", " ", latex)
        word_count = len(text_only.split())
        if word_count < 100:
            warnings.append("Document content appears very short. Consider adding more detail.")

        # 2. Sections present for report/ieee templates
        sections = re.findall(r"\\(?:section|subsection)\{([^}]+)\}", latex)
        if not sections and template in ("report", "ieee"):
            warnings.append(f"Template '{template}' typically has sections but none were found.")

        # 3. Title or name command
        if r"\title{" not in latex and r"\name{" not in latex:
            warnings.append("No title or name command found. Consider adding one.")

        # 4. IEEE-specific checks
        if template == "ieee":
            if r"\author{" not in latex:
                warnings.append("IEEE papers should have an \\author{} command.")
            if r"\maketitle" not in latex:
                warnings.append("IEEE papers need \\maketitle to display title.")

        # 5. Resume templates — key sections expected
        if template in ("resume", "altacv", "moderncv"):
            resume_keywords = ["experience", "education", "skills"]
            found = sum(1 for kw in resume_keywords if kw.lower() in latex.lower())
            if found < 2:
                warnings.append(
                    "Resume appears to be missing key sections. "
                    "Expected: experience, education, skills."
                )

        # 6. Placeholder text
        if "lorem ipsum" in latex.lower():
            warnings.append(
                "Document contains placeholder text ('lorem ipsum'). Replace with real content."
            )

        # 7. Developer markers
        if "TODO" in latex or "FIXME" in latex:
            warnings.append("Document contains TODO/FIXME markers. Remove before final output.")

        return errors, warnings
