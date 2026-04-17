"""Unit + integration tests for KIS token-bucket rate limiter (RL-006, RL-007).

TDD: these tests were written before the implementation.
"""

import asyncio
import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.kis_rate_limiter import KisRateLimiter, acquire, _limiter


# ---------------------------------------------------------------------------
# RL-006 — Unit tests: token bucket mechanics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKisRateLimiterTokenBucket:
    """Token bucket algorithm — correctness and edge-case coverage."""

    def test_initial_tokens_equal_burst(self) -> None:
        """New limiter starts with burst capacity available."""
        limiter = KisRateLimiter(rate=5.0, burst=10)
        assert limiter.available_tokens() == pytest.approx(10.0, abs=0.01)

    def test_acquire_within_burst_succeeds_immediately(self) -> None:
        """Acquiring tokens within burst does not block."""
        limiter = KisRateLimiter(rate=5.0, burst=10)
        wait = limiter._consume(n=1)
        assert wait == 0.0

    def test_acquire_exceeding_burst_returns_positive_wait(self) -> None:
        """Acquiring more tokens than burst should return a positive wait time."""
        limiter = KisRateLimiter(rate=5.0, burst=5)
        # Drain the bucket first
        for _ in range(5):
            limiter._consume(n=1)
        # Next acquire should require waiting
        wait = limiter._consume(n=1)
        assert wait > 0.0

    def test_tokens_refill_over_time(self) -> None:
        """Tokens accumulate at the configured rate."""
        limiter = KisRateLimiter(rate=10.0, burst=10)
        # Drain entirely
        for _ in range(10):
            limiter._consume(n=1)
        assert limiter.available_tokens() == pytest.approx(0.0, abs=0.1)

        # Manually advance internal clock by 0.5s → expect +5 tokens
        limiter._last_refill -= 0.5
        assert limiter.available_tokens() == pytest.approx(5.0, abs=0.15)

    def test_tokens_capped_at_burst(self) -> None:
        """Tokens never exceed burst capacity even after a long idle period."""
        limiter = KisRateLimiter(rate=5.0, burst=5)
        # Advance internal clock by 100 seconds
        limiter._last_refill -= 100.0
        assert limiter.available_tokens() <= 5.0 + 0.01

    def test_wait_time_proportional_to_deficit(self) -> None:
        """Wait time equals deficit / rate."""
        rate = 4.0
        limiter = KisRateLimiter(rate=rate, burst=4)
        for _ in range(4):
            limiter._consume(n=1)
        # One token needed, rate=4 → wait ≈ 0.25s
        wait = limiter._consume(n=1)
        assert wait == pytest.approx(1.0 / rate, rel=0.05)

    def test_mock_mode_disables_limiting(self) -> None:
        """Mock mode: acquire always returns 0 wait regardless of token state."""
        limiter = KisRateLimiter(rate=1.0, burst=1, mock_mode=True)
        # Drain bucket
        limiter._consume(n=1)
        # In mock mode, further consumes should return 0
        for _ in range(50):
            assert limiter._consume(n=1) == 0.0

    @pytest.mark.asyncio
    async def test_acquire_async_no_sleep_when_tokens_available(self) -> None:
        """async acquire() returns immediately when tokens are available."""
        limiter = KisRateLimiter(rate=100.0, burst=100)
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.05  # well under 50ms

    @pytest.mark.asyncio
    async def test_acquire_async_sleeps_when_empty(self) -> None:
        """async acquire() sleeps the computed wait time when bucket is empty."""
        rate = 50.0  # fast enough that test stays short
        limiter = KisRateLimiter(rate=rate, burst=1)
        await limiter.acquire()  # drain
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await limiter.acquire()
            assert mock_sleep.called
            slept = mock_sleep.call_args[0][0]
            assert slept == pytest.approx(1.0 / rate, rel=0.2)

    @pytest.mark.asyncio
    async def test_acquire_timeout_raises(self) -> None:
        """acquire() with timeout raises asyncio.TimeoutError if wait > timeout."""
        limiter = KisRateLimiter(rate=0.1, burst=1)
        await limiter.acquire()  # drain — next token takes 10s
        with pytest.raises(asyncio.TimeoutError):
            await limiter.acquire(timeout=0.01)

    @pytest.mark.asyncio
    async def test_global_acquire_helper(self) -> None:
        """Module-level acquire() delegates to the singleton _limiter."""
        with patch.object(_limiter, "acquire", new_callable=AsyncMock) as mock_acq:
            await acquire()
            mock_acq.assert_called_once()


