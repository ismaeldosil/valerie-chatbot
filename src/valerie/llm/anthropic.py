"""Anthropic Claude LLM Provider.

Provides integration with Anthropic's Claude models.
This is the original provider used by the system.

Configuration:
    VALERIE_ANTHROPIC_API_KEY: Your Anthropic API key (required)
    VALERIE_MODEL_NAME: Default model (optional)

Get API key at: https://console.anthropic.com/
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
    MessageRole,
    ModelNotFoundError,
    RateLimitError,
    StreamChunk,
)

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM Provider.

    Supported Models:
    - claude-sonnet-4-20250514 (default)
    - claude-opus-4-20250514
    - claude-3-5-sonnet-20241022
    - claude-3-5-haiku-20241022

    Features:
    - High quality responses
    - Tool use support
    - Long context (200K tokens)
    """

    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    AVAILABLE_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ]

    def __init__(self, config: dict | None = None):
        """Initialize Anthropic provider.

        Args:
            config: Configuration dictionary with optional keys:
                - api_key: Anthropic API key (or use VALERIE_ANTHROPIC_API_KEY env var)
                - model: Default model to use
                - timeout: Request timeout in seconds (default: 120)
        """
        super().__init__(config)
        self.api_key = (config.get("api_key") if config else None) or os.getenv(
            "VALERIE_ANTHROPIC_API_KEY"
        )

        self._default_model = (config.get("model") if config else None) or os.getenv(
            "VALERIE_MODEL_NAME", "claude-sonnet-4-20250514"
        )

        self.timeout = config.get("timeout", 120) if config else 120

    @property
    def name(self) -> str:
        """Return provider name."""
        return "anthropic"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return self._default_model

    @property
    def available_models(self) -> list[str]:
        """Return list of available models."""
        return self.AVAILABLE_MODELS

    async def is_available(self) -> bool:
        """Check if Anthropic API is accessible."""
        if self._is_available is not None:
            return self._is_available

        if not self.api_key:
            self._is_available = False
            return False

        # Anthropic doesn't have a models list endpoint, so just check auth
        self._is_available = True
        return True

    def _convert_messages(self, messages: list[LLMMessage]) -> tuple[str | None, list[dict]]:
        """Convert messages to Anthropic format.

        Anthropic requires system message to be separate from messages.

        Returns:
            Tuple of (system_prompt, messages_list)
        """
        system_prompt = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                anthropic_messages.append(
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                    }
                )

        return system_prompt, anthropic_messages

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Generate a response from Anthropic Claude.

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

        system_prompt, anthropic_messages = self._convert_messages(messages)

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if config.stop_sequences:
            payload["stop_sequences"] = config.stop_sequences

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/messages",
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
                        f"Anthropic request failed: {response.text}",
                        provider=self.name,
                        status_code=response.status_code,
                        retryable=response.status_code >= 500,
                    )

                data = response.json()

                # Extract content from response
                content_blocks = data.get("content", [])
                content = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        content += block.get("text", "")

                return LLMResponse(
                    content=content,
                    model=model,
                    provider=self.name,
                    usage={
                        "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                        "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                    },
                    finish_reason=data.get("stop_reason", "stop"),
                    raw_response=data,
                )

        except httpx.TimeoutException:
            raise LLMProviderError(
                "Anthropic request timed out",
                provider=self.name,
                retryable=True,
            )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from Anthropic Claude.

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

        system_prompt, anthropic_messages = self._convert_messages(messages)

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": True,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if config.stop_sequences:
            payload["stop_sequences"] = config.stop_sequences

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.BASE_URL}/messages",
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
                            f"Anthropic request failed: {error_text.decode()}",
                            provider=self.name,
                            status_code=response.status_code,
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                event_type = data.get("type")

                                if event_type == "content_block_delta":
                                    delta = data.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        yield StreamChunk(
                                            content=delta.get("text", ""),
                                            done=False,
                                            model=model,
                                            provider=self.name,
                                        )

                                elif event_type == "message_stop":
                                    yield StreamChunk(
                                        content="",
                                        done=True,
                                        model=model,
                                        provider=self.name,
                                    )
                                    break

                            except json.JSONDecodeError:
                                continue

        except httpx.TimeoutException:
            raise LLMProviderError(
                "Anthropic request timed out",
                provider=self.name,
                retryable=True,
            )

    async def health_check(self) -> dict:
        """Perform health check."""
        base_check = await super().health_check()
        base_check["api_key_set"] = bool(self.api_key)
        return base_check
