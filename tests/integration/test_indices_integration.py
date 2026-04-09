"""Integration smoke tests for IndicesScraper — hits real PSX. Requires network."""
import pandas as pd
import pytest

from psxdata.scrapers.indices import IndicesScraper

pytestmark = pytest.mark.integration


class TestIndicesScraperIntegration:
    def test_fetch_kse100_returns_constituents(self):
        df = IndicesScraper().fetch("KSE100")
        assert len(df) > 90  # KSE-100 has 100 constituents
        assert "symbol" in df.columns
