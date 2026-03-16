"""KIS price 서비스 단위 테스트 — Redis 캐시 폴백 로직."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.services.kis_price import (
    _cache_price,
    _get_cached_price,
    fetch_prices_parallel,
)


@pytest.mark.unit
class TestPriceCache:
    @patch("app.services.kis_price.aioredis")
    async def test_cache_and_retrieve(self, mock_aioredis) -> None:
        """캐시 저장 후 조회 시 값이 반환되어야 한다."""
        store: dict[str, str] = {}

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(side_effect=lambda k, t, v: store.update({k: v}))
        mock_redis.get = AsyncMock(side_effect=lambda k: store.get(k))
        mock_redis.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_redis.__aexit__ = AsyncMock(return_value=False)
        mock_aioredis.from_url.return_value = mock_redis

        await _cache_price("005930", Decimal("70000"))
        result = await _get_cached_price("005930")
        assert result == Decimal("70000")

    @patch("app.services.kis_price.aioredis")
    async def test_cache_miss_returns_none(self, mock_aioredis) -> None:
        """캐시에 없으면 None 반환."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_redis.__aexit__ = AsyncMock(return_value=False)
        mock_aioredis.from_url.return_value = mock_redis

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
