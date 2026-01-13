"""Groq LLM Provider.

Provides integration with Groq's ultra-fast LLM inference API.
Groq offers a generous free tier with rate limits.

Free Tier Limits:
- 30 requests per minute
- 14,400 requests per day
- Models: Llama 3.1 70B, Mixtral 8x7B, Gemma 2 9B

Configuration:
    VALERIE_GROQ_API_KEY: Your Groq API key (required)
    VALERIE_GROQ_MODEL: Default model (optional)

Get API key at: https://console.groq.com/
"""

import json
import logging
import os
from collections.abc import AsyncIterator

import httpx

from valerie.llm.base import (
    AuthenticationError,
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMProviderError,
    LLMResponse,
    ModelNotFoundError,
    RateLimitError,
    StreamChunk,
)

logger = logging.getLogger(__name__)


class GroqProvider(BaseLLMProvider):
    """Groq LLM Provider for ultra-fast inference.

    Supported Models:
    - llama-3.1-70b-versatile (recommended)
    - llama-3.1-8b-instant
    - mixtral-8x7b-32768
    - gemma2-9b-it

    Features:
    - Extremely fast inference (10x faster than typical)
    - Free tier: 30 req/min, 14,400 req/day
    - OpenAI-compatible API
    """

    BASE_URL = "https://api.groq.com/openai/v1"

    AVAILABLE_MODELS = [
        "llama-3.3-70b-versatile",  # Latest recommended
        "llama-3.1-8b-instant",
        "llama-3.2-3b-preview",
        "llama-3.2-1b-preview",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    def __init__(self, config: dict | None = None):
        """Initialize Groq provider.

        Args:
            config: Configuration dictionary with optional keys:
                - api_key: Groq API key (or use VALERIE_GROQ_API_KEY env var)
                - model: Default model to use
                - timeout: Request timeout in seconds (default: 60)
        """
        super().__init__(config)
        self.api_key = (config.get("api_key") if config else None) or os.getenv(
            "VALERIE_GROQ_API_KEY"
        )

        self._default_model = (config.get("model") if config else None) or os.getenv(
            "VALERIE_GROQ_MODEL", "llama-3.3-70b-versatile"
        )

        self.timeout = config.get("timeout", 60) if config else 60

    @property
    def name(self) -> str:
        """Return provider name."""
        return "groq"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return self._default_model

    @property
    def available_models(self) -> list[str]:
        """Return list of available models."""
        return self.AVAILABLE_MODELS

    async def is_available(self) -> bool:
        """Check if Groq API is accessible."""
        if self._is_available is not None:
            return self._is_available

        if not self.api_key:
            self._is_available = False
            return False

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                self._is_available = response.status_code == 200
                return self._is_available
        except Exception as e:
            logger.debug(f"Groq not available: {e}")
            self._is_available = False
            return False

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Generate a response from Groq.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Returns:
            LLMResponse with the generated content.
        """
        if not self.api_key:
            raise AuthenticationError(self.name)

        config = self._get_config(config)
        model = self._get_model(config)

        # Convert messages to OpenAI format (Groq uses OpenAI-compatible API)
        openai_messages = [msg.to_dict() for msg in messages]

        payload = {
            "model": model,
            "messages": openai_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": False,
        }

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise AuthenticationError(self.name)

                if response.status_code == 429:
                    retry_after = response.headers.get("retry-after")
                    raise RateLimitError(
                        self.name,
                        retry_after=int(retry_after) if retry_after else None,
                    )

                if response.status_code == 404:
                    raise ModelNotFoundError(self.name, model)

                if response.status_code != 200:
                    raise LLMProviderError(
                        f"Groq request failed: {response.text}",
                        provider=self.name,
                        status_code=response.status_code,
                        retryable=response.status_code >= 500,
                    )

                data = response.json()
                choice = data.get("choices", [{}])[0]

                return LLMResponse(
                    content=choice.get("message", {}).get("content", ""),
                    model=model,
                    provider=self.name,
                    usage={
                        "input_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                        "output_tokens": data.get("usage", {}).get("completion_tokens", 0),
                    },
                    finish_reason=choice.get("finish_reason", "stop"),
                    raw_response=data,
                )

        except httpx.TimeoutException:
            raise LLMProviderError(
                "Groq request timed out",
                provider=self.name,
                retryable=True,
            )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from Groq.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Yields:
            StreamChunk objects with partial content.
        """
        if not self.api_key:
            raise AuthenticationError(self.name)

        config = self._get_config(config)
        model = self._get_model(config)

        # Convert messages to OpenAI format
        openai_messages = [msg.to_dict() for msg in messages]

        payload = {
            "model": model,
            "messages": openai_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": True,
        }

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status_code == 401:
                        raise AuthenticationError(self.name)

                    if response.status_code == 429:
                        raise RateLimitError(self.name)

                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise LLMProviderError(
                            f"Groq request failed: {error_text.decode()}",
                            provider=self.name,
                            status_code=response.status_code,
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                yield StreamChunk(
                                    content="",
                                    done=True,
                                    model=model,
                                    provider=self.name,
                                )
                                break

                            try:
                                data = json.loads(data_str)
                                choice = data.get("choices", [{}])[0]
                                delta = choice.get("delta", {})
                                content = delta.get("content", "")
                                finish_reason = choice.get("finish_reason")

                                yield StreamChunk(
                                    content=content,
                                    done=finish_reason is not None,
                                    model=model,
                                    provider=self.name,
                                )
                            except json.JSONDecodeError:
                                continue

        except httpx.TimeoutException:
            raise LLMProviderError(
                "Groq request timed out",
                provider=self.name,
                retryable=True,
            )

    async def health_check(self) -> dict:
        """Perform health check including API status."""
        base_check = await super().health_check()
        base_check["api_key_set"] = bool(self.api_key)
        base_check["free_tier_limits"] = {
            "requests_per_minute": 30,
            "requests_per_day": 14400,
        }
        return base_check
