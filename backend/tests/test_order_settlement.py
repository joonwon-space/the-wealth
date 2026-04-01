"""체결 확인 서비스(order_settlement) 단위 테스트."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _register_login(client: AsyncClient, email: str) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


async def _add_kis_account(client: AsyncClient, token: str) -> int:
    resp = await client.post(
        "/users/kis-accounts",
        json={
            "label": "Test Account",
            "account_no": "12345678",
            "acnt_prdt_cd": "01",
            "app_key": "dummy_key",
            "app_secret": "dummy_secret",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _make_balance_raw_result() -> tuple:
    from app.services.kis_account import KisHolding

    summary = {
        "dnca_tot_amt": "1000000",
        "tot_evlu_amt": "1100000",
        "scts_evlu_amt": "700000",
        "evlu_pfls_smtl_amt": "100000",
    }
    holdings = [
        KisHolding(
            ticker="005930",
            name="삼성전자",
            quantity=Decimal("10"),
            avg_price=Decimal("70000"),
            market="KRW",
        )
    ]
    return summary, holdings


async def _setup_portfolio_with_kis(
    client: AsyncClient, email: str
) -> tuple[str, int, int]:
    token = await _register_login(client, email)
    await _add_kis_account(client, token)

    summary, holdings = _make_balance_raw_result()
    with patch(
        "app.api.sync._fetch_balance_raw",
        new_callable=AsyncMock,
        return_value=(summary, holdings),
    ):
        await client.post(
            "/sync/balance",
            headers={"Authorization": f"Bearer {token}"},
        )

    portfolios_resp = await client.get(
        "/portfolios",
        headers={"Authorization": f"Bearer {token}"},
    )
    portfolio_id = portfolios_resp.json()[0]["id"]

    # KIS account ID
    accts_resp = await client.get(
        "/users/kis-accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    kis_id = accts_resp.json()[0]["id"]
    return token, portfolio_id, kis_id


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestSettlePendingOrders:
    """settle_pending_orders 서비스 통합 테스트."""

    async def test_settle_fully_filled_order(self, client: AsyncClient) -> None:
        """pending 주문이 체결 확인되면 filled로 전환되고 transaction/holding이 생성된다."""
        from app.services.kis_order import OrderResult

        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "settle_full@test.com"
        )

        # 1. 주문 접수 (pending → transaction/holding 생성 안 됨)
        mock_result = OrderResult(
            order_no="9999000001",
            ticker="005930",
            order_type="BUY",
            quantity=Decimal("5"),
            price=Decimal("70000"),
            status="pending",
            message="",
        )
        with patch(
            "app.api.orders.place_domestic_order", new_callable=AsyncMock
        ) as mock_order:
            mock_order.return_value = mock_result
            resp = await client.post(
                f"/portfolios/{pid}/orders",
                json={
                    "ticker": "005930",
                    "name": "삼성전자",
                    "order_type": "BUY",
                    "order_class": "limit",
                    "quantity": 5,
                    "price": 70000,
                },
                headers=_auth(token),
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

        # transaction이 없어야 한다
        txn_resp = await client.get(
            f"/portfolios/{pid}/transactions", headers=_auth(token)
        )
        assert txn_resp.json() == []

        # 2. 체결 확인 실행
        from app.services.kis_order import FilledOrderInfo
        from app.services.order_settlement import settle_pending_orders
        from app.db.session import AsyncSessionLocal

        filled_info = FilledOrderInfo(
            order_no="9999000001",
            ticker="005930",
            order_type="BUY",
            filled_quantity=Decimal("5"),
            filled_price=Decimal("69500"),
            total_quantity=Decimal("5"),
            is_fully_filled=True,
        )

        with patch(
            "app.services.order_settlement.check_filled_orders",
            new_callable=AsyncMock,
            return_value=[filled_info],
        ):
            async with AsyncSessionLocal() as db:
                counts = await settle_pending_orders(
                    db=db,
                    portfolio_id=pid,
                    app_key="dummy",
                    app_secret="dummy",
                    account_no="12345678",
                    account_product_code="01",
                )

        assert counts["settled"] == 1
        assert counts["partial"] == 0

        # 3. transaction이 생성되었는지 확인
        txn_resp = await client.get(
            f"/portfolios/{pid}/transactions", headers=_auth(token)
        )
        txns = txn_resp.json()
        assert len(txns) == 1
        assert txns[0]["ticker"] == "005930"

    async def test_settle_partial_fill(self, client: AsyncClient) -> None:
        """부분 체결 시 partial 상태로 전환되고 체결 수량만 반영된다."""
        from app.services.kis_order import OrderResult

        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "settle_partial@test.com"
        )

        mock_result = OrderResult(
            order_no="9999000002",
            ticker="005930",
            order_type="BUY",
            quantity=Decimal("10"),
            price=Decimal("70000"),
            status="pending",
            message="",
        )
        with patch(
            "app.api.orders.place_domestic_order", new_callable=AsyncMock
        ) as mock_order:
            mock_order.return_value = mock_result
            await client.post(
                f"/portfolios/{pid}/orders",
                json={
                    "ticker": "005930",
                    "name": "삼성전자",
                    "order_type": "BUY",
                    "order_class": "limit",
                    "quantity": 10,
                    "price": 70000,
                },
                headers=_auth(token),
            )

        from app.services.kis_order import FilledOrderInfo
        from app.services.order_settlement import settle_pending_orders
        from app.db.session import AsyncSessionLocal

        filled_info = FilledOrderInfo(
            order_no="9999000002",
            ticker="005930",
            order_type="BUY",
            filled_quantity=Decimal("3"),
            filled_price=Decimal("69800"),
            total_quantity=Decimal("10"),
            is_fully_filled=False,
        )

        with patch(
            "app.services.order_settlement.check_filled_orders",
            new_callable=AsyncMock,
            return_value=[filled_info],
        ):
            async with AsyncSessionLocal() as db:
                counts = await settle_pending_orders(
                    db=db,
                    portfolio_id=pid,
                    app_key="dummy",
                    app_secret="dummy",
                    account_no="12345678",
                    account_product_code="01",
                )

        assert counts["settled"] == 0
        assert counts["partial"] == 1

    async def test_settle_no_pending_orders(self, client: AsyncClient) -> None:
        """pending 주문이 없으면 아무 작업도 하지 않는다."""
        from app.services.order_settlement import settle_pending_orders
        from app.db.session import AsyncSessionLocal

        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "settle_none@test.com"
        )

        async with AsyncSessionLocal() as db:
            counts = await settle_pending_orders(
                db=db,
                portfolio_id=pid,
                app_key="dummy",
                app_secret="dummy",
                account_no="12345678",
                account_product_code="01",
            )

        assert counts == {"settled": 0, "partial": 0, "unchanged": 0}
