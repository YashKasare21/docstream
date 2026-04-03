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

    try:
        raw_response = ai_provider.complete(prompt, system_prompt)
    except Exception as e:
        raise StructuringError(
            f"AI provider failed: {e}"
        )

    # Extract and validate LaTeX from response
    latex = _extract_latex(raw_response)

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
8. The output must compile with XeLaTeX without errors
9. Preserve ALL content from the source document
10. Do not truncate or summarize — include everything"""


def _build_prompt(
    document: dict[str, Any],
    skeleton: str,
    instructions: str,
    template: str,
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
        else:
            content_parts.append(text)

    structured_content = "\n\n".join(content_parts)

    # Truncate if too long (preserve first and last parts)
    max_chars = 12000
    if len(structured_content) > max_chars:
        half = max_chars // 2
        structured_content = (
            structured_content[:half]
            + "\n\n[... content continues ...]\n\n"
            + structured_content[-half:]
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


def _extract_latex(response: str) -> str:
    """
    Extract clean LaTeX from AI response.

    Handles cases where AI wraps output in markdown fences
    or adds explanation text before/after the LaTeX.
    """
    # Remove markdown code fences
    response = re.sub(r'```latex\s*', '', response)
    response = re.sub(r'```\s*', '', response)
    response = response.strip()

    # Find the start of LaTeX (\\documentclass)
    start = response.find('\\documentclass')

    if start == -1:
        return response  # Return as-is, validation will catch it

    # Find the end of LaTeX (\\end{document})
    end_marker = '\\end{document}'
    end = response.rfind(end_marker)

    if end == -1:
        return response[start:]  # Take from documentclass to end

    return response[start:end + len(end_marker)]
