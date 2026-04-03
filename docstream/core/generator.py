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
    For long documents (>15 000 chars), uses a two-call split
    strategy to avoid output truncation.

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
            f"Valid: {', '.join(sorted(VALID_TEMPLATES))}"
        )

    skeleton = _load_skeleton(template)
    instructions = _load_instructions(template)

    if ai_provider is None:
        ai_provider = AIProviderChain()

    system_prompt = _build_system_prompt()

    # Build full content string once
    content_parts = _build_content_parts(document)
    full_content = '\n\n'.join(content_parts)
    full_content = _preprocess_content(full_content)

    logger.info(
        f"Generating LaTeX for template '{template}' "
        f"({len(document.get('structure', []))} blocks, "
        f"{len(full_content)} chars)"
    )

    if len(full_content) <= 15000:
        return _generate_single(
            full_content, skeleton, instructions,
            template, system_prompt, ai_provider,
        )

    logger.info("Document is long — using split generation strategy")
    return _generate_split(
        full_content, skeleton, instructions,
        template, system_prompt, ai_provider,
    )


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
13. CITATIONS — This is critical:
The document may contain [?] where citations should be.
The document also contains [REF] lines with the actual references.
STEP 1: Number the [REF] entries in order: ref1, ref2, ref3...
STEP 2: Replace [?] placeholders with \\cite{ref1}, \\cite{ref2} \
in the ORDER they appear in text. \
First [?] → \\cite{ref1}, second [?] → \\cite{ref2}, etc.
STEP 3: Format the bibliography as: \
\\begin{thebibliography}{99} \
\\bibitem{ref1} First reference text. \
\\bibitem{ref2} Second reference text. \
\\end{thebibliography}
If NO [REF] entries exist but [?] are present: replace [?] \
with \\textsuperscript{N} where N increments.
14. NEVER leave [?] in the output. Always resolve them.
15. Never create enumerate lists with more than 15 items. \
Use itemize (bullet points) for longer lists.
16. Do not use \\alph, \\Alph counters.
17. Keep \\title{} SHORT — maximum 2 lines. Move footnotes \
and acknowledgments to AFTER \\maketitle using \
\\footnotetext{} or a separate section. NEVER put long \
text inside \\thanks{}.
18. CRITICAL — output budget management: write sections in \
this strict order: (1) \\documentclass and packages, \
(2) \\title{Short title only}, (3) \\author{names}, \
(4) \\date{}, (5) \\begin{document}, (6) \\maketitle, \
(7) \\begin{abstract}...\\end{abstract} — MUST complete, \
(8) keywords if needed, (9) sections as many as fit, \
(10) bibliography, (11) \\end{document} — MUST include. \
If running long, SHORTEN SECTIONS — never skip \
\\end{abstract} or \\end{document}.
19. For author footnotes (∗ † ‡ symbols): use \
\\thanks{brief note} inline — keep each \\thanks{} \
under 20 words. Example: \
\\author{John Smith\\thanks{Google Brain}}"""


def _build_content_parts(document: dict[str, Any]) -> list[str]:
    """Extract and format content parts from a document structure dict."""
    content_parts: list[str] = []

    meta = document.get("metadata", {})
    if meta.get("author"):
        content_parts.append(f"[AUTHOR]: {meta['author']}")

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

    return content_parts


def _build_prompt_from_content(
    content: str,
    skeleton: str,
    instructions: str,
    template: str,  # noqa: ARG001 — reserved for future per-template tuning
) -> str:
    """Build a full generation prompt from a pre-processed content string."""
    return f"""Convert the following document content into a \
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
{content}

═══════════════════════════════
YOUR TASK:
═══════════════════════════════
CRITICAL REQUIREMENTS:
- Use the ACTUAL TEXT provided — do NOT summarize
- Include ALL sections from the content above
- Every section must contain real extracted text
- Do not write placeholder text like "content truncated"
- Properly escape special characters: & % $ # _ {{}} ~ ^ \\
- Citations [1],[2] etc. should become \\cite{{ref1}},\\cite{{ref2}}
- [?] placeholders: replace with \\cite{{refN}} sequentially

