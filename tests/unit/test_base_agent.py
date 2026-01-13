"""Tests for base agent class."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from valerie.agents.base import BaseAgent
from valerie.llm.base import MessageRole
from valerie.models import ChatState, Settings


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    name = "test_agent"
    use_provider = False

    def get_system_prompt(self) -> str:
        return "You are a test agent."

    async def process(self, state: ChatState) -> ChatState:
        return state


class ConcreteProviderAgent(BaseAgent):
    """Concrete agent that uses the LLM provider abstraction."""

    name = "test_provider_agent"
    use_provider = True

    def get_system_prompt(self) -> str:
        return "You are a provider-based test agent."

    async def process(self, state: ChatState) -> ChatState:
        return state


class TestBaseAgentInit:
    """Tests for BaseAgent initialization."""

    def test_init_with_default_settings(self):
        agent = ConcreteAgent()
        assert agent.settings is not None
        assert agent._llm is None
        assert agent._provider is None

    def test_init_with_custom_settings(self):
        settings = Settings(anthropic_api_key="test-key", model_name="custom-model")
        agent = ConcreteAgent(settings=settings)
        assert agent.settings.model_name == "custom-model"


class TestBaseAgentLLMProperty:
    """Tests for the llm property (LangChain lazy initialization)."""

    def test_llm_lazy_initialization(self):
        settings = Settings(anthropic_api_key="test-key")
        agent = ConcreteAgent(settings=settings)

        with patch("valerie.agents.base.ChatAnthropic") as mock_anthropic:
            mock_llm = MagicMock()
            mock_anthropic.return_value = mock_llm

            # First access should initialize
            result = agent.llm
            assert mock_anthropic.called
            assert result == mock_llm

            # Second access should return same instance
            mock_anthropic.reset_mock()
            result2 = agent.llm
            assert not mock_anthropic.called
            assert result2 == mock_llm


class TestBaseAgentProviderProperty:
    """Tests for the provider property."""

    def test_provider_lazy_initialization(self):
        agent = ConcreteAgent()

        with patch("valerie.agents.base.get_llm_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider

            # First access should initialize
            result = agent.provider
            assert mock_get_provider.called
            assert result == mock_provider

            # Second access should return same instance
            mock_get_provider.reset_mock()
            result2 = agent.provider
            assert not mock_get_provider.called
            assert result2 == mock_provider


class TestBaseAgentCreateOutput:
    """Tests for create_output method."""

    def test_create_output_success(self):
        agent = ConcreteAgent()
        output = agent.create_output(success=True, data={"key": "value"})

        assert output.agent_name == "test_agent"
        assert output.success is True
        assert output.data == {"key": "value"}
        assert output.error is None
        assert output.confidence == 1.0

    def test_create_output_failure(self):
        agent = ConcreteAgent()
        output = agent.create_output(success=False, error="Test error", confidence=0.5)

        assert output.success is False
        assert output.error == "Test error"
        assert output.confidence == 0.5

    def test_create_output_with_start_time(self):
        agent = ConcreteAgent()
        start_time = datetime.now() - timedelta(milliseconds=150)
        output = agent.create_output(success=True, start_time=start_time)

        # Processing time should be approximately 150ms
        assert output.processing_time_ms >= 100
        assert output.processing_time_ms < 500

    def test_create_output_no_start_time(self):
        agent = ConcreteAgent()
        output = agent.create_output(success=True)
        assert output.processing_time_ms == 0

    def test_create_output_empty_data(self):
        agent = ConcreteAgent()
        output = agent.create_output(success=True)
        assert output.data == {}


class TestBaseAgentInvokeLLM:
    """Tests for invoke_llm and related methods."""

    @pytest.mark.asyncio
    async def test_invoke_llm_uses_langchain_by_default(self):
        agent = ConcreteAgent()
        agent.use_provider = False

        with patch.object(agent, "_invoke_langchain", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = "langchain response"
            result = await agent.invoke_llm("Hello")

            mock_invoke.assert_called_once_with("Hello", None, None)
            assert result == "langchain response"

    @pytest.mark.asyncio
    async def test_invoke_llm_uses_provider_when_enabled(self):
        agent = ConcreteProviderAgent()

        with patch.object(agent, "_invoke_provider", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = "provider response"
            result = await agent.invoke_llm("Hello")

            mock_invoke.assert_called_once_with("Hello", None, None)
            assert result == "provider response"


class TestBaseAgentInvokeLangchain:
    """Tests for _invoke_langchain method."""

    @pytest.mark.asyncio
    async def test_invoke_langchain_basic(self):
        settings = Settings(anthropic_api_key="test-key")
        agent = ConcreteAgent(settings=settings)

        mock_response = MagicMock()
        mock_response.content = "LLM response"

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        agent._llm = mock_llm

        result = await agent._invoke_langchain("Hello")
        assert result == "LLM response"

    @pytest.mark.asyncio
    async def test_invoke_langchain_with_custom_prompt(self):
        settings = Settings(anthropic_api_key="test-key")
        agent = ConcreteAgent(settings=settings)

        mock_response = MagicMock()
        mock_response.content = "Response"

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        agent._llm = mock_llm

        await agent._invoke_langchain("Hello", system_prompt="Custom prompt")
        call_args = mock_llm.ainvoke.call_args[0][0]

        # Check that custom system prompt was used
        assert isinstance(call_args[0], SystemMessage)
        assert call_args[0].content == "Custom prompt"

    @pytest.mark.asyncio
    async def test_invoke_langchain_with_context(self):
        settings = Settings(anthropic_api_key="test-key")
        agent = ConcreteAgent(settings=settings)

        mock_response = MagicMock()
        mock_response.content = "Response"

        context = [
            HumanMessage(content="Previous question"),
            AIMessage(content="Previous answer"),
        ]

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        agent._llm = mock_llm

        await agent._invoke_langchain("Hello", context=context)
        call_args = mock_llm.ainvoke.call_args[0][0]

        # System + 2 context + user = 4 messages
        assert len(call_args) == 4
        assert isinstance(call_args[1], HumanMessage)
        assert isinstance(call_args[2], AIMessage)


class TestBaseAgentInvokeProvider:
    """Tests for _invoke_provider method."""

    @pytest.mark.asyncio
    async def test_invoke_provider_basic(self):
        agent = ConcreteProviderAgent()

        mock_response = MagicMock()
        mock_response.content = "Provider response"
        mock_response.provider = "test"
        mock_response.model = "test-model"
        mock_response.total_tokens = 100

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = mock_response
        agent._provider = mock_provider

        result = await agent._invoke_provider("Hello")
        assert result == "Provider response"

    @pytest.mark.asyncio
    async def test_invoke_provider_with_custom_prompt(self):
        agent = ConcreteProviderAgent()

        mock_response = MagicMock()
        mock_response.content = "Response"
        mock_response.provider = "test"
        mock_response.model = "test-model"
        mock_response.total_tokens = 50

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = mock_response
        agent._provider = mock_provider

        await agent._invoke_provider("Hello", system_prompt="Custom system")
        call_args = mock_provider.generate.call_args[0][0]

        # Check system message has custom prompt
        assert call_args[0].role == MessageRole.SYSTEM
        assert call_args[0].content == "Custom system"

    @pytest.mark.asyncio
    async def test_invoke_provider_with_context(self):
        agent = ConcreteProviderAgent()

        mock_response = MagicMock()
        mock_response.content = "Response"
        mock_response.provider = "test"
        mock_response.model = "test-model"
        mock_response.total_tokens = 75

        context = [
            SystemMessage(content="Ignored system"),
            HumanMessage(content="User question"),
            AIMessage(content="Assistant answer"),
        ]

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = mock_response
        agent._provider = mock_provider

        await agent._invoke_provider("New question", context=context)
        call_args = mock_provider.generate.call_args[0][0]

        # System + user context + assistant context + new user = 4
        # (system from context is skipped)
        assert len(call_args) == 4
        assert call_args[0].role == MessageRole.SYSTEM
        assert call_args[1].role == MessageRole.USER
        assert call_args[2].role == MessageRole.ASSISTANT
        assert call_args[3].role == MessageRole.USER

    @pytest.mark.asyncio
    async def test_invoke_provider_error(self):
        agent = ConcreteProviderAgent()

        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = Exception("Provider error")
        agent._provider = mock_provider

        with pytest.raises(Exception, match="Provider error"):
            await agent._invoke_provider("Hello")


class TestBaseAgentSystemPrompt:
    """Tests for system prompt functionality."""

    def test_get_system_prompt(self):
        agent = ConcreteAgent()
        assert agent.get_system_prompt() == "You are a test agent."

    def test_provider_agent_system_prompt(self):
        agent = ConcreteProviderAgent()
        assert agent.get_system_prompt() == "You are a provider-based test agent."


class TestBaseAgentProcess:
    """Tests for process method."""

    @pytest.mark.asyncio
    async def test_process_returns_state(self):
        agent = ConcreteAgent()
        state = ChatState()
        result = await agent.process(state)
        assert result is state
