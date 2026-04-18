"""
Semantic Analyzer — understands document meaning and type.

This is the core intelligence of Docstream v2.

Two-pass approach:
  Pass 1: Fast heuristic analysis (no AI, instant)
          Detects obvious document-type indicators.
          Estimates word count and page count.

  Pass 2: AI-powered deep analysis
          Sends structured text to AIProviderChain.
          Returns rich JSON with document type, chunks,
          entities, and metadata.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from docstream.core.ai_provider import AIProviderChain
from docstream.exceptions import StructuringError
from docstream.models.document import (
    Block,
    BlockType,
    DocumentType,
    SemanticChunk,
    SemanticDocument,
)

logger = logging.getLogger(__name__)

# Maximum words sent to AI before truncation
_MAX_WORDS = 6000


class SemanticAnalyzer:
    """Analyze a list of blocks and produce a ``SemanticDocument``.

    Args:
        ai_provider: Optional ``AIProviderChain`` instance.
                     A new chain is built automatically if not supplied.
    """

    def __init__(self, ai_provider: AIProviderChain | None = None) -> None:
        self.ai = ai_provider or AIProviderChain()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def analyze(self, blocks: list[Block]) -> SemanticDocument:
        """Run full two-pass semantic analysis.

        Args:
            blocks: Blocks produced by a format handler.

        Returns:
            A ``SemanticDocument`` with detected type, chunks, and metadata.

        Raises:
            StructuringError: If the AI response cannot be parsed.
            AIUnavailableError: If all AI providers fail.
        """
        # Pass 1: fast heuristics
        doc_type_hint, heuristic_metadata = self._heuristic_analysis(blocks)

        # Pass 2: AI deep analysis
        text_for_ai = self._prepare_text(blocks)
        ai_result = self._ai_analysis(text_for_ai, doc_type_hint)

        return self._build_semantic_document(blocks, ai_result, heuristic_metadata)

    def detect_document_type(self, blocks: list[Block]) -> DocumentType:
        """Return the detected ``DocumentType`` for a list of blocks.

        Runs the full two-pass analysis and extracts only the type.

        Args:
            blocks: Blocks produced by a format handler.

        Returns:
            Detected ``DocumentType``.
        """
        return self.analyze(blocks).document_type

    def create_semantic_chunks(self, blocks: list[Block]) -> list[SemanticChunk]:
        """Return semantic chunks for a list of blocks.

        Runs the full two-pass analysis and extracts only the chunks.

        Args:
            blocks: Blocks produced by a format handler.

        Returns:
            List of ``SemanticChunk`` objects.
        """
        return self.analyze(blocks).chunks

    # -------------------------------------------------------------------------
    # Pass 1 — heuristics
    # -------------------------------------------------------------------------

    def _heuristic_analysis(
        self, blocks: list[Block]
    ) -> tuple[DocumentType, dict]:
        """Fast pattern-based document type detection — no AI required.

        Checks for strong signals in the first 20 blocks:
        - "curriculum vitae" / "resume"          → RESUME
        - "abstract" + "methodology" + …         → RESEARCH_PAPER
        - "dear" / "sincerely"                   → LETTER
        - "executive summary" / "chapter"        → ACADEMIC_REPORT

        Args:
            blocks: All extracted blocks.

        Returns:
            Tuple of (DocumentType hint, metadata dict with word_count).
        """
        preview_text = " ".join(b.content.lower() for b in blocks[:20])
        word_count = sum(len(b.content.split()) for b in blocks)
        metadata: dict = {"word_count": word_count}

        # Resume signals
        resume_signals = [
            "curriculum vitae", "resume", "work experience",
            "employment history", "objective:", "summary:",
            "references available",
        ]
        if any(s in preview_text for s in resume_signals):
            return DocumentType.RESUME, metadata

        # Research paper signals (need 3+ to reduce false positives)
        paper_signals = [
            "abstract", "keywords:", "introduction",
            "methodology", "results", "conclusion",
            "references", "doi:", "arxiv",
        ]
        paper_score = sum(1 for s in paper_signals if s in preview_text)
        if paper_score >= 3:
            return DocumentType.RESEARCH_PAPER, metadata

        # Letter signals
        letter_signals = ["dear ", "sincerely", "regards,", "to whom"]
        if any(s in preview_text for s in letter_signals):
            return DocumentType.LETTER, metadata

        # Report / academic signals
        report_signals = [
            "executive summary", "table of contents",
            "appendix", "chapter ",
        ]
        if any(s in preview_text for s in report_signals):
            return DocumentType.ACADEMIC_REPORT, metadata

        return DocumentType.UNKNOWN, metadata

    # -------------------------------------------------------------------------
    # Pass 2 helpers
    # -------------------------------------------------------------------------

    def _prepare_text(self, blocks: list[Block]) -> str:
        """Build a structured text representation of the document for AI.

        Truncates at ``_MAX_WORDS`` words and adds structural markers
        for headings, tables, and code blocks to help the AI understand
        document hierarchy.

        Args:
            blocks: All extracted blocks.

        Returns:
            Plain text string ready for the AI prompt.
        """
        lines: list[str] = []
        word_count = 0

        for block in blocks:
            if word_count >= _MAX_WORDS:
                lines.append("[... document truncated ...]")
                break

            if block.type == BlockType.HEADING:
                prefix = "## " if (block.font_size or 0) >= 18 else "### "
                lines.append(f"{prefix}{block.content}")
            elif block.type == BlockType.TABLE:
                lines.append(f"[TABLE]\n{block.content}\n[/TABLE]")
            elif block.type == BlockType.CODE:
                lines.append(f"[CODE]\n{block.content}\n[/CODE]")
            else:
                lines.append(block.content)

            word_count += len(block.content.split())

        return "\n\n".join(lines)

    def _ai_analysis(self, text: str, type_hint: DocumentType) -> dict:
        """Send document text to the AI provider chain for deep analysis.

        Args:
            text: Prepared document text (output of ``_prepare_text``).
            type_hint: Heuristic type hint to include in the prompt.

        Returns:
            Parsed dict from the AI JSON response.

        Raises:
            StructuringError: If the AI response cannot be parsed as JSON.
            AIUnavailableError: If all providers fail.
        """
        system_prompt = (
            "You are a document analysis expert. "
            "Your job is to analyze documents and extract their semantic structure. "
            "You MUST respond with valid JSON only. "
            "No explanation, no markdown fences. "
            "The JSON must be parseable by Python's json.loads()."
        )

        user_prompt = f"""Analyze this document and return a JSON object.

