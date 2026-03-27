"""
Semantic Analyzer — understands document meaning and type.

This is the core intelligence of Docstream v2.

Responsibilities:
- Detect document type (resume, research paper, report,
  thesis, presentation, letter, notes, etc.)
- Extract semantic entities (person names, dates,
  organizations, skills, sections)
- Understand content hierarchy beyond just headings
- Score content relevance per template type
- Create semantic chunks that preserve meaning

Uses AI (Gemini/Groq/Ollama) with a specialized prompt
designed for document type detection and entity extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from docstream import Block


class DocumentType(Enum):
    """Enumeration of supported document types."""

    RESUME = "resume"
    RESEARCH_PAPER = "research_paper"
    ACADEMIC_REPORT = "academic_report"
    TECHNICAL_REPORT = "technical_report"
    PRESENTATION = "presentation"
    LETTER = "letter"
    NOTES = "notes"
    UNKNOWN = "unknown"


@dataclass
class SemanticChunk:
    """A semantically meaningful unit of document content.

    Attributes:
        chunk_type: Semantic category (e.g. ``"experience"``, ``"abstract"``).
        content: Raw text content of the chunk.
        importance: Relevance weight in [0.0, 1.0].
        template_hints: Template names this chunk maps well to.
    """

    chunk_type: str
    content: str
    importance: float = 0.0
    template_hints: List[str] = field(default_factory=list)


@dataclass
class SemanticDocument:
    """Fully analyzed document with detected type and chunked content.

    Attributes:
        document_type: Detected type from ``DocumentType``.
        chunks: Ordered list of semantic chunks.
        entities: Key/value metadata (names, dates, organizations, etc.).
    """

    document_type: DocumentType
    chunks: List[SemanticChunk] = field(default_factory=list)
    entities: dict[str, str] = field(default_factory=dict)


class SemanticAnalyzer:
    """Analyze a list of blocks and produce a ``SemanticDocument``."""

    def analyze(self, blocks: "List[Block]") -> SemanticDocument:
        """Run full semantic analysis on extracted blocks.

        Args:
            blocks: Blocks produced by a format handler.

        Returns:
            A ``SemanticDocument`` with detected type, chunks, and entities.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError

    def detect_document_type(self, blocks: "List[Block]") -> DocumentType:
        """Detect the high-level document type from its blocks.

        Args:
            blocks: Blocks produced by a format handler.

        Returns:
            The most likely ``DocumentType``.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError

    def create_semantic_chunks(self, blocks: "List[Block]") -> List[SemanticChunk]:
        """Group blocks into semantically coherent chunks.

        Args:
            blocks: Blocks produced by a format handler.

        Returns:
            List of ``SemanticChunk`` objects.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError
