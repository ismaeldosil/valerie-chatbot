"""Core state that is shared across all domains.

This module defines the domain-agnostic state that every domain uses.
Domain-specific state is stored in the domain_data field.
"""

from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field


class AgentOutput(BaseModel):
    """Standard output from any agent."""

    agent_name: str
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    confidence: float = 1.0
    processing_time_ms: int = 0


class HITLRequest(BaseModel):
    """Human-in-the-loop request."""

    request_type: str  # approval_required, review_request, escalation
    priority: str = "normal"  # low, normal, high, urgent, critical
    context: dict[str, Any] = Field(default_factory=dict)
    decision_options: list[dict[str, Any]] = Field(default_factory=list)
    timeout_ms: int = 86400000  # 24 hours default


class CoreState(BaseModel):
    """Core state that is shared across all domains.

    This state contains only domain-agnostic fields that every
    domain needs. Domain-specific data is stored in domain_data.

    Fields:
        messages: Conversation history (LangGraph annotated)
        session_id: Unique session identifier
        user_id: Optional user identifier
        user_role: User's role for access control

        current_domain: ID of the active domain
        intent: Current intent (string, domain interprets it)
        entities: Extracted entities from user input
        confidence: Intent classification confidence

        domain_data: Domain-specific state extensions
        agent_outputs: Outputs from executed agents

        guardrails_passed: Whether content passed safety checks
        guardrails_warnings: Any warnings from guardrails
        pii_detected: Whether PII was detected
        requires_human_approval: Whether HITL is needed
        hitl_request: Pending HITL request
        hitl_decision: HITL decision result

        final_response: Generated response to user
        response_type: Type of response (text, table, etc.)
        error: Error message if any
        degraded_mode: Whether running in degraded mode

        trace_id: Observability trace ID
        span_id: Current span ID
        evaluation_score: Quality evaluation score
        evaluation_feedback: Detailed evaluation feedback
    """

    # Core conversation
    messages: Annotated[list[Any], add_messages] = Field(default_factory=list)
    session_id: str = ""
    user_id: str | None = None
    user_role: str = "standard_user"

    # Domain routing
    current_domain: str | None = None

    # Intent and entities (domain-agnostic representation)
    intent: str = "unknown"
    entities: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0

    # Domain-specific state extensions
    # Key is domain_id, value is serialized domain state
    domain_data: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Agent outputs
    agent_outputs: dict[str, AgentOutput] = Field(default_factory=dict)

    # Infrastructure flags (shared across domains)
    guardrails_passed: bool = True
    guardrails_warnings: list[str] = Field(default_factory=list)
    pii_detected: bool = False

    # HITL
    requires_human_approval: bool = False
    hitl_request: HITLRequest | None = None
    hitl_decision: dict[str, Any] | None = None

    # Response
    final_response: str | None = None
    response_type: str = "text"  # text, table, comparison, error

    # Quality
    evaluation_score: float | None = None
    evaluation_feedback: dict[str, Any] = Field(default_factory=dict)

    # Tracing
    trace_id: str | None = None
    span_id: str | None = None

    # Error handling
    error: str | None = None
    degraded_mode: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_domain_state(self, domain_id: str) -> dict[str, Any]:
        """Get state for a specific domain.

        Args:
            domain_id: The domain identifier.

        Returns:
            The domain-specific state dictionary.
        """
        return self.domain_data.get(domain_id, {})

    def set_domain_state(self, domain_id: str, state: dict[str, Any]) -> None:
        """Set state for a specific domain.

        Args:
            domain_id: The domain identifier.
            state: The domain-specific state to set.
        """
        self.domain_data[domain_id] = state

    def update_domain_state(self, domain_id: str, **kwargs: Any) -> None:
        """Update specific fields in domain state.

        Args:
            domain_id: The domain identifier.
            **kwargs: Fields to update.
        """
        if domain_id not in self.domain_data:
            self.domain_data[domain_id] = {}
        self.domain_data[domain_id].update(kwargs)

    def clear_domain_state(self, domain_id: str) -> None:
        """Clear state for a specific domain.

        Args:
            domain_id: The domain identifier.
        """
        self.domain_data.pop(domain_id, None)

    def add_agent_output(self, output: AgentOutput) -> None:
        """Add an agent output to the state.

        Args:
            output: The agent output to add.
        """
        self.agent_outputs[output.agent_name] = output

    def get_agent_output(self, agent_name: str) -> AgentOutput | None:
        """Get output from a specific agent.

        Args:
            agent_name: The agent name.

        Returns:
            The agent output or None.
        """
        return self.agent_outputs.get(agent_name)

    def has_error(self) -> bool:
        """Check if there's an error in the state."""
        return self.error is not None

    def needs_human_review(self) -> bool:
        """Check if HITL review is required."""
        return self.requires_human_approval and self.hitl_decision is None
