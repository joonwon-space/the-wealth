"""종목 검색 서비스 단위 테스트."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.stock_search import StockInfo, search_stocks


MOCK_STOCKS: list[StockInfo] = [
    {"ticker": "005930", "name": "삼성전자", "market": "KOSPI"},
    {"ticker": "000660", "name": "SK하이닉스", "market": "KOSPI"},
    {"ticker": "035720", "name": "카카오", "market": "KOSPI"},
    {"ticker": "069500", "name": "KODEX 200", "market": "ETF"},
    {"ticker": "105560", "name": "KB자산운용", "market": "KOSDAQ"},
    {"ticker": "252670", "name": "KODEX 200선물인버스2X", "market": "ETF"},
]


@pytest.mark.unit
class TestSearchStocks:
    @patch("app.services.stock_search._load_stock_list")
    async def test_search_by_name(self, mock_load) -> None:
        mock_load.return_value = MOCK_STOCKS
        results = await search_stocks("삼성")
        assert len(results) == 1
        assert results[0]["ticker"] == "005930"

    @patch("app.services.stock_search._load_stock_list")
    async def test_search_by_ticker(self, mock_load) -> None:
        mock_load.return_value = MOCK_STOCKS
        results = await search_stocks("005930")
        assert len(results) == 1
        assert results[0]["name"] == "삼성전자"

    @patch("app.services.stock_search._load_stock_list")
    async def test_search_etf(self, mock_load) -> None:
        mock_load.return_value = MOCK_STOCKS
        results = await search_stocks("KODEX")
        assert len(results) == 2
        assert all(r["market"] == "ETF" for r in results)

    @patch("app.services.stock_search._load_stock_list")
    async def test_search_case_insensitive(self, mock_load) -> None:
        mock_load.return_value = MOCK_STOCKS
        results = await search_stocks("kodex")
        assert len(results) == 2

    @patch("app.services.stock_search._load_stock_list")
    async def test_search_empty_query(self, mock_load) -> None:
        mock_load.return_value = MOCK_STOCKS
        results = await search_stocks("")
        assert results == []

    @patch("app.services.stock_search._load_stock_list")
    async def test_search_no_match(self, mock_load) -> None:
        mock_load.return_value = MOCK_STOCKS
        results = await search_stocks("존재하지않는종목")
        assert results == []

    @patch("app.services.stock_search._load_stock_list")
    async def test_search_limit(self, mock_load) -> None:
        mock_load.return_value = MOCK_STOCKS
        results = await search_stocks("K", limit=2)
        assert len(results) <= 2

    @patch("app.services.stock_search._load_stock_list")
    async def test_search_partial_name(self, mock_load) -> None:
        mock_load.return_value = MOCK_STOCKS
        results = await search_stocks("카카")
        assert len(results) == 1
        assert results[0]["name"] == "카카오"
