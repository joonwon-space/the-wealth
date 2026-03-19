"""KIS API 가용성 상태 관리 단위 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def reset_kis_state() -> None:
    """각 테스트 전후로 KIS 가용성 상태를 초기화."""
    from app.services.kis_health import set_kis_availability

    set_kis_availability(True)
    yield
    set_kis_availability(True)


@pytest.mark.unit
class TestKisHealthState:
    def test_default_state_is_available(self) -> None:
        from app.services.kis_health import get_kis_availability

        assert get_kis_availability() is True

    def test_set_availability_false(self) -> None:
        from app.services.kis_health import get_kis_availability, set_kis_availability

        set_kis_availability(False, "connection refused")
        assert get_kis_availability() is False

    def test_set_availability_true_resets_error(self) -> None:
        from app.services.kis_health import _state, set_kis_availability

        set_kis_availability(False, "some error")
        set_kis_availability(True)
        assert _state.is_available is True
        assert _state.last_error == ""


@pytest.mark.unit
class TestCheckKisApiHealth:
    @pytest.mark.asyncio
    async def test_sets_available_on_http_success(self) -> None:
        from app.services.kis_health import check_kis_api_health, get_kis_availability

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.kis_health.httpx.AsyncClient", return_value=mock_client):
            result = await check_kis_api_health()

        assert result is True
        assert get_kis_availability() is True

    @pytest.mark.asyncio
    async def test_sets_unavailable_on_timeout(self) -> None:
        from app.services.kis_health import check_kis_api_health, get_kis_availability

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.kis_health.httpx.AsyncClient", return_value=mock_client):
            result = await check_kis_api_health()

        assert result is False
        assert get_kis_availability() is False

    @pytest.mark.asyncio
    async def test_sets_unavailable_on_connect_error(self) -> None:
        from app.services.kis_health import check_kis_api_health, get_kis_availability

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.kis_health.httpx.AsyncClient", return_value=mock_client):
            result = await check_kis_api_health()

        assert result is False
        assert get_kis_availability() is False

    @pytest.mark.asyncio
    async def test_sets_available_on_4xx_response(self) -> None:
        """4xx 응답도 서버가 응답한 것이므로 가용으로 간주."""
        from app.services.kis_health import check_kis_api_health, get_kis_availability

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.kis_health.httpx.AsyncClient", return_value=mock_client):
            result = await check_kis_api_health()

        assert result is True
        assert get_kis_availability() is True

    @pytest.mark.asyncio
    async def test_sets_unavailable_on_unexpected_error(self) -> None:
        from app.services.kis_health import check_kis_api_health, get_kis_availability

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(side_effect=RuntimeError("unexpected"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.kis_health.httpx.AsyncClient", return_value=mock_client):
            result = await check_kis_api_health()

        assert result is False
        assert get_kis_availability() is False


@pytest.mark.unit
class TestFetchPricesParallelCacheOnlyMode:
    @pytest.mark.asyncio
    async def test_skips_api_when_kis_unavailable(self) -> None:
        """KIS 불가 시 API 호출 없이 캐시에서만 조회."""
        from app.services.kis_health import set_kis_availability
        from app.services import kis_price

        set_kis_availability(False)

        with (
            patch.object(kis_price, "fetch_domestic_price", new_callable=AsyncMock) as mock_fetch,
            patch.object(kis_price._cache, "get", new_callable=AsyncMock, return_value="75000"),
        ):
            result = await kis_price.fetch_prices_parallel(
                ["005930"], "key", "secret", "domestic"
            )

        mock_fetch.assert_not_called()
        assert result["005930"] is not None

    @pytest.mark.asyncio
    async def test_calls_api_when_kis_available(self) -> None:
        """KIS 가용 시 정상적으로 API 호출."""
        from app.services.kis_health import set_kis_availability
        from app.services import kis_price
        from decimal import Decimal

        set_kis_availability(True)

        with (
            patch.object(
                kis_price,
                "fetch_domestic_price",
                new_callable=AsyncMock,
                return_value=Decimal("75000"),
            ) as mock_fetch,
            patch.object(kis_price, "_cache_price", new_callable=AsyncMock),
            patch("app.services.kis_price.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await kis_price.fetch_prices_parallel(
                ["005930"], "key", "secret", "domestic"
            )

        mock_fetch.assert_called_once()
        assert result["005930"] == Decimal("75000")
