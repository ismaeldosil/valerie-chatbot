"""Azure OpenAI LLM Provider.

Provides integration with Azure-hosted OpenAI services for enterprise compliance.
Azure OpenAI offers the same models as OpenAI but with enterprise-grade security,
compliance, data residency, and private network support.

Enterprise Features:
- Data residency and regional deployment
- Private networking via Azure Virtual Networks
- Compliance with GDPR, HIPAA, SOC 2
- SLA-backed uptime guarantees
- Content filtering and abuse monitoring

Configuration:
    AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint (required)
        Example: https://myresource.openai.azure.com
    AZURE_OPENAI_API_KEY: Your Azure OpenAI API key (required)
    AZURE_OPENAI_DEPLOYMENT: Default deployment name (required)
    AZURE_OPENAI_API_VERSION: API version (optional, default: 2024-02-15-preview)

Get started at: https://azure.microsoft.com/en-us/products/ai-services/openai-service
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


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI LLM Provider for enterprise-grade AI.

    Supported Models (via deployments):
    - gpt-4-turbo (recommended)
    - gpt-4
    - gpt-35-turbo
    - gpt-4o

    Features:
    - Enterprise compliance and security
    - Data residency and regional deployment
    - Private networking support
    - SLA-backed availability
    - OpenAI-compatible API with Azure authentication
    """

    DEFAULT_API_VERSION = "2024-02-15-preview"

    def __init__(self, config: dict | None = None):
        """Initialize Azure OpenAI provider.

        Args:
            config: Configuration dictionary with optional keys:
                - endpoint: Azure OpenAI endpoint URL (or use AZURE_OPENAI_ENDPOINT env var)
                - api_key: Azure OpenAI API key (or use AZURE_OPENAI_API_KEY env var)
                - deployment: Default deployment name (or use AZURE_OPENAI_DEPLOYMENT env var)
                - api_version: API version (or use AZURE_OPENAI_API_VERSION env var)
                - timeout: Request timeout in seconds (default: 60)
        """
        super().__init__(config)
        self.endpoint = (config.get("endpoint") if config else None) or os.getenv(
            "AZURE_OPENAI_ENDPOINT"
        )
        self.api_key = (config.get("api_key") if config else None) or os.getenv(
            "AZURE_OPENAI_API_KEY"
        )
        self.deployment = (config.get("deployment") if config else None) or os.getenv(
            "AZURE_OPENAI_DEPLOYMENT"
        )
        self.api_version = (config.get("api_version") if config else None) or os.getenv(
            "AZURE_OPENAI_API_VERSION", self.DEFAULT_API_VERSION
        )
        self.timeout = config.get("timeout", 60) if config else 60

        # Normalize endpoint - remove trailing slash
        if self.endpoint and self.endpoint.endswith("/"):
            self.endpoint = self.endpoint.rstrip("/")

    @property
    def name(self) -> str:
        """Return provider name."""
        return "azure_openai"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return "gpt-4-turbo"

    @property
    def available_models(self) -> list[str]:
        """Return list of available models."""
        return [
            "gpt-4-turbo",
            "gpt-4",
            "gpt-4o",
            "gpt-35-turbo",
        ]

    def _get_chat_url(self, deployment: str) -> str:
        """Construct Azure OpenAI chat completions URL.

        Args:
            deployment: The deployment name to use.

        Returns:
            Full URL for chat completions endpoint.
        """
        return (
            f"{self.endpoint}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )

    async def is_available(self) -> bool:
        """Check if Azure OpenAI API is accessible."""
        if self._is_available is not None:
            return self._is_available

        if not self.endpoint or not self.api_key or not self.deployment:
            logger.debug("Azure OpenAI not available: missing endpoint, api_key, or deployment")
            self._is_available = False
            return False

        try:
            # Test with a minimal request
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    self._get_chat_url(self.deployment),
                    headers={
                        "api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 1,
                    },
                )
                # Accept both 200 and 400 (bad request) as signs the endpoint is available
                # 401 would mean auth failed, 404 would mean deployment not found
                self._is_available = response.status_code in (200, 400)
                return self._is_available
        except Exception as e:
            logger.debug(f"Azure OpenAI not available: {e}")
            self._is_available = False
            return False

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Generate a response from Azure OpenAI.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Returns:
            LLMResponse with the generated content.

        Raises:
            AuthenticationError: If API key is invalid.
            ModelNotFoundError: If deployment is not found.
            RateLimitError: If quota is exceeded.
            LLMProviderError: For other API errors.
        """
        if not self.api_key or not self.endpoint or not self.deployment:
            raise AuthenticationError(self.name)

        config = self._get_config(config)
        # In Azure OpenAI, deployment name is used instead of model
        deployment = self.deployment

        # Convert messages to OpenAI format (Azure uses OpenAI-compatible API)
        openai_messages = [msg.to_dict() for msg in messages]

        payload = {
            "messages": openai_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": False,
        }

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self._get_chat_url(deployment),
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise AuthenticationError(self.name)

                if response.status_code == 404:
                    raise ModelNotFoundError(self.name, deployment)

                if response.status_code == 429:
                    retry_after = response.headers.get("retry-after")
                    raise RateLimitError(
                        self.name,
                        retry_after=int(retry_after) if retry_after else None,
                    )

                if response.status_code != 200:
                    error_message = response.text
                    # Azure-specific error handling
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error_message = error_data["error"].get("message", error_message)
                    except Exception:
                        pass

                    raise LLMProviderError(
                        f"Azure OpenAI request failed: {error_message}",
                        provider=self.name,
                        status_code=response.status_code,
                        retryable=response.status_code >= 500,
                    )

                data = response.json()
                choice = data.get("choices", [{}])[0]

                return LLMResponse(
                    content=choice.get("message", {}).get("content", ""),
                    model=config.model or self.default_model,
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
                "Azure OpenAI request timed out",
                provider=self.name,
                retryable=True,
            )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from Azure OpenAI.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Yields:
            StreamChunk objects with partial content.

        Raises:
            AuthenticationError: If API key is invalid.
            ModelNotFoundError: If deployment is not found.
            RateLimitError: If quota is exceeded.
            LLMProviderError: For other API errors.
        """
        if not self.api_key or not self.endpoint or not self.deployment:
            raise AuthenticationError(self.name)

        config = self._get_config(config)
        deployment = self.deployment

        # Convert messages to OpenAI format
        openai_messages = [msg.to_dict() for msg in messages]

        payload = {
            "messages": openai_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": True,
        }

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self._get_chat_url(deployment),
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status_code == 401:
                        raise AuthenticationError(self.name)

                    if response.status_code == 404:
                        raise ModelNotFoundError(self.name, deployment)

                    if response.status_code == 429:
                        raise RateLimitError(self.name)

                    if response.status_code != 200:
                        error_text = await response.aread()
                        error_message = error_text.decode()
                        # Try to parse Azure error format
                        try:
                            error_data = json.loads(error_message)
                            if "error" in error_data:
                                error_message = error_data["error"].get("message", error_message)
                        except Exception:
                            pass

                        raise LLMProviderError(
                            f"Azure OpenAI request failed: {error_message}",
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
                                    model=config.model or self.default_model,
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
                                    model=config.model or self.default_model,
                                    provider=self.name,
                                )
                            except json.JSONDecodeError:
                                continue

        except httpx.TimeoutException:
            raise LLMProviderError(
                "Azure OpenAI request timed out",
                provider=self.name,
                retryable=True,
            )

    async def health_check(self) -> dict:
        """Perform health check including API configuration status."""
        base_check = await super().health_check()
        base_check["endpoint_set"] = bool(self.endpoint)
        base_check["api_key_set"] = bool(self.api_key)
        base_check["deployment_set"] = bool(self.deployment)
        base_check["api_version"] = self.api_version
        base_check["enterprise_features"] = [
            "Data residency",
            "Private networking",
            "GDPR/HIPAA compliance",
            "SLA-backed uptime",
            "Content filtering",
        ]
        return base_check
