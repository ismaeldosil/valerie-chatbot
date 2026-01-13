"""Base domain class for pluggable business domains.

This module provides the abstract base class that all business domains must implement.
A domain encapsulates:
- Domain-specific intents and entities
- State extensions for domain data
- Domain-specific agents and their configurations
- Graph nodes and routing logic
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from ...agents.base import BaseAgent


class DomainIntent(str, Enum):
    """Base class for domain-specific intents.

    Each domain should define its own Intent enum that inherits from this.
    Common intents that apply across all domains.
    """

    GREETING = "greeting"
    CLARIFICATION = "clarification"
    UNKNOWN = "unknown"


class DomainStateExtension(BaseModel):
    """Base class for domain-specific state extensions.

    Each domain can define additional state fields by subclassing this.
    The domain state is stored in ChatState.domain_data[domain_id].
    """

    pass


class DomainAgentConfig(BaseModel):
    """Configuration for a domain-specific agent."""

    agent_class: str
    name: str
    description: str
    handles_intents: list[str] = []
    requires_hitl: bool = False
    priority: int = 0  # Higher priority agents are tried first


class BaseDomain(ABC):
    """Abstract base class for business domains.

    Each business domain (suppliers, clients, inventory, etc.) should implement
    this class to plug into the Valerie chatbot platform.

    Example:
        class SupplierDomain(BaseDomain):
            domain_id = "supplier"
            display_name = "Supplier Management"

            def get_intent_enum(self) -> type[Enum]:
                return SupplierIntent

            def get_state_extension(self) -> type[DomainStateExtension]:
                return SupplierState

            # ... other implementations
    """

    # Domain identification
    domain_id: str = ""
    display_name: str = ""
    description: str = ""
    version: str = "1.0.0"

    # Domain capabilities
    supports_hitl: bool = True
    supports_streaming: bool = True
    requires_auth: bool = False

    def __init__(self) -> None:
        """Initialize the domain."""
        if not self.domain_id:
            raise ValueError("domain_id must be set in subclass")
        self._agents: dict[str, BaseAgent] = {}

    @abstractmethod
    def get_intent_enum(self) -> type[Enum]:
        """Return the enum class containing domain-specific intents.

        Returns:
            The Intent enum class for this domain.

        Example:
            def get_intent_enum(self) -> type[Enum]:
                return SupplierIntent
        """
        pass

    @abstractmethod
    def get_state_extension(self) -> type[DomainStateExtension]:
        """Return the Pydantic model for domain-specific state.

        This state extension will be stored in ChatState.domain_data[domain_id].

        Returns:
            The state extension class for this domain.
        """
        pass

    @abstractmethod
    def get_agent_configs(self) -> list[DomainAgentConfig]:
        """Return configuration for all domain-specific agents.

        Returns:
            List of agent configurations for this domain.
        """
        pass

    @abstractmethod
    def get_keywords(self) -> list[str]:
        """Return keywords that help identify this domain.

        These keywords are used by the DomainClassifier to route
        user queries to the appropriate domain.

        Returns:
            List of keywords associated with this domain.
        """
        pass

    @abstractmethod
    def get_example_queries(self) -> list[str]:
        """Return example queries for this domain.

        Used for domain classification training and help text.

        Returns:
            List of example user queries for this domain.
        """
        pass

    def get_intent_from_string(self, intent_str: str) -> Enum:
        """Convert a string to the domain's intent enum.

        Args:
            intent_str: The intent as a string.

        Returns:
            The corresponding intent enum value.

        Raises:
            ValueError: If the intent string is not valid for this domain.
        """
        intent_enum = self.get_intent_enum()
        try:
            return intent_enum(intent_str)
        except ValueError:
            # Try to find by name
            for member in intent_enum:
                if member.name.lower() == intent_str.lower():
                    return member
            # Fall back to UNKNOWN if available
            if hasattr(intent_enum, "UNKNOWN"):
                return intent_enum.UNKNOWN
            raise ValueError(f"Unknown intent '{intent_str}' for domain '{self.domain_id}'")

    def initialize_state_extension(self) -> DomainStateExtension:
        """Create a new instance of the domain state extension.

        Returns:
            A new instance of the domain's state extension.
        """
        state_class = self.get_state_extension()
        return state_class()

    def register_agent(self, agent: "BaseAgent") -> None:
        """Register an agent instance for this domain.

        Args:
            agent: The agent instance to register.
        """
        self._agents[agent.name] = agent

    def get_agent(self, name: str) -> "BaseAgent | None":
        """Get a registered agent by name.

        Args:
            name: The agent name.

        Returns:
            The agent instance or None if not found.
        """
        return self._agents.get(name)

    def get_all_agents(self) -> dict[str, "BaseAgent"]:
        """Get all registered agents.

        Returns:
            Dictionary of agent name to agent instance.
        """
        return self._agents.copy()

    def validate_intent(self, intent: str) -> bool:
        """Check if an intent is valid for this domain.

        Args:
            intent: The intent string to validate.

        Returns:
            True if the intent is valid for this domain.
        """
        intent_enum = self.get_intent_enum()
        try:
            intent_enum(intent)
            return True
        except ValueError:
            return False

    def get_routing_info(self) -> dict[str, Any]:
        """Get routing information for the graph builder.

        Returns:
            Dictionary with routing configuration for this domain.
        """
        return {
            "domain_id": self.domain_id,
            "intents": [e.value for e in self.get_intent_enum()],
            "keywords": self.get_keywords(),
            "agents": [cfg.name for cfg in self.get_agent_configs()],
        }

    def __repr__(self) -> str:
        """String representation of the domain."""
        return f"<{self.__class__.__name__} domain_id='{self.domain_id}'>"
