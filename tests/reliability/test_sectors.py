"""Reliability tests for SectorsScraper — mocked network, no real HTTP calls."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from psxdata.scrapers.sectors import SectorsScraper

pytestmark = pytest.mark.reliability

FIXTURE = (Path(__file__).parent.parent / "fixtures" / "sector_summary.html").read_text(encoding="utf-8")


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


class TestSectorsScraper:
    def test_returns_dataframe_with_key_columns(self):
        scraper = SectorsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)
        for col in ("sector_code", "sector_name"):
            assert col in df.columns, f"Missing column: {col}"

    def test_returns_expected_sector_count(self):
        scraper = SectorsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch()
        assert len(df) >= 30  # PSX has ~37 sectors

    def test_empty_html_returns_empty_dataframe(self):
        scraper = SectorsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response("<html></html>")):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_malformed_html_no_th_returns_empty_dataframe(self):
        bad_html = "<html><body><table><tbody><tr><td>Tech</td></tr></tbody></table></body></html>"
        scraper = SectorsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(bad_html)):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
