"""Extended KIS price service tests — httpx response mocking for all scenarios.

Covers fetch_domestic_price, fetch_overseas_price, fetch_domestic_daily_ohlcv,
fetch_usd_krw_rate, fetch_overseas_price_detail with success / 429 / 401 /
timeout / empty-response scenarios. Target: services/kis_price.py 85%+.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.kis_price import (
    _cache_price,
    _get_cached_price,
    fetch_domestic_daily_ohlcv,
    fetch_domestic_price,
    fetch_overseas_price,
    fetch_overseas_price_detail,
    fetch_usd_krw_rate,
)


def _make_response(status_code: int, json_body: dict) -> MagicMock:
    """Build a mock httpx.Response with given status + JSON body."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json = MagicMock(return_value=json_body)
    if status_code >= 400:
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                f"HTTP {status_code}",
                request=MagicMock(),
                response=resp,
            )
        )
    else:
        resp.raise_for_status = MagicMock(return_value=None)
    return resp


def _make_error_response(status_code: int) -> MagicMock:
    return _make_response(status_code, {"error": "err"})


# ---------------------------------------------------------------------------
# fetch_domestic_price
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchDomesticPrice:
    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_success(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        response = _make_response(200, {"output": {"stck_prpr": "75000"}})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_domestic_price("005930", "key", "secret", mock_client)
        assert result == Decimal("75000")

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_empty_price_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        response = _make_response(200, {"output": {"stck_prpr": ""}})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_domestic_price("005930", "key", "secret", mock_client)
        assert result is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_429_rate_limit_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        error_response = _make_error_response(429)
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=error_response)

        result = await fetch_domestic_price("005930", "key", "secret", mock_client)
        assert result is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_401_unauthorized_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        error_response = _make_error_response(401)
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=error_response)

        result = await fetch_domestic_price("005930", "key", "secret", mock_client)
        assert result is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_timeout_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        result = await fetch_domestic_price("005930", "key", "secret", mock_client)
        assert result is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_missing_output_key_returns_zero_decimal(
        self, mock_token: AsyncMock
    ) -> None:
        """When output dict is missing, stck_prpr defaults to '0', returning Decimal('0')."""
        mock_token.return_value = "fake-token"
        response = _make_response(200, {})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_domestic_price("005930", "key", "secret", mock_client)
        # stck_prpr defaults to "0" → Decimal("0"), not None (actual service behavior)
        assert result == Decimal("0")


# ---------------------------------------------------------------------------
# fetch_overseas_price
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchOverseasPrice:
    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_success(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        response = _make_response(200, {"output": {"last": "185.50"}})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_overseas_price("AAPL", "NAS", "key", "secret", mock_client)
        assert result == Decimal("185.50")

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_empty_price_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        response = _make_response(200, {"output": {"last": ""}})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_overseas_price("AAPL", "NAS", "key", "secret", mock_client)
        assert result is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_429_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_make_error_response(429))

        result = await fetch_overseas_price("AAPL", "NAS", "key", "secret", mock_client)
        assert result is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_timeout_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("t/o"))

        result = await fetch_overseas_price("AAPL", "NAS", "key", "secret", mock_client)
        assert result is None


