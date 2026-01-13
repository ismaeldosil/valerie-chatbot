"""Correlation ID management for request tracing.

Provides utilities for generating and propagating correlation IDs
across the entire request lifecycle.
"""

import uuid
from contextvars import ContextVar
from typing import Any

from .logging_config import bind_correlation_id, clear_context

# Context variable for storing correlation ID
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def generate_correlation_id() -> str:
    """Generate a new correlation ID.

    Returns:
        A new UUID string for correlation
    """
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context.

    Args:
        correlation_id: The correlation ID to set
    """
    _correlation_id.set(correlation_id)
    bind_correlation_id(correlation_id)


def get_correlation_id() -> str | None:
    """Get the current correlation ID.

    Returns:
        The current correlation ID or None if not set
    """
    return _correlation_id.get()


def get_or_create_correlation_id() -> str:
    """Get the current correlation ID or create a new one.

    Returns:
        The current or newly created correlation ID
    """
    current = get_correlation_id()
    if current is None:
        current = generate_correlation_id()
        set_correlation_id(current)
    return current


def reset_correlation_context() -> None:
    """Reset the correlation context (useful for testing)."""
    _correlation_id.set(None)
    clear_context()


class CorrelationContext:
    """Context manager for correlation ID scope."""

    def __init__(self, correlation_id: str | None = None):
        """Initialize with optional correlation ID.

        Args:
            correlation_id: Optional correlation ID to use, generates new if None
        """
        self.correlation_id = correlation_id or generate_correlation_id()
        self._token: Any = None

    def __enter__(self) -> str:
        """Enter the context and set correlation ID."""
        self._token = _correlation_id.set(self.correlation_id)
        bind_correlation_id(self.correlation_id)
        return self.correlation_id

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context and reset correlation ID."""
        if self._token is not None:
            _correlation_id.reset(self._token)


# Header name for HTTP correlation ID
CORRELATION_ID_HEADER = "X-Correlation-ID"
