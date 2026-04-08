"""Integration smoke tests for FundamentalsScraper — hits real PSX. Requires network."""
import pandas as pd
import pytest

from psxdata.scrapers.fundamentals import FundamentalsScraper

pytestmark = pytest.mark.integration


class TestFundamentalsScraperIntegration:
    def test_fetch_returns_dataframe_no_crash(self):
        """May return empty table outside reporting season — just verify no crash."""
        df = FundamentalsScraper().fetch()
        assert isinstance(df, pd.DataFrame)
