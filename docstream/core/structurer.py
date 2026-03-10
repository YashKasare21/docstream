"""
AI-powered content structuring for document organization.

The DocumentStructurer class takes List[Block] from the extractor and uses
Gemini 2.0 Flash (primary) or Groq llama-3.3-70b (fallback) to produce a
structured DocumentAST. Keys are loaded from a .env file via python-dotenv.
"""

import json
import logging
import re
import time
import warnings
from typing import Any

from dotenv import load_dotenv

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import google.generativeai as genai
from groq import Groq

from docstream.exceptions import StructuringError
from docstream.models.document import (
    Block,
    DocumentAST,
    DocumentMetadata,
    Image,
    Section,
    Table,
)

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt constants
# ---------------------------------------------------------------------------

_EXAMPLE_OUTPUT = """{
  "title": "Example Document",
  "authors": ["Jane Doe"],
  "abstract": "A brief summary of the document.",
  "sections": [
    {
      "heading": "Introduction",
      "level": 1,
      "content": ["First paragraph text.", "Second paragraph text."],
      "tables": [],
      "images": [],
      "subsections": [
        {
          "heading": "Background",
          "level": 2,
          "content": ["Background paragraph."],
          "tables": [],
          "images": [],
          "subsections": []
        }
      ]
    }
  ],
  "metadata": {}
}"""

_SYSTEM_PROMPT = (
    "You are a document structure expert. Analyze the document content blocks below "
    "and produce a structured JSON representation.\n\n"
    "Rules:\n"
    "1. Return ONLY valid JSON — no markdown fences, no commentary, no preamble.\n"
    "2. Use font_size hints to detect headings: larger font_size = higher heading level.\n"
    '3. Group consecutive paragraphs as the "content" list of their parent section.\n'
    "4. Nest subsections logically (level 1 > level 2 > level 3).\n"
    "5. Preserve table and image references exactly as provided.\n\n"
    "Expected output format:\n" + _EXAMPLE_OUTPUT
)

_STRICT_SUFFIX = (
    "\n\nCRITICAL: Your entire response must be a single valid JSON object. "
    "No markdown, no prose, no code fences."
)

