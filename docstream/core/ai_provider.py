"""
AI Provider — unified interface for all AI providers.

Implements a fallback chain:
1. Gemini 1.5 Flash  (primary — free tier, 1 500 req/day)
2. Groq Llama 3.1 70B (fast fallback, generous free tier)
3. Ollama             (local or Colab — no rate limits, always free)
4. Raises AIUnavailableError if all providers fail

All providers implement the same interface so the
rest of the system doesn't care which one is used.
"""

from __future__ import annotations


class AIUnavailableError(Exception):
    """Raised when all AI providers in the chain have been exhausted."""


class AIProvider:
    """Abstract base for all AI provider implementations."""

    def complete(self, prompt: str, system: str = "") -> str:
        """Generate a text completion.

        Args:
            prompt: User prompt to send to the model.
            system: Optional system instruction.

        Returns:
            Model response as a plain string.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError


class GeminiProvider(AIProvider):
    """Calls Google Gemini 1.5 Flash via ``google-generativeai``."""

    def complete(self, prompt: str, system: str = "") -> str:
        """Generate a completion using Gemini 1.5 Flash.

        Args:
            prompt: User prompt.
            system: Optional system instruction.

        Returns:
            Model response as a plain string.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError


class GroqProvider(AIProvider):
    """Calls Groq (Llama 3.1 70B) via the ``groq`` SDK."""

    def complete(self, prompt: str, system: str = "") -> str:
        """Generate a completion using Groq Llama 3.1 70B.

        Args:
            prompt: User prompt.
            system: Optional system instruction.

        Returns:
            Model response as a plain string.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError


class OllamaProvider(AIProvider):
    """Connects to an Ollama instance (local or Colab via ngrok)."""

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        """Initialize with the Ollama server URL.

        Args:
            base_url: Base URL of the Ollama HTTP server.
        """
        self.base_url = base_url

    def complete(self, prompt: str, system: str = "") -> str:
        """Generate a completion via Ollama.

        Args:
            prompt: User prompt.
            system: Optional system instruction.

        Returns:
            Model response as a plain string.

        Raises:
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError


class AIProviderChain:
    """Try providers in priority order, falling back on failure.

    Default chain: Gemini → Groq → Ollama.
    Raises ``AIUnavailableError`` if all providers fail.
    """

    def __init__(
        self,
        providers: list[AIProvider] | None = None,
    ) -> None:
        """Initialize with an ordered list of providers.

        Args:
            providers: Ordered list of ``AIProvider`` instances.
                       Defaults to ``[GeminiProvider, GroqProvider, OllamaProvider]``.
        """
        self.providers: list[AIProvider] = providers or [
            GeminiProvider(),
            GroqProvider(),
            OllamaProvider(),
        ]

    def complete(self, prompt: str, system: str = "") -> str:
        """Try each provider in order and return the first success.

        Args:
            prompt: User prompt.
            system: Optional system instruction.

        Returns:
            Model response as a plain string.

        Raises:
            AIUnavailableError: If every provider raises an exception.
            NotImplementedError: Until this method is implemented.
        """
        raise NotImplementedError
