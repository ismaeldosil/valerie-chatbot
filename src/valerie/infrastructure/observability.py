"""Observability manager - unified tracing, metrics, and logging.

Provides a unified interface for observability with:
- LangSmith tracing in development
- Langfuse tracing in production
- Prometheus metrics collection
- Structlog structured logging
"""

import os
import time
import uuid
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any

from .correlation import (
    get_correlation_id,
    get_or_create_correlation_id,
)
from .logging_config import bind_context, get_logger
from .metrics import (
    record_agent_execution,
    record_llm_request,
    set_provider_availability,
)

logger = get_logger(__name__)

# Environment detection
VALERIE_ENV = os.getenv("VALERIE_ENV", "development")
IS_PRODUCTION = VALERIE_ENV == "production"

# LangSmith configuration
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "valerie-chatbot")

# Langfuse configuration
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")


class TracingBackend:
    """Base class for tracing backends."""

    def start_trace(self, name: str, metadata: dict | None = None) -> str:
        """Start a new trace."""
        raise NotImplementedError

    def start_span(self, trace_id: str, name: str, metadata: dict | None = None) -> str:
        """Start a new span within a trace."""
        raise NotImplementedError

    def end_span(
        self,
        trace_id: str,
        span_id: str,
        status: str = "success",
        output: Any = None,
    ) -> None:
        """End a span."""
        raise NotImplementedError

    def end_trace(self, trace_id: str, output: Any = None) -> None:
        """End a trace."""
        raise NotImplementedError

    def log_llm_call(
        self,
        trace_id: str,
        provider: str,
        model: str,
        messages: list,
        response: str,
        tokens: dict | None = None,
        duration_ms: float = 0,
    ) -> None:
        """Log an LLM call."""
        raise NotImplementedError


