"""Tests for structured logging configuration."""

import json
import logging
import os
import tempfile

import pytest

from app.core.logging import configure_logging, get_logger, get_request_id, set_request_id


@pytest.fixture(autouse=True)
def reset_root_logger():
    """Restore root logger state after each test."""
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    yield
    root.handlers = original_handlers
    root.level = original_level


@pytest.mark.unit
def test_configure_logging_stdout_only(monkeypatch):
    """configure_logging with no LOG_DIR sets a single StreamHandler."""
    monkeypatch.setenv("LOG_DIR", "")
    configure_logging()

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0], logging.StreamHandler)


@pytest.mark.unit
def test_configure_logging_creates_file_handler(monkeypatch):
    """configure_logging with a writable LOG_DIR adds a RotatingFileHandler."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("LOG_DIR", tmpdir)
        monkeypatch.setenv("LOG_MAX_BYTES", "1024")
        monkeypatch.setenv("LOG_BACKUP_COUNT", "3")
        configure_logging()

        root = logging.getLogger()
        handler_types = [type(h) for h in root.handlers]
        assert logging.StreamHandler in handler_types
        assert logging.handlers.RotatingFileHandler in handler_types


@pytest.mark.unit
def test_configure_logging_file_is_json(monkeypatch):
    """File handler writes valid JSON log entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("LOG_DIR", tmpdir)
        configure_logging()

        logger = get_logger("test")
        logger.info("hello from test", key="value")

        log_path = os.path.join(tmpdir, "app.log")
        assert os.path.exists(log_path)

        with open(log_path) as f:
            line = f.readline().strip()

        entry = json.loads(line)
        assert entry["event"] == "hello from test"
        assert entry["key"] == "value"
        assert "timestamp" in entry


@pytest.mark.unit
def test_configure_logging_unwritable_dir_degrades_gracefully(monkeypatch, capsys):
    """configure_logging falls back to stdout-only when LOG_DIR is not writable."""
    monkeypatch.setenv("LOG_DIR", "/nonexistent/path/that/cannot/be/created/xyz")
    configure_logging()

    root = logging.getLogger()
    # Only the StreamHandler should be present — no RotatingFileHandler.
    file_handlers = [
        h for h in root.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(file_handlers) == 0

    captured = capsys.readouterr()
    assert "WARNING" in captured.out


@pytest.mark.unit
def test_request_id_propagation(monkeypatch):
    """Request ID set via set_request_id appears in log output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("LOG_DIR", tmpdir)
        configure_logging()

        test_request_id = "test-request-id-1234"
        set_request_id(test_request_id)

        logger = get_logger("test_req_id")
        logger.info("request scoped log")

        log_path = os.path.join(tmpdir, "app.log")
        with open(log_path) as f:
            line = f.readline().strip()

        entry = json.loads(line)
        assert entry.get("request_id") == test_request_id

        # Cleanup context
        set_request_id("")


@pytest.mark.unit
def test_get_request_id_default_empty():
    """get_request_id returns empty string when no request_id is set."""
    set_request_id("")
    assert get_request_id() == ""


@pytest.mark.unit
def test_log_rotation(monkeypatch):
    """RotatingFileHandler rotates when log file exceeds maxBytes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("LOG_DIR", tmpdir)
        monkeypatch.setenv("LOG_MAX_BYTES", "512")
        monkeypatch.setenv("LOG_BACKUP_COUNT", "2")
        configure_logging()

        logger = get_logger("rotation_test")
        # Write enough entries to trigger rotation.
        for i in range(50):
            logger.info("rotation test entry", index=i, padding="x" * 50)

        log_path = os.path.join(tmpdir, "app.log")
        backup_path = os.path.join(tmpdir, "app.log.1")
        assert os.path.exists(log_path)
        assert os.path.exists(backup_path)
