"""Structured logging configuration using structlog."""

import logging
import os
import uuid
from contextvars import ContextVar

import structlog

# Context variable for request_id propagation
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the current request_id from context."""
    return _request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set the request_id in context."""
    _request_id_var.set(request_id)


def _add_request_id(
    logger: object, method: str, event_dict: dict
) -> dict:
    """Structlog processor: inject request_id from contextvar."""
    request_id = _request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def configure_logging() -> None:
    """Configure structlog for the application.

    Uses JSON renderer in production (ENV=production) and
    a human-readable console renderer in development.
    """
    is_production = os.getenv("ENV", "development").lower() == "production"

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        _add_request_id,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if is_production:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)


def generate_request_id() -> str:
    """Generate a new UUID-based request_id."""
    return str(uuid.uuid4())
