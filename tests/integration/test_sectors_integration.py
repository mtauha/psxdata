"""Integration smoke tests for SectorsScraper — hits real PSX. Requires network."""
import pandas as pd
import pytest

from psxdata.scrapers.sectors import SectorsScraper

pytestmark = pytest.mark.integration


class TestSectorsScraperIntegration:
    def test_fetch_returns_sectors(self):
        df = SectorsScraper().fetch()
        assert len(df) >= 30
        for col in ("sector_code", "sector_name"):
            assert col in df.columns
