"""Reliability tests for PSXClient exception handling — mocked scrapers, no network.

Issue #92: verifies that scraper-level failures propagate cleanly through
PSXClient without corrupting the cache or returning partial/stale data.
"""
from unittest.mock import MagicMock

import pandas as pd
import pytest

from psxdata.client import PSXClient
from psxdata.exceptions import PSXConnectionError, PSXServerError

pytestmark = pytest.mark.reliability


@pytest.fixture
def client(tmp_path):
    c = PSXClient(cache_dir=str(tmp_path / "cache"))
    c._historical = MagicMock()
    c._screener = MagicMock()
    c._sectors = MagicMock()
    c._symbols = MagicMock()
    c._indices = MagicMock()
    c._fundamentals = MagicMock()
    c._debt_market = MagicMock()
    c._eligible_scrips = MagicMock()
    return c


class TestClientConnectionFailure:
    def test_stocks_connection_error_propagates(self, client):
        """PSXConnectionError from scraper is not swallowed by client.stocks()."""
        client._historical.fetch.side_effect = PSXConnectionError("timeout")
        with pytest.raises(PSXConnectionError):
            client.stocks("ENGRO", cache=False)

    def test_stocks_server_error_propagates(self, client):
        """PSXServerError from scraper propagates out of client.stocks()."""
        client._historical.fetch.side_effect = PSXServerError("503")
        with pytest.raises(PSXServerError):
            client.stocks("ENGRO", cache=False)

    def test_stocks_error_does_not_write_cache(self, client):
        """On scraper failure, nothing is written to the cache."""
        client._cache.set = MagicMock()
        client._historical.fetch.side_effect = PSXConnectionError("timeout")
        try:
            client.stocks("ENGRO", cache=True)
        except PSXConnectionError:
            pass
        assert client._cache.set.call_count == 0

    def test_quote_connection_error_propagates(self, client):
        client._screener.fetch.side_effect = PSXConnectionError("timeout")
        with pytest.raises(PSXConnectionError):
            client.quote("ENGRO", cache=False)

    def test_sectors_server_error_propagates(self, client):
        client._sectors.fetch.side_effect = PSXServerError("503")
        with pytest.raises(PSXServerError):
            client.sectors(cache=False)

    def test_debt_market_error_does_not_write_cache(self, client):
        """dict cache key is not written on scraper failure."""
        client._cache.set_dict = MagicMock()
        client._debt_market.fetch.side_effect = PSXConnectionError("timeout")
        try:
            client.debt_market(cache=True)
        except PSXConnectionError:
            pass
        assert client._cache.set_dict.call_count == 0

    def test_eligible_scrips_error_does_not_write_cache(self, client):
        client._cache.set_dict = MagicMock()
        client._eligible_scrips.fetch.side_effect = PSXConnectionError("timeout")
        try:
            client.eligible_scrips(cache=True)
        except PSXConnectionError:
            pass
        assert client._cache.set_dict.call_count == 0


class TestClientSuccessAfterFailure:
    def test_stocks_succeeds_on_retry(self, client):
        """First call fails, second call with cache=False hits scraper again and succeeds."""
        good_df = pd.DataFrame({
            "date": [pd.Timestamp("2024-01-01")],
            "open": [100.0], "high": [110.0], "low": [90.0], "close": [105.0],
            "volume": pd.array([1000], dtype="Int64"), "is_anomaly": [False],
        })
        client._historical.fetch.side_effect = [
            PSXConnectionError("first call fails"),
            good_df,
        ]
        with pytest.raises(PSXConnectionError):
            client.stocks("ENGRO", cache=False)
        result = client.stocks("ENGRO", cache=False)
        assert not result.empty
