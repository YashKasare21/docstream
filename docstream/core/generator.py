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
    image_dir: Path | None = None,
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
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass  # dotenv not installed — keys must be in env already

    from docstream.core.ai_provider import AIProviderChain
    from docstream.exceptions import TemplateError

    if template not in VALID_TEMPLATES:
        raise TemplateError(
            f"Unknown template: '{template}'. Valid: {', '.join(sorted(VALID_TEMPLATES))}"
        )

    skeleton = _load_skeleton(template)
    instructions = _load_instructions(template)

    if ai_provider is None:
        ai_provider = AIProviderChain()

    system_prompt = _build_system_prompt()

    # Extract real bibliography BEFORE calling AI so we can
    # replace whatever the AI generates with the real text.
    real_bib = _extract_bibliography(document)
    if real_bib:
        ref_count = sum(1 for b in document.get("structure", []) if b.get("type") == "reference")
        logger.info(f"Pre-extracted {ref_count} reference blocks for direct injection")

    # Build full content string once
    content_parts = _build_content_parts(document)
    full_content = "\n\n".join(content_parts)
    full_content = _preprocess_content(full_content)

    logger.info(
        f"Generating LaTeX for template '{template}' "
        f"({len(document.get('structure', []))} blocks, "
        f"{len(full_content)} chars)"
    )

    if len(full_content) <= 15000:
        latex = _generate_single(
            full_content,
            skeleton,
            instructions,
            template,
            system_prompt,
            ai_provider,
        )
    else:
        logger.info("Document is long — using split generation strategy")
        latex = _generate_split(
            full_content,
            skeleton,
            instructions,
            template,
            system_prompt,
            ai_provider,
        )
        # _generate_single calls _postprocess_latex internally;
        # _generate_split does not — apply it here so Fix 1 (fbox
        # replacer) removes any AI-hallucinated \includegraphics
        # BEFORE _insert_figures adds the real ones.
        latex = _postprocess_latex(latex)

    # Replace AI-generated (placeholder) bibliography with real extracted text
    if real_bib:
        latex = _replace_bibliography(latex, real_bib)

    images = document.get("images", [])
    if images and image_dir:
        pre_len = len(latex)
        has_end = "\\end{document}" in latex
        bib_pos = latex.find("\\begin{thebibliography}")
        logger.info(
            f"Before figure insertion: latex={pre_len} chars, "
            f"has_end_doc={has_end}, bib_pos={bib_pos}"
        )
        latex = _insert_figures(latex, images, template)
        post_figs = len(re.findall(r"\\includegraphics", latex))
        post_fbox = len(re.findall(r"\\fbox", latex))
        logger.info(
            f"After figure insertion: latex={len(latex)} chars, "
            f"includegraphics={post_figs}, fbox={post_fbox}"
        )

    return latex


