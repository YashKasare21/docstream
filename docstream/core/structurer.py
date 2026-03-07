"""
AI-powered content structuring for document organization.

The Structurer class uses AI models to organize raw content into
structured DocumentAST with proper hierarchy and relationships.
"""

import logging
import warnings
from abc import ABC, abstractmethod
from typing import Any

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import google.generativeai as genai
from groq import Groq

from docstream.exceptions import StructuringError
from docstream.models.document import (
    Block,
    BlockType,
    DocumentAST,
    DocumentMetadata,
    HeadingBlock,
    RawContent,
    Section,
    TextBlock,
)

logger = logging.getLogger(__name__)


class BaseStructurer(ABC):
    """Abstract base class for content structurers."""

    @abstractmethod
    def structure(self, raw_content: RawContent) -> DocumentAST:
        """Structure raw content into DocumentAST.

        Args:
            raw_content: Raw content from extractor

        Returns:
            DocumentAST with structured content

        Raises:
            StructuringError: If structuring fails
        """
        pass


class GeminiStructurer(BaseStructurer):
    """Structurer using Google Gemini AI model."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        """Initialize Gemini structurer.

        Args:
            api_key: Google Gemini API key
            model: Gemini model to use
        """
        self.model_name = model
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def structure(self, raw_content: RawContent) -> DocumentAST:
        """Structure content using Gemini AI."""
        try:
            logger.info(f"Structuring content with Gemini: {self.model_name}")

            # Prepare prompt for Gemini
            prompt = self._create_structuring_prompt(raw_content)

            # Generate structured content
            response = self.model.generate_content(prompt)

            # Parse response into DocumentAST
            return self._parse_response(response.text, raw_content.metadata)

        except Exception as e:
            logger.error(f"Gemini structuring failed: {e}")
            raise StructuringError(f"Failed to structure content with Gemini: {e}")

    def _create_structuring_prompt(self, raw_content: RawContent) -> str:
        """Create prompt for AI structuring."""
        prompt = f"""
Analyze the following document content and structure it into a hierarchical format.

Content:
{raw_content.text[:10000]}  # Limit content length

Please structure this content by:
1. Identifying main sections and subsections
2. Classifying content blocks (text, headings, lists, etc.)
3. Organizing into a clear hierarchy

Return the result in this JSON format:
{{
    "sections": [
        {{
            "title": "Section Title",
            "level": 1,
            "blocks": [
                {{
                    "type": "text|heading|list",
                    "content": "Block content",
                    "level": 1  // for headings
                }}
            ]
        }}
    ]
}}
"""
        return prompt

    def _parse_response(self, response_text: str, metadata: DocumentMetadata) -> DocumentAST:
        """Parse AI response into DocumentAST."""
        import json

        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise StructuringError("No valid JSON found in AI response")

            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)

            # Build DocumentAST
            sections = []
            for section_data in data.get("sections", []):
                section = self._create_section(section_data)
                sections.append(section)

            return DocumentAST(
                metadata=metadata, sections=sections, blocks=[], tables=[], images=[]
            )

        except json.JSONDecodeError as e:
            raise StructuringError(f"Failed to parse AI response as JSON: {e}")

    def _create_section(self, section_data: dict[str, Any]) -> Section:
        """Create Section from data."""
        blocks = []

        for block_data in section_data.get("blocks", []):
            block = self._create_block(block_data)
            blocks.append(block)

        return Section(
            title=section_data.get("title", ""), level=section_data.get("level", 1), blocks=blocks
        )

    def _create_block(self, block_data: dict[str, Any]) -> Block:
        """Create Block from data."""
        block_type = BlockType(block_data.get("type", "text"))
        content = block_data.get("content", "")

        if block_type == BlockType.HEADING:
            return HeadingBlock(type=block_type, content=content, level=block_data.get("level", 1))
        else:
            return TextBlock(type=block_type, content=content)


class GroqStructurer(BaseStructurer):
    """Structurer using Groq AI model."""

    def __init__(self, api_key: str, model: str = "llama3-70b-8192"):
        """Initialize Groq structurer.

        Args:
            api_key: Groq API key
            model: Groq model to use
        """
        self.model_name = model
        self.client = Groq(api_key=api_key)

    def structure(self, raw_content: RawContent) -> DocumentAST:
        """Structure content using Groq AI."""
        try:
            logger.info(f"Structuring content with Groq: {self.model_name}")

            # Prepare prompt for Groq
            prompt = self._create_structuring_prompt(raw_content)

            # Generate structured content
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=4000,
            )

            # Parse response into DocumentAST
            return self._parse_response(response.choices[0].message.content, raw_content.metadata)

        except Exception as e:
            logger.error(f"Groq structuring failed: {e}")
            raise StructuringError(f"Failed to structure content with Groq: {e}")

    def _create_structuring_prompt(self, raw_content: RawContent) -> str:
        """Create prompt for AI structuring."""
        # Similar to Gemini prompt but optimized for Groq
        prompt = f"""
