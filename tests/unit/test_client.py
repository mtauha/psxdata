"""Unit tests for psxdata/client.py — all mocked, no network required."""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from psxdata.client import PSXClient

# Fixed "today" used throughout — avoids flakiness around midnight.
FIXED_TODAY = pd.Timestamp("2024-06-15")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def freeze_today(monkeypatch):
    """Patch psxdata.client._today() to return FIXED_TODAY for all tests."""
    monkeypatch.setattr("psxdata.client._today", lambda: FIXED_TODAY)


@pytest.fixture
def client(tmp_path):
    """PSXClient with a real isolated DiskCache and all scrapers replaced by MagicMocks."""
    c = PSXClient(cache_dir=str(tmp_path / "cache"))
    c._historical = MagicMock()
    c._screener = MagicMock()
    c._symbols = MagicMock()
    c._indices = MagicMock()
    c._sectors = MagicMock()
    c._fundamentals = MagicMock()
    c._debt_market = MagicMock()
    c._eligible_scrips = MagicMock()
    return c


@pytest.fixture
def today():
    return FIXED_TODAY


@pytest.fixture
def ohlcv_df(today):
    """Sample OHLCV DataFrame spanning yesterday and today."""
    yesterday = today - pd.Timedelta(days=1)
    return pd.DataFrame({
        "date": [yesterday, today],
        "open": [100.0, 101.0],
        "high": [105.0, 106.0],
        "low": [98.0, 99.0],
        "close": [103.0, 104.0],
        "volume": pd.array([10000, 11000], dtype="Int64"),
        "is_anomaly": [False, False],
    })


@pytest.fixture
def hist_only_df(today):
    """Sample OHLCV DataFrame with only historical rows (all dates before today)."""
    day_before = today - pd.Timedelta(days=2)
    yesterday = today - pd.Timedelta(days=1)
    return pd.DataFrame({
        "date": [day_before, yesterday],
        "open": [100.0, 101.0],
        "high": [105.0, 106.0],
        "low": [98.0, 99.0],
        "close": [103.0, 104.0],
        "volume": pd.array([10000, 11000], dtype="Int64"),
        "is_anomaly": [False, False],
    })


@pytest.fixture
def screener_df():
    return pd.DataFrame({
        "symbol": ["ENGRO", "LUCK", "HBL"],
        "price": [250.0, 150.0, 100.0],
        "market_cap": [1e9, 5e8, 8e8],
    })


@pytest.fixture
def symbols_df():
    return pd.DataFrame({
        "symbol": ["ENGRO", "LUCK", "HBL"],
        "name": ["Engro Corp", "Lucky Cement", "HBL"],
        "sector_name": ["Fertilizer", "Cement", "Banks"],
    })


@pytest.fixture
def indices_df():
    return pd.DataFrame({
        "symbol": ["ENGRO", "LUCK"],
        "current_index": [45000.0, 45100.0],
        "idx_weight": [2.5, 1.8],
    })


@pytest.fixture
def sectors_df():
    return pd.DataFrame({
        "sector_code": [1, 2],
        "sector_name": ["Fertilizer", "Cement"],
        "advance": [5, 3],
        "decline": [2, 4],
        "unchanged": [1, 1],
        "turnover": [1e8, 5e7],
        "market_cap_b": [50.0, 30.0],
    })


@pytest.fixture
def fundamentals_df():
    return pd.DataFrame({
        "symbol": ["ENGRO", "ENGRO", "LUCK"],
        "year": [2024, 2023, 2024],
        "type": ["Annual", "Annual", "Annual"],
        "period_ended": pd.to_datetime(["2024-12-31", "2023-12-31", "2024-12-31"]),
        "posting_date": pd.to_datetime(["2025-02-15", "2024-02-10", "2025-02-20"]),
    })


# ---------------------------------------------------------------------------
# stocks()
# ---------------------------------------------------------------------------