def _load_skeleton(template: str) -> str:
    """Load the LaTeX skeleton file for a template."""
    path = TEMPLATES_DIR / f"{template}.tex"
    if not path.exists():
        raise FileNotFoundError(f"Template skeleton not found: {path}")
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
19. AUTHOR AFFILIATIONS — the content contains [AFFILIATION] \
tagged blocks. EVERY [AFFILIATION] block MUST appear in \
\\thanks{} inside \\author{}. This is mandatory. \
Format: \\author{Name One\\thanks{Affiliation text here. \
Email: x@y.z} \\and Name Two\\thanks{Affiliation text.}} \
Copy the [AFFILIATION] text verbatim — never omit it.
20. CITATIONS must use \\cite{} ALWAYS. \
NEVER use \\textsuperscript for citation numbers. \
[1] → \\cite{ref1}, [1,2] → \\cite{ref1,ref2}. \
This is non-negotiable.
21. SECTION TITLES: Write full words in Title Case. \
NEVER prefix section headings with Roman numerals or \
split words with a leading letter. \
CORRECT: \\section{Introduction} \
WRONG: \\section{I. INTRODUCTION} \
WRONG: \\section{I NTRODUCTION} \
WRONG: \\section{INTRODUCTION}"""


_AFFILIATION_KEYWORDS = (
    "university",
    "college",
    "institute",
    "department",
    "dept",
    "school",
    "laboratory",
    "lab",
)


def _build_content_parts(document: dict[str, Any]) -> list[str]:
    """Extract and format content parts from a document structure dict."""
    content_parts: list[str] = []

    meta = document.get("metadata", {})
    if meta.get("author"):
        content_parts.append(f"[AUTHOR]: {meta['author']}")

    for i, block in enumerate(document.get("structure", [])):
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
            # Tag affiliation/email blocks in the first 10 paragraphs
            # so the AI knows to put them in \thanks{}
            if i < 10:
                has_email = "@" in text
                is_affil = any(kw in text.lower() for kw in _AFFILIATION_KEYWORDS)
                if has_email or is_affil:
                    content_parts.append(f"[AFFILIATION] {text}")
                    continue
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
- [AFFILIATION] blocks → MUST appear in \\thanks{{}} inside \\author{{}}

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

    return _build_prompt_from_content(structured_content, skeleton, instructions, template)


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

    prompt = _build_prompt_from_content(full_content, skeleton, instructions, template)

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
            prompt = _build_prompt_from_content(short_content, skeleton, instructions, template)

    latex = _extract_latex(raw)
    if not latex or "\\documentclass" not in latex:
        raise StructuringError(f"AI returned invalid LaTeX. Response starts with: {raw[:200]}")
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
    Generate LaTeX in 2 or 3 AI calls for long documents.

    Chunks are capped at ~8 000 chars to stay within Groq's
    free-tier token limit (~6 000 tokens per chunk).
    """
    chunk_size = 8000

    n_parts = 3 if len(full_content) > chunk_size * 2 else 2
    chunks = _split_at_headings(full_content, n_parts)

    logger.info(f"Split into {len(chunks)} chunks: {[len(c) for c in chunks]} chars")

    part1_latex = _generate_part1(
        chunks[0],
        skeleton,
        instructions,
        template,
        system_prompt,
        ai_provider,
    )

    # Extract last section from Part 1 for context handoff
    sections_in_part1 = re.findall(r"\\section\{([^}]+)\}", part1_latex)
    last_section = sections_in_part1[-1] if sections_in_part1 else "Introduction"

    continuation_parts: list[str] = []
    for i, chunk in enumerate(chunks[1:], start=2):
        try:
            part = _generate_continuation(
                chunk,
                i,
                len(chunks),
                system_prompt,
                ai_provider,
                last_section_written=last_section,
            )
            # Update last section for next part
            new_sections = re.findall(r"\\section\{([^}]+)\}", part)
            if new_sections:
                last_section = new_sections[-1]
            continuation_parts.append(part)
        except Exception as e:
            logger.warning(f"Part {i} failed: {e}")
            continuation_parts.append("")

    merged = _merge_all_parts(part1_latex, continuation_parts)
    logger.info(f"Split generation complete: {len(merged)} chars")
    return merged


def _split_at_headings(content: str, n_parts: int) -> list[str]:
    """
    Split content into n_parts chunks.

    Priority: heading boundary > paragraph boundary > word boundary.
    Never splits mid-sentence to avoid truncated sections.
    """
    target_size = len(content) // n_parts
    parts: list[str] = []
    remaining = content

    for i in range(n_parts - 1):
        split_target = min(target_size, len(remaining) - 1)
        search_start = max(0, split_target - 2000)
        search_end = min(len(remaining), split_target + 2000)
        search_area = remaining[search_start:search_end]

        # Priority 1: split at a heading
        heading_match = re.search(r"\n#{1,3} ", search_area)
        if heading_match:
            split_pos = search_start + heading_match.start()
        else:
            # Priority 2a: split at sentence-ending paragraph break
            # (avoids cutting mid-sentence when paragraph break is in
            # the middle of a sentence due to extractor fragmentation)
            sent_para = re.search(r'[.!?][)\]"]?\s*\n\n', remaining[split_target:])
            if sent_para:
                split_pos = split_target + sent_para.end()
            else:
                # Priority 2b: any paragraph break
                para_match = re.search(r"\n\n", remaining[split_target:])
                if para_match:
                    split_pos = split_target + para_match.end()
                else:
                    # Priority 3: split at next word boundary
                    split_pos = split_target
                    while split_pos < len(remaining) and remaining[split_pos] not in (" ", "\n"):
                        split_pos += 1

        parts.append(remaining[:split_pos].strip())
        remaining = remaining[split_pos:].strip()

        if not remaining:
            break

        target_size = len(remaining) // max(1, n_parts - i - 1)

    parts.append(remaining.strip())
    return [p for p in parts if p.strip()]


