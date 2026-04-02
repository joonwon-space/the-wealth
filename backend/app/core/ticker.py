"""Ticker utility functions shared across API modules."""

import re

# Domestic (KRX) tickers are exactly 6 alphanumeric characters.
# Overseas tickers (e.g. AAPL, TSLA) do not match this pattern.
DOMESTIC_TICKER_RE = re.compile(r"^[0-9A-Z]{6}$")


def is_domestic(ticker: str) -> bool:
    """Return True if the ticker is a domestic (KRX) ticker.

    KRX tickers are exactly 6 alphanumeric characters (digits or uppercase
    letters), e.g. '005930' (Samsung), '000660' (SK Hynix).
    Overseas tickers such as 'AAPL' or 'TSLA' do not match and return False.
    """
    return bool(DOMESTIC_TICKER_RE.match(ticker))
