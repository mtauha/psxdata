"""Expanded integration tests — hits real PSX servers. Network required.

Run: pytest tests/integration/test_integration_expanded.py -v -m integration
Runs in scheduled CI daily (integration.yml) — keep assertions drift-stable.
"""
from datetime import date

import pandas as pd
import pytest

from psxdata.scrapers.historical import HistoricalScraper
from psxdata.scrapers.indices import IndicesScraper
from psxdata.scrapers.realtime import RealtimeScraper
from psxdata.scrapers.screener import ScreenerScraper
from psxdata.scrapers.sectors import SectorsScraper
from psxdata.scrapers.symbols import SymbolsScraper
from psxdata.scrapers.fundamentals import FundamentalsScraper
from psxdata.scrapers.debt_market import DebtMarketScraper
from psxdata.scrapers.eligible_scrips import EligibleScripsScraper

pytestmark = pytest.mark.integration


class TestHistoricalScraperExpanded:
    def test_fetch_hbl_returns_ohlcv(self):
        df = HistoricalScraper().fetch("HBL")
        assert len(df) > 0
        for col in ("date", "open", "high", "low", "close", "volume"):
            assert col in df.columns

    def test_ohlcv_dtypes_correct(self):
        df = HistoricalScraper().fetch("LUCK", start=date(2024, 1, 1), end=date(2024, 6, 30))
        assert pd.api.types.is_float_dtype(df["open"])
        assert pd.api.types.is_float_dtype(df["high"])
        assert pd.api.types.is_float_dtype(df["low"])
        assert pd.api.types.is_float_dtype(df["close"])
        assert str(df["volume"].dtype) == "Int64"
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_ohlc_constraints_satisfied(self):
        """Low <= Open <= High, Low <= Close <= High for non-anomaly rows."""
        df = HistoricalScraper().fetch("ENGRO", start=date(2024, 1, 1), end=date(2024, 12, 31))
        if "is_anomaly" not in df.columns:
            pytest.skip("is_anomaly column absent from scraper output")
        clean = df[~df["is_anomaly"]]
        assert (clean["low"] <= clean["open"]).all()
        assert (clean["open"] <= clean["high"]).all()
        assert (clean["low"] <= clean["close"]).all()
        assert (clean["close"] <= clean["high"]).all()

    def test_date_range_boundaries_respected(self):
        start, end = date(2023, 6, 1), date(2023, 8, 31)
        df = HistoricalScraper().fetch("LUCK", start=start, end=end)
        assert len(df) > 0
        dates = pd.to_datetime(df["date"])
        assert (dates >= pd.Timestamp(start)).all()
        assert (dates <= pd.Timestamp(end)).all()

    def test_volume_non_negative(self):
        df = HistoricalScraper().fetch("HBL", start=date(2024, 1, 1), end=date(2024, 3, 31))
        clean = df.dropna(subset=["volume"])
        assert (clean["volume"] >= 0).all()


class TestRealtimeScraperExpanded:
    def test_fetch_reg_gem_returns_dataframe(self):
        df = RealtimeScraper().fetch("REG", "gem")
        assert isinstance(df, pd.DataFrame)

    def test_fetch_bnb_board_returns_dataframe(self):
        df = RealtimeScraper().fetch("BNB", "bnb")
        assert isinstance(df, pd.DataFrame)

    def test_reg_main_has_symbol_column(self):
        df = RealtimeScraper().fetch("REG", "main")
        assert isinstance(df, pd.DataFrame)
        if len(df) > 0:
            assert "symbol" in df.columns


class TestIndicesScraperExpanded:
    def test_fetch_allshr_returns_dataframe(self):
        df = IndicesScraper().fetch("ALLSHR")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_kse100_returns_dataframe_with_symbol_column(self):
        df = IndicesScraper().fetch("KSE100")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "symbol" in df.columns

    def test_kse100_symbol_column_not_empty(self):
        df = IndicesScraper().fetch("KSE100")
        if len(df) > 0:
            assert df["symbol"].notna().any()


class TestSectorsScraperExpanded:
    def test_sector_codes_are_numeric(self):
        df = SectorsScraper().fetch()
        non_null = df["sector_code"].dropna()
        pd.to_numeric(non_null, errors="raise")

    def test_sector_names_are_strings(self):
        df = SectorsScraper().fetch()
        assert df["sector_name"].dtype == object
        assert (df["sector_name"].str.len() > 0).all()

    def test_returns_sectors(self):
        df = SectorsScraper().fetch()
        assert len(df) > 0


class TestScreenerScraperExpanded:
    def test_screener_returns_dataframe_with_symbol_column(self):
        df = ScreenerScraper().fetch()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "symbol" in df.columns

    def test_symbol_column_all_uppercase(self):
        df = ScreenerScraper().fetch()
        if len(df) > 0:
            symbols = df["symbol"].dropna()
            assert (symbols == symbols.str.upper()).all()

    def test_screener_returns_stocks(self):
        df = ScreenerScraper().fetch()
        assert len(df) > 0


class TestSymbolsScraperExpanded:
    def test_symbols_returns_dataframe_with_symbol_column(self):
        df = SymbolsScraper().fetch()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "symbol" in df.columns

    def test_boolean_columns_have_no_nulls(self):
        df = SymbolsScraper().fetch()
        if len(df) > 0:
            for col in ("is_etf", "is_debt", "is_gem"):
                assert df[col].isna().sum() == 0, f"{col} has unexpected nulls"

    def test_sector_name_column_exists(self):
        df = SymbolsScraper().fetch()
        assert "sector_name" in df.columns


class TestFundamentalsScraperExpanded:
    def test_returns_dataframe_with_expected_columns(self):
        df = FundamentalsScraper().fetch()
        assert isinstance(df, pd.DataFrame)
        if len(df) > 0:
            for col in ("symbol", "year", "type", "period_ended"):
                assert col in df.columns


class TestDebtMarketScraperExpanded:
    def test_all_values_are_dataframes(self):
        result = DebtMarketScraper().fetch()
        for key, df in result.items():
            assert isinstance(df, pd.DataFrame), f"{key} is not a DataFrame"

    def test_returns_tables(self):
        result = DebtMarketScraper().fetch()
        assert len(result) >= 1


class TestEligibleScripsScraperExpanded:
    def test_all_values_are_dataframes(self):
        result = EligibleScripsScraper().fetch()
        for key, df in result.items():
            assert isinstance(df, pd.DataFrame), f"{key} is not a DataFrame"

    def test_returns_tables(self):
        result = EligibleScripsScraper().fetch()
        assert len(result) >= 1
