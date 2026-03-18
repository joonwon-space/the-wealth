"""Ticker regex validation tests for HoldingCreate, TransactionCreate, WatchlistCreate."""

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str | None:
    """Register and login; skip if rate-limited."""
    reg = await client.post(
        "/auth/register", json={"email": email, "password": "Test1234!"}
    )
    if reg.status_code == 429:
        pytest.skip("Rate limit hit during test setup — run individually")
    login = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    if login.status_code == 429:
        pytest.skip("Rate limit hit during test setup — run individually")
    return login.json()["access_token"]


async def _auth(client: AsyncClient, email: str) -> tuple[str, int]:
    token = await _register_and_login(client, email)
    port = await client.post(
        "/portfolios",
        json={"name": "ticker test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, port.json()["id"]


@pytest.mark.unit
class TestTickerValidation:
    """Unit tests for validate_ticker helper."""

    def test_korean_ticker_valid(self) -> None:
        from app.schemas.portfolio import validate_ticker
        assert validate_ticker("005930") == "005930"

    def test_us_ticker_valid(self) -> None:
        from app.schemas.portfolio import validate_ticker
        assert validate_ticker("AAPL") == "AAPL"

    def test_us_ticker_lowercase_normalized(self) -> None:
        from app.schemas.portfolio import validate_ticker
        assert validate_ticker("aapl") == "AAPL"

    def test_us_ticker_5_chars_valid(self) -> None:
        from app.schemas.portfolio import validate_ticker
        assert validate_ticker("GOOGL") == "GOOGL"

    def test_single_letter_us_ticker(self) -> None:
        from app.schemas.portfolio import validate_ticker
        assert validate_ticker("A") == "A"

    def test_invalid_ticker_empty(self) -> None:
        from app.schemas.portfolio import validate_ticker
        with pytest.raises(ValueError):
            validate_ticker("")

    def test_etf_ticker_alphanum_valid(self) -> None:
        # Korean ETF/ETN tickers can mix digits and uppercase letters (e.g. 0087F0)
        from app.schemas.portfolio import validate_ticker
        assert validate_ticker("0087F0") == "0087F0"

    def test_invalid_ticker_7_alphanum(self) -> None:
        # 7-char alphanumeric is not a valid Korean ticker (must be exactly 6)
        from app.schemas.portfolio import validate_ticker
        with pytest.raises(ValueError):
            validate_ticker("0087F00")

    def test_invalid_ticker_too_long_us(self) -> None:
        from app.schemas.portfolio import validate_ticker
        with pytest.raises(ValueError):
            validate_ticker("TOOLONGGG")

    def test_invalid_ticker_7_digits(self) -> None:
        from app.schemas.portfolio import validate_ticker
        with pytest.raises(ValueError):
            validate_ticker("0059300")

    def test_invalid_ticker_5_digits(self) -> None:
        from app.schemas.portfolio import validate_ticker
        with pytest.raises(ValueError):
            validate_ticker("00593")

    def test_invalid_ticker_special_chars(self) -> None:
        from app.schemas.portfolio import validate_ticker
        with pytest.raises(ValueError):
            validate_ticker("AAPL-US")


@pytest.mark.integration
class TestHoldingTickerValidation:
    async def test_holding_create_korean_ticker(self, client: AsyncClient) -> None:
        token, pid = await _auth(client, "htv_k1@test.com")
        resp = await client.post(
            f"/portfolios/{pid}/holdings",
            json={"ticker": "005930", "name": "Samsung", "quantity": 10, "avg_price": 70000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    async def test_holding_create_us_ticker(self, client: AsyncClient) -> None:
        token, pid = await _auth(client, "htv_u1@test.com")
        resp = await client.post(
            f"/portfolios/{pid}/holdings",
            json={"ticker": "AAPL", "name": "Apple", "quantity": 5, "avg_price": 180},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    async def test_holding_create_invalid_ticker(self, client: AsyncClient) -> None:
        token, pid = await _auth(client, "htv_i1@test.com")
        resp = await client.post(
            f"/portfolios/{pid}/holdings",
            json={"ticker": "INVALID123", "name": "Bad", "quantity": 1, "avg_price": 100},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_transaction_create_korean_ticker(self, client: AsyncClient) -> None:
        token, pid = await _auth(client, "ttv_k1@test.com")
        resp = await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "005930", "type": "BUY", "quantity": 1, "price": 70000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    async def test_transaction_create_invalid_ticker(self, client: AsyncClient) -> None:
        token, pid = await _auth(client, "ttv_i1@test.com")
        resp = await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "BAD_TICKER", "type": "BUY", "quantity": 1, "price": 100},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422


@pytest.mark.integration
class TestWatchlistTickerValidation:
    async def test_watchlist_add_korean_ticker(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "wltv_k1@test.com")
        resp = await client.post(
            "/watchlist",
            json={"ticker": "005930", "name": "Samsung", "market": "KRX"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    async def test_watchlist_add_invalid_ticker(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "wltv_i1@test.com")
        resp = await client.post(
            "/watchlist",
            json={"ticker": "TOOLONGGGGG", "name": "Bad", "market": "KRX"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422
