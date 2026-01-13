"""Ollama LLM Provider.

Provides integration with Ollama for running LLMs locally.
Ollama is completely free and runs on your own hardware.

Installation:
    curl -fsSL https://ollama.com/install.sh | sh
    ollama pull llama3.2

Configuration:
    VALERIE_OLLAMA_BASE_URL: http://localhost:11434 (default)
    VALERIE_OLLAMA_MODEL: llama3.2 (default)
"""

import json
import logging
import os
from collections.abc import AsyncIterator

import httpx

from valerie.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMProviderError,
    LLMResponse,
    ModelNotFoundError,
    StreamChunk,
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM Provider for local model execution.

    Supports:
    - Llama 3.2 (3B, 8B, 70B)
    - Mistral 7B
    - Phi-3
    - Gemma 2
    - Any model available in Ollama

    Features:
    - Completely free (runs locally)
    - No API key required
    - Full privacy (data never leaves your machine)
    - Streaming support
    """

    POPULAR_MODELS = [
        "llama3.2",
        "llama3.2:3b",
        "llama3.2:70b",
        "mistral",
        "mistral:7b",
        "phi3",
        "phi3:mini",
        "gemma2",
        "gemma2:9b",
        "codellama",
        "qwen2.5",
    ]

    def __init__(self, config: dict | None = None):
        """Initialize Ollama provider.

        Args:
            config: Configuration dictionary with optional keys:
                - base_url: Ollama server URL (default: http://localhost:11434)
                - model: Default model to use (default: llama3.2)
                - timeout: Request timeout in seconds (default: 120)
        """
        super().__init__(config)
        self.base_url = (
            config.get("base_url", os.getenv("VALERIE_OLLAMA_BASE_URL", "http://localhost:11434"))
            if config
            else os.getenv("VALERIE_OLLAMA_BASE_URL", "http://localhost:11434")
        )

        self._default_model = (
            config.get("model", os.getenv("VALERIE_OLLAMA_MODEL", "llama3.2"))
            if config
            else os.getenv("VALERIE_OLLAMA_MODEL", "llama3.2")
        )

        self.timeout = config.get("timeout", 120) if config else 120
        self._cached_models: list[str] | None = None

    @property
    def name(self) -> str:
        """Return provider name."""
        return "ollama"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return self._default_model

    @property
    def available_models(self) -> list[str]:
        """Return cached list of available models."""
        if self._cached_models:
            return self._cached_models
        return self.POPULAR_MODELS

    async def _fetch_available_models(self) -> list[str]:
        """Fetch list of available models from Ollama server."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    self._cached_models = models
                    return models
        except Exception as e:
            logger.debug(f"Failed to fetch Ollama models: {e}")
        return self.POPULAR_MODELS

    async def is_available(self) -> bool:
        """Check if Ollama server is running and accessible."""
        if self._is_available is not None:
            return self._is_available

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                self._is_available = response.status_code == 200
                if self._is_available:
                    # Cache available models
                    data = response.json()
                    self._cached_models = [m["name"] for m in data.get("models", [])]
                return self._is_available
        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            self._is_available = False
            return False

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Generate a response from Ollama.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Returns:
            LLMResponse with the generated content.
        """
        config = self._get_config(config)
        model = self._get_model(config)

        # Convert messages to Ollama format
        ollama_messages = [msg.to_dict() for msg in messages]

        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
            },
        }

        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )

                if response.status_code == 404:
                    raise ModelNotFoundError(self.name, model)

                if response.status_code != 200:
                    raise LLMProviderError(
                        f"Ollama request failed: {response.text}",
                        provider=self.name,
                        status_code=response.status_code,
                        retryable=response.status_code >= 500,
                    )

                data = response.json()

                return LLMResponse(
                    content=data.get("message", {}).get("content", ""),
                    model=model,
                    provider=self.name,
                    usage={
                        "input_tokens": data.get("prompt_eval_count", 0),
                        "output_tokens": data.get("eval_count", 0),
                    },
                    finish_reason="stop" if data.get("done") else "length",
                    raw_response=data,
                )

        except httpx.ConnectError:
            raise LLMProviderError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running: ollama serve",
                provider=self.name,
                retryable=True,
            )
        except httpx.TimeoutException:
            raise LLMProviderError(
                "Ollama request timed out",
                provider=self.name,
                retryable=True,
            )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from Ollama.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Yields:
            StreamChunk objects with partial content.
        """
        config = self._get_config(config)
        model = self._get_model(config)

        # Convert messages to Ollama format
        ollama_messages = [msg.to_dict() for msg in messages]

        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
            },
        }

        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response:
                    if response.status_code == 404:
                        raise ModelNotFoundError(self.name, model)

                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise LLMProviderError(
                            f"Ollama request failed: {error_text.decode()}",
                            provider=self.name,
                            status_code=response.status_code,
                        )

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                content = data.get("message", {}).get("content", "")
                                done = data.get("done", False)

                                yield StreamChunk(
                                    content=content,
                                    done=done,
                                    model=model,
                                    provider=self.name,
                                )

                                if done:
                                    break
                            except json.JSONDecodeError:
                                continue

        except httpx.ConnectError:
            raise LLMProviderError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running: ollama serve",
                provider=self.name,
                retryable=True,
            )

    async def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama registry.

        Args:
            model: Model name to pull (e.g., "llama3.2")

        Returns:
            True if successful, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model},
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False

    async def health_check(self) -> dict:
        """Perform health check including model availability."""
        base_check = await super().health_check()

        if base_check.get("available"):
            await self._fetch_available_models()
            base_check["models"] = self._cached_models or []
            base_check["base_url"] = self.base_url

        return base_check
