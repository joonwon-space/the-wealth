"""Structured logging configuration using structlog."""

import logging
import logging.handlers
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


def _make_file_handler(
    log_dir: str,
    max_bytes: int,
    backup_count: int,
    json_formatter: logging.Formatter,
) -> logging.Handler | None:
    """Create a RotatingFileHandler writing JSON to log_dir/app.log.

    Returns None (and logs a warning to stdout) if the directory cannot
    be created or is not writable, so the app continues with stdout only.
    """
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "app.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(json_formatter)
        return file_handler
    except OSError as exc:
        print(  # noqa: T201 — intentional: logging not yet configured
            f"[logging] WARNING: cannot create file handler at {log_dir!r}: {exc}. "
            "Falling back to stdout only."
        )
        return None


def configure_logging() -> None:
    """Configure structlog for the application.

    Uses JSON renderer in production (ENV=production) and
    a human-readable console renderer in development.
    File logging (RotatingFileHandler) is enabled when LOG_DIR is set.
    """
    is_production = os.getenv("ENV", "development").lower() == "production"
    log_dir = os.getenv("LOG_DIR", "")
    log_max_bytes = int(os.getenv("LOG_MAX_BYTES", "10485760"))
    log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

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

    # File logs are always JSON regardless of environment (machine-parseable).
    json_renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    stdout_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    json_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            json_renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(stdout_formatter)

    handlers: list[logging.Handler] = [stream_handler]

    if log_dir:
        file_handler = _make_file_handler(
            log_dir, log_max_bytes, log_backup_count, json_formatter
        )
        if file_handler is not None:
            handlers.append(file_handler)

    root_logger = logging.getLogger()
    root_logger.handlers = handlers
    root_logger.setLevel(logging.INFO)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)


def generate_request_id() -> str:
    """Generate a new UUID-based request_id."""
    return str(uuid.uuid4())
