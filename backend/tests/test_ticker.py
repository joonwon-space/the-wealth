"""Unit tests for app.core.ticker utility."""

import pytest

from app.core.ticker import DOMESTIC_TICKER_RE, is_domestic


@pytest.mark.unit
class TestIsDomestic:
    """Tests for is_domestic() covering KRX and overseas ticker patterns."""

    def test_numeric_6digit_is_domestic(self) -> None:
        assert is_domestic("005930") is True  # Samsung Electronics

    def test_numeric_6digit_sk_hynix(self) -> None:
        assert is_domestic("000660") is True

    def test_alphanumeric_6char_is_domestic(self) -> None:
        assert is_domestic("A00001") is True

    def test_all_uppercase_6char_is_domestic(self) -> None:
        assert is_domestic("AAAAAA") is True

    def test_4char_ticker_is_overseas(self) -> None:
        assert is_domestic("AAPL") is False

    def test_4char_tsla_is_overseas(self) -> None:
        assert is_domestic("TSLA") is False

    def test_4char_msft_is_overseas(self) -> None:
        assert is_domestic("MSFT") is False

    def test_5char_is_overseas(self) -> None:
        assert is_domestic("GOOGL") is False

    def test_7char_is_not_domestic(self) -> None:
        assert is_domestic("0059300") is False

    def test_lowercase_is_not_domestic(self) -> None:
        assert is_domestic("005abc") is False

    def test_empty_string_is_not_domestic(self) -> None:
        assert is_domestic("") is False

    def test_special_chars_is_not_domestic(self) -> None:
        assert is_domestic("005-30") is False

    def test_regex_constant_matches_6_alphanumeric(self) -> None:
        assert DOMESTIC_TICKER_RE.match("123456") is not None
        assert DOMESTIC_TICKER_RE.match("ABC") is None