Document type hint (from heuristics): {type_hint.value}

Document content:
---
{text}
---

Return this exact JSON structure:
{{
  "document_type": "resume|research_paper|academic_report|technical_report|presentation|letter|notes|unknown",
  "confidence": 0.0-1.0,
  "title": "detected document title or empty string",
  "language": "en|es|fr|de|zh|etc",
  "metadata": {{
    "note": "include only fields actually present in the document",
    "resume_fields": "name, email, phone, linkedin, github",
    "paper_fields": "authors (list), year, journal, abstract_text",
    "report_fields": "organization, date, version",
    "letter_fields": "sender, recipient, date"
  }},
  "chunks": [
    {{
      "chunk_type": "type of content (see below)",
      "content": "the actual content of this chunk",
      "importance": 0.0-1.0,
      "template_hints": ["resume", "ieee"],
      "metadata": {{}}
    }}
  ]
}}

chunk_type values:
- Resume: contact_info, summary, work_experience, education, skills,
          projects, certifications, awards, languages, references
- Research paper: abstract, keywords, introduction, related_work,
                  methodology, results, discussion, conclusion,
                  references, appendix
- Report: executive_summary, introduction, section, methodology,
          findings, recommendations, conclusion, appendix
- Letter: salutation, body, closing, signature
- Presentation: slide_title, slide_content, speaker_notes
- Any type: table, code_block, figure_caption, footnote

Rules:
1. Every meaningful piece of content must appear in a chunk
2. importance = 1.0 for critical content (name, abstract, etc.)
3. importance = 0.5 for supporting content
4. importance = 0.2 for boilerplate/formatting
5. template_hints = which LaTeX templates this chunk works best with
6. Return ONLY valid JSON, nothing else"""

        response = self.ai.complete(user_prompt, system_prompt)
        return self._parse_ai_response(response)

    def _parse_ai_response(self, response: str) -> dict:
        """Parse the AI JSON response safely.

        Handles common AI formatting mistakes such as markdown fences
        and leading/trailing whitespace.

        Args:
            response: Raw string returned by the AI provider.

        Returns:
            Parsed dict with at minimum ``document_type``, ``confidence``,
            and ``chunks`` keys.

        Raises:
            StructuringError: If no valid JSON is found or required
                              fields are missing.
        """
        # Strip markdown code fences if present
        cleaned = re.sub(r"```json\s*", "", response)
        cleaned = re.sub(r"```\s*", "", cleaned)
        cleaned = cleaned.strip()

        # Find the outermost JSON object
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            raise StructuringError(
                "AI returned invalid response — no JSON object found"
            )

        json_str = cleaned[start:end]

        try:
            result: dict = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise StructuringError(f"AI returned malformed JSON: {exc}") from exc

        # Validate required fields
        for field in ("document_type", "confidence", "chunks"):
            if field not in result:
                raise StructuringError(
                    f"AI response missing required field: '{field}'"
                )

        return result

    def _build_semantic_document(
        self,
        blocks: list[Block],
        ai_result: dict,
        heuristic_metadata: dict,
    ) -> SemanticDocument:
        """Assemble the final ``SemanticDocument`` from all analysis data.

        Args:
            blocks: Original blocks.
            ai_result: Parsed dict from ``_parse_ai_response``.
            heuristic_metadata: Dict from ``_heuristic_analysis``.

        Returns:
            A fully populated ``SemanticDocument``.
        """
        # Parse document type safely
        try:
            doc_type = DocumentType(ai_result["document_type"])
        except (ValueError, KeyError):
            doc_type = DocumentType.UNKNOWN

        # Build semantic chunks (skip empty content)
        chunks: list[SemanticChunk] = []
        for chunk_data in ai_result.get("chunks", []):
            content = chunk_data.get("content", "").strip()
            if not content:
                continue
            chunks.append(
                SemanticChunk(
                    chunk_type=chunk_data.get("chunk_type", "section"),
                    content=content,
                    importance=float(chunk_data.get("importance", 0.5)),
                    metadata=chunk_data.get("metadata", {}),
                    template_hints=chunk_data.get("template_hints", []),
                )
            )

        # Merge metadata — heuristics first, AI result overwrites
        merged_metadata: dict = {
            **heuristic_metadata,
            **{
                k: v
                for k, v in ai_result.get("metadata", {}).items()
                if k != "note"
                and not k.endswith("_fields")
            },
        }

        word_count: int = heuristic_metadata.get("word_count", 0)

        return SemanticDocument(
            document_type=doc_type,
            confidence=float(ai_result.get("confidence", 0.5)),
            title=ai_result.get("title", ""),
            language=ai_result.get("language", "en"),
            chunks=chunks,
            raw_blocks=blocks,
            metadata=merged_metadata,
            word_count=word_count,
            estimated_pages=max(1, word_count // 250),
        )
