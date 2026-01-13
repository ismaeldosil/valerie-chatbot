"""Google Gemini LLM Provider.

Provides integration with Google's Gemini API for advanced language models.
Gemini offers powerful models with large context windows and multimodal capabilities.

Models:
- gemini-1.5-pro: Most capable, 2M token context window
- gemini-1.5-flash: Fast and efficient, 1M token context
- gemini-1.0-pro: Previous generation, stable

Configuration:
    VALERIE_GEMINI_API_KEY: Your Google AI Studio API key (required)
    VALERIE_GEMINI_MODEL: Default model (optional)

Get API key at: https://aistudio.google.com/app/apikey
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


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM Provider.

    Supported Models:
    - gemini-1.5-pro (recommended for complex tasks)
    - gemini-1.5-flash (fast, efficient)
    - gemini-1.0-pro (stable, previous gen)

    Features:
    - Up to 2M token context window (1.5 Pro)
    - Multimodal support (text, images, video, audio)
    - Free tier: 15 requests/min, 1M tokens/min
    - Competitive pricing for production
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    AVAILABLE_MODELS = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.0-pro",
        "gemini-2.0-flash-exp",
    ]

    # Map our role names to Gemini's role names
    ROLE_MAP = {
        MessageRole.USER: "user",
        MessageRole.ASSISTANT: "model",
        MessageRole.SYSTEM: "user",  # Gemini handles system as first user message
    }

    def __init__(self, config: dict | None = None):
        """Initialize Gemini provider.

        Args:
            config: Configuration dictionary with optional keys:
                - api_key: Google AI API key (or use VALERIE_GEMINI_API_KEY env var)
                - model: Default model to use
                - timeout: Request timeout in seconds (default: 120)
        """
        super().__init__(config)
        self.api_key = (config.get("api_key") if config else None) or os.getenv(
            "VALERIE_GEMINI_API_KEY"
        )

        self._default_model = (config.get("model") if config else None) or os.getenv(
            "VALERIE_GEMINI_MODEL", "gemini-1.5-flash"
        )

        self.timeout = config.get("timeout", 120) if config else 120

    @property
    def name(self) -> str:
        """Return provider name."""
        return "gemini"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return self._default_model

    @property
    def available_models(self) -> list[str]:
        """Return list of available models."""
        return self.AVAILABLE_MODELS

    def _convert_messages_to_gemini(
        self, messages: list[LLMMessage]
    ) -> tuple[list[dict], str | None]:
        """Convert messages to Gemini format.

        Gemini uses a different format:
        - 'contents' array with 'role' and 'parts'
        - Roles are 'user' and 'model' (not 'assistant')
        - System prompts are handled separately

        Returns:
            Tuple of (contents list, system instruction or None)
        """
        contents = []
        system_instruction = None

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # Gemini handles system prompt as systemInstruction
                system_instruction = msg.content
            else:
                role = self.ROLE_MAP.get(msg.role, "user")
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        return contents, system_instruction

    async def is_available(self) -> bool:
        """Check if Gemini API is accessible."""
        if self._is_available is not None:
            return self._is_available

        if not self.api_key:
            self._is_available = False
            return False

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    params={"key": self.api_key},
                )
                self._is_available = response.status_code == 200
                return self._is_available
        except Exception as e:
            logger.debug(f"Gemini not available: {e}")
            self._is_available = False
            return False

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Generate a response from Gemini.

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

        # Convert messages to Gemini format
        contents, system_instruction = self._convert_messages_to_gemini(messages)

        # Build payload
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": config.temperature,
                "maxOutputTokens": config.max_tokens,
                "topP": config.top_p,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        if config.stop_sequences:
            payload["generationConfig"]["stopSequences"] = config.stop_sequences

        url = f"{self.BASE_URL}/models/{model}:generateContent"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 401 or response.status_code == 403:
                    raise AuthenticationError(self.name)

                if response.status_code == 429:
                    raise RateLimitError(self.name)

                if response.status_code == 404:
                    raise ModelNotFoundError(self.name, model)

                if response.status_code != 200:
                    raise LLMProviderError(
                        f"Gemini request failed: {response.text}",
                        provider=self.name,
                        status_code=response.status_code,
                        retryable=response.status_code >= 500,
                    )

                data = response.json()

                # Extract content from Gemini response
                candidates = data.get("candidates", [])
                if not candidates:
                    raise LLMProviderError(
                        "Gemini returned no candidates",
                        provider=self.name,
                    )

                content = ""
                candidate = candidates[0]
                parts = candidate.get("content", {}).get("parts", [])
                for part in parts:
                    if "text" in part:
                        content += part["text"]

                # Extract usage metadata
                usage_metadata = data.get("usageMetadata", {})

                return LLMResponse(
                    content=content,
                    model=model,
                    provider=self.name,
                    usage={
                        "input_tokens": usage_metadata.get("promptTokenCount", 0),
                        "output_tokens": usage_metadata.get("candidatesTokenCount", 0),
                    },
                    finish_reason=candidate.get("finishReason", "STOP"),
                    raw_response=data,
                )

        except httpx.TimeoutException:
            raise LLMProviderError(
                "Gemini request timed out",
                provider=self.name,
                retryable=True,
            )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from Gemini.

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

        # Convert messages to Gemini format
        contents, system_instruction = self._convert_messages_to_gemini(messages)

        # Build payload
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": config.temperature,
                "maxOutputTokens": config.max_tokens,
                "topP": config.top_p,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        if config.stop_sequences:
            payload["generationConfig"]["stopSequences"] = config.stop_sequences

        url = f"{self.BASE_URL}/models/{model}:streamGenerateContent"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    params={"key": self.api_key, "alt": "sse"},
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status_code == 401 or response.status_code == 403:
                        raise AuthenticationError(self.name)

                    if response.status_code == 429:
                        raise RateLimitError(self.name)

                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise LLMProviderError(
                            f"Gemini request failed: {error_text.decode()}",
                            provider=self.name,
                            status_code=response.status_code,
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                candidates = data.get("candidates", [])

                                if candidates:
                                    candidate = candidates[0]
                                    parts = candidate.get("content", {}).get("parts", [])
                                    content = ""
                                    for part in parts:
                                        if "text" in part:
                                            content += part["text"]

                                    finish_reason = candidate.get("finishReason")
                                    done = finish_reason is not None and finish_reason != "STOP"

                                    yield StreamChunk(
                                        content=content,
                                        done=done,
                                        model=model,
                                        provider=self.name,
                                    )

                            except json.JSONDecodeError:
                                continue

                    # Final chunk
                    yield StreamChunk(
                        content="",
                        done=True,
                        model=model,
                        provider=self.name,
                    )

        except httpx.TimeoutException:
            raise LLMProviderError(
                "Gemini request timed out",
                provider=self.name,
                retryable=True,
            )

    async def health_check(self) -> dict:
        """Perform health check including API status."""
        base_check = await super().health_check()
        base_check["api_key_set"] = bool(self.api_key)
        base_check["free_tier_limits"] = {
            "requests_per_minute": 15,
            "tokens_per_minute": 1_000_000,
        }
        base_check["features"] = {
            "max_context": "2M tokens (1.5 Pro)",
            "multimodal": True,
            "streaming": True,
        }
        return base_check
