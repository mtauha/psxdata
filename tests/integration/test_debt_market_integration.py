"""Integration smoke tests for DebtMarketScraper — hits real PSX. Requires network."""
import pandas as pd
import pytest

from psxdata.scrapers.debt_market import DebtMarketScraper

pytestmark = pytest.mark.integration


class TestDebtMarketScraperIntegration:
    def test_fetch_returns_four_tables(self):
        result = DebtMarketScraper().fetch()
        assert isinstance(result, dict)
        assert len(result) == 4
        for df in result.values():
            assert isinstance(df, pd.DataFrame)
