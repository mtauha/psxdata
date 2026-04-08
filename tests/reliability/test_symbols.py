"""Reliability tests for SymbolsScraper — mocked network, no real HTTP calls."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from psxdata.scrapers.symbols import SymbolsScraper

pytestmark = pytest.mark.reliability

FIXTURE = json.loads((Path(__file__).parent.parent / "fixtures" / "symbols.json").read_text(encoding="utf-8"))


def _mock_json_response(data: list, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    return resp


class TestSymbolsScraper:
    def test_returns_dataframe_with_correct_columns(self):
        scraper = SymbolsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_json_response(FIXTURE)):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)
        for col in ("symbol", "name", "sector_name", "is_etf", "is_debt", "is_gem"):
            assert col in df.columns, f"Missing column: {col}"

    def test_returns_expected_row_count(self):
        scraper = SymbolsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_json_response(FIXTURE)):
            df = scraper.fetch()
        assert len(df) > 900  # PSX has ~1029 instruments

    def test_empty_json_returns_empty_dataframe(self):
        scraper = SymbolsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_json_response([])):
            df = scraper.fetch()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_missing_boolean_flags_filled_as_false(self):
        """PSX omits isGEM/isETF/isDebt keys for instruments where flag is False."""
        # Create records: some with isGEM, some without
        records_without = [{"symbol": "X", "name": "X Corp", "sectorName": "Tech", "isETF": False, "isDebt": False}]
        records_with = [{"symbol": "Y", "name": "Y Corp", "sectorName": "Tech", "isETF": False, "isDebt": False, "isGEM": True}]
        mixed = records_without + records_with
        scraper = SymbolsScraper()
        with patch.object(scraper._session, "request", return_value=_mock_json_response(mixed)):
            df = scraper.fetch()
        assert df["is_gem"].isna().sum() == 0
        assert df.loc[df["symbol"] == "X", "is_gem"].iloc[0] == False
        assert df.loc[df["symbol"] == "Y", "is_gem"].iloc[0] == True
