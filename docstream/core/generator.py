"""
LaTeX Generator — AI-powered template filling.

Takes structured document content from extractor_v2.py
and uses AI to fill a LaTeX template skeleton with
the actual document content.

This is the core intelligence of the pipeline.
The AI receives:
1. The LaTeX skeleton with <<PLACEHOLDERS>>
2. The template instruction file
3. The extracted document structure
And returns a complete, compilable LaTeX document.
"""

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "skeletons"

VALID_TEMPLATES = {"report", "ieee"}


def generate_latex(
    document: dict[str, Any],
    template: str,
    ai_provider=None,
) -> str:
    """
    Generate complete LaTeX document from structured content.

    Uses AI to fill a LaTeX template skeleton with the
    content extracted from the source document.

    Args:
        document: Structured document dict from extract_structured()
        template: Template name — 'report' or 'ieee'
        ai_provider: Optional AIProviderChain instance.
                     If None, creates one automatically.

    Returns:
        Complete LaTeX document as string, ready for compilation.

    Raises:
        TemplateError: If template name is invalid
        StructuringError: If AI fails to generate valid LaTeX
    """
    from docstream.exceptions import TemplateError, StructuringError
    from docstream.core.ai_provider import AIProviderChain

    if template not in VALID_TEMPLATES:
        raise TemplateError(
            f"Unknown template: '{template}'. "
            f"Valid templates: {', '.join(sorted(VALID_TEMPLATES))}"
        )

    # Load template skeleton and instructions
    skeleton = _load_skeleton(template)
    instructions = _load_instructions(template)

    # Build the AI prompt
    prompt = _build_prompt(document, skeleton, instructions, template)

    # Get AI provider
    if ai_provider is None:
        ai_provider = AIProviderChain()

    # Call AI
    logger.info(
        f"Generating LaTeX for template '{template}' "
        f"({len(document.get('structure', []))} blocks)"
    )

    system_prompt = _build_system_prompt()

    # Try up to 2 times if output is truncated
    latex = ""
    for attempt in range(2):
        try:
            raw_response = ai_provider.complete(prompt, system_prompt)
        except Exception as e:
            raise StructuringError(
                f"AI provider failed: {e}"
            )

        latex = _extract_latex(raw_response)

        # Check if LaTeX is complete
        if _is_complete_latex(latex):
            break

        if attempt == 0:
            logger.warning(
                "LaTeX appears truncated, retrying with "
                "shorter content..."
            )
            # Shorten the prompt for retry
            prompt = _build_prompt(
                document, skeleton, instructions,
                template, max_chars=25000,
            )

    if not latex:
        raise StructuringError(
            "AI returned empty response. "
            "Check AI provider keys are valid."
        )

    if "\\documentclass" not in latex:
        raise StructuringError(
            "AI response does not contain valid LaTeX. "
            f"Response starts with: {latex[:200]}"
        )

    logger.info(
        f"Generated {len(latex)} characters of LaTeX"
    )

    return latex


def _load_skeleton(template: str) -> str:
    """Load the LaTeX skeleton file for a template."""
    path = TEMPLATES_DIR / f"{template}.tex"
    if not path.exists():
        raise FileNotFoundError(
            f"Template skeleton not found: {path}"
        )
    return path.read_text(encoding="utf-8")


def _load_instructions(template: str) -> str:
    """Load the instruction file for a template."""
    path = TEMPLATES_DIR / f"{template}_instructions.txt"
    if not path.exists():
        return ""  # Instructions are optional
    return path.read_text(encoding="utf-8")