class TestStocks:
    def test_stocks_cache_miss_fetches_scraper(self, client, ohlcv_df):
        """On cache miss the scraper is called and the result is returned."""
        client._historical.fetch.return_value = ohlcv_df
        result = client.stocks("ENGRO", cache=True)
        client._historical.fetch.assert_called_once_with("ENGRO", start=None, end=None)
        assert not result.empty

    def test_stocks_cache_hit_skips_scraper(self, client, hist_only_df, today):
        """When historical data is cached and today is not needed, scraper is not called."""
        yesterday = today - pd.Timedelta(days=1)
        client._cache.set("ENGRO_historical", hist_only_df, ttl=None)
        result = client.stocks("ENGRO", end=yesterday.date(), cache=True)
        client._historical.fetch.assert_not_called()
        assert len(result) == len(hist_only_df)

    def test_stocks_today_split_cached_separately(self, client, ohlcv_df, today):
        """After a cache miss, historical and today rows are stored under separate keys."""
        client._historical.fetch.return_value = ohlcv_df
        client.stocks("ENGRO", cache=True)
        hist_cached = client._cache.get("ENGRO_historical")
        today_cached = client._cache.get("ENGRO_today")
        assert hist_cached is not None, "historical rows should be cached"
        assert today_cached is not None, "today rows should be cached"
        assert (hist_cached["date"] < today).all()
        assert (today_cached["date"] >= today).all()

    def test_stocks_day_boundary_today_cache_covers_past_end(self, client, today):
        """After day rollover, yesterday's row in {sym}_today is returned for end=yesterday.

        Regression: before the fix, need_today=False caused {sym}_today to be skipped
        entirely, so the most recent historical row (not yet moved to {sym}_historical)
        was silently omitted.
        """
        yesterday = today - pd.Timedelta(days=1)
        day_before = today - pd.Timedelta(days=2)

        # Simulate post-rollover state: historical only has data up to day_before;
        # yesterday's row is still in the today cache (not yet expired).
        hist_df = pd.DataFrame({
            "date": [day_before],
            "open": [100.0], "high": [105.0], "low": [98.0], "close": [103.0],
            "volume": pd.array([10000], dtype="Int64"), "is_anomaly": [False],
        })
        today_df = pd.DataFrame({
            "date": [yesterday],
            "open": [101.0], "high": [106.0], "low": [99.0], "close": [104.0],
            "volume": pd.array([11000], dtype="Int64"), "is_anomaly": [False],
        })
        client._cache.set("ENGRO_historical", hist_df, ttl=None)
        client._cache.set("ENGRO_today", today_df, ttl=900)

        result = client.stocks("ENGRO", end=yesterday.date(), cache=True)

        client._historical.fetch.assert_not_called()
        assert len(result) == 2
        assert yesterday in result["date"].values

    def test_stocks_cache_false_bypasses_cache(self, client, ohlcv_df):
        """cache=False always calls the scraper regardless of what is in cache."""
        client._historical.fetch.return_value = ohlcv_df
        client.stocks("ENGRO", cache=True)   # populates cache
        client.stocks("ENGRO", cache=False)  # must bypass and call again
        assert client._historical.fetch.call_count == 2

    def test_stocks_invalid_range_raises(self, client):
        """start > end raises ValueError before any scraper call."""
        with pytest.raises(ValueError, match="must not be after"):
            client.stocks("ENGRO", start="2024-12-31", end="2024-01-01")
        client._historical.fetch.assert_not_called()

    def test_stocks_empty_response(self, client):
        """Scraper returning empty DataFrame is forwarded unchanged."""
        empty = pd.DataFrame(
            columns=["date", "open", "high", "low", "close", "volume", "is_anomaly"]
        )
        client._historical.fetch.return_value = empty
        result = client.stocks("ENGRO", cache=False)
        assert result.empty
        assert list(result.columns) == [
            "date", "open", "high", "low", "close", "volume", "is_anomaly"
        ]


# ---------------------------------------------------------------------------
# quote()
# ---------------------------------------------------------------------------

class TestQuote:
    def test_quote_returns_matching_row(self, client, screener_df):
        """quote() returns the single row matching the requested symbol."""
        client._screener.fetch.return_value = screener_df
        result = client.quote("ENGRO", cache=False)
        assert len(result) == 1
        assert result["symbol"].iloc[0] == "ENGRO"

    def test_quote_unknown_symbol_returns_empty(self, client, screener_df):
        """Symbol absent from the screener returns an empty DataFrame."""
        client._screener.fetch.return_value = screener_df
        result = client.quote("XXXX", cache=False)
        assert result.empty

    def test_quote_caches_screener(self, client, screener_df):
        """Screener is fetched once; subsequent calls for different symbols reuse it."""
        client._screener.fetch.return_value = screener_df
        client.quote("ENGRO", cache=True)
        client.quote("LUCK", cache=True)
        client._screener.fetch.assert_called_once()


