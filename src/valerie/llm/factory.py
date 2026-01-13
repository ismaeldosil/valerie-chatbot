"""LLM Provider Factory.

Provides a unified interface for creating and switching between LLM providers.
Supports automatic fallback to alternative providers when the primary is unavailable.

Configuration:
    VALERIE_LLM_PROVIDER: Default provider (ollama, groq, anthropic)
    VALERIE_LLM_FALLBACK: Fallback chain (comma-separated, e.g., "groq,anthropic")

Usage:
    from valerie.llm import get_llm_provider

    # Get default provider
    provider = get_llm_provider()

    # Get specific provider
    provider = get_llm_provider("ollama")

    # Generate response
    response = await provider.generate(messages)
"""

import logging
import os
from enum import Enum

from valerie.llm.anthropic import AnthropicProvider
from valerie.llm.azure_openai import AzureOpenAIProvider
from valerie.llm.base import (
    BaseLLMProvider,
    LLMProviderError,
)
from valerie.llm.bedrock import BedrockProvider
from valerie.llm.gemini import GeminiProvider
from valerie.llm.groq import GroqProvider
from valerie.llm.lightllm import LightLLMProvider
from valerie.llm.ollama import OllamaProvider

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Available LLM providers."""

    OLLAMA = "ollama"
    GROQ = "groq"
    GEMINI = "gemini"
    LIGHTLLM = "lightllm"
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    AZURE_OPENAI = "azure_openai"


# Provider registry
PROVIDERS: dict[ProviderType, type[BaseLLMProvider]] = {
    ProviderType.OLLAMA: OllamaProvider,
    ProviderType.GROQ: GroqProvider,
    ProviderType.GEMINI: GeminiProvider,
    ProviderType.LIGHTLLM: LightLLMProvider,
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.BEDROCK: BedrockProvider,
    ProviderType.AZURE_OPENAI: AzureOpenAIProvider,
}

# Default fallback chain (free → paid, local → cloud)
DEFAULT_FALLBACK_CHAIN = [
    ProviderType.OLLAMA,
    ProviderType.LIGHTLLM,
    ProviderType.GROQ,
    ProviderType.GEMINI,
    ProviderType.ANTHROPIC,
    ProviderType.BEDROCK,
    ProviderType.AZURE_OPENAI,
]

# Singleton instances
_provider_instances: dict[ProviderType, BaseLLMProvider] = {}


def get_available_providers() -> list[ProviderType]:
    """Return list of available provider types."""
    return list(ProviderType)


def _get_default_provider() -> ProviderType:
    """Get the default provider from environment or config."""
    provider_name = os.getenv("VALERIE_LLM_PROVIDER", "ollama").lower()
    try:
        return ProviderType(provider_name)
    except ValueError:
        logger.warning(f"Unknown provider '{provider_name}', using ollama")
        return ProviderType.OLLAMA


def _get_fallback_chain() -> list[ProviderType]:
    """Get the fallback chain from environment or config."""
    fallback_env = os.getenv("VALERIE_LLM_FALLBACK", "")
    if fallback_env:
        chain = []
        for name in fallback_env.split(","):
            name = name.strip().lower()
            try:
                chain.append(ProviderType(name))
            except ValueError:
                logger.warning(f"Unknown provider in fallback chain: {name}")
        return chain if chain else DEFAULT_FALLBACK_CHAIN
    return DEFAULT_FALLBACK_CHAIN


def get_llm_provider(
    provider_type: ProviderType | str | None = None,
    config: dict | None = None,
    use_fallback: bool = True,
) -> BaseLLMProvider:
    """Get an LLM provider instance.

    Args:
        provider_type: The type of provider to get. If None, uses default.
        config: Optional configuration for the provider.
        use_fallback: If True and the requested provider is unavailable,
                     try to find an available alternative.

    Returns:
        An initialized LLM provider instance.

    Raises:
        LLMProviderError: If no provider is available.

    Example:
        # Get default provider (tries ollama first, then groq, then anthropic)
        provider = get_llm_provider()

        # Get specific provider
        provider = get_llm_provider("groq")

        # Get with custom config
        provider = get_llm_provider("ollama", config={"model": "llama3.2:70b"})
    """
    # Determine provider type
    if provider_type is None:
        provider_type = _get_default_provider()
    elif isinstance(provider_type, str):
        try:
            provider_type = ProviderType(provider_type.lower())
        except ValueError:
            raise LLMProviderError(
                f"Unknown provider: {provider_type}",
                provider=provider_type,
            )

    # Check if we have a cached instance (only if no custom config)
    if config is None and provider_type in _provider_instances:
        return _provider_instances[provider_type]

    # Create provider instance
    provider_class = PROVIDERS.get(provider_type)
    if not provider_class:
        raise LLMProviderError(
            f"Provider not implemented: {provider_type}",
            provider=str(provider_type),
        )

    provider = provider_class(config)

    # Cache if no custom config
    if config is None:
        _provider_instances[provider_type] = provider

    return provider


async def get_available_provider(
    preferred: ProviderType | str | None = None,
) -> BaseLLMProvider:
    """Get the first available provider from the fallback chain.

    Args:
        preferred: Preferred provider to try first.

    Returns:
        An available LLM provider instance.

    Raises:
        LLMProviderError: If no provider is available.
    """
    # Build the chain to try
    chain = _get_fallback_chain()
    if preferred:
        if isinstance(preferred, str):
            try:
                preferred = ProviderType(preferred.lower())
            except ValueError:
                pass
        if isinstance(preferred, ProviderType) and preferred not in chain:
            chain = [preferred] + chain
        elif isinstance(preferred, ProviderType):
            chain.remove(preferred)
            chain = [preferred] + chain

    # Try each provider in chain
    for provider_type in chain:
        try:
            provider = get_llm_provider(provider_type)
            if await provider.is_available():
                logger.info(f"Using LLM provider: {provider.name}")
                return provider
            else:
                logger.debug(f"Provider {provider.name} not available, trying next")
        except Exception as e:
            logger.debug(f"Error with provider {provider_type}: {e}")
            continue

    raise LLMProviderError(
        "No LLM provider available. Please configure one of: "
        "Ollama (local), Groq (free API key), or Anthropic (paid API key)",
        provider="none",
    )


async def health_check_all() -> dict[str, dict]:
    """Perform health check on all providers.

    Returns:
        Dictionary mapping provider names to their health status.
    """
    results = {}
    for provider_type in ProviderType:
        try:
            provider = get_llm_provider(provider_type)
            results[provider_type.value] = await provider.health_check()
        except Exception as e:
            results[provider_type.value] = {
                "available": False,
                "error": str(e),
            }
    return results


def clear_provider_cache() -> None:
    """Clear cached provider instances."""
    _provider_instances.clear()


# Convenience function for quick generation
async def generate(
    prompt: str,
    system_prompt: str | None = None,
    provider: ProviderType | str | None = None,
    **kwargs,
) -> str:
    """Quick generation helper.

    Args:
        prompt: The user prompt.
        system_prompt: Optional system prompt.
        provider: Optional provider to use.
        **kwargs: Additional generation parameters.

    Returns:
        Generated text content.

    Example:
        response = await generate("Explain quantum computing")
    """
    from valerie.llm.base import LLMConfig, LLMMessage, MessageRole

    messages = []
    if system_prompt:
        messages.append(LLMMessage(role=MessageRole.SYSTEM, content=system_prompt))
    messages.append(LLMMessage(role=MessageRole.USER, content=prompt))

    llm = await get_available_provider(provider)
    config = LLMConfig(**kwargs) if kwargs else None
    response = await llm.generate(messages, config)
    return response.content
