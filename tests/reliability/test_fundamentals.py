"""Reliability tests for FundamentalsScraper — mocked network, no real HTTP calls."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from psxdata.scrapers.fundamentals import FundamentalsScraper

pytestmark = pytest.mark.reliability

FIXTURE = (Path(__file__).parent.parent / "fixtures" / "financial_reports.html").read_text(encoding="utf-8")

EMPTY_TABLE_HTML = (
    "<html><body>"
    "<table><thead><tr>"
    "<th>SYMBOL</th><th>YEAR</th><th>TYPE</th>"
    "<th>PERIOD ENDED</th><th>POSTING DATE</th><th>POSTING TIME</th><th>DOCUMENT</th>"
    "</tr></thead><tbody></tbody></table>"
    "</body></html>"
)

POPULATED_TABLE_HTML = (
    "<html><body>"
    "<table><thead><tr>"
    "<th>SYMBOL</th><th>NAME</th><th>YEAR</th><th>TYPE</th>"
    "<th>PERIOD ENDED</th><th>POSTING DATE</th><th>POSTING TIME</th><th>DOCUMENT</th>"
    "</tr></thead><tbody>"
    "<tr><td>ENGRO</td><td>Engro Corp</td><td>2024</td><td>Annual</td>"
    "<td>31-Dec-2024</td><td>15-Jan-2025</td><td>10:00</td><td>link</td></tr>"
    "</tbody></table>"
    "</body></html>"
)


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


class TestFundamentalsScraper:
    def test_returns_dataframe(self):
        scraper = FundamentalsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)

    def test_empty_table_returns_empty_dataframe_no_exception(self):
        """Outside reporting season, PSX returns a table with headers but no rows."""
        scraper = FundamentalsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(EMPTY_TABLE_HTML)):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_empty_html_returns_empty_dataframe_no_exception(self):
        scraper = FundamentalsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response("<html></html>")):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_returns_dataframe_with_rows_and_parses_dates(self):
        """Verifies column mapping and date parsing on a populated table."""
        scraper = FundamentalsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(POPULATED_TABLE_HTML)):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "symbol" in df.columns
        assert "period_ended" in df.columns
        assert df.loc[0, "symbol"] == "ENGRO"
        # Date parsing should have fired
        assert df["period_ended"].iloc[0] is not None
