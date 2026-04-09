"""Reliability tests for DebtMarketScraper — mocked network, no real HTTP calls."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from psxdata.scrapers.debt_market import DebtMarketScraper

pytestmark = pytest.mark.reliability

FIXTURE = (Path(__file__).parent.parent / "fixtures" / "debt_market.html").read_text(encoding="utf-8")


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


class TestDebtMarketScraper:
    def test_returns_dict_of_dataframes(self):
        scraper = DebtMarketScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            result = scraper.fetch()
        assert isinstance(result, dict)
        assert len(result) > 0
        for key, df in result.items():
            assert isinstance(df, pd.DataFrame), f"Value for key {key!r} is not a DataFrame"

    def test_returns_four_tables(self):
        scraper = DebtMarketScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            result = scraper.fetch()
        assert len(result) == 4

    def test_each_table_has_security_code_column(self):
        scraper = DebtMarketScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            result = scraper.fetch()
        for key, df in result.items():
            assert "security_code" in df.columns or len(df) == 0, \
                f"Table {key!r} missing security_code column"

    def test_empty_html_returns_empty_dict(self):
        scraper = DebtMarketScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response("<html></html>")):
            result = scraper.fetch()
        assert result == {}

    def test_table_without_h2_gets_fallback_key(self):
        """Table with no preceding <h2> should be keyed as 'table_0', not crash."""
        html = (
            "<html><body>"
            "<table><thead><tr><th>Security Code</th><th>Security Name</th></tr></thead>"
            "<tbody><tr><td>TB001</td><td>T-Bill 1</td></tr></tbody></table>"
            "</body></html>"
        )
        scraper = DebtMarketScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(html)):
            result = scraper.fetch()
        assert "table_0" in result
        assert len(result["table_0"]) == 1