# ~8 000 tokens ≈ 32 000 chars; reserve space for system prompt + framing
_MAX_CONTENT_CHARS = 30_000


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class DocumentStructurer:
    """Structure a list of Blocks into a DocumentAST using Gemini / Groq."""

    GEMINI_MODEL = "gemini-2.0-flash"
    GROQ_MODEL = "llama-3.3-70b-versatile"
    MAX_RETRIES = 2
    _BACKOFF = [1, 2]

    def __init__(self, gemini_key: str, groq_key: str | None = None) -> None:
        """Initialise with explicit API keys (never hardcoded).

        Keys are typically injected from os.environ after calling load_dotenv().

        Args:
            gemini_key: Google Gemini API key.
            groq_key: Groq API key (optional; used as fallback).
        """
        self._gemini_key = gemini_key
        self._groq_key = groq_key
        self._gemini_client: Any | None = None
        self._groq_client: Any | None = None
        self._init_clients()

    def _init_clients(self) -> None:
        if self._gemini_key:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                genai.configure(api_key=self._gemini_key)
                self._gemini_client = genai.GenerativeModel(self.GEMINI_MODEL)
        if self._groq_key:
            self._groq_client = Groq(api_key=self._groq_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def structure(self, blocks: list[Block]) -> DocumentAST:
        """Convert a list of Blocks into a DocumentAST.

        Tries Gemini first (up to MAX_RETRIES), then Groq (up to MAX_RETRIES).
        On the second attempt for any provider a stricter prompt is used.

        Args:
            blocks: Content blocks produced by the extractor.

        Returns:
            Validated DocumentAST.

        Raises:
            StructuringError: When both providers are exhausted or unavailable.
        """
        if not self._gemini_client and not self._groq_client:
            raise StructuringError(
                "No AI provider available. "
                "Set GEMINI_API_KEY or GROQ_API_KEY (or pass keys directly)."
            )

        prompt = self._build_prompt(blocks)
        last_error: Exception | None = None

        if self._gemini_client:
            result = self._run_with_retry("gemini", prompt)
            if isinstance(result, DocumentAST):
                return result
            last_error = result

        if self._groq_client:
            result = self._run_with_retry("groq", prompt)
            if isinstance(result, DocumentAST):
                return result
            last_error = result

        raise StructuringError(f"All providers failed. Last error: {last_error}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_with_retry(self, provider: str, prompt: str) -> "DocumentAST | Exception":
        """Run one provider with exponential-backoff retries.

        Returns DocumentAST on success, or the last Exception on failure.
        """
        call_fn = self._call_gemini if provider == "gemini" else self._call_groq
        last_exc: Exception = StructuringError("Unknown error")

        for attempt in range(self.MAX_RETRIES):
            current_prompt = prompt if attempt == 0 else prompt + _STRICT_SUFFIX
            try:
                logger.info(
                    "%s attempt %d/%d",
                    provider.capitalize(),
                    attempt + 1,
                    self.MAX_RETRIES,
                )
                raw = call_fn(current_prompt)
                return self._parse_response(raw)
            except StructuringError as exc:
                last_exc = exc
                if attempt < self.MAX_RETRIES - 1:
                    wait = self._BACKOFF[attempt]
                    logger.warning(
                        "%s attempt %d failed, retrying in %ds: %s",
                        provider.capitalize(),
                        attempt + 1,
                        wait,
                        exc,
                    )
                    time.sleep(wait)
            except Exception as exc:
                last_exc = StructuringError(f"{provider.capitalize()} call error: {exc}")
                if attempt < self.MAX_RETRIES - 1:
                    wait = self._BACKOFF[attempt]
                    logger.warning(
                        "%s attempt %d failed, retrying in %ds: %s",
                        provider.capitalize(),
                        attempt + 1,
                        wait,
                        exc,
                    )
                    time.sleep(wait)

        logger.warning("%s exhausted retries. Last error: %s", provider.capitalize(), last_exc)
        return last_exc

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API and return the raw text response."""
        if not self._gemini_client:
            raise StructuringError("Gemini client is not initialised.")
        try:
            response = self._gemini_client.generate_content(prompt)
            return response.text
        except Exception as exc:
            raise StructuringError(f"Gemini API error: {exc}") from exc

    def _call_groq(self, prompt: str) -> str:
        """Call Groq API and return the raw text response."""
        if not self._groq_client:
            raise StructuringError("Groq client is not initialised.")
        try:
            response = self._groq_client.chat.completions.create(
                model=self.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as exc:
            raise StructuringError(f"Groq API error: {exc}") from exc

    def _build_prompt(self, blocks: list[Block]) -> str:
        """Build the structuring prompt, truncating blocks to stay under ~8 000 tokens."""
        lines: list[str] = []
        total = 0

        for block in blocks:
            font_hint = ""
            if block.metadata.get("font_size"):
                font_hint = f" [font_size={block.metadata['font_size']}]"
            line = f"[{block.type}]{font_hint} {block.content}"

            if total + len(line) > _MAX_CONTENT_CHARS:
                lines.append("[...document truncated to fit token limit...]")
                break

            lines.append(line)
            total += len(line)

        blocks_text = "\n".join(lines)
        return (
            f"{_SYSTEM_PROMPT}\n\n"
            "--- DOCUMENT BLOCKS ---\n"
            f"{blocks_text}\n"
            "--- END OF BLOCKS ---\n\n"
            "Now return the structured JSON for this document:"
        )

    def _parse_response(self, response: str) -> DocumentAST:
        """Parse raw AI response into a DocumentAST.

        Strips markdown fences if present. On validation failure raises
        StructuringError so the retry loop can re-attempt with a stricter prompt.
        """
        cleaned = response.strip()

        # Strip ```json ... ``` or ``` ... ``` fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

        # Extract first complete JSON object
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            raise StructuringError("No JSON object found in response.")
        cleaned = cleaned[start:end]

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise StructuringError(f"Invalid JSON in response: {exc}") from exc

        if not self._validate_ast(data):
            raise StructuringError(
                "Response JSON failed DocumentAST validation "
                "(missing required fields: title, sections[].heading, sections[].level)."
            )

        return self._dict_to_ast(data)

    def _validate_ast(self, ast: dict[str, Any]) -> bool:
        """Return True only when the dict satisfies the minimum DocumentAST contract."""
        if not isinstance(ast, dict):
            return False
        if "sections" not in ast or not isinstance(ast["sections"], list):
            return False
        for sec in ast["sections"]:
            if not isinstance(sec, dict):
                return False
            if "heading" not in sec or "level" not in sec:
                return False
            if not isinstance(sec.get("content", []), list):
                return False
        return True

    def _dict_to_ast(self, data: dict[str, Any]) -> DocumentAST:
        """Convert a validated response dict into a DocumentAST instance."""
        sections = [self._dict_to_section(s) for s in data.get("sections", [])]
        metadata = DocumentMetadata(
            title=data.get("title") or None,
            abstract=data.get("abstract") or None,
            custom_fields=data.get("metadata") or {},
        )
        return DocumentAST(
            title=data.get("title", ""),
            authors=data.get("authors", []),
            abstract=data.get("abstract") or None,
            metadata=metadata,
            sections=sections,
        )

    def _dict_to_section(self, data: dict[str, Any]) -> Section:
        """Recursively convert a section dict into a Section model instance."""
        tables: list[Table] = []
        for t in data.get("tables", []):
            if isinstance(t, dict) and "headers" in t:
                tables.append(Table(**t))

        images: list[Image] = []
        for img in data.get("images", []):
            if isinstance(img, dict) and "src" in img:
                images.append(Image(**img))

        subsections = [self._dict_to_section(s) for s in data.get("subsections", [])]

        return Section(
            heading=data.get("heading", ""),
            level=int(data.get("level", 1)),
            content=data.get("content", []),
            tables=tables,
            images=images,
            subsections=subsections,
        )


# Backward-compatible alias
Structurer = DocumentStructurer