def _generate_part1(
    chunk: str,
    skeleton: str,
    instructions: str,
    template: str,
    system_prompt: str,
    ai_provider: Any,
) -> str:
    """Generate the first part with full document structure."""
    from docstream.exceptions import StructuringError

    prompt = (
        f"Convert this document content to LaTeX.\n"
        f"Use the template skeleton below.\n"
        f"This is Part 1 — generate the complete document up to "
        f"where the content ends. End with % CONTINUES_NEXT_PART\n\n"
        f"TEMPLATE:\n{skeleton}\n\n"
        f"INSTRUCTIONS:\n{instructions}\n\n"
        f"CONTENT (Part 1):\n{chunk}\n\n"
        f"RULES:\n"
        f"- Fill all <<PLACEHOLDERS>> from the content\n"
        f"- Include all sections from this content chunk\n"
        f"- End file with comment: % CONTINUES_NEXT_PART\n"
        f"- Do NOT write \\end{{document}}\n"
        f"- Return only LaTeX"
    )

    try:
        raw = ai_provider.complete(prompt, system_prompt)
        latex = _extract_latex_partial(raw)
        logger.info(f"Part 1: {len(latex)} chars")
        return latex
    except Exception as e:
        raise StructuringError(f"Part 1 failed: {e}")


def _generate_continuation(
    chunk: str,
    part_num: int,
    total_parts: int,
    system_prompt: str,
    ai_provider: Any,
    last_section_written: str = "",
) -> str:
    """Generate a continuation part (sections only)."""
    is_last = part_num == total_parts
    ending_rule = (
        "End with \\\\begin{thebibliography} and \\\\end{document}"
        if is_last
        else "End with % CONTINUES_NEXT_PART"
    )

    context_hint = ""
    if last_section_written:
        context_hint = (
            f"\nCONTEXT: Part {part_num - 1} wrote up to (and may have ended "
            f"mid-sentence within) section '{last_section_written}'. "
            f"Continue the document from exactly where Part {part_num - 1} "
            f"left off. If Part {part_num - 1} ended mid-sentence or "
            f"mid-subsection, complete that thought first before starting "
            f"new sections. Do NOT repeat content already written.\n"
        )

    # If this chunk contains [REF] lines, add explicit bibliography instruction
    ref_instruction = ""
    if "[REF]" in chunk:
        ref_instruction = (
            "\nBIBLIOGRAPHY INSTRUCTION:\n"
            "This chunk contains [REF] lines — these are REAL reference entries.\n"
            "Format each as a \\bibitem using the FULL TEXT after [REF]:\n"
            "\\begin{thebibliography}{99}\n"
            "\\bibitem{ref1}\n"
            "Author A and Author B, ``Title of Paper,'' Journal, vol. X, 2020.\n"
            "\\bibitem{ref2}\n"
            "Author C, \\textit{Book Title}. Publisher, 2019.\n"
            "\\end{thebibliography}\n"
            "CRITICAL: Copy the ACTUAL text from each [REF] line verbatim.\n"
            "Do NOT write [REF1], [REF2] or any placeholder. Use the real text.\n"
        )

    word_count = len(chunk.split())
    min_chars = max(3000, word_count * 4)

    prompt = (
        f"You are continuing a LaTeX document. "
        f"Generate ALL remaining sections from the content below.\n"
        f"This is Part {part_num} of {total_parts}.\n"
        f"{context_hint}"
        f"{ref_instruction}\n"
        f"CONTENT TO CONVERT (Part {part_num}, ~{word_count} words):\n"
        f"{chunk}\n\n"
        f"STRICT REQUIREMENTS:\n"
        f"1. Convert ALL {word_count} words above into LaTeX — do NOT stop early\n"
        f"2. Do NOT summarize or truncate any section\n"
        f"3. Do NOT repeat sections from previous parts\n"
        f"4. Start with \\section{{}} for each new section\n"
        f"5. Convert [REF] lines to \\bibitem{{}} with REAL text — never placeholders\n"
        f"6. Use \\cite{{refN}} for citations — NEVER \\textsuperscript\n"
        f"7. Every \\begin{{}} must have a matching \\end{{}}\n"
        f"8. {ending_rule}\n"
        f"9. CRITICAL: Output MUST be at least {min_chars} characters. "
        f"If running short, write each section in full prose — never skip content.\n"
        f"\nReturn ONLY LaTeX — no preamble, no explanation:"
    )

    raw = ai_provider.complete(prompt, system_prompt)
    latex = _extract_latex_continuation(raw)
    logger.info(f"Part {part_num}: {len(latex)} chars")
    return latex


