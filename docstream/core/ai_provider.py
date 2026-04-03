"""
AI Provider — unified interface for all AI providers.

Implements a fallback chain:
1. Gemini 1.5 Flash  (primary — free tier, 1 500 req/day)
2. Groq Llama 3.1 70B (fast fallback, generous free tier)
3. Ollama             (local or Colab via ngrok — no rate limits)
4. Raises AIUnavailableError if all providers fail or are unavailable

All providers implement the same interface so the
rest of the system doesn't care which one is used.
"""

from __future__ import annotations

import logging
import os

from docstream.exceptions import AIUnavailableError, APIError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class AIProvider:
    """Abstract base for all AI provider implementations."""

    def complete(self, prompt: str, system: str = "") -> str:
        """Generate a text completion.

        Args:
            prompt: User prompt to send to the model.
            system: Optional system instruction.

        Returns:
            Model response as a plain string.
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        """Return True if this provider can accept requests right now."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------


class GeminiProvider(AIProvider):
    """
    Google Gemini AI provider using the google-genai SDK.

    Tries models in order of preference:
    1. gemini-2.5-flash (best quality, free tier)
    2. gemini-2.0-flash (fast, reliable)
    3. gemini-2.0-flash-lite (lightweight fallback)
    """

    # Models to try in order (without 'models/' prefix)
    MODELS = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ]

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise APIError("GEMINI_API_KEY not set")

    def complete(self, prompt: str, system: str = "") -> str:
        """Call Gemini API using google-genai SDK.

        Tries models in order, returns first successful response.
        """
        from google import genai  # lazy import
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        last_error = None

        for model_name in self.MODELS:
            try:
                config = types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=16384,
                )

                if system:
                    config.system_instruction = system

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )

                if response.text:
                    logger.info(
                        f"Gemini responded using: {model_name}"
                    )
                    return response.text

            except Exception as e:
                last_error = e
                logger.debug(
                    f"Gemini model {model_name} failed: {e}"
                )
                continue

        raise APIError(
            f"All Gemini models failed. "
            f"Last error: {last_error}"
        )

    def is_available(self) -> bool:
        return bool(self.api_key)


# ---------------------------------------------------------------------------
# Groq provider
# ---------------------------------------------------------------------------


class GroqProvider(AIProvider):
    """Calls Groq (Llama 3.1 70B) via the ``groq`` SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise APIError("GROQ_API_KEY not set")

    def complete(self, prompt: str, system: str = "") -> str:
        """Call Groq Llama 3.1 70B and return the response text."""
        from groq import Groq  # lazy import

        client = Groq(api_key=self.api_key)
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.1,
            max_tokens=4096,
        )
        return response.choices[0].message.content

    def is_available(self) -> bool:
        return bool(self.api_key)


# ---------------------------------------------------------------------------
# Ollama provider
# ---------------------------------------------------------------------------


class OllamaProvider(AIProvider):
    """Connects to an Ollama instance (local or Colab via ngrok).

    Uses direct ``httpx`` HTTP calls to the Ollama REST API so that
    the ``ollama`` Python package is not required, and error messages
    are clear about whether the server is unreachable vs. timed out.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str = "llama3.1:8b",
    ) -> None:
        self.base_url = (
            base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self.model = model

    def complete(self, prompt: str, system: str = "") -> str:
        """Call the Ollama /api/chat endpoint and return the response text."""
        import httpx  # lazy import — available via FastAPI/Starlette

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = httpx.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
                timeout=120.0,
                headers={"ngrok-skip-browser-warning": "true"},
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except httpx.ConnectError as exc:
            raise APIError(
                f"Ollama unreachable at {self.base_url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise APIError("Ollama timed out after 120 s.") from exc
        except httpx.HTTPStatusError as exc:
            raise APIError(
                f"Ollama HTTP {exc.response.status_code}: "
                f"{exc.response.text[:200]}"
            ) from exc

    def is_available(self) -> bool:
        """Return True if Ollama is reachable and the model is loaded."""
        import httpx

        try:
            resp = httpx.get(
                f"{self.base_url}/api/tags",
                timeout=5.0,
                headers={"ngrok-skip-browser-warning": "true"},
            )
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            return any(self.model in m for m in models)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Provider chain
# ---------------------------------------------------------------------------


class AIProviderChain:
    """Try AI providers in priority order, falling back on failure.

    Default chain (auto-built from environment):
      Gemini 1.5 Flash → Groq Llama 3.1 70B → Ollama

    Pass a ``providers`` list to override for testing.
    Raises ``AIUnavailableError`` if every provider fails or is unreachable.
    """

    def __init__(
        self,
        providers: list[AIProvider] | None = None,
    ) -> None:
        self._providers: list[AIProvider] = (
            providers if providers is not None else self._build_chain()
        )

    def _build_chain(self) -> list[AIProvider]:
        """Build provider list from available environment credentials."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # dotenv not installed — keys must be in env already

        chain: list[AIProvider] = []

        for cls in (GeminiProvider, GroqProvider):
            try:
                chain.append(cls())
            except APIError:
                pass  # key not set — skip silently

        # Ollama is always added; availability is checked at call time
        chain.append(OllamaProvider())
        return chain

    def complete(self, prompt: str, system: str = "") -> str:
        """Try each provider in order and return the first success.

        Args:
            prompt: User prompt.
            system: Optional system instruction.

        Returns:
            Model response as a plain string.

        Raises:
            AIUnavailableError: If every provider fails or is unavailable.
        """
        last_error: Exception | None = None

        for provider in self._providers:
            # Skip Ollama if the server is not reachable right now
            if isinstance(provider, OllamaProvider) and not provider.is_available():
                continue

            try:
                result = provider.complete(prompt, system)
                if result and result.strip():
                    return result.strip()
            except Exception as exc:
                last_error = exc
                logger.warning("%s failed: %s", provider.__class__.__name__, exc)

        raise AIUnavailableError(
            "All AI providers failed or are unavailable. "
            "Check your API keys (GEMINI_API_KEY / GROQ_API_KEY) "
            "or start an Ollama server. "
            f"Last error: {last_error}"
        )

    @property
    def available_providers(self) -> list[str]:
        """Return the names of currently available providers."""
        available: list[str] = []
        for provider in self._providers:
            if isinstance(provider, OllamaProvider):
                if provider.is_available():
                    available.append("Ollama")
            else:
                available.append(
                    provider.__class__.__name__.replace("Provider", "")
                )
        return available
