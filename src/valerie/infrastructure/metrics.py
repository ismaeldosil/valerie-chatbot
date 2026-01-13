"""Prometheus metrics for the Valerie Supplier Chatbot.

Provides metrics collection for:
- API request rates and latencies
- LLM provider performance
- Agent execution metrics
- Session tracking
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# =============================================================================
# Application Info
# =============================================================================

app_info = Info(
    "valerie_app",
    "Application information",
)
app_info.info(
    {
        "version": "2.0.0",
        "service": "valerie-chatbot",
    }
)

# =============================================================================
# Request Metrics
# =============================================================================

requests_total = Counter(
    "valerie_requests_total",
    "Total number of requests",
    ["endpoint", "method", "status"],
)

request_duration_seconds = Histogram(
    "valerie_request_duration_seconds",
    "Request duration in seconds",
    ["endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

request_in_progress = Gauge(
    "valerie_requests_in_progress",
    "Number of requests currently being processed",
    ["endpoint"],
)

# =============================================================================
# LLM Provider Metrics
# =============================================================================

llm_requests_total = Counter(
    "valerie_llm_requests_total",
    "Total LLM requests by provider",
    ["provider", "model", "status"],
)

llm_latency_seconds = Histogram(
    "valerie_llm_latency_seconds",
    "LLM request latency in seconds",
    ["provider", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

llm_tokens_total = Counter(
    "valerie_llm_tokens_total",
    "Total tokens processed",
    ["provider", "model", "direction"],  # direction: input/output
)

llm_provider_available = Gauge(
    "valerie_llm_provider_available",
    "LLM provider availability (1=available, 0=unavailable)",
    ["provider"],
)

llm_errors_total = Counter(
    "valerie_llm_errors_total",
    "Total LLM errors by type",
    ["provider", "error_type"],
)

# =============================================================================
# Agent Metrics
# =============================================================================

agent_invocations_total = Counter(
    "valerie_agent_invocations_total",
    "Total agent invocations",
    ["agent_name", "status"],
)

agent_duration_seconds = Histogram(
    "valerie_agent_duration_seconds",
    "Agent execution time in seconds",
    ["agent_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

agent_errors_total = Counter(
    "valerie_agent_errors_total",
    "Total agent errors",
    ["agent_name", "error_type"],
)

# =============================================================================
# Session Metrics
# =============================================================================

active_sessions = Gauge(
    "valerie_active_sessions",
    "Number of active chat sessions",
)

session_duration_seconds = Histogram(
    "valerie_session_duration_seconds",
    "Session duration in seconds",
    buckets=[60, 300, 600, 1800, 3600, 7200],
)

session_messages_total = Counter(
    "valerie_session_messages_total",
    "Total messages per session type",
    ["message_type"],  # user/assistant
)

# =============================================================================
# WebSocket Metrics
# =============================================================================

websocket_connections_active = Gauge(
    "valerie_websocket_connections_active",
    "Number of active WebSocket connections",
)

websocket_messages_total = Counter(
    "valerie_websocket_messages_total",
    "Total WebSocket messages",
    ["direction"],  # sent/received
)

websocket_connection_duration_seconds = Histogram(
    "valerie_websocket_connection_duration_seconds",
    "WebSocket connection duration",
    buckets=[60, 300, 600, 1800, 3600],
)

# =============================================================================
# Intent Classification Metrics
# =============================================================================

intent_classifications_total = Counter(
    "valerie_intent_classifications_total",
    "Total intent classifications by type",
    ["intent"],
)

# =============================================================================
# Oracle Fusion Integration Metrics
# =============================================================================

oracle_api_requests_total = Counter(
    "valerie_oracle_api_requests_total",
    "Total Oracle Fusion API requests",
    ["endpoint", "status"],
)

oracle_api_latency_seconds = Histogram(
    "valerie_oracle_api_latency_seconds",
    "Oracle Fusion API request latency",
    ["endpoint"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# =============================================================================
# Health Check Metrics
# =============================================================================

health_check_status = Gauge(
    "valerie_health_check_status",
    "Health check status (1=healthy, 0=unhealthy)",
    ["component"],
)


# =============================================================================
# Helper Functions
# =============================================================================


def record_request(endpoint: str, method: str, status: int, duration: float) -> None:
    """Record a request with all relevant metrics.

    Args:
        endpoint: The API endpoint
        method: HTTP method
        status: HTTP status code
        duration: Request duration in seconds
    """
    requests_total.labels(endpoint=endpoint, method=method, status=str(status)).inc()
    request_duration_seconds.labels(endpoint=endpoint).observe(duration)


def record_llm_request(
    provider: str,
    model: str,
    status: str,
    duration: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    """Record an LLM request with all relevant metrics.

    Args:
        provider: LLM provider name
        model: Model name
        status: Request status (success/error)
        duration: Request duration in seconds
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
    """
    llm_requests_total.labels(provider=provider, model=model, status=status).inc()
    llm_latency_seconds.labels(provider=provider, model=model).observe(duration)

    if input_tokens > 0:
        llm_tokens_total.labels(provider=provider, model=model, direction="input").inc(input_tokens)

    if output_tokens > 0:
        llm_tokens_total.labels(provider=provider, model=model, direction="output").inc(
            output_tokens
        )


def record_agent_execution(agent_name: str, status: str, duration: float) -> None:
    """Record an agent execution.

    Args:
        agent_name: Name of the agent
        status: Execution status (success/error)
        duration: Execution duration in seconds
    """
    agent_invocations_total.labels(agent_name=agent_name, status=status).inc()
    agent_duration_seconds.labels(agent_name=agent_name).observe(duration)


def set_provider_availability(provider: str, available: bool) -> None:
    """Set LLM provider availability status.

    Args:
        provider: Provider name
        available: Whether the provider is available
    """
    llm_provider_available.labels(provider=provider).set(1 if available else 0)


def set_health_status(component: str, healthy: bool) -> None:
    """Set health check status for a component.

    Args:
        component: Component name
        healthy: Whether the component is healthy
    """
    health_check_status.labels(component=component).set(1 if healthy else 0)
