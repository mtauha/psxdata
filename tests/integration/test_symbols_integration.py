"""Integration smoke tests for SymbolsScraper — hits real PSX. Requires network."""
import pandas as pd
import pytest

from psxdata.scrapers.symbols import SymbolsScraper

pytestmark = pytest.mark.integration


class TestSymbolsScraperIntegration:
    def test_fetch_returns_instruments(self):
        df = SymbolsScraper().fetch()
        assert len(df) > 900
        for col in ("symbol", "name", "sector_name", "is_etf", "is_debt", "is_gem"):
            assert col in df.columns