Replace every <<PLACEHOLDER>> with the appropriate content.
- <<TITLE>> → document title
- <<ABSTRACT>> → abstract text
- <<SECTIONS>> → properly formatted LaTeX sections
- <<BIBLIOGRAPHY_BLOCK>> → formatted references
- IEEE: <<AUTHORS_BLOCK>>, <<KEYWORDS>>, <<ACKNOWLEDGMENT_BLOCK>>
- Report: <<AUTHOR>>, <<DATE>> (use \\today if not found)

Return the complete LaTeX document now:"""


def _build_prompt(
    document: dict[str, Any],
    skeleton: str,
    instructions: str,
    template: str,
    max_chars: int = 50000,
) -> str:
    """Build the user prompt for LaTeX generation (legacy single-call path)."""
    content_parts = _build_content_parts(document)
    structured_content = "\n\n".join(content_parts)
    structured_content = _preprocess_content(structured_content)

    # Truncate if too long (preserve first 80%, last 20%)
    if len(structured_content) > max_chars:
        first_part = int(max_chars * 0.8)
        last_part = max_chars - first_part
        structured_content = (
            structured_content[:first_part]
            + "\n\n[... middle section truncated ...]\n\n"
            + structured_content[-last_part:]
        )

    return _build_prompt_from_content(
        structured_content, skeleton, instructions, template
    )


def _generate_single(
    full_content: str,
    skeleton: str,
    instructions: str,
    template: str,
    system_prompt: str,
    ai_provider: Any,
) -> str:
    """Generate LaTeX in a single AI call."""
    from docstream.exceptions import StructuringError

    prompt = _build_prompt_from_content(
        full_content, skeleton, instructions, template
    )

    raw = ""
    for attempt in range(2):
        try:
            raw = ai_provider.complete(prompt, system_prompt)
        except Exception as e:
            raise StructuringError(f"AI provider failed: {e}")

        latex = _extract_latex(raw)

        if _is_complete_latex(latex):
            logger.info(f"Generated {len(latex)} chars of LaTeX")
            return latex

        if attempt == 0:
            logger.warning("LaTeX truncated, retrying with shorter content")
            short_content = full_content[:8000]
            prompt = _build_prompt_from_content(
                short_content, skeleton, instructions, template
            )

    latex = _extract_latex(raw)
    if not latex or "\\documentclass" not in latex:
        raise StructuringError(
            "AI returned invalid LaTeX. "
            f"Response starts with: {raw[:200]}"
        )
    return latex


def _generate_split(
    full_content: str,
    skeleton: str,
    instructions: str,
    template: str,
    system_prompt: str,
    ai_provider: Any,
) -> str:
    """
    Generate LaTeX in two AI calls for long documents.

    Call 1: document header + first half of content
    Call 2: remaining sections + bibliography
    Merge: combine both into one complete document
    """
    from docstream.exceptions import StructuringError

    # Split at midpoint, preferring a heading boundary
    midpoint = len(full_content) // 2
    split_pos = midpoint

    search_area = full_content[midpoint:midpoint + 3000]
    heading_match = re.search(r'\n#{1,3} ', search_area)
    if heading_match:
        split_pos = midpoint + heading_match.start()

    first_half = full_content[:split_pos].strip()
    second_half = full_content[split_pos:].strip()

    logger.info(
        f"Split: {len(first_half)} chars + {len(second_half)} chars"
    )

    # ── Call 1: full document structure with first half ──
    prompt1 = (
        f"Convert this document to LaTeX using the template below.\n"
        f"This is PART 1 of 2. Generate the COMPLETE document structure "
        f"including: documentclass, packages, title, abstract, and "
        f"ALL sections from the content below. End with a placeholder "
        f"comment: % BIBLIOGRAPHY_PLACEHOLDER\n\n"
        f"{skeleton}\n\n"
        f"INSTRUCTIONS:\n{instructions}\n\n"
        f"DOCUMENT CONTENT (Part 1 — main sections):\n{first_half}\n\n"
        f"CRITICAL:\n"
        f"- Generate complete LaTeX from \\documentclass to the sections\n"
        f"- Include ALL sections from the content above\n"
        f"- End with: % BIBLIOGRAPHY_PLACEHOLDER\n"
        f"- Do NOT write \\end{{document}} yet\n"
        f"- Return only LaTeX, no explanation"
    )

    try:
        raw1 = ai_provider.complete(prompt1, system_prompt)
        latex_part1 = _extract_latex_partial(raw1)
    except Exception as e:
        raise StructuringError(f"Part 1 generation failed: {e}")

    # ── Call 2: remaining sections + bibliography ──
    prompt2 = (
        f"Continue the LaTeX document. Generate the REMAINING "
        f"sections and the bibliography.\n\n"
        f"REMAINING CONTENT (Part 2):\n{second_half}\n\n"
        f"INSTRUCTIONS:\n{instructions}\n\n"
        f"Generate ONLY:\n"
        f"1. Any remaining \\section{{}} content from part 2\n"
        f"2. The bibliography (\\begin{{thebibliography}} block)\n"
        f"3. \\end{{document}}\n\n"
        f"Do NOT repeat documentclass, packages, title, or abstract.\n"
        f"Start directly with remaining sections.\n"
        f"Return only LaTeX, no explanation."
    )

    try:
        raw2 = ai_provider.complete(prompt2, system_prompt)
        latex_part2 = _extract_latex_continuation(raw2)
    except Exception as e:
        logger.warning(f"Part 2 generation failed: {e}")
        latex_part2 = "\\end{document}"

    merged = _merge_latex_parts(latex_part1, latex_part2)

    if "\\end{document}" not in merged:
        merged += "\n\\end{document}"

    logger.info(f"Split generation complete: {len(merged)} chars")
    return merged


def _extract_latex_partial(response: str) -> str:
    """Extract partial LaTeX (no \\end{document} expected)."""
    response = re.sub(r'```latex\s*', '', response)
    response = re.sub(r'```\s*', '', response)
    response = response.strip()

    start = response.find('\\documentclass')
    if start == -1:
        return response

    latex = response[start:]
    # Remove any \end{document} that snuck in
    latex = re.sub(r'\\end\{document\}', '', latex)
    return latex.rstrip()


def _extract_latex_continuation(response: str) -> str:
    """Extract continuation LaTeX (sections + bibliography only)."""
    response = re.sub(r'```latex\s*', '', response)
    response = re.sub(r'```\s*', '', response)
    response = response.strip()

    # If AI accidentally included a full preamble, strip it
    if '\\documentclass' in response:
        section_match = re.search(r'\\section\{', response)
        biblio_match = re.search(r'\\begin\{thebibliography\}', response)

        start = None
        if section_match:
            start = section_match.start()
        elif biblio_match:
            start = biblio_match.start()

        if start is not None:
            response = response[start:]

    return response.strip()


def _merge_latex_parts(part1: str, part2: str) -> str:
    """Merge two LaTeX parts into one complete document."""
    # Remove placeholder comment from part 1
    part1 = re.sub(r'%\s*BIBLIOGRAPHY_PLACEHOLDER.*', '', part1)
    part1 = part1.rstrip()

    # Ensure part 2 ends with \end{document}
    if '\\end{document}' not in part2:
        part2 = part2.rstrip() + '\n\\end{document}'

    return part1 + '\n\n' + part2


def _preprocess_content(structured_content: str) -> str:
    """
    Preprocess content to prevent AI from stuffing
    footnotes into \\title{\\thanks{}}.

    Moves footnote-heavy blocks from the document start
    to the end so they don't inflate the title area.
    """
    footnote_markers = [
        '∗', '†', '‡', 'Equal contribution',
        'Work performed', 'Google Brain', 'Google Research',
    ]

    lines = structured_content.split('\n\n')
    if not lines:
        return structured_content

    clean_start: list[str] = []
    footnotes: list[str] = []

    for i, block in enumerate(lines[:10]):
        is_footnote = any(marker in block for marker in footnote_markers)
        word_count = len(block.split())
        # Only move blocks that are footnote-heavy, long, and not first two
        if is_footnote and word_count > 30 and i > 1:
            footnotes.append(f"[FOOTNOTE] {block}")
        else:
            clean_start.append(block)

    result_lines = clean_start + lines[10:]
    if footnotes:
        result_lines.append("\n[AUTHOR NOTES]")
        result_lines.extend(footnotes)

    return '\n\n'.join(result_lines)


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
