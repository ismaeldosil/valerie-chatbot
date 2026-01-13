"""Base agent class for all chatbot agents."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..llm import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    get_llm_provider,
)
from ..llm.base import MessageRole
from ..models import AgentOutput, ChatState, Settings, get_settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the system.

    Supports both LangChain (legacy) and the new multi-LLM provider abstraction.
    Set use_provider=True in subclass to use the new provider system.
    """

    name: str = "base_agent"
    use_provider: bool = False  # Set to True to use new LLM provider abstraction

    def __init__(self, settings: Settings | None = None):
        """Initialize the agent."""
        self.settings = settings or get_settings()
        self._llm: ChatAnthropic | None = None
        self._provider: BaseLLMProvider | None = None

    @property
    def llm(self) -> ChatAnthropic:
        """Get the LangChain LLM instance (lazy initialization)."""
        if self._llm is None:
            self._llm = ChatAnthropic(
                model=self.settings.model_name,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                api_key=self.settings.anthropic_api_key,
            )
        return self._llm

    @property
    def provider(self) -> BaseLLMProvider:
        """Get the LLM provider instance (lazy initialization)."""
        if self._provider is None:
            self._provider = get_llm_provider()
        return self._provider

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        pass

    @abstractmethod
    async def process(self, state: ChatState) -> ChatState:
        """Process the state and return updated state."""
        pass

    def create_output(
        self,
        success: bool,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        confidence: float = 1.0,
        start_time: datetime | None = None,
    ) -> AgentOutput:
        """Create a standardized agent output."""
        processing_time = 0
        if start_time:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return AgentOutput(
            agent_name=self.name,
            success=success,
            data=data or {},
            error=error,
            confidence=confidence,
            processing_time_ms=processing_time,
        )

    async def invoke_llm(
        self,
        user_message: str,
        system_prompt: str | None = None,
        context: list[Any] | None = None,
    ) -> str:
        """Invoke the LLM with a message.

        Uses either LangChain (legacy) or the new provider abstraction
        based on the use_provider flag.
        """
        if self.use_provider:
            return await self._invoke_provider(user_message, system_prompt, context)
        else:
            return await self._invoke_langchain(user_message, system_prompt, context)

    async def _invoke_langchain(
        self,
        user_message: str,
        system_prompt: str | None = None,
        context: list[Any] | None = None,
    ) -> str:
        """Invoke using LangChain (legacy method)."""
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        else:
            messages.append(SystemMessage(content=self.get_system_prompt()))

        if context:
            for msg in context:
                if isinstance(msg, HumanMessage | AIMessage | SystemMessage):
                    messages.append(msg)

        messages.append(HumanMessage(content=user_message))

        response = await self.llm.ainvoke(messages)
        return str(response.content)

    async def _invoke_provider(
        self,
        user_message: str,
        system_prompt: str | None = None,
        context: list[Any] | None = None,
    ) -> str:
        """Invoke using the new LLM provider abstraction."""
        messages: list[LLMMessage] = []

        # Add system prompt
        prompt = system_prompt or self.get_system_prompt()
        messages.append(LLMMessage(role=MessageRole.SYSTEM, content=prompt))

        # Add context messages
        if context:
            for msg in context:
                if isinstance(msg, SystemMessage):
                    # Skip system messages in context (already added)
                    continue
                elif isinstance(msg, HumanMessage):
                    messages.append(LLMMessage(role=MessageRole.USER, content=str(msg.content)))
                elif isinstance(msg, AIMessage):
                    messages.append(
                        LLMMessage(role=MessageRole.ASSISTANT, content=str(msg.content))
                    )

        # Add user message
        messages.append(LLMMessage(role=MessageRole.USER, content=user_message))

        # Create config
        config = LLMConfig(
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
        )

        # Generate response
        try:
            response = await self.provider.generate(messages, config)
            logger.debug(
                f"Agent {self.name} used provider {response.provider} "
                f"(model: {response.model}, tokens: {response.total_tokens})"
            )
            return response.content
        except Exception as e:
            logger.error(f"Agent {self.name} LLM error: {e}")
            raise
