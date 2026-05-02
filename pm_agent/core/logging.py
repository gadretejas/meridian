"""
Logging configuration for PM Agent.
Uses structlog for structured logging with context variables.
Configures rich console output for local dev and JSON for production.
"""

import logging
import logging.config
import json
import sys
from typing import Any
from contextvars import ContextVar
import structlog


# Context variables for structured logging
ritual_name_var: ContextVar[str] = ContextVar("ritual_name", default="")
compression_event_var: ContextVar[bool] = ContextVar("compression_event", default=False)


def get_logger(name: str = __name__) -> Any:
    """
    Get a structlog logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance with context awareness
    """
    return structlog.get_logger(name)


def set_ritual_context(ritual_name: str) -> None:
    """
    Set the ritual name in the context. This will be injected into all log lines
    during ritual execution.
    
    Args:
        ritual_name: Name of the ritual being executed
    """
    ritual_name_var.set(ritual_name)


def clear_ritual_context() -> None:
    """Clear the ritual context."""
    ritual_name_var.set("")


def set_compression_event(is_compression: bool) -> None:
    """
    Mark whether this log entry is related to context compression.
    
    Args:
        is_compression: True if this is a compression event
    """
    compression_event_var.set(is_compression)


def _add_context(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Processor that adds context variables to every log entry.
    Called automatically by structlog for each log line.
    """
    ritual = ritual_name_var.get()
    if ritual:
        event_dict["ritual"] = ritual
    
    is_compression = compression_event_var.get()
    if is_compression:
        event_dict["compression_event"] = True
        compression_event_var.set(False)  # Reset after logging
    
    return event_dict


def configure_logging(log_level: str = "INFO", json_output: bool = False) -> None:
    """
    Configure structlog and stdlib logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_output: If True, output JSON for production; False for rich console for dev
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    if json_output:
        # JSON output for production / log aggregation
        processors: list[Any] = [
            _add_context,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
        logging_config: dict[str, Any] = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.processors.JSONRenderer(),
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["console"],
                    "level": log_level,
                }
            },
        }
    else:
        # Rich console output for local development
        processors = [
            _add_context,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "standard",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["console"],
                    "level": log_level,
                }
            },
        }
    
    # Apply stdlib logging config
    logging.config.dictConfig(logging_config)
    
    # Configure structlog
    structlog.configure(  # type: ignore[misc]
        processors=processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


# Set up default logging on module import
try:
    import os
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    json_output = os.environ.get("JSON_LOGS", "false").lower() == "true"
    configure_logging(log_level, json_output)
except Exception as e:
    # Fall back to basic logging if config fails
    logging.basicConfig(level=logging.INFO)
    logging.warning(f"Failed to configure structlog: {e}")