class InMemoryBackend(TracingBackend):
    """In-memory tracing backend for testing and fallback."""

    def __init__(self) -> None:
        self._traces: dict[str, dict] = {}

    def start_trace(self, name: str, metadata: dict | None = None) -> str:
        trace_id = str(uuid.uuid4())
        self._traces[trace_id] = {
            "trace_id": trace_id,
            "name": name,
            "start_time": datetime.now().isoformat(),
            "metadata": metadata or {},
            "spans": [],
        }
        return trace_id

    def start_span(self, trace_id: str, name: str, metadata: dict | None = None) -> str:
        span_id = str(uuid.uuid4())
        if trace_id in self._traces:
            self._traces[trace_id]["spans"].append(
                {
                    "span_id": span_id,
                    "name": name,
                    "start_time": datetime.now().isoformat(),
                    "metadata": metadata or {},
                    "status": "running",
                }
            )
        return span_id

    def end_span(
        self,
        trace_id: str,
        span_id: str,
        status: str = "success",
        output: Any = None,
    ) -> None:
        if trace_id not in self._traces:
            return
        for span in self._traces[trace_id]["spans"]:
            if span["span_id"] == span_id:
                span["end_time"] = datetime.now().isoformat()
                span["status"] = status
                span["output"] = output
                break

    def end_trace(self, trace_id: str, output: Any = None) -> None:
        if trace_id in self._traces:
            self._traces[trace_id]["end_time"] = datetime.now().isoformat()
            self._traces[trace_id]["output"] = output

    def log_llm_call(
        self,
        trace_id: str,
        provider: str,
        model: str,
        messages: list,
        response: str,
        tokens: dict | None = None,
        duration_ms: float = 0,
    ) -> None:
        if trace_id in self._traces:
            self._traces[trace_id].setdefault("llm_calls", []).append(
                {
                    "provider": provider,
                    "model": model,
                    "messages": messages,
                    "response": response,
                    "tokens": tokens,
                    "duration_ms": duration_ms,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    def get_trace(self, trace_id: str) -> dict | None:
        return self._traces.get(trace_id)


class LangSmithBackend(TracingBackend):
    """LangSmith tracing backend for development."""

    def __init__(self) -> None:
        self._fallback = InMemoryBackend()
        self._initialized = False
        try:
            if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
                # LangSmith is configured via environment variables
                # LangChain/LangGraph will automatically trace when these are set
                self._initialized = True
                logger.info(
                    "langsmith_initialized",
                    project=LANGCHAIN_PROJECT,
                )
        except Exception as e:
            logger.warning("langsmith_init_failed", error=str(e))

    def start_trace(self, name: str, metadata: dict | None = None) -> str:
        # LangSmith traces are automatic with LangGraph
        # We return a correlation ID for our internal tracking
        return self._fallback.start_trace(name, metadata)

    def start_span(self, trace_id: str, name: str, metadata: dict | None = None) -> str:
        return self._fallback.start_span(trace_id, name, metadata)

    def end_span(
        self,
        trace_id: str,
        span_id: str,
        status: str = "success",
        output: Any = None,
    ) -> None:
        self._fallback.end_span(trace_id, span_id, status, output)

    def end_trace(self, trace_id: str, output: Any = None) -> None:
        self._fallback.end_trace(trace_id, output)

    def log_llm_call(
        self,
        trace_id: str,
        provider: str,
        model: str,
        messages: list,
        response: str,
        tokens: dict | None = None,
        duration_ms: float = 0,
    ) -> None:
        # LangSmith automatically captures LLM calls via LangChain
        self._fallback.log_llm_call(
            trace_id, provider, model, messages, response, tokens, duration_ms
        )


class LangfuseBackend(TracingBackend):
    """Langfuse tracing backend for production."""

    def __init__(self) -> None:
        self._fallback = InMemoryBackend()
        self._client = None
        self._traces: dict[str, Any] = {}

        try:
            if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
                from langfuse import Langfuse

                self._client = Langfuse(
                    public_key=LANGFUSE_PUBLIC_KEY,
                    secret_key=LANGFUSE_SECRET_KEY,
                    host=LANGFUSE_HOST,
                )
                logger.info(
                    "langfuse_initialized",
                    host=LANGFUSE_HOST,
                )
        except ImportError:
            logger.warning("langfuse_not_installed")
        except Exception as e:
            logger.warning("langfuse_init_failed", error=str(e))

    def start_trace(self, name: str, metadata: dict | None = None) -> str:
        trace_id = str(uuid.uuid4())

        if self._client:
            try:
                trace = self._client.trace(
                    id=trace_id,
                    name=name,
                    metadata=metadata,
                )
                self._traces[trace_id] = trace
            except Exception as e:
                logger.warning("langfuse_trace_failed", error=str(e))

        # Always use fallback for local tracking
        self._fallback.start_trace(name, metadata)
        return trace_id

    def start_span(self, trace_id: str, name: str, metadata: dict | None = None) -> str:
        span_id = str(uuid.uuid4())

        if self._client and trace_id in self._traces:
            try:
                self._traces[trace_id].span(
                    id=span_id,
                    name=name,
                    metadata=metadata,
                )
            except Exception as e:
                logger.warning("langfuse_span_failed", error=str(e))

        self._fallback.start_span(trace_id, name, metadata)
        return span_id

    def end_span(
        self,
        trace_id: str,
        span_id: str,
        status: str = "success",
        output: Any = None,
    ) -> None:
        # Langfuse spans are ended automatically or via update
        self._fallback.end_span(trace_id, span_id, status, output)

    def end_trace(self, trace_id: str, output: Any = None) -> None:
        if self._client and trace_id in self._traces:
            try:
                self._traces[trace_id].update(output=output)
            except Exception as e:
                logger.warning("langfuse_trace_end_failed", error=str(e))

        self._fallback.end_trace(trace_id, output)

    def log_llm_call(
        self,
        trace_id: str,
        provider: str,
        model: str,
        messages: list,
        response: str,
        tokens: dict | None = None,
        duration_ms: float = 0,
    ) -> None:
        if self._client and trace_id in self._traces:
            try:
                self._traces[trace_id].generation(
                    name=f"{provider}:{model}",
                    model=model,
                    input=messages,
                    output=response,
                    usage={
                        "input": tokens.get("input_tokens", 0) if tokens else 0,
                        "output": tokens.get("output_tokens", 0) if tokens else 0,
                    },
                    metadata={"provider": provider, "duration_ms": duration_ms},
                )
            except Exception as e:
                logger.warning("langfuse_generation_failed", error=str(e))

        self._fallback.log_llm_call(
            trace_id, provider, model, messages, response, tokens, duration_ms
        )

    def flush(self) -> None:
        """Flush pending traces to Langfuse."""
        if self._client:
            try:
                self._client.flush()
            except Exception as e:
                logger.warning("langfuse_flush_failed", error=str(e))


class ObservabilityManager:
    """Unified observability manager with environment-based routing."""

    def __init__(self) -> None:
        self.env = VALERIE_ENV
        self._backend = self._init_backend()
        self._active_traces: dict[str, str] = {}

        logger.info(
            "observability_initialized",
            environment=self.env,
            backend=type(self._backend).__name__,
        )

    def _init_backend(self) -> TracingBackend:
        """Initialize the appropriate tracing backend."""
        if IS_PRODUCTION:
            if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
                return LangfuseBackend()
            logger.warning("production_without_langfuse")
        else:
            if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
                return LangSmithBackend()

        return InMemoryBackend()

    @contextmanager
    def trace(self, name: str, metadata: dict | None = None) -> Generator[str, None, None]:
        """Context manager for tracing a request.

        Args:
            name: Name of the trace
            metadata: Optional metadata to attach

        Yields:
            The trace ID
        """
        correlation_id = get_or_create_correlation_id()
        trace_id = self._backend.start_trace(name, metadata)
        self._active_traces[correlation_id] = trace_id

        bind_context(trace_id=trace_id)
        logger.info("trace_started", trace_name=name)

        start_time = time.time()
        try:
            yield trace_id
            duration = time.time() - start_time
            logger.info(
                "trace_completed",
                trace_name=name,
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "trace_failed",
                trace_name=name,
                duration_seconds=duration,
                error=str(e),
            )
            raise
        finally:
            self._backend.end_trace(trace_id)
            self._active_traces.pop(correlation_id, None)

    @contextmanager
    def span(self, name: str, metadata: dict | None = None) -> Generator[str, None, None]:
        """Context manager for a span within the current trace.

        Args:
            name: Name of the span
            metadata: Optional metadata to attach

        Yields:
            The span ID
        """
        correlation_id = get_correlation_id()
        trace_id = self._active_traces.get(correlation_id) if correlation_id else None

        if not trace_id:
            # Create a standalone trace if none exists
            trace_id = self._backend.start_trace(f"standalone:{name}")

        span_id = self._backend.start_span(trace_id, name, metadata)
        start_time = time.time()

        try:
            yield span_id
            duration = time.time() - start_time
            self._backend.end_span(trace_id, span_id, "success")
            logger.debug(
                "span_completed",
                span_name=name,
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            self._backend.end_span(trace_id, span_id, "error", str(e))
            logger.error(
                "span_failed",
                span_name=name,
                duration_seconds=duration,
                error=str(e),
            )
            raise

    def trace_agent(self, agent_name: str) -> Callable:
        """Decorator to trace agent execution.

        Args:
            agent_name: Name of the agent

        Returns:
            Decorated function
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                status = "success"

                with self.span(f"agent:{agent_name}"):
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    except Exception:
                        status = "error"
                        raise
                    finally:
                        duration = time.time() - start_time
                        record_agent_execution(agent_name, status, duration)

            return wrapper

        return decorator

    def trace_llm(
        self,
        provider: str,
        model: str,
        messages: list,
        response: str,
        tokens: dict | None = None,
        duration_ms: float = 0,
    ) -> None:
        """Log an LLM call to the tracing backend.

        Args:
            provider: LLM provider name
            model: Model name
            messages: Input messages
            response: Response text
            tokens: Token usage dict
            duration_ms: Duration in milliseconds
        """
        correlation_id = get_correlation_id()
        trace_id = self._active_traces.get(correlation_id) if correlation_id else None

        if trace_id:
            self._backend.log_llm_call(
                trace_id, provider, model, messages, response, tokens, duration_ms
            )

        # Also record metrics
        record_llm_request(
            provider=provider,
            model=model,
            status="success",
            duration=duration_ms / 1000,
            input_tokens=tokens.get("input_tokens", 0) if tokens else 0,
            output_tokens=tokens.get("output_tokens", 0) if tokens else 0,
        )

        logger.info(
            "llm_call",
            provider=provider,
            model=model,
            duration_ms=duration_ms,
            input_tokens=tokens.get("input_tokens") if tokens else None,
            output_tokens=tokens.get("output_tokens") if tokens else None,
        )

    def set_provider_status(self, provider: str, available: bool) -> None:
        """Set LLM provider availability status.

        Args:
            provider: Provider name
            available: Whether provider is available
        """
        set_provider_availability(provider, available)
        logger.info(
            "provider_status",
            provider=provider,
            available=available,
        )

    def flush(self) -> None:
        """Flush pending data to backends."""
        if isinstance(self._backend, LangfuseBackend):
            self._backend.flush()


# Global observability instance
_observability: ObservabilityManager | None = None


def get_observability() -> ObservabilityManager:
    """Get the global observability manager."""
    global _observability
    if _observability is None:
        _observability = ObservabilityManager()
    return _observability


def reset_observability() -> None:
    """Reset the global observability manager (for testing)."""
    global _observability
    _observability = None
