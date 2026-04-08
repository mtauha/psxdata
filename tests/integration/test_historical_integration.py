"""Integration smoke tests for HistoricalScraper — hits real PSX. Requires network.

Run with: pytest tests/integration/test_historical_integration.py -v -m integration
Excluded from CI by default.
"""
from datetime import date

import pandas as pd
import pytest

from psxdata.scrapers.historical import HistoricalScraper

pytestmark = pytest.mark.integration


class TestHistoricalScraperIntegration:
    def test_fetch_engro_returns_nonempty_ohlcv(self):
        df = HistoricalScraper().fetch("ENGRO")
        assert len(df) > 100
        for col in ("date", "open", "high", "low", "close", "volume"):
            assert col in df.columns

    def test_fetch_with_date_range(self):
        df = HistoricalScraper().fetch("LUCK", start=date(2023, 1, 1), end=date(2023, 12, 31))
        assert len(df) > 0
        assert (pd.to_datetime(df["date"]) >= pd.Timestamp("2023-01-01")).all()
        assert (pd.to_datetime(df["date"]) <= pd.Timestamp("2023-12-31")).all()
