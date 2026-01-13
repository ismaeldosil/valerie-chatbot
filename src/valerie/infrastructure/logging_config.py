"""Structlog configuration for structured logging.

Provides a unified logging interface with:
- JSON output in production for log aggregation
- Colored console output in development
- Automatic timestamp and log level injection
- Correlation ID propagation
"""

import logging
import os
import sys
from typing import Any

import structlog
from structlog.types import Processor

# Environment detection
VALERIE_ENV = os.getenv("VALERIE_ENV", "development")
IS_PRODUCTION = VALERIE_ENV == "production"


def add_environment(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add environment to log events."""
    event_dict["environment"] = VALERIE_ENV
    return event_dict


def add_service_info(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add service information to log events."""
    event_dict["service"] = "valerie-chatbot"
    event_dict["version"] = os.getenv("APP_VERSION", "2.0.0")
    return event_dict


def configure_structlog() -> None:
    """Configure structlog with appropriate processors for the environment."""
    # Shared processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        add_environment,
        add_service_info,
    ]

    if IS_PRODUCTION:
        # Production: JSON output for log aggregation
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Colored console output
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if IS_PRODUCTION else logging.DEBUG,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (usually __name__ from the calling module)

    Returns:
        A bound structlog logger instance
    """
    return structlog.get_logger(name)


def bind_correlation_id(correlation_id: str) -> None:
    """Bind a correlation ID to the current context.

    Args:
        correlation_id: The correlation ID to bind
    """
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


def bind_context(**kwargs: Any) -> None:
    """Bind additional context variables.

    Args:
        **kwargs: Key-value pairs to bind to the logging context
    """
    structlog.contextvars.bind_contextvars(**kwargs)


# Initialize structlog on module import
configure_structlog()
