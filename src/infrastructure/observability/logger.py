"""Structured logging configuration using structlog."""

import logging
import sys
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from structlog.typing import Processor


def configure_logging(log_level: str, environment: str) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Application environment (development, production, etc.)
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Choose processors based on environment
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if environment == "development":
        # Beautiful human-readable output for development with colors
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                level_styles={
                    "critical": "\033[95m",  # Magenta
                    "exception": "\033[95m",
                    "error": "\033[91m",  # Red
                    "warn": "\033[93m",  # Yellow
                    "warning": "\033[93m",
                    "info": "\033[96m",  # Cyan
                    "debug": "\033[90m",  # Dark gray
                },
                exception_formatter=structlog.dev.plain_traceback,
            ),
        )
    else:
        # JSON output for production/staging
        processors.append(structlog.processors.JSONRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically module name)

    Returns:
        Configured structured logger
    """
    return structlog.get_logger(name)
