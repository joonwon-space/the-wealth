"""CSV 내보내기 엔드포인트 통합 테스트 (holdings CSV, transactions CSV, IDOR 방지)."""

import csv
import io

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    client: AsyncClient, email: str = "csv@example.com"
) -> str:
    """Helper: register user and return access token."""
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_portfolio(
    client: AsyncClient, token: str, name: str = "CSV 테스트"
) -> int:
    resp = await client.post(
        "/portfolios",
        json={"name": name, "currency": "KRW"},
        headers=_auth_headers(token),
    )
    return resp.json()["id"]


async def _add_holding(
    client: AsyncClient,
    token: str,
    portfolio_id: int,
    ticker: str = "005930",
    name: str = "삼성전자",
    quantity: int = 10,
    avg_price: int = 70000,
) -> int:
    resp = await client.post(
        f"/portfolios/{portfolio_id}/holdings",
        json={"ticker": ticker, "name": name, "quantity": quantity, "avg_price": avg_price},
        headers=_auth_headers(token),
    )
    return resp.json()["id"]


async def _add_transaction(
    client: AsyncClient,
    token: str,
    portfolio_id: int,
    ticker: str = "005930",
    txn_type: str = "buy",
    quantity: int = 10,
    price: int = 70000,
) -> int:
    resp = await client.post(
        f"/portfolios/{portfolio_id}/transactions",
        json={"ticker": ticker, "type": txn_type, "quantity": quantity, "price": price},
        headers=_auth_headers(token),
    )
    return resp.json()["id"]


