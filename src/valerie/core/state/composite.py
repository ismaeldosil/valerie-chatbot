"""Composite state management for multi-domain architecture.

This module provides utilities for working with domain-specific state
within the core state framework.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from ..domain.base import BaseDomain, DomainStateExtension
from .core import CoreState

T = TypeVar("T", bound=DomainStateExtension)


class CompositeState:
    """Utility class for managing composite state with domain extensions.

    This class provides type-safe access to domain-specific state
    stored within CoreState.domain_data.

    Example:
        # Get typed domain state
        supplier_state = CompositeState.get_domain_state(
            core_state,
            supplier_domain,
            SupplierStateExtension
        )

        # Update domain state
        supplier_state.suppliers = [...]
        CompositeState.set_domain_state(core_state, supplier_domain, supplier_state)
    """

    @staticmethod
    def get_domain_state(
        core_state: CoreState,
        domain: BaseDomain,
        state_class: type[T],
    ) -> T:
        """Get typed domain-specific state from CoreState.

        Args:
            core_state: The core state containing domain data.
            domain: The domain to get state for.
            state_class: The expected state extension class.

        Returns:
            The domain state as the specified type.
        """
        domain_data = core_state.get_domain_state(domain.domain_id)
        if domain_data:
            return state_class.model_validate(domain_data)
        return state_class()

    @staticmethod
    def set_domain_state(
        core_state: CoreState,
        domain: BaseDomain,
        state: DomainStateExtension,
    ) -> None:
        """Set domain-specific state in CoreState.

        Args:
            core_state: The core state to update.
            domain: The domain the state belongs to.
            state: The domain state to set.
        """
        core_state.set_domain_state(domain.domain_id, state.model_dump())

    @staticmethod
    def update_domain_state(
        core_state: CoreState,
        domain: BaseDomain,
        **kwargs: Any,
    ) -> None:
        """Update specific fields in domain state.

        Args:
            core_state: The core state to update.
            domain: The domain to update state for.
            **kwargs: Fields to update.
        """
        core_state.update_domain_state(domain.domain_id, **kwargs)

    @staticmethod
    def initialize_domain(
        core_state: CoreState,
        domain: BaseDomain,
    ) -> None:
        """Initialize domain state if not already present.

        Args:
            core_state: The core state to initialize in.
            domain: The domain to initialize.
        """
        if domain.domain_id not in core_state.domain_data:
            initial_state = domain.initialize_state_extension()
            core_state.set_domain_state(domain.domain_id, initial_state.model_dump())

    @staticmethod
    def switch_domain(
        core_state: CoreState,
        new_domain: BaseDomain,
    ) -> None:
        """Switch the active domain.

        This sets current_domain and initializes the domain state
        if not already present.

        Args:
            core_state: The core state to update.
            new_domain: The domain to switch to.
        """
        core_state.current_domain = new_domain.domain_id
        CompositeState.initialize_domain(core_state, new_domain)

    @staticmethod
    def get_current_domain_data(core_state: CoreState) -> dict[str, Any]:
        """Get the state data for the current domain.

        Args:
            core_state: The core state.

        Returns:
            The current domain's state data or empty dict.
        """
        if core_state.current_domain:
            return core_state.get_domain_state(core_state.current_domain)
        return {}


class StateConverter:
    """Utility for converting between legacy ChatState and new CoreState.

    This is used during migration to maintain backward compatibility.
    """

    @staticmethod
    def from_legacy_state(
        legacy_state: BaseModel,
        domain: BaseDomain,
        core_fields: list[str] | None = None,
    ) -> CoreState:
        """Convert a legacy domain-specific state to CoreState.

        Args:
            legacy_state: The legacy state model.
            domain: The domain the state belongs to.
            core_fields: Fields that should go into CoreState (not domain_data).
                        Defaults to common fields like messages, session_id, etc.

        Returns:
            A new CoreState with domain data populated.
        """
        if core_fields is None:
            core_fields = [
                "messages",
                "session_id",
                "user_id",
                "user_role",
                "intent",
                "entities",
                "confidence",
                "agent_outputs",
                "guardrails_passed",
                "guardrails_warnings",
                "pii_detected",
                "requires_human_approval",
                "hitl_request",
                "hitl_decision",
                "final_response",
                "response_type",
                "evaluation_score",
                "evaluation_feedback",
                "trace_id",
                "span_id",
                "error",
                "degraded_mode",
            ]

        legacy_data = legacy_state.model_dump()

        # Extract core fields
        core_data: dict[str, Any] = {}
        domain_data: dict[str, Any] = {}

        for key, value in legacy_data.items():
            if key in core_fields:
                core_data[key] = value
            else:
                domain_data[key] = value

        # Convert intent enum to string if needed
        if "intent" in core_data and hasattr(core_data["intent"], "value"):
            core_data["intent"] = core_data["intent"].value

        # Create core state with domain data
        core_state = CoreState(**core_data)
        core_state.current_domain = domain.domain_id
        core_state.set_domain_state(domain.domain_id, domain_data)

        return core_state

    @staticmethod
    def to_legacy_state(
        core_state: CoreState,
        domain: BaseDomain,
        legacy_state_class: type[BaseModel],
    ) -> BaseModel:
        """Convert CoreState back to a legacy domain-specific state.

        Args:
            core_state: The core state to convert.
            domain: The domain the state belongs to.
            legacy_state_class: The legacy state class to create.

        Returns:
            A new instance of the legacy state class.
        """
        # Get all core fields
        core_data = core_state.model_dump(exclude={"domain_data", "current_domain"})

        # Get domain-specific fields
        domain_data = core_state.get_domain_state(domain.domain_id)

        # Merge and create legacy state
        combined = {**core_data, **domain_data}

        # Filter to only fields in legacy class
        legacy_fields = set(legacy_state_class.model_fields.keys())
        filtered = {k: v for k, v in combined.items() if k in legacy_fields}

        return legacy_state_class(**filtered)