# ---------------------------------------------------------------------------
# RL-007 — Integration test: burst of 20 requests through httpx mock
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRateLimiterIntegration:
    """End-to-end: fetch_prices_parallel fires 20 calls; rate limiter controls pacing."""

    @pytest.mark.asyncio
    async def test_burst_20_completes_within_budget(self) -> None:
        """Burst of 20 calls with rate=20/s and burst=20 should all complete.

        All tokens available upfront, so real elapsed time is near-zero.
        Rate limiter must not raise even under concurrency.
        """
        limiter = KisRateLimiter(rate=20.0, burst=20)

        async def single_acquire() -> None:
            await limiter.acquire()

        start = time.monotonic()
        await asyncio.gather(*[single_acquire() for _ in range(20)])
        elapsed = time.monotonic() - start
        # With burst=20, all 20 should be served immediately
        assert elapsed < 1.0, f"Expected <1s for full burst, got {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_burst_20_with_mock_kis_calls(self) -> None:
        """20 concurrent fetch_domestic_price calls pass through rate limiter.

        httpx is mocked — only rate-limiter overhead is measured.
        """
        from app.services import kis_price as kis_price_module

        # A fast limiter (rate=100/s, burst=20) so test stays quick
        fast_limiter = KisRateLimiter(rate=100.0, burst=20)

        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {
            "output": {"stck_prpr": "70000"}
        }

        call_count = 0

        async def mock_get(*args, **kwargs):  # noqa: ANN001
            nonlocal call_count
            await fast_limiter.acquire()
            call_count += 1
            return fake_response

        mock_client = AsyncMock()
        mock_client.get = mock_get

        with (
            patch(
                "app.services.kis_price.get_kis_access_token",
                new_callable=AsyncMock,
                return_value="tok",
            ),
            patch(
                "app.services.kis_price.get_kis_availability",
                return_value=True,
            ),
            patch(
                "app.services.kis_price._cache_price",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.kis_price._get_cached_price",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_ctx

            tickers = [f"00{i:04d}" for i in range(20)]
            result = await kis_price_module.fetch_prices_parallel(
                tickers, "key", "secret"
            )

        assert len(result) == 20
        assert call_count == 20
        assert all(v == Decimal("70000") for v in result.values())

    @pytest.mark.asyncio
    async def test_acquire_timeout_counter_increments(self) -> None:
        """Timeout counter increments on each TimeoutError from acquire()."""
        from app.services.kis_rate_limiter import get_timeout_counter

        limiter = KisRateLimiter(rate=0.01, burst=1)
        await limiter.acquire()  # drain the bucket

        initial = get_timeout_counter()
        with pytest.raises(asyncio.TimeoutError):
            await limiter.acquire(timeout=0.001)

        assert get_timeout_counter() == initial + 1

    @pytest.mark.asyncio
    async def test_p95_hint_logged_on_slow_acquire(self, caplog) -> None:
        """A slow acquire (>500ms wait) emits a P95 hint log at WARNING level."""
        import logging

        limiter = KisRateLimiter(rate=1.0, burst=1)
        await limiter.acquire()  # drain

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            caplog.at_level(logging.WARNING, logger="app.services.kis_rate_limiter"),
        ):
            # Patch _consume to return a wait > 0.5s
            original_consume = limiter._consume

            def slow_consume(n: int = 1) -> float:  # noqa: ANN001
                _ = original_consume(n)
                return 0.6  # simulate 600ms wait

            limiter._consume = slow_consume  # type: ignore[method-assign]
            await limiter.acquire()

        assert any("P95" in r.message or "slow" in r.message.lower() for r in caplog.records)
