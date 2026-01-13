"""LLM Provider Abstraction Layer.

Provides a unified interface for multiple LLM providers:
- Ollama (local, free)
- LightLLM (local/on-premise GPU cluster, free)
- Groq (cloud, free tier)
- Google Gemini (cloud, free tier available)
- Anthropic Claude (cloud, paid)
- AWS Bedrock (cloud, paid)
- Azure OpenAI (cloud, paid)

Usage:
    from valerie.llm import get_llm_provider

    provider = get_llm_provider()  # Uses default from config
    response = await provider.generate("Hello, world!")
"""

from valerie.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
)
from valerie.llm.factory import (
    ProviderType,
    get_available_providers,
    get_llm_provider,
)

__all__ = [
    "BaseLLMProvider",
    "LLMResponse",
    "LLMMessage",
    "LLMConfig",
    "get_llm_provider",
    "get_available_providers",
    "ProviderType",
]
