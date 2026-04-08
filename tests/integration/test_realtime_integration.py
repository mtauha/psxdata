"""Integration smoke tests for RealtimeScraper — hits real PSX. Requires network."""
import pandas as pd
import pytest

from psxdata.scrapers.realtime import RealtimeScraper

pytestmark = pytest.mark.integration


class TestRealtimeScraperIntegration:
    def test_fetch_reg_main_returns_data(self):
        df = RealtimeScraper().fetch("REG", "main")
        assert isinstance(df, pd.DataFrame)
        # Board may be empty outside trading hours — just verify no crash