# ---------------------------------------------------------------------------
# fetch_domestic_daily_ohlcv
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchDomesticDailyOhlcv:
    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_success(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        row = {
            "stck_clpr": "75000",
            "stck_oprc": "74000",
            "stck_hgpr": "76000",
            "stck_lwpr": "73500",
            "acml_vol": "1234567",
        }
        response = _make_response(200, {"output2": [row]})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_domestic_daily_ohlcv(
            "005930", "key", "secret", mock_client
        )
        assert result is not None
        assert result["close"] == Decimal("75000")
        assert result["open"] == Decimal("74000")
        assert result["volume"] == 1234567

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_empty_output2_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        response = _make_response(200, {"output2": []})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_domestic_daily_ohlcv(
            "005930", "key", "secret", mock_client
        )
        assert result is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_zero_close_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        row = {"stck_clpr": "0"}
        response = _make_response(200, {"output2": [row]})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_domestic_daily_ohlcv(
            "005930", "key", "secret", mock_client
        )
        assert result is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_with_explicit_target_date(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        row = {"stck_clpr": "80000", "stck_oprc": "79000", "stck_hgpr": "81000",
               "stck_lwpr": "78000", "acml_vol": "500000"}
        response = _make_response(200, {"output2": [row]})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_domestic_daily_ohlcv(
            "005930", "key", "secret", mock_client, target_date="20250101"
        )
        assert result is not None
        assert result["close"] == Decimal("80000")

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_timeout_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("t/o"))

        result = await fetch_domestic_daily_ohlcv(
            "005930", "key", "secret", mock_client
        )
        assert result is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_row_with_missing_optional_fields(self, mock_token: AsyncMock) -> None:
        """Row with only close value — optional fields yield None."""
        mock_token.return_value = "fake-token"
        row = {"stck_clpr": "75000"}
        response = _make_response(200, {"output2": [row]})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_domestic_daily_ohlcv(
            "005930", "key", "secret", mock_client
        )
        assert result is not None
        assert result["close"] == Decimal("75000")
        assert result["open"] is None
        assert result["volume"] is None


# ---------------------------------------------------------------------------
# fetch_usd_krw_rate
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchUsdKrwRate:
    @patch("app.core.redis_cache.get_redis_client")
    async def test_success_with_cache_miss(self, mock_get_client: MagicMock) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # cache miss
        mock_redis.setex = AsyncMock()
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_redis)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = ctx

        # frankfurter.app 응답 형식
        response = _make_response(200, {"rates": {"KRW": 1330.50}})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_usd_krw_rate("key", "secret", mock_client)
        assert result == Decimal("1330.5")

    @patch("app.core.redis_cache.get_redis_client")
    async def test_cache_hit_returns_cached(self, mock_get_client: MagicMock) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="1340.00")  # cache hit
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_redis)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = ctx

        mock_client = AsyncMock(spec=httpx.AsyncClient)

        result = await fetch_usd_krw_rate("key", "secret", mock_client)
        assert result == Decimal("1340.00")
        # Client should NOT be called since cache was hit
        mock_client.get.assert_not_called()

    @patch("app.core.redis_cache.get_redis_client")
    async def test_fallback_on_api_failure(self, mock_get_client: MagicMock) -> None:
        """API timeout/error → fallback rate 1450."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # cache miss
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_redis)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = ctx

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("t/o"))

        result = await fetch_usd_krw_rate("key", "secret", mock_client)
        assert result == Decimal("1450")

    @patch("app.core.redis_cache.get_redis_client")
    async def test_zero_rate_uses_fallback(self, mock_get_client: MagicMock) -> None:
        """Zero/empty exchange rate in response → fallback."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_redis)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = ctx

        response = _make_response(200, {"rates": {"KRW": 0}})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_usd_krw_rate("key", "secret", mock_client)
        assert result == Decimal("1450")


# ---------------------------------------------------------------------------
# fetch_overseas_price_detail
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchOverseasPriceDetail:
    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_success(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        response = _make_response(
            200,
            {"output": {"last": "185.50", "rate": "1.25", "base": "183.20"}},
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        detail = await fetch_overseas_price_detail(
            "AAPL", "NAS", "key", "secret", mock_client
        )
        assert detail is not None
        assert detail.current == Decimal("185.50")
        assert detail.day_change_rate == Decimal("1.25")
        assert detail.prev_close == Decimal("183.20")

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_zero_price_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        response = _make_response(200, {"output": {"last": "0"}})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        detail = await fetch_overseas_price_detail(
            "AAPL", "NAS", "key", "secret", mock_client
        )
        assert detail is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_empty_price_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        response = _make_response(200, {"output": {"last": ""}})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        detail = await fetch_overseas_price_detail(
            "AAPL", "NAS", "key", "secret", mock_client
        )
        assert detail is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_zero_prev_close_becomes_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        response = _make_response(
            200, {"output": {"last": "150.0", "rate": "0.5", "base": "0"}}
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        detail = await fetch_overseas_price_detail(
            "MSFT", "NAS", "key", "secret", mock_client
        )
        assert detail is not None
        assert detail.prev_close is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_401_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_make_error_response(401))

        detail = await fetch_overseas_price_detail(
            "AAPL", "NAS", "key", "secret", mock_client
        )
        assert detail is None

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    async def test_timeout_returns_none(self, mock_token: AsyncMock) -> None:
        mock_token.return_value = "fake-token"
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("t/o"))

        detail = await fetch_overseas_price_detail(
            "AAPL", "NAS", "key", "secret", mock_client
        )
        assert detail is None


# ---------------------------------------------------------------------------
# _cache_price / _get_cached_price Redis error handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCachePriceErrorHandling:
    def setup_method(self) -> None:
        """각 테스트 전에 in-memory fallback 캐시를 초기화한다."""
        from app.core.redis_cache import reset_fallback_cache
        reset_fallback_cache()

    @patch("app.core.redis_cache.get_redis_client")
    async def test_cache_price_redis_error_silently_ignored(
        self, mock_get_client: MagicMock
    ) -> None:
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(side_effect=ConnectionError("redis down"))
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_redis)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = ctx

        # Should not raise — falls back to in-memory cache
        await _cache_price("005930", Decimal("70000"))

    @patch("app.core.redis_cache.get_redis_client")
    async def test_get_cached_price_redis_error_returns_none(
        self, mock_get_client: MagicMock
    ) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=ConnectionError("redis down"))
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_redis)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = ctx

        # Redis fails → fallback to in-memory, which is empty → returns None
        result = await _get_cached_price("fresh_key_12345")
        assert result is None


