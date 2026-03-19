"""해외주식 지원 기능 단위 및 통합 테스트."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.user import User
from app.core.security import hash_password
from app.services.kis_account import KisHolding, fetch_overseas_account_holdings
from app.services.kis_price import (
    fetch_overseas_price_detail,
    fetch_usd_krw_rate,
)
from app.services.reconciliation import reconcile_holdings
from tests.conftest import TEST_DB_URL


# ---------------------------------------------------------------------------
# KisHolding dataclass
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKisHoldingMarketField:
    def test_domestic_holding_has_no_market(self) -> None:
        """국내주식 KisHolding은 market=None."""
        h = KisHolding(
            ticker="005930",
            name="삼성전자",
            quantity=Decimal("10"),
            avg_price=Decimal("70000"),
        )
        assert h.market is None

    def test_overseas_holding_has_market(self) -> None:
        """해외주식 KisHolding은 market 코드가 설정돼야 한다."""
        h = KisHolding(
            ticker="AAPL",
            name="Apple Inc.",
            quantity=Decimal("5"),
            avg_price=Decimal("183.42"),
            market="NAS",
        )
        assert h.market == "NAS"

    def test_kis_holding_is_frozen(self) -> None:
        """KisHolding은 불변 dataclass여야 한다."""
        h = KisHolding(
            ticker="TSLA",
            name="Tesla",
            quantity=Decimal("2"),
            avg_price=Decimal("250.00"),
            market="NAS",
        )
        with pytest.raises(Exception):
            h.ticker = "AMZN"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# fetch_overseas_account_holdings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchOverseasAccountHoldings:
    @patch("app.services.kis_account.get_kis_access_token")
    async def test_returns_holdings_on_success(self, mock_token) -> None:
        """API 응답이 정상이면 KisHolding 리스트 반환."""
        mock_token.return_value = "test-token"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "rt_cd": "0",
            "output1": [
                {
                    "ovrs_pdno": "AAPL",
                    "ovrs_item_name": "Apple Inc.",
                    "ovrs_cblc_qty": "5",
                    "pchs_avg_pric": "183.42",
                    "ovrs_excg_cd": "NAS",
                },
                {
                    "ovrs_pdno": "TSLA",
                    "ovrs_item_name": "Tesla Inc.",
                    "ovrs_cblc_qty": "0",  # 수량 0 — 제외돼야 함
                    "pchs_avg_pric": "250.00",
                    "ovrs_excg_cd": "NAS",
                },
            ],
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.services.kis_account.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            holdings, summary = await fetch_overseas_account_holdings("key", "secret", "12345678", "01")

        assert len(holdings) == 1
        assert holdings[0].ticker == "AAPL"
        assert holdings[0].market == "NAS"
        assert holdings[0].quantity == Decimal("5")
        assert holdings[0].avg_price == Decimal("183.42")
        assert isinstance(summary, dict)

    @patch("app.services.kis_account.get_kis_access_token")
    async def test_returns_empty_on_api_error(self, mock_token) -> None:
        """API rt_cd != '0' 이면 빈 리스트 반환."""
        mock_token.return_value = "test-token"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"rt_cd": "1", "msg1": "Error"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.services.kis_account.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            holdings, summary = await fetch_overseas_account_holdings("key", "secret", "12345678", "01")

        assert holdings == []
        assert summary == {}

    @patch("app.services.kis_account.get_kis_access_token")
    async def test_returns_empty_on_exception(self, mock_token) -> None:
        """예외 발생 시 빈 리스트 반환."""
        mock_token.return_value = "test-token"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("network error"))

        with patch("app.services.kis_account.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            holdings, summary = await fetch_overseas_account_holdings("key", "secret", "12345678", "01")

        assert holdings == []
        assert summary == {}


# ---------------------------------------------------------------------------
# fetch_overseas_price_detail
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchOverseasPriceDetail:
    @patch("app.services.kis_price.get_kis_access_token")
    async def test_returns_detail_on_success(self, mock_token) -> None:
        """API 응답이 정상이면 OverseasPriceDetail 반환."""
        mock_token.return_value = "test-token"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "output": {
                "last": "183.42",
                "rate": "1.25",
                "base": "181.15",
            }
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await fetch_overseas_price_detail("AAPL", "NAS", "key", "secret", mock_client)

        assert result is not None
        assert result.current == Decimal("183.42")
        assert result.day_change_rate == Decimal("1.25")
        assert result.prev_close == Decimal("181.15")

    @patch("app.services.kis_price.get_kis_access_token")
    async def test_returns_none_when_price_zero(self, mock_token) -> None:
        """가격이 0 이면 None 반환."""
        mock_token.return_value = "test-token"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"output": {"last": "0"}}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await fetch_overseas_price_detail("AAPL", "NAS", "key", "secret", mock_client)
        assert result is None

    @patch("app.services.kis_price.get_kis_access_token")
    async def test_returns_none_on_exception(self, mock_token) -> None:
        """예외 발생 시 None 반환."""
        mock_token.return_value = "test-token"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("timeout"))

        result = await fetch_overseas_price_detail("AAPL", "NAS", "key", "secret", mock_client)
        assert result is None


# ---------------------------------------------------------------------------
# fetch_usd_krw_rate
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchUsdKrwRate:
    @patch("app.core.redis_cache.aioredis")
    @patch("app.services.kis_price.get_kis_access_token")
    async def test_returns_cached_rate(self, mock_token, mock_aioredis) -> None:
        """Redis에 캐시된 환율이 있으면 API 호출 없이 반환."""
        mock_token.return_value = "test-token"

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="1380.5")
        mock_redis.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_redis.__aexit__ = AsyncMock(return_value=False)
        mock_aioredis.from_url.return_value = mock_redis

        mock_client = AsyncMock()
        result = await fetch_usd_krw_rate("key", "secret", mock_client)

        assert result == Decimal("1380.5")
        mock_client.get.assert_not_called()

    @patch("app.core.redis_cache.aioredis")
    @patch("app.services.kis_price.get_kis_access_token")
    async def test_fallback_rate_on_exception(self, mock_token, mock_aioredis) -> None:
        """API 호출 및 캐시 모두 실패하면 fallback 1350 반환."""
        mock_token.return_value = "test-token"

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.__aenter__ = AsyncMock(return_value=mock_redis)
        mock_redis.__aexit__ = AsyncMock(return_value=False)
        mock_aioredis.from_url.return_value = mock_redis

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("network error"))

        result = await fetch_usd_krw_rate("key", "secret", mock_client)
        assert result == Decimal("1350")


# ---------------------------------------------------------------------------
# reconcile_holdings — market 컬럼 저장 검증
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReconcileHoldingsWithMarket:
    async def test_insert_overseas_holding_with_market(self) -> None:
        """해외주식 INSERT 시 market 컬럼이 저장돼야 한다."""
        engine = create_async_engine(TEST_DB_URL, echo=False)
        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        async with factory() as db:
            user = User(
                email="overseas_recon@test.com",
                hashed_password=hash_password("test"),
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            portfolio = Portfolio(user_id=user.id, name="test")
            db.add(portfolio)
            await db.commit()
            await db.refresh(portfolio)

            kis_holdings = [
                KisHolding(
                    ticker="AAPL",
                    name="Apple Inc.",
                    quantity=Decimal("5"),
                    avg_price=Decimal("183.42"),
                    market="NAS",
                ),
            ]
            counts = await reconcile_holdings(db, portfolio.id, kis_holdings)
            assert counts["inserted"] == 1

            from sqlalchemy import select

            result = await db.execute(
                select(Holding).where(Holding.portfolio_id == portfolio.id)
            )
            holding = result.scalar_one()
            assert holding.ticker == "AAPL"
            assert holding.market == "NAS"

        await engine.dispose()

    async def test_update_holding_market_on_change(self) -> None:
        """market 코드가 변경되면 UPDATE 카운트에 포함돼야 한다."""
        engine = create_async_engine(TEST_DB_URL, echo=False)
        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        async with factory() as db:
            user = User(
                email="overseas_recon2@test.com",
                hashed_password=hash_password("test"),
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            portfolio = Portfolio(user_id=user.id, name="test")
            db.add(portfolio)
            await db.commit()
            await db.refresh(portfolio)

            # 기존 holding — market=None
            holding = Holding(
                portfolio_id=portfolio.id,
                ticker="AAPL",
                name="Apple Inc.",
                quantity=Decimal("5"),
                avg_price=Decimal("183.42"),
                market=None,
            )
            db.add(holding)
            await db.commit()

            # KIS에서 market=NAS로 업데이트
            kis_holdings = [
                KisHolding(
                    ticker="AAPL",
                    name="Apple Inc.",
                    quantity=Decimal("5"),
                    avg_price=Decimal("183.42"),
                    market="NAS",
                ),
            ]
            counts = await reconcile_holdings(db, portfolio.id, kis_holdings)
            assert counts["updated"] == 1

        await engine.dispose()


# ---------------------------------------------------------------------------
# Dashboard integration — overseas holding with currency
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDashboardOverseasHolding:
    async def test_overseas_holding_shows_usd_currency(self, client) -> None:
        """해외주식 holding은 currency='USD'로 반환돼야 한다."""
        # 사용자 등록/로그인
        await client.post(
            "/auth/register",
            json={"email": "overseas_dash@example.com", "password": "Test1234!"},
        )
        resp = await client.post(
            "/auth/login",
            json={"email": "overseas_dash@example.com", "password": "Test1234!"},
        )
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 포트폴리오 생성
        port = await client.post("/portfolios", json={"name": "test"}, headers=headers)
        pid = port.json()["id"]

        # 해외주식 추가 (ticker: AAPL)
        await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "quantity": 5,
                "avg_price": 183.42,
                "market": "NAS",
            },
            headers=headers,
        )

        resp = await client.get("/dashboard/summary", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["holdings"]) == 1
        holding = data["holdings"][0]
        assert holding["currency"] == "USD"
        assert holding["ticker"] == "AAPL"

    async def test_domestic_holding_shows_krw_currency(self, client) -> None:
        """국내주식 holding은 currency='KRW'로 반환돼야 한다."""
        await client.post(
            "/auth/register",
            json={"email": "domestic_dash@example.com", "password": "Test1234!"},
        )
        resp = await client.post(
            "/auth/login",
            json={"email": "domestic_dash@example.com", "password": "Test1234!"},
        )
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        port = await client.post("/portfolios", json={"name": "test"}, headers=headers)
        pid = port.json()["id"]

        await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "005930",
                "name": "삼성전자",
                "quantity": 10,
                "avg_price": 70000,
            },
            headers=headers,
        )

        resp = await client.get("/dashboard/summary", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["holdings"]) == 1
        holding = data["holdings"][0]
        assert holding["currency"] == "KRW"