def _insert_figures(
    latex: str,
    images: list[dict],
    template: str,
) -> str:
    """
    Insert figure environments into a LaTeX document.

    Figures are always placed BEFORE \\begin{thebibliography}
    or \\end{document} — never after either.
    """
    if not images:
        return latex

    # Remove fbox placeholders left by _postprocess_latex — we are
    # about to insert the real figures, so these boxes are redundant.
    latex = re.sub(
        r"\\fbox\{\\parbox\{[^}]+\}\{[^\}]*\[Figure:[^\]]*\][^\}]*\}\}",
        "",
        latex,
    )

    # Determine the insertion boundary — priority order:
    # 1. \\begin{thebibliography}
    # 2. \\bibliography{
    # 3. \\end{document}
    # 4. end of string
    insert_before = len(latex)
    for marker in (
        "\\begin{thebibliography}",
        "\\bibliography{",
        "\\end{document}",
    ):
        pos = latex.find(marker)
        if pos != -1 and pos < insert_before:
            insert_before = pos

    body = latex[:insert_before]
    tail = latex[insert_before:]  # starts at bibliography or \end{document}

    def make_figure(img: dict, fig_num: int) -> str:
        stem = img["filename"].rsplit(".", 1)[0]
        width = "0.9\\columnwidth" if template == "ieee" else "0.75\\linewidth"
        env = "figure*" if template == "ieee" and img["width"] > img["height"] else "figure"
        return (
            f"\n\\begin{{{env}}}[H]\n"
            f"\\centering\n"
            f"\\includegraphics[width={width}]{{{stem}}}\n"
            f"\\caption*{{Figure {fig_num}}}\n"
            f"\\label{{fig:{fig_num}}}\n"
            f"\\end{{{env}}}\n"
        )

    # Broad pattern covers: Fig 1, Figure 1, Fig. 1, Fig.~1, Fig.\ 1
    fig_pattern = re.compile(r"(?i)fig(?:ure)?\.?\s*[~\\]?\s*(\d+)")
    ref_pattern = re.compile(r"(?i)\\ref\{fig:(\d+)\}")

    mentions: dict[int, int] = {}
    for pat in (fig_pattern, ref_pattern):
        for m in pat.finditer(body):
            num = int(m.group(1))
            if num <= len(images) and num not in mentions:
                mentions[num] = m.end()

    logger.info(
        f"Figure insertion: mentions={sorted(mentions.keys())}, "
        f"images={len(images)}, insert_before={insert_before}, "
        f"body_len={len(body)}, tail_starts_with="
        f"{repr(tail[:40])}"
    )

    if not mentions:
        logger.info("No figure mentions found — inserting figures section before bibliography")
        figures_section = "\n\\clearpage\n" + "".join(
            make_figure(img, i) for i, img in enumerate(images, 1)
        )
        return body + figures_section + tail

    result = body
    inserted: set[int] = set()

    for fig_num in sorted(mentions.keys(), reverse=True):
        figure_env = make_figure(images[fig_num - 1], fig_num)
        pos = mentions[fig_num]
        para_end = re.search(
            r"\n\n|\n\\(?:sub)*section|\n\\clearpage",
            result[pos:],
        )
        insert_pos = pos + para_end.start() + 1 if para_end else min(pos + 300, len(result))
        result = result[:insert_pos] + figure_env + result[insert_pos:]
        inserted.add(fig_num)

    # Remaining figures (no mention) go into body, before tail
    remaining = "".join(
        make_figure(images[i - 1], i) for i in range(1, len(images) + 1) if i not in inserted
    )
    return result + remaining + tail


