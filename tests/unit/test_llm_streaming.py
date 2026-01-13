"""Tests for LLM provider streaming and additional methods."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from valerie.llm.anthropic import AnthropicProvider
from valerie.llm.base import (
    AuthenticationError,
    LLMConfig,
    LLMMessage,
    LLMProviderError,
    MessageRole,
)
from valerie.llm.groq import GroqProvider
from valerie.llm.ollama import OllamaProvider


class TestAnthropicProvider:
    """Additional tests for Anthropic provider."""

    @pytest.fixture
    def provider(self):
        return AnthropicProvider({"api_key": "test-key"})

    @pytest.fixture
    def messages(self):
        return [
            LLMMessage(role=MessageRole.SYSTEM, content="You are a test assistant"),
            LLMMessage(role=MessageRole.USER, content="Hello"),
        ]

    @pytest.mark.asyncio
    async def test_generate_stream_no_api_key(self, messages):
        provider = AnthropicProvider({})
        provider.api_key = None

        with pytest.raises(AuthenticationError):
            async for _ in provider.generate_stream(messages):
                pass

    @pytest.mark.asyncio
    async def test_generate_with_stop_sequences(self, provider, messages):
        config = LLMConfig(stop_sequences=["STOP", "END"])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Response"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await provider.generate(messages, config)

            # Check stop_sequences was included
            call_kwargs = mock_client.post.call_args
            payload = call_kwargs.kwargs["json"]
            assert payload["stop_sequences"] == ["STOP", "END"]

    @pytest.mark.asyncio
    async def test_generate_server_error(self, provider, messages):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMProviderError) as exc_info:
                await provider.generate(messages)

            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_is_available_cached(self, provider):
        provider._is_available = True
        result = await provider.is_available()
        assert result is True

    @pytest.mark.asyncio
    async def test_is_available_no_api_key(self):
        provider = AnthropicProvider({})
        provider.api_key = None
        result = await provider.is_available()
        assert result is False


class TestGroqProvider:
    """Additional tests for Groq provider."""

    @pytest.fixture
    def provider(self):
        return GroqProvider({"api_key": "test-key"})

    @pytest.fixture
    def messages(self):
        return [
            LLMMessage(role=MessageRole.SYSTEM, content="You are a test assistant"),
            LLMMessage(role=MessageRole.USER, content="Hello"),
        ]

    @pytest.mark.asyncio
    async def test_generate_stream_no_api_key(self, messages):
        provider = GroqProvider({})
        provider.api_key = None

        with pytest.raises(AuthenticationError):
            async for _ in provider.generate_stream(messages):
                pass

    @pytest.mark.asyncio
    async def test_generate_with_stop_sequences(self, provider, messages):
        config = LLMConfig(stop_sequences=["STOP"])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "llama-3.3-70b-versatile",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await provider.generate(messages, config)

            call_kwargs = mock_client.post.call_args
            payload = call_kwargs.kwargs["json"]
            assert payload["stop"] == ["STOP"]

    @pytest.mark.asyncio
    async def test_generate_server_error(self, provider, messages):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMProviderError) as exc_info:
                await provider.generate(messages)

            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_is_available_no_api_key(self):
        provider = GroqProvider({})
        provider.api_key = None
        result = await provider.is_available()
        assert result is False


class TestOllamaProvider:
    """Additional tests for Ollama provider."""

    @pytest.fixture
    def provider(self):
        return OllamaProvider({})

    @pytest.fixture
    def messages(self):
        return [
            LLMMessage(role=MessageRole.SYSTEM, content="You are a test assistant"),
            LLMMessage(role=MessageRole.USER, content="Hello"),
        ]

    @pytest.mark.asyncio
    async def test_is_available_cached_true(self, provider):
        provider._is_available = True
        result = await provider.is_available()
        assert result is True

    @pytest.mark.asyncio
    async def test_is_available_cached_false(self, provider):
        provider._is_available = False
        result = await provider.is_available()
        assert result is False

    @pytest.mark.asyncio
    async def test_is_available_connection_error(self, provider):
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await provider.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, provider, messages):
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMProviderError) as exc_info:
                await provider.generate(messages)

            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_generate_server_error(self, provider, messages):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMProviderError) as exc_info:
                await provider.generate(messages)

            assert exc_info.value.retryable is True