def _build_system_prompt() -> str:
    """Build the system prompt for the AI."""
    return """You are an expert LaTeX document author with deep \
knowledge of academic publishing standards.

Your task is to convert extracted document content into \
a complete, professionally formatted LaTeX document.

STRICT RULES:
1. Return ONLY the complete LaTeX document
2. Start with \\documentclass and end with \\end{document}
3. No explanation before or after the LaTeX
4. No markdown code fences (no ```latex or ```)
5. Every \\begin{} must have a matching \\end{}
6. Escape special characters: & % $ # _ { } ~ ^ \\
7. Use the exact document class specified in the template
8. The output MUST compile with XeLaTeX without errors
9. CRITICAL: You MUST include \\end{document} as the \
very last line. Never truncate the output.
10. CRITICAL: If content is long, summarize sections \
rather than stopping mid-document. A complete \
document with summarized content is better than \
an incomplete document with full content.
11. Do not use \\input{} or \\include{} commands
12. Do not reference external image files
13. For references: collect all [REF] lines from the content \
and format as thebibliography. Each [REF] entry becomes a \
\\bibitem. Example: [REF] [1] Vaswani et al., "Attention is \
All You Need" becomes \\bibitem{ref1} Vaswani et al., \
``Attention is All You Need,'' 2017.
Use \\cite{ref1}, \\cite{ref2} etc. in text where citations \
appear as [?] or [number]. NEVER use enumerate or itemize \
for references.
14. CITATION HANDLING: When you see [?] in the text, replace \
with \\cite{refN} where N matches the corresponding reference \
number. If no bibliography entries exist, replace [?] with \
\\textsuperscript{N} using sequential numbers.
15. Never create enumerate lists with more than 15 items. \
Use itemize (bullet points) for longer lists.
16. Do not use \\alph, \\Alph counters."""


def _build_prompt(
    document: dict[str, Any],
    skeleton: str,
    instructions: str,
    template: str,
    max_chars: int = 50000,
) -> str:
    """Build the user prompt for LaTeX generation."""
    # Prepare structured content representation
    content_parts: list[str] = []

    # Add metadata
    meta = document.get("metadata", {})
    if meta.get("author"):
        content_parts.append(f"[AUTHOR]: {meta['author']}")

    # Add structure blocks
    for block in document.get("structure", []):
        block_type = block.get("type", "paragraph")
        text = block.get("text", "").strip()

        if not text:
            continue

        if block_type == "heading":
            level = block.get("level", 1)
            prefix = "#" * level
            content_parts.append(f"{prefix} {text}")
        elif block_type == "table":
            content_parts.append(f"[TABLE]\n{text}\n[/TABLE]")
        elif block_type == "reference":
            content_parts.append(f"[REF] {text}")
        else:
            content_parts.append(text)

    structured_content = "\n\n".join(content_parts)

    # Truncate if too long (preserve first 80%, last 20%)
    if len(structured_content) > max_chars:
        first_part = int(max_chars * 0.8)
        last_part = max_chars - first_part
        structured_content = (
            structured_content[:first_part]
            + "\n\n[... middle section truncated ...]\n\n"
            + structured_content[-last_part:]
        )

    prompt = f"""Convert the following document content into a \
complete LaTeX document using the provided template.

═══════════════════════════════
TEMPLATE SKELETON (fill the <<PLACEHOLDERS>>):
═══════════════════════════════
{skeleton}

═══════════════════════════════
TEMPLATE INSTRUCTIONS:
═══════════════════════════════
{instructions}

═══════════════════════════════
DOCUMENT CONTENT TO CONVERT:
═══════════════════════════════
{structured_content}

═══════════════════════════════
YOUR TASK:
═══════════════════════════════
CRITICAL REQUIREMENT:
- Use the ACTUAL TEXT provided above for all sections
- Do NOT summarize or paraphrase — use the real content
- Do NOT write placeholder text like "content was truncated"
- Every section must contain the real extracted text
- If content seems incomplete, use what is available

Replace every <<PLACEHOLDER>> in the skeleton with the \
appropriate content from the document above.

Rules:
- Replace <<TITLE>> with the document title
- Replace <<ABSTRACT>> with the abstract text
- Replace <<SECTIONS>> with properly formatted LaTeX sections
- Replace <<BIBLIOGRAPHY_BLOCK>> with formatted references
- For IEEE: replace <<AUTHORS_BLOCK>> with IEEEauthorblock format
- For IEEE: replace <<KEYWORDS>> with comma-separated keywords
- For IEEE: replace <<ACKNOWLEDGMENT_BLOCK>> with acknowledgment \
section or empty string if none found
- For Report: replace <<AUTHOR>> with author name
- For Report: replace <<DATE>> with date or \\today
- Preserve ALL content — do not skip any sections
- Format tables using the format specified in instructions
- Every special character must be properly escaped

Return the complete LaTeX document now:"""

    return prompt