def _merge_all_parts(part1: str, continuation_parts: list[str]) -> str:
    """Merge all generated parts into one complete LaTeX document."""
    part1 = re.sub(r"%\s*CONTINUES_NEXT_PART.*", "", part1).rstrip()
    # Strip any bibliography Part 1 generated — it belongs only in the
    # final part. AI sometimes emits a placeholder \begin{thebibliography}
    # even though the prompt says not to include \end{document}.
    part1 = re.sub(
        r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}",
        "",
        part1,
        flags=re.DOTALL,
    )

    cleaned: list[str] = []
    for i, part in enumerate(continuation_parts):
        if part:
            part = re.sub(r"%\s*CONTINUES_NEXT_PART.*", "", part).rstrip()
            # Strip any stray bibliography from non-final parts —
            # Groq sometimes ignores the "no bibliography" instruction.
            # The final part is responsible for the real bibliography.
            is_final = i == len(continuation_parts) - 1
            if not is_final:
                part = re.sub(
                    r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}",
                    "",
                    part,
                    flags=re.DOTALL,
                )
            cleaned.append(part)

    # Track section AND subsection titles seen in Part 1 for deduplication
    seen_sections: set[str] = {
        s.lower().strip() for s in re.findall(r"\\section\{([^}]+)\}", part1)
    }
    seen_subsections: set[str] = {
        s.lower().strip() for s in re.findall(r"\\subsection\{([^}]+)\}", part1)
    }

    # Remove duplicate sections/subsections from continuation parts
    deduped: list[str] = []
    for part in cleaned:
        lines = part.split("\n")
        filtered: list[str] = []
        skip = False

        for line in lines:
            section_match = re.match(r"\\section\{([^}]+)\}", line.strip())
            subsection_match = re.match(r"\\subsection\{([^}]+)\}", line.strip())
            if section_match:
                title = section_match.group(1).lower().strip()
                if title in seen_sections:
                    skip = True
                    continue
                else:
                    seen_sections.add(title)
                    skip = False
            elif subsection_match:
                title = subsection_match.group(1).lower().strip()
                if title in seen_subsections:
                    skip = True
                    continue
                else:
                    seen_subsections.add(title)
                    skip = False
            elif skip and re.match(r"\\(?:sub)*section\{", line.strip()):
                # Any new (sub)section ends the skip region
                skip = False

            if not skip:
                filtered.append(line)

        deduped.append("\n".join(filtered))

    merged = "\n\n".join(p for p in [part1] + deduped if p.strip())

    if "\\end{document}" not in merged:
        merged = merged.rstrip() + "\n\\end{document}"

    return merged


def _extract_latex_partial(response: str) -> str:
    """Extract partial LaTeX (no \\end{document} expected)."""
    response = re.sub(r"```latex\s*", "", response)
    response = re.sub(r"```\s*", "", response)
    response = response.strip()

    start = response.find("\\documentclass")
    if start == -1:
        return response

    latex = response[start:]
    # Remove any \end{document} that snuck in
    latex = re.sub(r"\\end\{document\}", "", latex)
    return latex.rstrip()


def _extract_latex_continuation(response: str) -> str:
    """Extract continuation LaTeX (sections + bibliography only)."""
    response = re.sub(r"```latex\s*", "", response)
    response = re.sub(r"```\s*", "", response)
    response = response.strip()

    # If AI accidentally included a full preamble, strip it
    if "\\documentclass" in response:
        section_match = re.search(r"\\section\{", response)
        biblio_match = re.search(r"\\begin\{thebibliography\}", response)

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
    part1 = re.sub(r"%\s*BIBLIOGRAPHY_PLACEHOLDER.*", "", part1)
    part1 = part1.rstrip()

    # Ensure part 2 ends with \end{document}
    if "\\end{document}" not in part2:
        part2 = part2.rstrip() + "\n\\end{document}"

    return part1 + "\n\n" + part2


def _extract_bibliography(document: dict) -> str:
    """
    Extract real reference text from document structure
    and format as a LaTeX thebibliography block.

    Returns complete \\begin{thebibliography}...\\end block
    or empty string if no references found.
    """
    refs = [block for block in document.get("structure", []) if block.get("type") == "reference"]

    if not refs:
        return ""

    lines = [f"\\begin{{thebibliography}}{{{len(refs)}}}"]

    for i, ref in enumerate(refs, 1):
        text = ref.get("text", "").strip()

        # Remove leading [N] from reference text
        text = re.sub(r"^\[\d+\]\s*", "", text)

        # Escape LaTeX special chars (basic)
        text = text.replace("&", "\\&")
        text = text.replace("%", "\\%")
        text = text.replace("#", "\\#")
        text = text.replace("_", "\\_")

        lines.append(f"\\bibitem{{ref{i}}}")
        lines.append(text)
        lines.append("")

    lines.append("\\end{thebibliography}")
    return "\n".join(lines)


