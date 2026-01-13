"""Infrastructure agents and observability for the chatbot."""

from .correlation import (
    CORRELATION_ID_HEADER,
    CorrelationContext,
    generate_correlation_id,
    get_correlation_id,
    get_or_create_correlation_id,
    reset_correlation_context,
    set_correlation_id,
)
from .evaluation import EvaluationAgent
from .fallback import FallbackAgent
from .guardrails import GuardrailsAgent
from .hitl import HITLAgent
from .logging_config import (
    bind_context,
    bind_correlation_id,
    clear_context,
    configure_structlog,
    get_logger,
)
from .metrics import (
    active_sessions,
    agent_duration_seconds,
    agent_invocations_total,
    health_check_status,
    llm_latency_seconds,
    llm_provider_available,
    llm_requests_total,
    llm_tokens_total,
    record_agent_execution,
    record_llm_request,
    record_request,
    request_duration_seconds,
    requests_total,
    set_health_status,
    set_provider_availability,
)
from .observability import (
    ObservabilityManager,
    get_observability,
    reset_observability,
)
from .session_store import (
    InMemorySessionStore,
    RedisSessionStore,
    SessionStore,
    get_default_ttl,
    get_session_store,
)

__all__ = [
    # Agents
    "GuardrailsAgent",
    "HITLAgent",
    "FallbackAgent",
    "EvaluationAgent",
    # Observability
    "ObservabilityManager",
    "get_observability",
    "reset_observability",
    # Logging
    "get_logger",
    "bind_context",
    "bind_correlation_id",
    "clear_context",
    "configure_structlog",
    # Correlation
    "CORRELATION_ID_HEADER",
    "CorrelationContext",
    "generate_correlation_id",
    "get_correlation_id",
    "get_or_create_correlation_id",
    "set_correlation_id",
    "reset_correlation_context",
    # Metrics
    "requests_total",
    "request_duration_seconds",
    "llm_requests_total",
    "llm_latency_seconds",
    "llm_tokens_total",
    "llm_provider_available",
    "agent_invocations_total",
    "agent_duration_seconds",
    "active_sessions",
    "health_check_status",
    "record_request",
    "record_llm_request",
    "record_agent_execution",
    "set_provider_availability",
    "set_health_status",
    # Session
    "SessionStore",
    "InMemorySessionStore",
    "RedisSessionStore",
    "get_session_store",
    "get_default_ttl",
]