def _is_complete_latex(latex: str) -> bool:
    """
    Check if LaTeX document is complete.

    Returns False if document appears truncated.
    """
    if not latex:
        return False

    # Must have both begin and end document
    has_begin = "\\begin{document}" in latex
    has_end = "\\end{document}" in latex

    if not has_begin or not has_end:
        return False

    # The \end{document} must be near the end (within last 200 chars)
    end_pos = latex.rfind("\\end{document}")
    if len(latex) - end_pos > 200:
        return False

    return True


def _extract_latex(response: str) -> str:
    """
    Extract clean LaTeX from AI response.

    Handles cases where AI wraps output in markdown fences
    or adds explanation text before/after the LaTeX.
    Also removes figure references we cannot fulfill.
    """
    # Remove markdown code fences
    response = re.sub(r'```latex\s*', '', response)
    response = re.sub(r'```\s*', '', response)
    response = response.strip()

    # Find LaTeX boundaries
    start = response.find('\\documentclass')
    if start == -1:
        return response  # Return as-is, validation will catch it

    end_marker = '\\end{document}'
    end = response.rfind(end_marker)
    if end == -1:
        latex = response[start:]
    else:
        latex = response[start:end + len(end_marker)]

    # Post-process
    latex = _postprocess_latex(latex)

    return latex


def _postprocess_latex(latex: str) -> str:
    """
    Post-process AI-generated LaTeX to fix common errors.

    Fixes:
    1. Replace \\includegraphics with placeholder boxes
    2. Fix bibliography formatted as enumerate
    3. Remove \\input{} and \\include{} commands
    4. Fix overly long enumerate lists (>20 items → itemize)
    """
    def replace_includegraphics(match: re.Match) -> str:
        filename = match.group(1)
        display_name = filename.replace('{', '').replace('}', '')
        display_name = display_name.split('/')[-1][:30]
        return (
            r'\fbox{\parbox{0.4\textwidth}{'
            r'\centering\small[Figure: ' + display_name + r']}}'
        )

    # Fix 1: Replace \includegraphics with placeholder
    latex = re.sub(
        r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',
        replace_includegraphics,
        latex,
    )

    # Fix 2: Replace enumerate used for references
    # Pattern: \begin{enumerate} containing \bibitem
    # This causes "Counter too large" with many refs
    if '\\bibitem' in latex and '\\begin{enumerate}' in latex:
        latex = re.sub(
            r'\\begin\{enumerate\}(.*?)\\end\{enumerate\}',
            lambda m: (
                '\\begin{thebibliography}{99}'
                + m.group(1)
                + '\\end{thebibliography}'
            ) if '\\bibitem' in m.group(1) else m.group(0),
            latex,
            flags=re.DOTALL,
        )

    # Fix 3: Remove \input{} and \include{} — reference missing files
    latex = re.sub(r'\\input\{[^}]+\}', '', latex)
    latex = re.sub(r'\\include\{[^}]+\}', '', latex)

    # Fix 4: Fix overly long enumerate lists
    # If > 20 items, convert to itemize (bullet points)
    def fix_long_enumerate(match: re.Match) -> str:
        content = match.group(1)
        item_count = content.count('\\item')
        if item_count > 20:
            return '\\begin{itemize}' + content + '\\end{itemize}'
        return match.group(0)

    latex = re.sub(
        r'\\begin\{enumerate\}(.*?)\\end\{enumerate\}',
        fix_long_enumerate,
        latex,
        flags=re.DOTALL,
    )

    return latex
