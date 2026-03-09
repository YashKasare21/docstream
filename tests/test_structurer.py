"""
Tests for DocumentStructurer — all API calls are mocked, no real network traffic.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from docstream.core.structurer import _MAX_CONTENT_CHARS, DocumentStructurer
from docstream.exceptions import StructuringError
from docstream.models.document import Block, BlockType, DocumentAST, TextBlock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_RESPONSE = json.dumps(
    {
        "title": "Test Document",
        "authors": ["Alice"],
        "abstract": "An abstract.",
        "sections": [
            {
                "heading": "Introduction",
                "level": 1,
                "content": ["First paragraph.", "Second paragraph."],
                "tables": [],
                "images": [],
                "subsections": [],
            }
        ],
        "metadata": {},
    }
)

_FENCED_RESPONSE = f"```json\n{_VALID_RESPONSE}\n```"


def _make_blocks(n: int = 2) -> list[Block]:
    return [TextBlock(type=BlockType.TEXT, content=f"Paragraph {i}.") for i in range(n)]


def _structurer(gemini_key: str = "fake-gemini", groq_key: str = "fake-groq") -> DocumentStructurer:
    """Return a DocumentStructurer whose clients are replaced with MagicMocks."""
    with patch("docstream.core.structurer.genai"):
        with patch("docstream.core.structurer.Groq"):
            ds = DocumentStructurer(gemini_key=gemini_key, groq_key=groq_key)
    ds._gemini_client = MagicMock()
    ds._groq_client = MagicMock()
    return ds


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestStructureReturnsValidAst:
    def test_structure_returns_valid_ast(self):
        """Gemini returns valid JSON → DocumentAST with correct fields."""
        ds = _structurer()
        ds._gemini_client.generate_content.return_value = MagicMock(text=_VALID_RESPONSE)

        result = ds.structure(_make_blocks())

        assert isinstance(result, DocumentAST)
        assert result.title == "Test Document"
        assert result.authors == ["Alice"]
        assert result.abstract == "An abstract."
        assert len(result.sections) == 1
        assert result.sections[0].heading == "Introduction"
        assert result.sections[0].content == ["First paragraph.", "Second paragraph."]

    def test_markdown_fences_are_stripped(self):
        """Markdown-fenced JSON response is parsed correctly."""
        ds = _structurer()
        ds._gemini_client.generate_content.return_value = MagicMock(text=_FENCED_RESPONSE)

        result = ds.structure(_make_blocks())

        assert isinstance(result, DocumentAST)
        assert result.title == "Test Document"

    def test_nested_subsections_are_parsed(self):
        """Subsections are recursively converted to Section objects."""
        response = json.dumps(
            {
                "title": "Doc",
                "authors": [],
                "abstract": None,
                "sections": [
                    {
                        "heading": "Top",
                        "level": 1,
                        "content": [],
                        "tables": [],
                        "images": [],
                        "subsections": [
                            {
                                "heading": "Sub",
                                "level": 2,
                                "content": ["text"],
                                "tables": [],
                                "images": [],
                                "subsections": [],
                            }
                        ],
                    }
                ],
                "metadata": {},
            }
        )
        ds = _structurer()
        ds._gemini_client.generate_content.return_value = MagicMock(text=response)

        result = ds.structure(_make_blocks())

        assert result.sections[0].subsections[0].heading == "Sub"
        assert result.sections[0].subsections[0].level == 2


class TestGeminiFallbackToGroq:
    def test_gemini_fallback_to_groq(self):
        """When Gemini fails all retries, Groq is called and returns a valid AST."""
        ds = _structurer()
        ds._gemini_client.generate_content.side_effect = Exception("Gemini down")
        ds._groq_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=_VALID_RESPONSE))]
        )

        with patch("time.sleep"):
            result = ds.structure(_make_blocks())

        assert isinstance(result, DocumentAST)
        assert result.title == "Test Document"
        assert ds._groq_client.chat.completions.create.called

    def test_groq_not_called_when_gemini_succeeds(self):
        """Groq must not be invoked when Gemini succeeds on the first attempt."""
        ds = _structurer()
        ds._gemini_client.generate_content.return_value = MagicMock(text=_VALID_RESPONSE)

        ds.structure(_make_blocks())

        ds._groq_client.chat.completions.create.assert_not_called()


class TestInvalidJsonTriggersRetry:
    def test_invalid_json_triggers_retry(self):
        """First call returns invalid JSON; second call returns valid JSON. Gemini called twice."""
        ds = _structurer()
        ds._gemini_client.generate_content.side_effect = [
            MagicMock(text="not valid json at all"),
            MagicMock(text=_VALID_RESPONSE),
        ]

        with patch("time.sleep") as mock_sleep:
            result = ds.structure(_make_blocks())

        assert isinstance(result, DocumentAST)
        assert ds._gemini_client.generate_content.call_count == 2
        mock_sleep.assert_called_once_with(1)

    def test_strict_prompt_used_on_retry(self):
        """The stricter prompt suffix is appended on the second attempt."""
        from docstream.core.structurer import _STRICT_SUFFIX

        ds = _structurer()
        received_prompts: list[str] = []

        def capture(prompt: str) -> MagicMock:
            received_prompts.append(prompt)
            if len(received_prompts) == 1:
                return MagicMock(text="bad json")
            return MagicMock(text=_VALID_RESPONSE)

        ds._gemini_client.generate_content.side_effect = capture

        with patch("time.sleep"):
            ds.structure(_make_blocks())

        assert _STRICT_SUFFIX not in received_prompts[0]
        assert received_prompts[1].endswith(_STRICT_SUFFIX)


class TestMissingApiKeyRaisesError:
    def test_missing_api_key_raises_error(self):
        """Empty keys → no clients → StructuringError on structure()."""
        with patch("docstream.core.structurer.genai"):
            with patch("docstream.core.structurer.Groq"):
                ds = DocumentStructurer(gemini_key="", groq_key=None)

        with pytest.raises(StructuringError, match="No AI provider available"):
            ds.structure(_make_blocks())

    def test_groq_only_works_without_gemini(self):
        """Groq-only setup (no Gemini key) falls through to Groq successfully."""
        with patch("docstream.core.structurer.genai"):
            with patch("docstream.core.structurer.Groq"):
                ds = DocumentStructurer(gemini_key="", groq_key="fake-groq")
        ds._groq_client = MagicMock()
        ds._groq_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=_VALID_RESPONSE))]
        )

        result = ds.structure(_make_blocks())

        assert isinstance(result, DocumentAST)


class TestPromptTruncationForLargeDocuments:
    def test_prompt_truncation_for_large_documents(self):
        """A document whose blocks exceed _MAX_CONTENT_CHARS is truncated in the prompt."""
        char_per_block = 1000
        n_blocks = (_MAX_CONTENT_CHARS // char_per_block) + 10
        large_blocks = [
            TextBlock(type=BlockType.TEXT, content="x" * char_per_block) for _ in range(n_blocks)
        ]

        ds = _structurer()
        prompt = ds._build_prompt(large_blocks)

        assert "[...document truncated to fit token limit...]" in prompt

    def test_prompt_within_limit_for_small_documents(self):
        """Small documents are not truncated."""
        ds = _structurer()
        prompt = ds._build_prompt(_make_blocks(5))

        assert "[...document truncated" not in prompt

    def test_prompt_contains_font_size_hints(self):
        """Blocks with font_size metadata include the hint in the prompt."""
        block = TextBlock(
            type=BlockType.TEXT,
            content="A heading",
            metadata={"font_size": 18},
        )
        ds = _structurer()
        prompt = ds._build_prompt([block])

        assert "[font_size=18]" in prompt