@pytest.mark.integration
class TestHoldingsCSVExport:
    async def test_holdings_csv_returns_200(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_h_200@example.com")
        pid = await _create_portfolio(client, token)
        await _add_holding(client, token, pid)

        resp = await client.get(
            f"/portfolios/{pid}/export/csv", headers=_auth_headers(token)
        )
        assert resp.status_code == 200

    async def test_holdings_csv_content_type(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_h_ct@example.com")
        pid = await _create_portfolio(client, token)

        resp = await client.get(
            f"/portfolios/{pid}/export/csv", headers=_auth_headers(token)
        )
        assert "text/csv" in resp.headers["content-type"]

    async def test_holdings_csv_content_disposition(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_h_cd@example.com")
        pid = await _create_portfolio(client, token)

        resp = await client.get(
            f"/portfolios/{pid}/export/csv", headers=_auth_headers(token)
        )
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert f"holdings_portfolio_{pid}" in resp.headers.get("content-disposition", "")

    async def test_holdings_csv_has_header_row(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_h_header@example.com")
        pid = await _create_portfolio(client, token)

        resp = await client.get(
            f"/portfolios/{pid}/export/csv", headers=_auth_headers(token)
        )
        reader = csv.reader(io.StringIO(resp.text))
        header = next(reader)
        assert "ticker" in header
        assert "quantity" in header
        assert "avg_price" in header

    async def test_holdings_csv_contains_data(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_h_data@example.com")
        pid = await _create_portfolio(client, token)
        await _add_holding(client, token, pid, "005930", "삼성전자", 10, 70000)
        await _add_holding(client, token, pid, "000660", "SK하이닉스", 5, 120000)

        resp = await client.get(
            f"/portfolios/{pid}/export/csv", headers=_auth_headers(token)
        )
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) == 2
        tickers = {row["ticker"] for row in rows}
        assert {"005930", "000660"} == tickers

    async def test_holdings_csv_invested_calculated(self, client: AsyncClient) -> None:
        """invested column should equal quantity * avg_price."""
        token = await _register_and_get_token(client, "csv_h_invest@example.com")
        pid = await _create_portfolio(client, token)
        await _add_holding(client, token, pid, "005930", "삼성전자", 10, 70000)

        resp = await client.get(
            f"/portfolios/{pid}/export/csv", headers=_auth_headers(token)
        )
        reader = csv.DictReader(io.StringIO(resp.text))
        row = next(reader)
        assert float(row["invested"]) == 10 * 70000

    async def test_holdings_csv_empty_portfolio(self, client: AsyncClient) -> None:
        """Empty portfolio should return CSV with only header row."""
        token = await _register_and_get_token(client, "csv_h_empty@example.com")
        pid = await _create_portfolio(client, token)

        resp = await client.get(
            f"/portfolios/{pid}/export/csv", headers=_auth_headers(token)
        )
        assert resp.status_code == 200
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        # Only header row
        assert len(rows) == 1

    async def test_holdings_csv_unauthenticated_denied(self, client: AsyncClient) -> None:
        resp = await client.get("/portfolios/1/export/csv")
        assert resp.status_code in (401, 403)

    async def test_holdings_csv_nonexistent_portfolio(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_h_404@example.com")
        resp = await client.get(
            "/portfolios/99999/export/csv", headers=_auth_headers(token)
        )
        assert resp.status_code == 404


@pytest.mark.integration
class TestTransactionsCSVExport:
    async def test_transactions_csv_returns_200(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_t_200@example.com")
        pid = await _create_portfolio(client, token)
        await _add_transaction(client, token, pid)

        resp = await client.get(
            f"/portfolios/{pid}/transactions/export/csv", headers=_auth_headers(token)
        )
        assert resp.status_code == 200

    async def test_transactions_csv_content_type(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_t_ct@example.com")
        pid = await _create_portfolio(client, token)

        resp = await client.get(
            f"/portfolios/{pid}/transactions/export/csv", headers=_auth_headers(token)
        )
        assert "text/csv" in resp.headers["content-type"]

    async def test_transactions_csv_content_disposition(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_t_cd@example.com")
        pid = await _create_portfolio(client, token)

        resp = await client.get(
            f"/portfolios/{pid}/transactions/export/csv", headers=_auth_headers(token)
        )
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert f"transactions_portfolio_{pid}" in resp.headers.get("content-disposition", "")

    async def test_transactions_csv_has_header_row(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_t_header@example.com")
        pid = await _create_portfolio(client, token)

        resp = await client.get(
            f"/portfolios/{pid}/transactions/export/csv", headers=_auth_headers(token)
        )
        reader = csv.reader(io.StringIO(resp.text))
        header = next(reader)
        assert "ticker" in header
        assert "type" in header
        assert "quantity" in header
        assert "price" in header
        assert "total" in header

    async def test_transactions_csv_contains_data(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_t_data@example.com")
        pid = await _create_portfolio(client, token)
        await _add_transaction(client, token, pid, "005930", "buy", 10, 70000)
        await _add_transaction(client, token, pid, "000660", "sell", 5, 120000)

        resp = await client.get(
            f"/portfolios/{pid}/transactions/export/csv", headers=_auth_headers(token)
        )
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) == 2
        tickers = {row["ticker"] for row in rows}
        assert {"005930", "000660"} == tickers

    async def test_transactions_csv_total_calculated(self, client: AsyncClient) -> None:
        """total column should equal quantity * price."""
        token = await _register_and_get_token(client, "csv_t_total@example.com")
        pid = await _create_portfolio(client, token)
        await _add_transaction(client, token, pid, "005930", "buy", 10, 70000)

        resp = await client.get(
            f"/portfolios/{pid}/transactions/export/csv", headers=_auth_headers(token)
        )
        reader = csv.DictReader(io.StringIO(resp.text))
        row = next(reader)
        assert float(row["total"]) == 10 * 70000

    async def test_transactions_csv_empty_portfolio(self, client: AsyncClient) -> None:
        """Empty portfolio should return CSV with only header row."""
        token = await _register_and_get_token(client, "csv_t_empty@example.com")
        pid = await _create_portfolio(client, token)

        resp = await client.get(
            f"/portfolios/{pid}/transactions/export/csv", headers=_auth_headers(token)
        )
        assert resp.status_code == 200
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) == 1

    async def test_transactions_csv_unauthenticated_denied(self, client: AsyncClient) -> None:
        resp = await client.get("/portfolios/1/transactions/export/csv")
        assert resp.status_code in (401, 403)

    async def test_transactions_csv_nonexistent_portfolio(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "csv_t_404@example.com")
        resp = await client.get(
            "/portfolios/99999/transactions/export/csv", headers=_auth_headers(token)
        )
        assert resp.status_code == 404


@pytest.mark.integration
class TestCSVExportIDOR:
    async def test_holdings_csv_idor_blocked(self, client: AsyncClient) -> None:
        """User B cannot export User A's holdings CSV."""
        token_a = await _register_and_get_token(client, "csv_idor_a@example.com")
        token_b = await _register_and_get_token(client, "csv_idor_b@example.com")

        pid = await _create_portfolio(client, token_a)
        await _add_holding(client, token_a, pid)

        resp = await client.get(
            f"/portfolios/{pid}/export/csv", headers=_auth_headers(token_b)
        )
        assert resp.status_code in (403, 404)

    async def test_transactions_csv_idor_blocked(self, client: AsyncClient) -> None:
        """User B cannot export User A's transactions CSV."""
        token_a = await _register_and_get_token(client, "csv_idor_ta@example.com")
        token_b = await _register_and_get_token(client, "csv_idor_tb@example.com")

        pid = await _create_portfolio(client, token_a)
        await _add_transaction(client, token_a, pid)

        resp = await client.get(
            f"/portfolios/{pid}/transactions/export/csv", headers=_auth_headers(token_b)
        )
        assert resp.status_code in (403, 404)
