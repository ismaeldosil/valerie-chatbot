"""Base LLM Provider Interface.

Defines the abstract base class and common types for all LLM providers.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum


class MessageRole(str, Enum):
    """Message roles in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    """A single message in a conversation."""

    role: MessageRole
    content: str

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {"role": self.role.value, "content": self.content}


@dataclass
class LLMConfig:
    """Configuration for LLM generation."""

    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    stop_sequences: list[str] = field(default_factory=list)
    stream: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "stop_sequences": self.stop_sequences,
            "stream": self.stream,
        }


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    provider: str
    usage: dict = field(default_factory=dict)
    finish_reason: str = "stop"
    raw_response: dict = field(default_factory=dict)

    @property
    def input_tokens(self) -> int:
        """Get input token count."""
        return self.usage.get("input_tokens", 0)

    @property
    def output_tokens(self) -> int:
        """Get output token count."""
        return self.usage.get("output_tokens", 0)

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self.input_tokens + self.output_tokens


@dataclass
class StreamChunk:
    """A single chunk in a streaming response."""

    content: str
    done: bool = False
    model: str = ""
    provider: str = ""


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers must implement this interface to ensure
    consistent behavior across different backends.
    """

    def __init__(self, config: dict | None = None):
        """Initialize the provider.

        Args:
            config: Provider-specific configuration dictionary.
        """
        self.config = config or {}
        self._is_available: bool | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model for this provider."""
        pass

    @property
    def available_models(self) -> list[str]:
        """Return list of available models for this provider."""
        return [self.default_model]

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Returns:
            LLMResponse with the generated content.

        Raises:
            LLMProviderError: If generation fails.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from the LLM.

        Args:
            messages: List of messages in the conversation.
            config: Generation configuration.

        Yields:
            StreamChunk objects with partial content.

        Raises:
            LLMProviderError: If generation fails.
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is available and configured.

        Returns:
            True if the provider can be used, False otherwise.
        """
        pass

    async def health_check(self) -> dict:
        """Perform a health check on the provider.

        Returns:
            Dictionary with health status information.
        """
        try:
            is_available = await self.is_available()
            return {
                "provider": self.name,
                "available": is_available,
                "default_model": self.default_model,
                "models": self.available_models,
            }
        except Exception as e:
            return {
                "provider": self.name,
                "available": False,
                "error": str(e),
            }

    def _get_model(self, config: LLMConfig | None) -> str:
        """Get model from config or use default."""
        if config and config.model:
            return config.model
        return self.config.get("model", self.default_model)

    def _get_config(self, config: LLMConfig | None) -> LLMConfig:
        """Merge provided config with defaults."""
        if config is None:
            config = LLMConfig()
        if not config.model:
            config.model = self._get_model(None)
        return config


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(
        self,
        message: str,
        provider: str,
        status_code: int | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.retryable = retryable


class RateLimitError(LLMProviderError):
    """Raised when rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None):
        super().__init__(
            f"Rate limit exceeded for {provider}",
            provider=provider,
            status_code=429,
            retryable=True,
        )
        self.retry_after = retry_after


class AuthenticationError(LLMProviderError):
    """Raised when authentication fails."""

    def __init__(self, provider: str):
        super().__init__(
            f"Authentication failed for {provider}",
            provider=provider,
            status_code=401,
            retryable=False,
        )


class ModelNotFoundError(LLMProviderError):
    """Raised when the requested model is not available."""

    def __init__(self, provider: str, model: str):
        super().__init__(
            f"Model '{model}' not found for {provider}",
            provider=provider,
            status_code=404,
            retryable=False,
        )
        self.model = model
