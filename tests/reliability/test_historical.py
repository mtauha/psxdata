"""Reliability tests for HistoricalScraper — mocked network, no real HTTP calls."""
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from psxdata.scrapers.historical import HistoricalScraper

pytestmark = pytest.mark.reliability

FIXTURE = (Path(__file__).parent.parent / "fixtures" / "historical_ENGRO.html").read_text(encoding="utf-8")


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


class TestHistoricalScraper:
    def test_returns_dataframe_with_ohlcv_columns(self):
        scraper = HistoricalScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch("ENGRO")
        assert isinstance(df, pd.DataFrame)
        for col in ("date", "open", "high", "low", "close", "volume"):
            assert col in df.columns, f"Missing column: {col}"

    def test_returns_non_empty_result(self):
        scraper = HistoricalScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch("ENGRO")
        assert len(df) > 0

    def test_no_date_filter_returns_all_rows(self):
        scraper = HistoricalScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df_all = scraper.fetch("ENGRO")
            df_none = scraper.fetch("ENGRO", start=None, end=None)
        assert len(df_all) == len(df_none)

    def test_start_filter_trims_early_rows(self):
        scraper = HistoricalScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df_all = scraper.fetch("ENGRO")
            df_filtered = scraper.fetch("ENGRO", start=date(2023, 1, 1))
        assert len(df_filtered) <= len(df_all)
        assert (pd.to_datetime(df_filtered["date"]) >= pd.Timestamp("2023-01-01")).all()

    def test_end_filter_trims_late_rows(self):
        scraper = HistoricalScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df_filtered = scraper.fetch("ENGRO", end=date(2022, 12, 31))
        assert (pd.to_datetime(df_filtered["date"]) <= pd.Timestamp("2022-12-31")).all()

    def test_start_and_end_filter(self):
        scraper = HistoricalScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch("ENGRO", start=date(2022, 1, 1), end=date(2022, 12, 31))
        dates = pd.to_datetime(df["date"])
        assert (dates >= pd.Timestamp("2022-01-01")).all()
        assert (dates <= pd.Timestamp("2022-12-31")).all()

    def test_start_after_end_raises_value_error(self):
        scraper = HistoricalScraper()
        # No network call needed — ValueError raised before POST
        with pytest.raises(ValueError, match="start.*end"):
            scraper.fetch("ENGRO", start=date(2023, 12, 31), end=date(2022, 1, 1))

    def test_empty_html_returns_empty_dataframe(self):
        scraper = HistoricalScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response("<html></html>")):
            df = scraper.fetch("ENGRO")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_is_anomaly_column_present(self):
        """validate_ohlc_dataframe() adds is_anomaly column."""
        scraper = HistoricalScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch("ENGRO")
        assert "is_anomaly" in df.columns

    def test_ohlcv_dtypes(self):
        """open/high/low/close are float, volume is Int64, date is datetime."""
        scraper = HistoricalScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(FIXTURE)):
            df = scraper.fetch("ENGRO")
        assert df["open"].dtype == float
        assert df["high"].dtype == float
        assert df["low"].dtype == float
        assert df["close"].dtype == float
        assert str(df["volume"].dtype) == "Int64"
        assert pd.api.types.is_datetime64_any_dtype(df["date"]) or all(
            isinstance(v, type(None)) or hasattr(v, "year") for v in df["date"]
        )

    def test_malformed_html_no_th_returns_empty_dataframe(self):
        """Table present but no <th> headers — return empty, no crash."""
        bad_html = "<html><body><table><tbody><tr><td>100</td></tr></tbody></table></body></html>"
        scraper = HistoricalScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(bad_html)):
            df = scraper.fetch("ENGRO")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
