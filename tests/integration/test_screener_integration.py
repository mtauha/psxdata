"""Integration smoke tests for ScreenerScraper — hits real PSX. Requires network."""
import pandas as pd
import pytest

from psxdata.scrapers.screener import ScreenerScraper

pytestmark = pytest.mark.integration


class TestScreenerScraperIntegration:
    def test_fetch_returns_stocks(self):
        df = ScreenerScraper().fetch()
        assert len(df) > 100
        for col in ("symbol", "sector", "listed_in"):
            assert col in df.columns
