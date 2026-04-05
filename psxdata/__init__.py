"""psxdata — Python library for Pakistan Stock Exchange data.

Public API (implemented in Phase 3):
    stocks(symbol, start, end)     — historical OHLCV data
    tickers(index=None)            — all listed tickers
    indices(name, start, end)      — index historical data
    sectors(name=None)             — sector summaries
    fundamentals(symbol)           — P/E, EPS, Book Value
"""
from psxdata.scrapers.base import BaseScraper

__version__ = "0.1.0"
__all__ = ["BaseScraper"]

# Public API — implemented in Phase 3 API (psxdata/client.py)
# from psxdata.client import stocks, tickers, indices, sectors, fundamentals, market