# ---------------------------------------------------------------------------
# fetch_prices_parallel — overseas market branch
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchPricesParallelOverseas:
    @patch("app.services.kis_price._get_cached_price")
    @patch("app.services.kis_price._cache_price")
    @patch("app.services.kis_price.fetch_overseas_price")
    async def test_overseas_market_calls_fetch_overseas(
        self, mock_fetch_overseas: AsyncMock, mock_cache: AsyncMock, mock_get_cache: AsyncMock
    ) -> None:
        """market != 'domestic' uses fetch_overseas_price."""
        from app.services.kis_price import fetch_prices_parallel

        mock_fetch_overseas.return_value = Decimal("185.50")
        mock_cache.return_value = None

        result = await fetch_prices_parallel(["AAPL"], "key", "secret", market="NAS")
        assert result["AAPL"] == Decimal("185.50")
        mock_fetch_overseas.assert_called_once()


# ---------------------------------------------------------------------------
# fetch_usd_krw_rate — Redis cache-write error silently ignored
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchUsdKrwRateCacheWriteError:
    def setup_method(self) -> None:
        """각 테스트 전에 in-memory fallback 캐시를 초기화한다."""
        from app.core.redis_cache import reset_fallback_cache
        reset_fallback_cache()

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.core.redis_cache.get_redis_client")
    async def test_cache_write_error_silently_ignored(
        self, mock_get_client: MagicMock, mock_token: AsyncMock
    ) -> None:
        """Redis setex failure during FX caching should not propagate."""
        mock_token.return_value = "fake-token"

        call_count = 0

        def _get_client_factory(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_redis = AsyncMock()
            if call_count == 1:
                # First call: cache miss (GET)
                mock_redis.get = AsyncMock(return_value=None)
            else:
                # Second call: cache write fails
                mock_redis.setex = AsyncMock(side_effect=ConnectionError("redis down"))
            ctx = MagicMock()
            ctx.__aenter__ = AsyncMock(return_value=mock_redis)
            ctx.__aexit__ = AsyncMock(return_value=None)
            return ctx

        mock_get_client.side_effect = _get_client_factory

        response = _make_response(200, {"rates": {"KRW": 1325.0}})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        # Should not raise even if Redis setex fails (falls back to in-memory)
        result = await fetch_usd_krw_rate("key", "secret", mock_client)
        assert result == Decimal("1325.0")

    @patch("app.services.kis_price.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.core.redis_cache.get_redis_client")
    async def test_redis_get_error_proceeds_to_api(
        self, mock_get_client: MagicMock, mock_token: AsyncMock
    ) -> None:
        """Redis GET error (ConnectionError) → falls through to API call via in-memory fallback."""
        mock_token.return_value = "fake-token"

        mock_redis = AsyncMock()
        # GET throws ConnectionError → RedisCache falls back to in-memory (returns None)
        mock_redis.get = AsyncMock(side_effect=ConnectionError("redis down"))
        mock_redis.setex = AsyncMock()
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_redis)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = ctx

        response = _make_response(200, {"rates": {"KRW": 1310.0}})
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=response)

        result = await fetch_usd_krw_rate("key", "secret", mock_client)
        assert result == Decimal("1310.0")