def _replace_bibliography(latex: str, real_bib: str) -> str:
    """
    Replace AI-generated bibliography with real extracted one.
    Handles multiple bibliography blocks — removes ALL of them
    and inserts a single real_bib before \\end{document}.
    When real_bib is empty, deduplicates by keeping the last block.
    """
    bib_pattern = re.compile(
        r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}",
        re.DOTALL,
    )

    if not real_bib:
        # No extracted bibliography — deduplicate AI-generated ones by
        # keeping only the last (final part's, most complete) bibliography.
        all_bibs = list(bib_pattern.finditer(latex))
        if len(all_bibs) > 1:
            last_bib_text = all_bibs[-1].group(0)
            # Remove all occurrences
            latex = bib_pattern.sub("", latex)
            # Re-insert the last (best) one before \end{document}
            end_doc = latex.rfind("\\end{document}")
            if end_doc != -1:
                latex = latex[:end_doc] + "\n" + last_bib_text + "\n" + latex[end_doc:]
            logger.info(
                f"Deduplicated {len(all_bibs)} bibliography blocks — kept final part's bibliography"
            )
        return latex

    all_bibs = list(bib_pattern.finditer(latex))

    if not all_bibs:
        # No bibliography found — insert before \end{document}
        end_doc = latex.rfind("\\end{document}")
        if end_doc != -1:
            return latex[:end_doc] + "\n" + real_bib + "\n" + latex[end_doc:]
        return latex + "\n" + real_bib

    if len(all_bibs) == 1:
        result = bib_pattern.sub(real_bib, latex, count=1)
        logger.info("Replaced AI bibliography with extracted references")
        return result

    # Multiple bibliographies — remove ALL, then insert real_bib once
    result = latex
    for bib_match in reversed(all_bibs):
        result = result[: bib_match.start()] + result[bib_match.end() :]

    end_doc = result.rfind("\\end{document}")
    if end_doc != -1:
        result = result[:end_doc] + "\n" + real_bib + "\n" + result[end_doc:]
    else:
        result = result + "\n" + real_bib

    logger.info(f"Replaced {len(all_bibs)} bibliography blocks with extracted references")
    return result


def _preprocess_content(structured_content: str) -> str:
    """
    Preprocess content to prevent AI from stuffing
    footnotes into \\title{\\thanks{}}.

    Moves footnote-heavy blocks from the document start
    to the end so they don't inflate the title area.
    """
    footnote_symbols = ["∗", "†", "‡", "§", "¶", "Equal contribution", "Work performed while at"]

    affiliation_keywords = [
        "university",
        "college",
        "institute",
        "department",
        "dept",
        "school",
        "laboratory",
        "lab",
    ]

    lines = structured_content.split("\n\n")
    if not lines:
        return structured_content

    clean_start: list[str] = []
    footnotes: list[str] = []

    for i, block in enumerate(lines[:10]):
        word_count = len(block.split())
        has_footnote_symbol = any(sym in block for sym in footnote_symbols)
        has_email = "@" in block
        is_affiliation = any(kw in block.lower() for kw in affiliation_keywords)

        # Only move blocks that are clearly footnotes:
        # must have a footnote symbol, be long, appear after
        # title/authors, and NOT be email/affiliation blocks
        if (
            has_footnote_symbol
            and word_count > 50
            and i > 1
            and not has_email
            and not is_affiliation
        ):
            footnotes.append(f"[FOOTNOTE] {block}")
        else:
            clean_start.append(block)

    result_lines = clean_start + lines[10:]
    if footnotes:
        result_lines.append("\n[AUTHOR NOTES]")
        result_lines.extend(footnotes)

    return "\n\n".join(result_lines)


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
    response = re.sub(r"```latex\s*", "", response)
    response = re.sub(r"```\s*", "", response)
    response = response.strip()

    # Find LaTeX boundaries
    start = response.find("\\documentclass")
    if start == -1:
        return response  # Return as-is, validation will catch it

    end_marker = "\\end{document}"
    end = response.rfind(end_marker)
    if end == -1:
        latex = response[start:]
    else:
        latex = response[start : end + len(end_marker)]

    # Post-process
    latex = _postprocess_latex(latex)

    return latex


