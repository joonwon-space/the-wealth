"""종목 검색 서비스 단위 테스트."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.stock_search import (
    StockInfo,
    _extract_chosung,
    _is_chosung_query,
    _parse_domestic,
    _parse_overseas,
    search_stocks,
)

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

    @patch("app.services.stock_search._load_stock_list")
    async def test_exact_match_returned_first(self, mock_load) -> None:
        mock_load.return_value = MOCK_STOCKS
        results = await search_stocks("005930")
        assert results[0]["ticker"] == "005930"

    @patch("app.services.stock_search._load_stock_list")
    async def test_chosung_search(self, mock_load) -> None:
        mock_load.return_value = MOCK_STOCKS
        results = await search_stocks("ㅅㅅㅈㅈ")
        assert any(r["ticker"] == "005930" for r in results)

    @patch("app.services.stock_search._load_stock_list")
    async def test_chosung_sk_hynix(self, mock_load) -> None:
        mock_load.return_value = MOCK_STOCKS
        results = await search_stocks("ㅎㅇㄴㅅ")
        assert any(r["ticker"] == "000660" for r in results)


# ---------------------------------------------------------------------------
# _extract_chosung
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestExtractChosung:
    def test_korean_syllables(self) -> None:
        result = _extract_chosung("삼성전자")
        assert result == "ㅅㅅㅈㅈ"

    def test_mixed_korean_and_english(self) -> None:
        result = _extract_chosung("SK하이닉스")
        assert "ㅎ" in result
        assert "S" in result
        assert "K" in result

    def test_english_only(self) -> None:
        result = _extract_chosung("AAPL")
        assert result == "AAPL"

    def test_empty_string(self) -> None:
        result = _extract_chosung("")
        assert result == ""

    def test_numbers_pass_through(self) -> None:
        result = _extract_chosung("005930")
        assert result == "005930"

    def test_naver(self) -> None:
        result = _extract_chosung("네이버")
        assert result == "ㄴㅇㅂ"

    def test_kakao(self) -> None:
        result = _extract_chosung("카카오")
        assert result == "ㅋㅋㅇ"


# ---------------------------------------------------------------------------
# _is_chosung_query
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestIsChosungQuery:
    def test_chosung_only_returns_true(self) -> None:
        assert _is_chosung_query("ㅅㅅ") is True

    def test_mixed_returns_false(self) -> None:
        assert _is_chosung_query("삼성") is False

    def test_english_returns_false(self) -> None:
        assert _is_chosung_query("AAPL") is False

    def test_single_chosung(self) -> None:
        assert _is_chosung_query("ㄱ") is True

    def test_another_chosung(self) -> None:
        assert _is_chosung_query("ㅎ") is True

    def test_full_syllable_not_chosung(self) -> None:
        assert _is_chosung_query("가") is False

    def test_all_19_chosung(self) -> None:
        from app.services.stock_search import _CHOSUNG
        for ch in _CHOSUNG:
            assert _is_chosung_query(ch) is True


# ---------------------------------------------------------------------------
# _parse_domestic
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestParseDomestic:
    """Tests for MST fixed-width file parsing."""

    def _make_mst_line(self, short_code: str, isin: str, name: str) -> bytes:
        """Build a fixed-width MST line (EUC-KR encoded).

        Layout: short_code(9B) + isin(12B) + name(40B)
        Total: 61+ bytes needed to pass the length check.
        """
        name_bytes = name.encode("euc-kr", errors="replace")
        name_bytes = name_bytes[:40].ljust(40, b" ")
        sc_bytes = short_code.encode("euc-kr", errors="replace")[:9].ljust(9, b" ")
        isin_bytes = isin.encode("euc-kr", errors="replace")[:12].ljust(12, b" ")
        return sc_bytes + isin_bytes + name_bytes + b"\n"

    def test_parses_6digit_ticker(self, tmp_path: Path) -> None:
        line = self._make_mst_line("005930", "KR7005930003", "삼성전자")
        mst_file = tmp_path / "kospi_code.mst"
        mst_file.write_bytes(line)

        with patch("app.services.stock_search._DATA_DIR", tmp_path):
            result = _parse_domestic("kospi_code.mst", "KOSPI")

        assert len(result) == 1
        assert result[0]["ticker"] == "005930"
        assert result[0]["name"] == "삼성전자"
        assert result[0]["market"] == "KOSPI"

    def test_parses_multiple_stocks(self, tmp_path: Path) -> None:
        lines = (
            self._make_mst_line("005930", "KR7005930003", "삼성전자")
            + self._make_mst_line("000660", "KR7000660001", "SK하이닉스")
            + self._make_mst_line("035420", "KR7035420009", "NAVER")
        )
        mst_file = tmp_path / "kospi_code.mst"
        mst_file.write_bytes(lines)

        with patch("app.services.stock_search._DATA_DIR", tmp_path):
            result = _parse_domestic("kospi_code.mst", "KOSPI")

        assert len(result) == 3
        tickers = [r["ticker"] for r in result]
        assert "005930" in tickers
        assert "000660" in tickers
        assert "035420" in tickers

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        with patch("app.services.stock_search._DATA_DIR", tmp_path):
            result = _parse_domestic("nonexistent.mst", "KOSPI")
        assert result == []

    def test_skips_short_lines(self, tmp_path: Path) -> None:
        """Lines shorter than 61 bytes are skipped."""
        mst_file = tmp_path / "kospi_code.mst"
        mst_file.write_bytes(b"005930\n")  # only 7 bytes

        with patch("app.services.stock_search._DATA_DIR", tmp_path):
            result = _parse_domestic("kospi_code.mst", "KOSPI")

        assert result == []

    def test_sets_correct_market_label(self, tmp_path: Path) -> None:
        line = self._make_mst_line("293490", "KR7293490008", "카카오")
        mst_file = tmp_path / "kosdaq_code.mst"
        mst_file.write_bytes(line)

        with patch("app.services.stock_search._DATA_DIR", tmp_path):
            result = _parse_domestic("kosdaq_code.mst", "KOSDAQ")

        assert result[0]["market"] == "KOSDAQ"


# ---------------------------------------------------------------------------
# _parse_overseas
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestParseOverseas:
    """Tests for COD tab-delimited file parsing."""

    def _make_cod_line(self, ticker: str, kr_name: str = "", en_name: str = "") -> bytes:
        """Build a tab-delimited COD line (EUC-KR encoded).

        Fields: country | exchange_code | exchange_name | exchange_kr |
                ticker | ticker+exchange | kr_name | en_name | ...
        """
        parts = ["US", "NAS", "NASDAQ", "나스닥", ticker, f"{ticker}.NAS", kr_name, en_name]
        line = "\t".join(parts) + "\n"
        return line.encode("euc-kr", errors="replace")

    def test_parses_ticker_with_kr_name(self, tmp_path: Path) -> None:
        line = self._make_cod_line("AAPL", "애플", "Apple Inc.")
        cod_file = tmp_path / "NASMST.COD"
        cod_file.write_bytes(line)

        with patch("app.services.stock_search._DATA_DIR", tmp_path):
            result = _parse_overseas("NASMST.COD", "NASDAQ")

        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"
        assert result[0]["name"] == "애플"
        assert result[0]["market"] == "NASDAQ"

    def test_falls_back_to_en_name_when_no_kr_name(self, tmp_path: Path) -> None:
        line = self._make_cod_line("NVDA", "", "NVIDIA Corporation")
        cod_file = tmp_path / "NASMST.COD"
        cod_file.write_bytes(line)

        with patch("app.services.stock_search._DATA_DIR", tmp_path):
            result = _parse_overseas("NASMST.COD", "NASDAQ")

        assert result[0]["name"] == "NVIDIA Corporation"

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        with patch("app.services.stock_search._DATA_DIR", tmp_path):
            result = _parse_overseas("NONEXIST.COD", "NYSE")
        assert result == []

    def test_skips_lines_with_fewer_than_8_fields(self, tmp_path: Path) -> None:
        line = b"US\tNAS\tNASDAQ\n"  # only 3 fields
        cod_file = tmp_path / "NASMST.COD"
        cod_file.write_bytes(line)

        with patch("app.services.stock_search._DATA_DIR", tmp_path):
            result = _parse_overseas("NASMST.COD", "NASDAQ")

        assert result == []

    def test_parses_multiple_stocks(self, tmp_path: Path) -> None:
        lines = (
            self._make_cod_line("AAPL", "애플", "Apple")
            + self._make_cod_line("MSFT", "마이크로소프트", "Microsoft")
        )
        cod_file = tmp_path / "NASMST.COD"
        cod_file.write_bytes(lines)

        with patch("app.services.stock_search._DATA_DIR", tmp_path):
            result = _parse_overseas("NASMST.COD", "NASDAQ")

        assert len(result) == 2
        tickers = {r["ticker"] for r in result}
        assert {"AAPL", "MSFT"} == tickers

    def test_sets_correct_market_label(self, tmp_path: Path) -> None:
        parts = ["US", "NYS", "NYSE", "뉴욕", "AMZN", "AMZN.NYS", "아마존", "Amazon"]
        line = ("\t".join(parts) + "\n").encode("euc-kr", errors="replace")
        cod_file = tmp_path / "NYSMST.COD"
        cod_file.write_bytes(line)

        with patch("app.services.stock_search._DATA_DIR", tmp_path):
            result = _parse_overseas("NYSMST.COD", "NYSE")

        assert result[0]["market"] == "NYSE"


# ---------------------------------------------------------------------------
# _load_stock_list (Redis cache miss → file load)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLoadStockListCaching:
    """Tests that _load_stock_list hits Redis and falls back to file parsing."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_parsed_stocks(self) -> None:
        cached_stocks = [{"ticker": "005930", "name": "삼성전자", "market": "KOSPI"}]
        redis_mock = AsyncMock()
        redis_mock.get.return_value = json.dumps(cached_stocks, ensure_ascii=False)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=redis_mock)
        ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.stock_search.get_redis_client", return_value=ctx):
            result = await search_stocks("005930")

        assert any(r["ticker"] == "005930" for r in result)

    @pytest.mark.asyncio
    async def test_cache_miss_loads_from_files(self, tmp_path: Path) -> None:
        """When Redis returns None, stocks are loaded from MST files."""
        redis_mock = AsyncMock()
        redis_mock.get.return_value = None
        redis_mock.setex = AsyncMock()
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=redis_mock)
        ctx.__aexit__ = AsyncMock(return_value=None)

        def _make_line(short_code: str, isin: str, name: str) -> bytes:
            name_bytes = name.encode("euc-kr", errors="replace")[:40].ljust(40, b" ")
            sc_bytes = short_code.encode("euc-kr")[:9].ljust(9, b" ")
            isin_bytes = isin.encode("euc-kr")[:12].ljust(12, b" ")
            return sc_bytes + isin_bytes + name_bytes + b"\n"

        mst_content = _make_line("005930", "KR7005930003", "삼성전자")
        (tmp_path / "kospi_code.mst").write_bytes(mst_content)

        with (
            patch("app.services.stock_search.get_redis_client", return_value=ctx),
            patch("app.services.stock_search._DATA_DIR", tmp_path),
        ):
            result = await search_stocks("005930")

        assert any(r["ticker"] == "005930" for r in result)
        redis_mock.setex.assert_called_once()
