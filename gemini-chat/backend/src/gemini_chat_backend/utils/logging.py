"""Structured logging configuration for Gemini Chat Backend."""

import logging
import sys
from typing import Any, Dict, Optional

import structlog
from pythonjsonlogger import jsonlogger


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "text",
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ("json" for production, "text" for development)
    """
    # Map string level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    if log_format == "json":
        # JSON format for production
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s"
        )
    else:
        # Text format for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers = []

    # Add stream handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(
    name: Optional[str] = None,
    **context: Any,
) -> structlog.stdlib.BoundLogger:
    """Get a structured logger with optional context binding.

    Args:
        name: Logger name (typically __name__)
        **context: Key-value pairs to bind to the logger context

    Returns:
        A structured logger instance
    """
    logger = structlog.get_logger(name)

    if context:
        logger = logger.bind(**context)

    return logger


def get_request_logger(
    request_id: str,
    **context: Any,
) -> structlog.stdlib.BoundLogger:
    """Get a logger bound with request context for request tracing.

    Args:
        request_id: Unique identifier for the request
        **context: Additional context to bind

    Returns:
        A structured logger with request context
    """
    return get_logger(
        request_id=request_id,
        **context,
    )
