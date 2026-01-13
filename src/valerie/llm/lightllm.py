"""LightLLM Provider.

Provides integration with LightLLM, a high-performance LLM inference framework
designed for GPU clusters with tensor parallelism and continuous batching.

LightLLM is optimized for:
- Multi-GPU deployment with tensor parallelism
- High throughput via continuous batching (unlike static batching)
- Low latency inference for large models (70B+)
- Efficient KV cache management for long contexts

The framework provides an OpenAI-compatible REST API, making it easy to
integrate with existing applications while benefiting from superior performance
on GPU infrastructure.

Configuration:
    VALERIE_LIGHTLLM_BASE_URL: LightLLM server URL (default: http://localhost:8080)
    VALERIE_LIGHTLLM_API_KEY: API key for secured deployments (optional)
    VALERIE_LIGHTLLM_MODEL: Default model name (default: llama-70b)

Typical deployment:
    # Start LightLLM server
    python -m lightllm.server.api_server \\
        --model_dir /path/to/llama-70b \\
        --host 0.0.0.0 \\
        --port 8080 \\
        --tp 4  # tensor parallelism across 4 GPUs
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


class LightLLMProvider(BaseLLMProvider):
    """LightLLM Provider for high-performance GPU inference.

    LightLLM is a Python-based LLM inference framework optimized for:
    - Tensor parallelism across multiple GPUs
    - Continuous batching for high throughput
    - Efficient memory management with PagedAttention
    - Support for large models (70B, 180B+)

    Features:
    - OpenAI-compatible API
    - Streaming support
    - No API key required for local deployments
    - Ideal for on-premise GPU clusters

    Supported Models (depends on server configuration):
    - LLaMA family (7B, 13B, 70B)
    - Mistral (7B, 8x7B)
    - Yi (6B, 34B)
    - Custom models loaded by the server
    """

    DEFAULT_BASE_URL = "http://localhost:8080"

    def __init__(self, config: dict | None = None):
        """Initialize LightLLM provider.

        Args:
            config: Configuration dictionary with optional keys:
                - base_url: LightLLM server URL (or use VALERIE_LIGHTLLM_BASE_URL env var)
                - api_key: API key for secured deployments (or use VALERIE_LIGHTLLM_API_KEY env var)
                - model: Default model name (or use VALERIE_LIGHTLLM_MODEL env var)
                - timeout: Request timeout in seconds (default: 120)
        """
        super().__init__(config)
        self.base_url = (
            (config.get("base_url") if config else None)
            or os.getenv("VALERIE_LIGHTLLM_BASE_URL")
            or self.DEFAULT_BASE_URL
        ).rstrip("/")

        self.api_key = (config.get("api_key") if config else None) or os.getenv(
            "VALERIE_LIGHTLLM_API_KEY"
        )

        self._default_model = (config.get("model") if config else None) or os.getenv(
            "VALERIE_LIGHTLLM_MODEL", "llama-70b"
        )

        self.timeout = config.get("timeout", 120) if config else 120

    @property
    def name(self) -> str:
        """Return provider name."""
        return "lightllm"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return self._default_model

    @property
    def available_models(self) -> list[str]:
        """Return list of available models.

        Note: The actual available models depend on what's loaded on the
        LightLLM server. This returns the default model as a placeholder.
        """
        return [self.default_model]

    async def is_available(self) -> bool:
        """Check if LightLLM server is accessible.

        Returns:
            True if the server is reachable and responding, False otherwise.
        """
        if self._is_available is not None:
            return self._is_available

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Try to reach the server's health endpoint or base URL
                response = await client.get(
                    f"{self.base_url}/v1/models",
                    headers=self._get_headers(),
                )
                self._is_available = response.status_code == 200
                return self._is_available
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.debug(f"LightLLM not available: {e}")
            self._is_available = False
            return False
        except Exception as e:
            logger.debug(f"LightLLM availability check failed: {e}")
            self._is_available = False
            return False

    def _get_headers(self) -> dict:
        """Build request headers.

        Returns:
            Dictionary of HTTP headers including authentication if configured.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Generate a response from LightLLM.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Returns:
            LLMResponse with the generated content.

        Raises:
            AuthenticationError: If API key is required but invalid.
            ModelNotFoundError: If the requested model is not available.
            LLMProviderError: If the request fails.
        """
        config = self._get_config(config)
        model = self._get_model(config)

        # Convert messages to OpenAI format (LightLLM uses OpenAI-compatible API)
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

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=self._get_headers(),
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
                        f"LightLLM request failed: {response.text}",
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

        except httpx.ConnectError:
            raise LLMProviderError(
                f"Failed to connect to LightLLM server at {self.base_url}. "
                "Ensure the server is running and accessible.",
                provider=self.name,
                retryable=True,
            )
        except httpx.TimeoutException:
            raise LLMProviderError(
                f"LightLLM request timed out after {self.timeout}s",
                provider=self.name,
                retryable=True,
            )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from LightLLM.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Yields:
            StreamChunk objects with partial content.

        Raises:
            AuthenticationError: If API key is required but invalid.
            ModelNotFoundError: If the requested model is not available.
            LLMProviderError: If the request fails.
        """
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

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=self._get_headers(),
                ) as response:
                    if response.status_code == 401:
                        raise AuthenticationError(self.name)

                    if response.status_code == 429:
                        raise RateLimitError(self.name)

                    if response.status_code == 404:
                        raise ModelNotFoundError(self.name, model)

                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise LLMProviderError(
                            f"LightLLM request failed: {error_text.decode()}",
                            provider=self.name,
                            status_code=response.status_code,
                        )

                    # Parse Server-Sent Events (SSE) stream
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
                                # Skip malformed JSON lines
                                continue

        except httpx.ConnectError:
            raise LLMProviderError(
                f"Failed to connect to LightLLM server at {self.base_url}. "
                "Ensure the server is running and accessible.",
                provider=self.name,
                retryable=True,
            )
        except httpx.TimeoutException:
            raise LLMProviderError(
                f"LightLLM request timed out after {self.timeout}s",
                provider=self.name,
                retryable=True,
            )

    async def health_check(self) -> dict:
        """Perform health check including server connectivity."""
        base_check = await super().health_check()
        base_check["base_url"] = self.base_url
        base_check["api_key_set"] = bool(self.api_key)
        base_check["timeout"] = self.timeout

        # Try to get model info if available
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/v1/models",
                    headers=self._get_headers(),
                )
                if response.status_code == 200:
                    models_data = response.json()
                    base_check["server_models"] = models_data.get("data", [])
        except Exception as e:
            logger.debug(f"Could not fetch models from LightLLM: {e}")

        return base_check
