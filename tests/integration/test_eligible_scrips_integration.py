"""Integration smoke tests for EligibleScripsScraper — hits real PSX. Requires network."""
import pandas as pd
import pytest

from psxdata.scrapers.eligible_scrips import EligibleScripsScraper

pytestmark = pytest.mark.integration


class TestEligibleScripsScraperIntegration:
    def test_fetch_returns_nine_tables(self):
        result = EligibleScripsScraper().fetch()
        assert isinstance(result, dict)
        assert len(result) == 9
        for df in result.values():
            assert isinstance(df, pd.DataFrame)
