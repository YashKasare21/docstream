"""
Tests for SemanticAnalyzer and AIProviderChain.

All AI provider calls are mocked — no real network requests are made.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docstream.exceptions import AIUnavailableError, StructuringError
from docstream.models.document import Block, BlockType, DocumentType, SemanticDocument


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / fixtures
# ─────────────────────────────────────────────────────────────────────────────


def _block(content: str, block_type: BlockType = BlockType.TEXT) -> Block:
    return Block(type=block_type, content=content)


def _resume_blocks() -> list[Block]:
    return [
        _block("Jane Doe", BlockType.HEADING),
        _block("work experience"),
        _block("Software Engineer at Acme Corp 2020-2023"),
        _block("education"),
        _block("BSc Computer Science, MIT, 2019"),
    ]


def _paper_blocks() -> list[Block]:
    return [
        _block("A Study of Things", BlockType.HEADING),
        _block("abstract: This paper studies important things."),
        _block("keywords: AI, ML"),
        _block("introduction: We introduce our work here."),
        _block("methodology: We used rigorous methods."),
        _block("results: We got great results."),
        _block("conclusion: We conclude that things are good."),
        _block("references: Smith et al. 2020."),
    ]


_VALID_AI_JSON = {
    "document_type": "resume",
    "confidence": 0.95,
    "title": "Jane Doe Resume",
    "language": "en",
    "metadata": {"name": "Jane Doe", "email": "jane@example.com"},
    "chunks": [
        {
            "chunk_type": "contact_info",
            "content": "Jane Doe, jane@example.com",
            "importance": 1.0,
            "template_hints": ["resume"],
            "metadata": {},
        },
        {
            "chunk_type": "work_experience",
            "content": "Software Engineer at Acme Corp 2020-2023",
            "importance": 0.9,
            "template_hints": ["resume"],
            "metadata": {"company": "Acme Corp"},
        },
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Heuristic — detects resume
# ─────────────────────────────────────────────────────────────────────────────


def test_heuristic_detects_resume():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    analyzer = SemanticAnalyzer.__new__(SemanticAnalyzer)
    doc_type, _ = analyzer._heuristic_analysis(_resume_blocks())
    assert doc_type == DocumentType.RESUME


# ─────────────────────────────────────────────────────────────────────────────
# 2. Heuristic — detects research paper
# ─────────────────────────────────────────────────────────────────────────────


def test_heuristic_detects_research_paper():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    analyzer = SemanticAnalyzer.__new__(SemanticAnalyzer)
    doc_type, _ = analyzer._heuristic_analysis(_paper_blocks())
    assert doc_type == DocumentType.RESEARCH_PAPER


# ─────────────────────────────────────────────────────────────────────────────
# 3. Heuristic — detects letter
# ─────────────────────────────────────────────────────────────────────────────


def test_heuristic_detects_letter():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    blocks = [
        _block("Dear Hiring Manager,"),
        _block("I am writing to apply for the position."),
        _block("Sincerely, John"),
    ]
    analyzer = SemanticAnalyzer.__new__(SemanticAnalyzer)
    doc_type, _ = analyzer._heuristic_analysis(blocks)
    assert doc_type == DocumentType.LETTER


# ─────────────────────────────────────────────────────────────────────────────
# 4. Heuristic — returns UNKNOWN for ambiguous text
# ─────────────────────────────────────────────────────────────────────────────


def test_heuristic_returns_unknown_for_ambiguous():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    blocks = [
        _block("The quick brown fox jumps over the lazy dog."),
        _block("This is a generic paragraph with no strong signals."),
    ]
    analyzer = SemanticAnalyzer.__new__(SemanticAnalyzer)
    doc_type, _ = analyzer._heuristic_analysis(blocks)
    assert doc_type == DocumentType.UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# 5. _prepare_text — truncates long documents
# ─────────────────────────────────────────────────────────────────────────────


def test_prepare_text_truncates_long_documents():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    # Each block has 20 words; 500 blocks = 10 000 words > 6 000 limit
    blocks = [_block(" ".join(["word"] * 20)) for _ in range(500)]
    analyzer = SemanticAnalyzer.__new__(SemanticAnalyzer)
    result = analyzer._prepare_text(blocks)
    assert "[... document truncated ...]" in result


# ─────────────────────────────────────────────────────────────────────────────
# 6. _prepare_text — adds heading markers
# ─────────────────────────────────────────────────────────────────────────────


def test_prepare_text_adds_heading_markers():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    heading = Block(
        type=BlockType.HEADING,
        content="Introduction",
        font_size=24.0,
    )
    analyzer = SemanticAnalyzer.__new__(SemanticAnalyzer)
    result = analyzer._prepare_text([heading])
    assert "## Introduction" in result or "### Introduction" in result


# ─────────────────────────────────────────────────────────────────────────────
# 7. _ai_analysis — parses valid JSON response
# ─────────────────────────────────────────────────────────────────────────────


def test_ai_analysis_parses_valid_json():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    mock_chain = MagicMock()
    mock_chain.complete.return_value = json.dumps(_VALID_AI_JSON)
    analyzer = SemanticAnalyzer(ai_provider=mock_chain)

    result = analyzer._ai_analysis("some text", DocumentType.RESUME)

    assert result["document_type"] == "resume"
    assert result["confidence"] == 0.95
    assert len(result["chunks"]) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 8. _ai_analysis — strips markdown fences before parsing
# ─────────────────────────────────────────────────────────────────────────────


def test_ai_analysis_strips_markdown_fences():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    fenced = f"```json\n{json.dumps(_VALID_AI_JSON)}\n```"
    mock_chain = MagicMock()
    mock_chain.complete.return_value = fenced
    analyzer = SemanticAnalyzer(ai_provider=mock_chain)

    result = analyzer._ai_analysis("some text", DocumentType.RESUME)
    assert result["document_type"] == "resume"


# ─────────────────────────────────────────────────────────────────────────────
# 9. _ai_analysis — raises StructuringError when no JSON found
# ─────────────────────────────────────────────────────────────────────────────


def test_ai_analysis_raises_on_no_json():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    mock_chain = MagicMock()
    mock_chain.complete.return_value = "I cannot analyze this document."
    analyzer = SemanticAnalyzer(ai_provider=mock_chain)

    with pytest.raises(StructuringError):
        analyzer._ai_analysis("some text", DocumentType.UNKNOWN)


# ─────────────────────────────────────────────────────────────────────────────
# 10. _build_semantic_document — sets correct document type
# ─────────────────────────────────────────────────────────────────────────────


def test_build_semantic_document_correct_type():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    ai_result = {
        "document_type": "resume",
        "confidence": 0.95,
        "title": "My Resume",
        "language": "en",
        "metadata": {},
        "chunks": [
            {
                "chunk_type": "contact_info",
                "content": "John Doe",
                "importance": 1.0,
                "template_hints": [],
                "metadata": {},
            }
        ],
    }
    analyzer = SemanticAnalyzer.__new__(SemanticAnalyzer)
    doc = analyzer._build_semantic_document(
        _resume_blocks(), ai_result, {"word_count": 50}
    )

    assert isinstance(doc, SemanticDocument)
    assert doc.document_type == DocumentType.RESUME
    assert doc.confidence == 0.95


# ─────────────────────────────────────────────────────────────────────────────
# 11. _build_semantic_document — skips empty chunks
# ─────────────────────────────────────────────────────────────────────────────


def test_build_semantic_document_skips_empty_chunks():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    ai_result = {
        "document_type": "resume",
        "confidence": 0.8,
        "title": "",
        "language": "en",
        "metadata": {},
        "chunks": [
            {
                "chunk_type": "contact_info",
                "content": "   ",  # whitespace-only → should be skipped
                "importance": 1.0,
                "template_hints": [],
                "metadata": {},
            },
            {
                "chunk_type": "summary",
                "content": "Experienced engineer",
                "importance": 0.9,
                "template_hints": [],
                "metadata": {},
            },
        ],
    }
    analyzer = SemanticAnalyzer.__new__(SemanticAnalyzer)
    doc = analyzer._build_semantic_document([], ai_result, {"word_count": 10})

    assert len(doc.chunks) == 1
    assert doc.chunks[0].chunk_type == "summary"


# ─────────────────────────────────────────────────────────────────────────────
# 12. analyze() full pipeline — mocked AI
# ─────────────────────────────────────────────────────────────────────────────


def test_analyze_full_pipeline_mocked():
    from docstream.core.semantic_analyzer import SemanticAnalyzer

    mock_chain = MagicMock()
    mock_chain.complete.return_value = json.dumps(_VALID_AI_JSON)
    analyzer = SemanticAnalyzer(ai_provider=mock_chain)

    result = analyzer.analyze(_resume_blocks())

    assert isinstance(result, SemanticDocument)
    assert result.document_type == DocumentType.RESUME
    assert len(result.chunks) == 2
    mock_chain.complete.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 13. Public API analyze() — accepts file path
# ─────────────────────────────────────────────────────────────────────────────


def test_public_api_analyze_accepts_path():
    import docstream

    sample_blocks = _resume_blocks()

    with (
        patch(
            "docstream.core.format_router.FormatRouter.extract",
            return_value=sample_blocks,
        ) as mock_extract,
        patch(
            "docstream.core.ai_provider.AIProviderChain.complete",
            return_value=json.dumps(_VALID_AI_JSON),
        ) as mock_ai,
    ):
        result = docstream.analyze("resume.pdf")

    assert isinstance(result, SemanticDocument)
    mock_extract.assert_called_once()
    mock_ai.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 14. AIProviderChain — falls back to Groq when Gemini fails
# ─────────────────────────────────────────────────────────────────────────────


def test_ai_provider_chain_falls_back_to_groq():
    from docstream.core.ai_provider import AIProviderChain, GroqProvider

    gemini_mock = MagicMock()
    gemini_mock.complete.side_effect = RuntimeError("Gemini quota exceeded")

    groq_mock = MagicMock(spec=GroqProvider)
    groq_mock.complete.return_value = "Groq response"

    chain = AIProviderChain(providers=[gemini_mock, groq_mock])
    result = chain.complete("test prompt")

    assert result == "Groq response"
    gemini_mock.complete.assert_called_once()
    groq_mock.complete.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 15. AIProviderChain — raises AIUnavailableError when all providers fail
# ─────────────────────────────────────────────────────────────────────────────


def test_ai_provider_chain_raises_when_all_fail():
    from docstream.core.ai_provider import AIProviderChain, OllamaProvider

    gemini_mock = MagicMock()
    gemini_mock.complete.side_effect = RuntimeError("Gemini down")

    groq_mock = MagicMock()
    groq_mock.complete.side_effect = RuntimeError("Groq down")

    # OllamaProvider mock — mark as unavailable
    ollama_mock = MagicMock(spec=OllamaProvider)
    ollama_mock.is_available.return_value = False

    chain = AIProviderChain(providers=[gemini_mock, groq_mock, ollama_mock])

    with pytest.raises(AIUnavailableError):
        chain.complete("test prompt")
