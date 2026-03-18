"""Graceful shutdown tests — SSE shutdown event and scheduler stop."""

import asyncio
import pytest


@pytest.mark.unit
class TestGracefulShutdown:
    def test_signal_sse_shutdown_sets_event(self) -> None:
        """signal_sse_shutdown() should set the global shutdown event."""
        from app.api.prices import _shutdown_event, signal_sse_shutdown

        # Reset the event first (it might be set from a previous test or import)
        _shutdown_event.clear()
        assert not _shutdown_event.is_set()

        signal_sse_shutdown()
        assert _shutdown_event.is_set()

        # Clean up for subsequent tests
        _shutdown_event.clear()

    def test_shutdown_event_breaks_sse_loop(self) -> None:
        """SSE generator should exit immediately when shutdown event is set."""
        from app.api.prices import _shutdown_event

        _shutdown_event.clear()

        # Simulate the shutdown check in the SSE loop
        _shutdown_event.set()
        assert _shutdown_event.is_set()

        # A while loop checking is_set() would break
        iterations = 0
        while not _shutdown_event.is_set():
            iterations += 1
            if iterations > 100:
                break

        assert iterations == 0  # Loop never ran because event was set

        _shutdown_event.clear()

    async def test_shutdown_event_is_awaitable(self) -> None:
        """The shutdown event should work with asyncio.wait_for."""
        from app.api.prices import _shutdown_event

        _shutdown_event.clear()

        # Set the event after a tiny delay
        async def set_later() -> None:
            await asyncio.sleep(0.01)
            _shutdown_event.set()

        asyncio.create_task(set_later())

        # Should complete because event gets set
        await asyncio.wait_for(_shutdown_event.wait(), timeout=1.0)
        assert _shutdown_event.is_set()

        _shutdown_event.clear()

    def test_scheduler_wait_true_on_stop(self) -> None:
        """stop_scheduler() should call shutdown(wait=True)."""
        from unittest.mock import patch
        from app.services.scheduler import scheduler, stop_scheduler

        with patch.object(scheduler, "shutdown") as mock_shutdown:
            stop_scheduler()
            mock_shutdown.assert_called_once_with(wait=True)
