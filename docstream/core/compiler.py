"""
LaTeX Compiler — XeLaTeX compilation wrapper.

Compiles LaTeX source to PDF using XeLaTeX.
Runs twice for proper cross-reference resolution.
Parses compilation log for errors.
"""

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def compile_latex(
    latex_content: str,
    output_dir: str | Path,
    filename: str = "document",
    image_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    """
    Compile LaTeX content to PDF using XeLaTeX.

    Runs XeLaTeX twice for proper cross-reference resolution.

    Args:
        latex_content: Complete LaTeX document string
        output_dir: Directory to save output files
        filename: Base filename (without extension)

    Returns:
        Tuple of (tex_path, pdf_path)

    Raises:
        RenderingError: If XeLaTeX fails or is not installed
        CompilationError: If LaTeX compilation produces errors
    """
    from docstream.exceptions import RenderingError, CompilationError

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check XeLaTeX is available
    if not _xelatex_available():
        raise RenderingError(
            "XeLaTeX not found. Install with:\n"
            "  sudo apt install texlive-xetex texlive-latex-extra"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Copy images to temp dir so xelatex can find them
        if image_dir:
            for img_file in Path(image_dir).glob("fig_p*.*"):
                shutil.copy2(str(img_file), str(tmpdir))
                logger.debug(f"Copied image: {img_file.name}")

        tex_file = tmpdir / f"{filename}.tex"

        # Ensure document is complete before compiling
        latex_content = _ensure_complete_latex(latex_content)

        # Write LaTeX file
        tex_file.write_text(latex_content, encoding="utf-8")

        # Save .tex to output_dir immediately (for debugging)
        # This ensures .tex is available even if compilation fails
        output_tex = output_dir / f"{filename}.tex"
        output_tex.write_text(latex_content, encoding="utf-8")

        # Run XeLaTeX twice
        errors: list[str] = []
        for run in range(2):
            _result, log_content = _run_xelatex(tex_file, tmpdir)

            if run == 1:  # Check errors only on second run
                errors = _parse_log_errors(log_content)

        pdf_file = tmpdir / f"{filename}.pdf"

        if not pdf_file.exists():
            # PDF not generated — compilation failed
            error_summary = "\n".join(errors[:5]) if errors else "Unknown error"
            raise CompilationError(
                f"XeLaTeX failed to produce PDF.\n"
                f"Errors found:\n{error_summary}\n"
                f"LaTeX saved to: {output_tex}"
            )

        output_pdf = output_dir / f"{filename}.pdf"
        shutil.copy2(str(pdf_file), str(output_pdf))

        logger.info(
            f"Compiled successfully: {output_pdf} "
            f"({output_pdf.stat().st_size} bytes)"
        )

        if errors:
            logger.warning(
                f"Compilation warnings: {errors[:3]}"
            )

        return output_tex, output_pdf


def _ensure_complete_latex(latex: str) -> str:
    """
    Ensure LaTeX document is complete and compilable.

    If document is truncated (missing \\end{document}),
    close all open environments and add the end marker.
    """
    from collections import Counter

    if "\\end{document}" in latex:
        return latex

    # Document is truncated — emergency repair
    begins = re.findall(r'\\begin\{(\w+)\}', latex)
    ends = re.findall(r'\\end\{(\w+)\}', latex)

    begin_counts: Counter[str] = Counter(begins)
    end_counts: Counter[str] = Counter(ends)

    # Find unclosed environments (in open order), skip 'document'
    # since we always append \end{document} explicitly below
    open_envs: list[str] = []
    for env in begins:
        if env == "document":
            continue
        if begin_counts[env] > end_counts.get(env, 0):
            open_envs.append(env)
            end_counts[env] = end_counts.get(env, 0) + 1

    closing = ""
    for env in reversed(open_envs):
        closing += f"\n\\end{{{env}}}"

    closing += "\n\\end{document}"

    logger.warning(
        "LaTeX was truncated — added emergency closing: %s",
        closing.strip(),
    )

    return latex + closing


def _xelatex_available() -> bool:
    """Check if xelatex is installed and accessible."""
    try:
        result = subprocess.run(
            ["xelatex", "--version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _run_xelatex(
    tex_file: Path,
    output_dir: Path,
) -> tuple[subprocess.CompletedProcess, str]:
    """Run XeLaTeX once and return result + log content."""
    try:
        result = subprocess.run(
            [
                "xelatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={output_dir}",
                str(tex_file),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(output_dir),
        )
    except subprocess.TimeoutExpired:
        from docstream.exceptions import CompilationError
        raise CompilationError(
            "XeLaTeX timed out after 120 seconds. "
            "Document may be too complex."
        )

    # Read log file
    log_file = output_dir / f"{tex_file.stem}.log"
    log_content = ""
    if log_file.exists():
        try:
            log_content = log_file.read_text(
                encoding="utf-8", errors="replace"
            )
        except Exception:
            log_content = result.stdout + result.stderr

    return result, log_content


def _parse_log_errors(log_content: str) -> list[str]:
    """
    Parse XeLaTeX log for errors and warnings.

    Returns list of error/warning strings.
    Filters out common harmless messages.
    """
    errors: list[str] = []

    error_patterns = [
        r'^! .*',                          # Fatal errors
        r'^.*Error:.*',                    # Error lines
        r'Undefined control sequence',     # Missing commands
        r'Missing \$ inserted',            # Math mode errors
        r'Runaway argument',               # Argument errors
    ]

    # Ignore these common harmless warnings
    ignore_patterns = [
        r'LaTeX Warning: Label',
        r'LaTeX Warning: Reference',
        r'Overfull \\hbox',
        r'Underfull \\hbox',
        r'LaTeX Font Warning',
    ]

    for line in log_content.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Skip ignored patterns
        if any(re.search(p, line) for p in ignore_patterns):
            continue

        # Collect error patterns
        if any(re.search(p, line) for p in error_patterns):
            errors.append(line[:200])

    return list(dict.fromkeys(errors))  # Deduplicate
