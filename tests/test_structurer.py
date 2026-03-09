"""
Tests for the Structurer module.

This module contains unit tests for AI-powered content structuring.
External AI API calls are mocked to keep tests fast and offline.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from docstream.core.structurer import GeminiStructurer, GroqStructurer, Structurer
from docstream.exceptions import StructuringError
from docstream.models.document import (
    DocumentAST,
)

MOCK_AI_RESPONSE = json.dumps(
    {
        "sections": [
            {
                "title": "Introduction",
                "level": 1,
                "blocks": [{"type": "text", "content": "This is the introduction."}],
            }
        ]
    }
)


class TestGeminiStructurer:
    """Unit tests for GeminiStructurer."""

    @patch("docstream.core.structurer.genai")
    def test_structure_returns_document_ast(self, mock_genai, sample_raw_content):
        """GeminiStructurer.structure should return a DocumentAST."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = MOCK_AI_RESPONSE
        mock_genai.GenerativeModel.return_value = mock_model

        structurer = GeminiStructurer(api_key="fake_key")
        result = structurer.structure(sample_raw_content)

        assert isinstance(result, DocumentAST)

    @patch("docstream.core.structurer.genai")
    def test_structure_creates_sections(self, mock_genai, sample_raw_content):
        """GeminiStructurer should produce at least one section."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = MOCK_AI_RESPONSE
        mock_genai.GenerativeModel.return_value = mock_model

        structurer = GeminiStructurer(api_key="fake_key")
        result = structurer.structure(sample_raw_content)

        assert len(result.sections) >= 1

    @patch("docstream.core.structurer.genai")
    def test_structure_raises_on_invalid_response(self, mock_genai, sample_raw_content):
        """GeminiStructurer should raise StructuringError for non-JSON responses."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "not valid json at all"
        mock_genai.GenerativeModel.return_value = mock_model

        structurer = GeminiStructurer(api_key="fake_key")
        with pytest.raises(StructuringError):
            structurer.structure(sample_raw_content)

    @patch("docstream.core.structurer.genai")
    def test_structure_propagates_metadata(self, mock_genai, sample_raw_content):
        """Structured DocumentAST should carry the original metadata."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = MOCK_AI_RESPONSE
        mock_genai.GenerativeModel.return_value = mock_model

        structurer = GeminiStructurer(api_key="fake_key")
        result = structurer.structure(sample_raw_content)

        assert result.metadata == sample_raw_content.metadata


class TestGroqStructurer:
    """Unit tests for GroqStructurer."""

    @patch("docstream.core.structurer.Groq")
    def test_structure_returns_document_ast(self, mock_groq_cls, sample_raw_content):
        """GroqStructurer.structure should return a DocumentAST."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value.choices[
            0
        ].message.content = MOCK_AI_RESPONSE
        mock_groq_cls.return_value = mock_client

        structurer = GroqStructurer(api_key="fake_key")
        result = structurer.structure(sample_raw_content)

        assert isinstance(result, DocumentAST)

    @patch("docstream.core.structurer.Groq")
    def test_structure_raises_on_api_error(self, mock_groq_cls, sample_raw_content):
        """GroqStructurer should raise StructuringError when API call fails."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_groq_cls.return_value = mock_client

        structurer = GroqStructurer(api_key="fake_key")
        with pytest.raises(StructuringError):
            structurer.structure(sample_raw_content)


class TestStructurer:
    """Unit tests for the main Structurer dispatcher."""

    def test_raises_when_no_models_configured(self, sample_raw_content):
        """Structurer with no API keys should raise StructuringError."""
        structurer = Structurer()  # no API keys
        with pytest.raises(StructuringError):
            structurer.structure(sample_raw_content)

    def test_get_available_models_empty(self):
        """No API keys → no available models."""
        structurer = Structurer()
        assert structurer.get_available_models() == []

    @patch("docstream.core.structurer.genai")
    def test_get_available_models_with_gemini(self, mock_genai):
        """Gemini key present → 'gemini' in available models."""
        mock_genai.GenerativeModel.return_value = MagicMock()
        structurer = Structurer(gemini_api_key="fake_key")
        assert "gemini" in structurer.get_available_models()

    @patch("docstream.core.structurer.Groq")
    def test_set_preferred_model(self, mock_groq_cls):
        """set_preferred_model should update the preferred model."""
        mock_groq_cls.return_value = MagicMock()
        structurer = Structurer(groq_api_key="fake_key", preferred_model="groq")
        structurer.set_preferred_model("groq")
        assert structurer.preferred_model == "groq"

    def test_set_preferred_model_raises_for_unavailable(self):
        """set_preferred_model should raise ValueError for unknown models."""
        structurer = Structurer()
        with pytest.raises(ValueError):
            structurer.set_preferred_model("nonexistent_model")

    @patch("docstream.core.structurer.genai")
    def test_falls_back_to_secondary_model(self, mock_genai, sample_raw_content):
        """Structurer should fall back to groq when gemini fails."""
        # Gemini raises, groq succeeds
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("Gemini down")
        mock_genai.GenerativeModel.return_value = mock_model

        with patch("docstream.core.structurer.Groq") as mock_groq_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value.choices[
                0
            ].message.content = MOCK_AI_RESPONSE
            mock_groq_cls.return_value = mock_client

            structurer = Structurer(
                gemini_api_key="fake_gemini",
                groq_api_key="fake_groq",
                preferred_model="gemini",
            )
            result = structurer.structure(sample_raw_content)
            assert isinstance(result, DocumentAST)