def _fix_citations(latex: str) -> str:
    """
    Resolve [?] citation placeholders left by the AI.

    Handles:
    - Standalone [?]  →  \\cite{refN}
    - Mixed [3, ?, ?] →  \\cite{ref3,refN,refM}
    - Numeric [3]     →  \\cite{ref3}  (when inside a mixed group)

    Falls back to \\textsuperscript{N} if no \\bibitem{} exist.
    """
    bibitems = re.findall(r"\\bibitem\{([^}]+)\}", latex)

    if not bibitems:
        if not re.search(r"\[\?\]", latex):
            return latex
        # No bibliography at all — number as superscripts
        counter = [0]

        def _sup(_m: re.Match) -> str:
            counter[0] += 1
            return f"\\textsuperscript{{{counter[0]}}}"

        return re.sub(r"\[\?\]", _sup, latex)

    # Split body / bibliography so we only touch the body
    bib_start = latex.find("\\begin{thebibliography}")
    if bib_start > 0:
        body, bib = latex[:bib_start], latex[bib_start:]
    else:
        body, bib = latex, ""

    cite_counter = [0]

    def _next_cite() -> str:
        key = bibitems[cite_counter[0] % len(bibitems)]
        cite_counter[0] += 1
        return key

    def _resolve_group(m: re.Match) -> str:
        """Convert [a, ?, b] to \\cite{key_a, key_?, key_b}."""
        parts = [p.strip() for p in m.group(1).split(",")]
        keys: list[str] = []
        for p in parts:
            if p == "?":
                keys.append(_next_cite())
            elif p.isdigit():
                idx = int(p) - 1
                keys.append(bibitems[idx] if 0 <= idx < len(bibitems) else _next_cite())
            else:
                keys.append(p)
        return f"\\cite{{{','.join(keys)}}}"

    # Replace mixed/group citations containing ? first
    body = re.sub(r"\[([^\]]*\?[^\]]*)\]", _resolve_group, body)
    # Replace any remaining standalone [?]
    body = re.sub(
        r"\[\?\]",
        lambda _m: f"\\cite{{{_next_cite()}}}",
        body,
    )
    return body + bib


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
        display_name = filename.replace("{", "").replace("}", "")
        display_name = display_name.split("/")[-1][:30]
        return (
            r"\fbox{\parbox{0.4\textwidth}{"
            r"\centering\small[Figure: " + display_name + r"]}}"
        )

    # Fix 1: Replace \includegraphics with placeholder
    latex = re.sub(
        r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}",
        replace_includegraphics,
        latex,
    )

    # Fix 2: Replace enumerate used for references
    # Pattern: \begin{enumerate} containing \bibitem
    # This causes "Counter too large" with many refs
    if "\\bibitem" in latex and "\\begin{enumerate}" in latex:
        latex = re.sub(
            r"\\begin\{enumerate\}(.*?)\\end\{enumerate\}",
            lambda m: (
                ("\\begin{thebibliography}{99}" + m.group(1) + "\\end{thebibliography}")
                if "\\bibitem" in m.group(1)
                else m.group(0)
            ),
            latex,
            flags=re.DOTALL,
        )

    # Fix 3: Remove \input{} and \include{} — reference missing files
    latex = re.sub(r"\\input\{[^}]+\}", "", latex)
    latex = re.sub(r"\\include\{[^}]+\}", "", latex)

    # Fix 4: Fix overly long enumerate lists
    # If > 20 items, convert to itemize (bullet points)
    def fix_long_enumerate(match: re.Match) -> str:
        content = match.group(1)
        item_count = content.count("\\item")
        if item_count > 20:
            return "\\begin{itemize}" + content + "\\end{itemize}"
        return match.group(0)

    latex = re.sub(
        r"\\begin\{enumerate\}(.*?)\\end\{enumerate\}",
        fix_long_enumerate,
        latex,
        flags=re.DOTALL,
    )

    # Fix 5: Replace dagger symbols not available in XeLaTeX TU encoding
    latex = latex.replace(r"\textddagger", r"\ddag")
    latex = latex.replace(r"\textdagger", r"\dag")

    # Fix 6: Replace other TU-encoding-incompatible symbols
    for old, new in (
        (r"\textparagraph", r"\P"),
        (r"\textsection", r"\S"),
        (r"\texttrademark", "TM"),
        (r"\textordfeminine", "a"),
        (r"\textordmasculine", "o"),
    ):
        latex = latex.replace(old, new)

    # Fix 7: Citation resolution — handles [?], [3,?,?], [?,5]
    latex = _fix_citations(latex)

    # Fix 8: Replace undefined control sequences common in AI output
    # Only replace when clearly used as a command (not part of a longer word)
    undefined_fixes = [
        (r"\\pd(?=[^a-zA-Z])", r"\\partial"),
        (r"\\R(?=[^a-zA-Z])", r"\\mathbb{R}"),
        (r"\\N(?=[^a-zA-Z])", r"\\mathbb{N}"),
        (r"\\Z(?=[^a-zA-Z])", r"\\mathbb{Z}"),
        (r"\\norm(?=[^a-zA-Z])", r"\\|\\cdot\\|"),
    ]
    for pattern, replacement in undefined_fixes:
        latex = re.sub(pattern, replacement, latex)

    # Fix 9: Clean section headings of Roman numeral prefixes and
    # ALL-CAPS formatting. Also repairs Groq's word-splitting artifact
    # where each word is prefixed with its first letter:
    # "I NTRODUCTION" → "INTRODUCTION", "R ELATED W ORK" → "RELATED WORK"
    def _clean_section_title(match: re.Match) -> str:
        cmd = match.group(1)  # "section" or "subsection" etc.
        title = match.group(2)

        # Repair Groq's word-split artifact: "X XXXX" → "XXXXX"
        # Single uppercase letter + space + 2+ uppercase letters → rejoin
        repaired = re.sub(r"\b([A-Z]) ([A-Z]{2,})\b", r"\1\2", title)
        # Apply twice to catch consecutive split words
        repaired = re.sub(r"\b([A-Z]) ([A-Z]{2,})\b", r"\1\2", repaired)

        # Strip leading Roman numeral prefix "IV. " or "4 V. "
        cleaned = re.sub(r"^\d*\s*[IVXivx]+\.\s+", "", repaired).strip()
        # Strip leading single-letter dot prefix "A. "
        cleaned = re.sub(r"^[A-Z]\.\s+", "", cleaned).strip()

        # Convert ALL-CAPS to Title Case only when no single-char fragments
        words = cleaned.split()
        all_caps = cleaned.isupper() and len(cleaned) > 4
        has_fragments = any(len(w) == 1 for w in words)
        if all_caps and not has_fragments:
            cleaned = cleaned.title()

        return f"\\{cmd}{{{cleaned}}}"

    latex = re.sub(
        r"\\((?:sub)*section\*?)\{([^}]+)\}",
        _clean_section_title,
        latex,
    )

    # Fix 10: Convert enumerate environments that look like subsection lists
    # into proper \subsection{} commands. AI sometimes formats subsections
    # as numbered enumerate items instead of \subsection{heading}\nparagraph.
    def _promote_enumerate_to_subsections(match: re.Match) -> str:
        content = match.group(1)
        raw_items = re.split(r"\\item\s*", content)
        items = [it for it in raw_items if it.strip()]
        if len(items) < 2:
            return match.group(0)

        # Classify each item: heading-like if first line is short
        heading_count = 0
        for item in items:
            first_line = item.split("\n")[0].strip()
            first_line = re.sub(r"^(?:\d+[.)]\s*|[a-zA-Z][.)]\s*)", "", first_line).strip()
            if 3 < len(first_line) < 80:
                heading_count += 1

        if heading_count < len(items):
            return match.group(0)  # Not all items look like headings

        promoted: list[str] = []
        for item in items:
            lines = item.strip().split("\n", 1)
            heading_text = re.sub(r"^(?:\d+[.)]\s*|[a-zA-Z][.)]\s*)", "", lines[0].strip()).strip()
            body = lines[1].strip() if len(lines) > 1 else ""
            if heading_text:
                promoted.append(f"\\subsection{{{heading_text}}}")
            if body:
                promoted.append(body)

        return "\n".join(promoted) if promoted else match.group(0)

    latex = re.sub(
        r"\\begin\{enumerate\}(.*?)\\end\{enumerate\}",
        _promote_enumerate_to_subsections,
        latex,
        flags=re.DOTALL,
    )

    # Fix 11: Remove inline \includegraphics not inside a figure environment.
    # AI sometimes hallucinates \includegraphics mid-paragraph; these paths
    # don't exist and XeLaTeX renders them as black rectangles.
    result_lines: list[str] = []
    in_figure = False
    for line in latex.split("\n"):
        if "\\begin{figure" in line:
            in_figure = True
        if "\\end{figure" in line:
            in_figure = False
            result_lines.append(line)
            continue
        if not in_figure and "\\includegraphics" in line:
            logger.debug(f"Removed inline graphics: {line[:80]}")
            continue
        result_lines.append(line)
    latex = "\n".join(result_lines)

    # Fix 12: Remove orphaned \caption{} lines outside figure environments.
    # After Fix 11 strips inline \includegraphics, the AI's paired \caption{}
    # lines are left behind as floating text in the paragraph flow.
    caption_lines: list[str] = []
    in_figure = False
    for line in latex.split("\n"):
        if "\\begin{figure" in line:
            in_figure = True
        if "\\end{figure" in line:
            in_figure = False
            caption_lines.append(line)
            continue
        if not in_figure and line.strip().startswith("\\caption{"):
            logger.debug(f"Removed orphaned caption: {line[:80]}")
            continue
        caption_lines.append(line)
    latex = "\n".join(caption_lines)

    return latex