# ---------------------------------------------------------------------------
# tickers()
# ---------------------------------------------------------------------------

class TestTickers:
    def test_tickers_no_index(self, client, symbols_df):
        """tickers() with no index returns all symbol strings from SymbolsScraper."""
        client._symbols.fetch.return_value = symbols_df
        result = client.tickers(cache=False)
        client._symbols.fetch.assert_called_once()
        assert result == ["ENGRO", "LUCK", "HBL"]
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_tickers_with_index(self, client, indices_df):
        """tickers(index=...) uses IndicesScraper and extracts the symbol column."""
        client._indices.fetch.return_value = indices_df
        result = client.tickers(index="KSE100", cache=False)
        client._indices.fetch.assert_called_once_with("KSE100")
        assert result == ["ENGRO", "LUCK"]

    def test_tickers_empty_result(self, client):
        """Scraper returning empty DataFrame yields an empty list."""
        client._symbols.fetch.return_value = pd.DataFrame()
        result = client.tickers(cache=False)
        assert result == []


# ---------------------------------------------------------------------------
# indices()
# ---------------------------------------------------------------------------

class TestIndices:
    def test_indices_returns_dataframe(self, client, indices_df):
        """indices() returns the full constituent DataFrame from IndicesScraper."""
        client._indices.fetch.return_value = indices_df
        result = client.indices("KSE100", cache=False)
        client._indices.fetch.assert_called_once_with("KSE100")
        pd.testing.assert_frame_equal(result, indices_df)


# ---------------------------------------------------------------------------
# sectors()
# ---------------------------------------------------------------------------

class TestSectors:
    def test_sectors_returns_dataframe(self, client, sectors_df):
        """sectors() returns the full sector summary DataFrame."""
        client._sectors.fetch.return_value = sectors_df
        result = client.sectors(cache=False)
        client._sectors.fetch.assert_called_once()
        pd.testing.assert_frame_equal(result, sectors_df)


# ---------------------------------------------------------------------------
# fundamentals()
# ---------------------------------------------------------------------------

class TestFundamentals:
    def test_fundamentals_no_filter(self, client, fundamentals_df):
        """fundamentals() with no symbol returns all rows."""
        client._fundamentals.fetch.return_value = fundamentals_df
        result = client.fundamentals(cache=False)
        assert len(result) == len(fundamentals_df)

    def test_fundamentals_symbol_filter(self, client, fundamentals_df):
        """fundamentals(symbol=...) filters rows in memory by symbol."""
        client._fundamentals.fetch.return_value = fundamentals_df
        result = client.fundamentals(symbol="ENGRO", cache=False)
        assert len(result) == 2
        assert (result["symbol"] == "ENGRO").all()


# ---------------------------------------------------------------------------
# debt_market()
# ---------------------------------------------------------------------------

class TestDebtMarket:
    def test_debt_market_returns_dict(self, client):
        """debt_market() passes through the scraper result; cache flag is a no-op."""
        mock_tables = {
            "table_0": pd.DataFrame({"security_name": ["Bond A"]}),
            "table_1": pd.DataFrame({"security_name": ["Bond B"]}),
        }
        client._debt_market.fetch.return_value = mock_tables
        result = client.debt_market(cache=True)
        client._debt_market.fetch.assert_called_once()
        assert set(result.keys()) == {"table_0", "table_1"}


# ---------------------------------------------------------------------------
# eligible_scrips()
# ---------------------------------------------------------------------------

class TestEligibleScrips:
    def test_eligible_scrips_returns_dict(self, client):
        """eligible_scrips() passes through the scraper result; cache flag is a no-op."""
        mock_tables = {
            f"table_{i}": pd.DataFrame({"symbol": [f"SYM{i}"]})
            for i in range(9)
        }
        client._eligible_scrips.fetch.return_value = mock_tables
        result = client.eligible_scrips(cache=True)
        client._eligible_scrips.fetch.assert_called_once()
        assert set(result.keys()) == {f"table_{i}" for i in range(9)}