Analyze and structure this document content:

{raw_content.text[:8000]}

Return a structured JSON with sections and blocks:
{{
    "sections": [
        {{
            "title": "Section Title",
            "level": 1,
            "blocks": [
                {{
                    "type": "text",
                    "content": "Content here"
                }}
            ]
        }}
    ]
}}
"""
        return prompt

    def _parse_response(self, response_text: str, metadata: DocumentMetadata) -> DocumentAST:
        """Parse AI response into DocumentAST."""
        # Similar parsing logic as Gemini
        import json

        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise StructuringError("No valid JSON found in AI response")

            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)

            sections = []
            for section_data in data.get("sections", []):
                section = Section(
                    title=section_data.get("title", ""),
                    level=section_data.get("level", 1),
                    blocks=[],
                )

                for block_data in section_data.get("blocks", []):
                    block_type = BlockType(block_data.get("type", "text"))
                    if block_type == BlockType.HEADING:
                        block = HeadingBlock(
                            type=block_type,
                            content=block_data.get("content", ""),
                            level=block_data.get("level", 1),
                        )
                    else:
                        block = TextBlock(type=block_type, content=block_data.get("content", ""))
                    section.blocks.append(block)

                sections.append(section)

            return DocumentAST(
                metadata=metadata, sections=sections, blocks=[], tables=[], images=[]
            )

        except json.JSONDecodeError as e:
            raise StructuringError(f"Failed to parse AI response as JSON: {e}")


class Structurer:
    """Main structurer class that manages AI-powered content organization."""

    def __init__(
        self,
        gemini_api_key: str | None = None,
        groq_api_key: str | None = None,
        preferred_model: str = "gemini",
        gemini_model: str = "gemini-1.5-pro",
        groq_model: str = "llama3-70b-8192",
    ):
        """Initialize structurer with AI models.

        Args:
            gemini_api_key: Google Gemini API key
            groq_api_key: Groq API key
            preferred_model: Preferred AI model ("gemini" or "groq")
            gemini_model: Specific Gemini model to use
            groq_model: Specific Groq model to use
        """
        self.structurers = {}

        if gemini_api_key:
            self.structurers["gemini"] = GeminiStructurer(
                api_key=gemini_api_key, model=gemini_model
            )

        if groq_api_key:
            self.structurers["groq"] = GroqStructurer(api_key=groq_api_key, model=groq_model)

        self.preferred_model = preferred_model

    def structure(self, raw_content: RawContent) -> DocumentAST:
        """Structure raw content into DocumentAST.

        Args:
            raw_content: Raw content from extractor

        Returns:
            DocumentAST with structured content

        Raises:
            StructuringError: If structuring fails
        """
        logger.info("Structuring document content")

        if not self.structurers:
            raise StructuringError("No AI structurers available. Check API keys.")

        # Try preferred model first
        if self.preferred_model in self.structurers:
            try:
                return self.structurers[self.preferred_model].structure(raw_content)
            except Exception as e:
                logger.warning(f"Preferred model {self.preferred_model} failed: {e}")

        # Try other available models
        for model_name, structurer in self.structurers.items():
            if model_name != self.preferred_model:
                try:
                    logger.info(f"Falling back to {model_name}")
                    return structurer.structure(raw_content)
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {e}")

        raise StructuringError("All AI models failed to structure content")

    def get_available_models(self) -> list[str]:
        """Get list of available AI models."""
        return list(self.structurers.keys())

    def set_preferred_model(self, model: str) -> None:
        """Set preferred AI model.

        Args:
            model: Model name ("gemini" or "groq")

        Raises:
            ValueError: If model is not available
        """
        if model not in self.structurers:
            raise ValueError(
                f"Model {model} not available. Available: {list(self.structurers.keys())}"
            )

        self.preferred_model = model
