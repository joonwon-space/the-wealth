"""KIS price 서비스 단위 테스트 — Redis 캐시 폴백 로직."""

from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.kis_price import (
    _cache_price,
    _get_cached_price,
    fetch_domestic_price,
    fetch_prices_parallel,
)


@asynccontextmanager
async def _noop_call_slot(*args, **kwargs):
    """Replacement for kis_call_slot in tests — bypasses rate limiter + concurrency cap."""
    yield


@pytest.mark.unit
class TestPriceCache:
    @patch("app.core.redis_cache.get_redis_client")
    async def test_cache_and_retrieve(self, mock_get_client) -> None:
        """캐시 저장 후 조회 시 값이 반환되어야 한다."""
        store: dict[str, str] = {}

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(side_effect=lambda k, t, v: store.update({k: v}))
        mock_redis.get = AsyncMock(side_effect=lambda k: store.get(k))
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_redis)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get_client.return_value = ctx

        await _cache_price("005930", Decimal("70000"))
        result = await _get_cached_price("005930")
        assert result == Decimal("70000")

    @patch("app.core.redis_cache.get_redis_client")
    async def test_cache_miss_returns_none(self, mock_get_client) -> None:
        """캐시에 없으면 None 반환."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_redis)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get_client.return_value = ctx

        result = await _get_cached_price("999999")
        assert result is None


@pytest.mark.unit
class TestFetchPricesParallel:
    @patch("app.services.kis_price._get_cached_price")
    @patch("app.services.kis_price._cache_price")
    @patch("app.services.kis_price.fetch_domestic_price")
    async def test_successful_fetch_caches_price(
        self, mock_fetch, mock_cache, mock_get_cache
    ) -> None:
        """가격 조회 성공 시 Redis에 캐시해야 한다."""
        mock_fetch.return_value = Decimal("70000")
        mock_cache.return_value = None

        result = await fetch_prices_parallel(["005930"], "key", "secret")
        assert result["005930"] == Decimal("70000")
        mock_cache.assert_called_once_with("005930", Decimal("70000"))

    @patch("app.services.kis_price._get_cached_price")
    @patch("app.services.kis_price._cache_price")
    @patch("app.services.kis_price.fetch_domestic_price")
    async def test_fallback_to_cache_on_failure(
        self, mock_fetch, mock_cache, mock_get_cache
    ) -> None:
        """가격 조회 실패 시 캐시에서 폴백."""
        mock_fetch.return_value = None  # API 실패
        mock_get_cache.return_value = Decimal("69000")  # 캐시에 이전 가격 있음

        result = await fetch_prices_parallel(["005930"], "key", "secret")
        assert result["005930"] == Decimal("69000")
        mock_cache.assert_not_called()

    @patch("app.services.kis_price._get_cached_price")
    @patch("app.services.kis_price._cache_price")
    @patch("app.services.kis_price.fetch_domestic_price")
    async def test_none_when_both_fail(
        self, mock_fetch, mock_cache, mock_get_cache
    ) -> None:
        """API 실패 + 캐시 없으면 None."""
        mock_fetch.return_value = None
        mock_get_cache.return_value = None

        result = await fetch_prices_parallel(["005930"], "key", "secret")
        assert result["005930"] is None

    @patch("app.services.kis_price.set_kis_availability")
    @patch("app.services.kis_price._get_cached_price")
    @patch("app.services.kis_price._cache_price")
    @patch("app.services.kis_price.fetch_domestic_price")
    async def test_bulk_failure_sets_unavailable(
        self, mock_fetch, mock_cache, mock_get_cache, mock_set_avail
    ) -> None:
        """80% 이상 종목 fetch 실패 시 KIS 가용성 플래그를 False로 전환한다."""
        # 5개 중 5개 None 반환 (100% 실패)
        mock_fetch.return_value = None
        mock_get_cache.return_value = None

        tickers = ["A", "B", "C", "D", "E"]
        result = await fetch_prices_parallel(tickers, "key", "secret")

        mock_set_avail.assert_called_once_with(False, "runtime: bulk connect failure")
        for t in tickers:
            assert result[t] is None


@pytest.mark.unit
class TestFetchDomesticPriceErrorClassification:
    """TASK-KIS-OUT-4 / TASK-KIS-OUT-9: 네트워크 오류 분류 및 anyio 회귀."""

    @patch("app.services.kis_price.kis_call_slot", new=_noop_call_slot)
    @patch("app.services.kis_price._get_headers", new_callable=AsyncMock)
    @patch("app.services.kis_price.kis_get", new_callable=AsyncMock)
    async def test_anyio_empty_oserrors_returns_none(
        self, mock_kis_get, mock_headers
    ) -> None:
        """anyio empty oserrors 버그 재현: ValueError 던져도 None 반환 + 예외 전파 없음.

        TASK-KIS-OUT-9: httpx.AsyncClient.get 대신 kis_get을 통해 ValueError
        ('second argument (exceptions) must be a non-empty sequence')가 발생해도
        fetch_domestic_price가 None을 반환하고 예외를 외부로 전파하지 않아야 한다.
        """
        mock_headers.return_value = {}
        mock_kis_get.side_effect = ValueError(
            "second argument (exceptions) must be a non-empty sequence"
        )

        import httpx

        async with httpx.AsyncClient() as client:
            result = await fetch_domestic_price("005930", "key", "secret", client)

        assert result is None

    @patch("app.services.kis_price.kis_call_slot", new=_noop_call_slot)
    @patch("app.services.kis_price._get_headers", new_callable=AsyncMock)
    @patch("app.services.kis_price.kis_get", new_callable=AsyncMock)
    async def test_connect_error_returns_none(
        self, mock_kis_get, mock_headers
    ) -> None:
        """httpx.ConnectError 발생 시 None 반환."""
        import httpx

        mock_headers.return_value = {}
        mock_kis_get.side_effect = httpx.ConnectError("Connection refused")

        async with httpx.AsyncClient() as client:
            result = await fetch_domestic_price("005930", "key", "secret", client)

        assert result is None

    @patch("app.services.kis_price.kis_call_slot", new=_noop_call_slot)
    @patch("app.services.kis_price._get_headers", new_callable=AsyncMock)
    @patch("app.services.kis_price.kis_get", new_callable=AsyncMock)
    async def test_timeout_error_returns_none(
        self, mock_kis_get, mock_headers
    ) -> None:
        """httpx.TimeoutException 발생 시 None 반환."""
        import httpx

        mock_headers.return_value = {}
        mock_kis_get.side_effect = httpx.TimeoutException("Timed out")

        async with httpx.AsyncClient() as client:
            result = await fetch_domestic_price("005930", "key", "secret", client)

        assert result is None
