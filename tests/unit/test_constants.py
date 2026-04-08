"""Tests for constants — verify new AJAX endpoints and COLUMN_MAP entries exist."""
from psxdata.constants import (
    BOARDS,
    COLUMN_MAP,
    ENDPOINTS,
    INDEX_NAMES,
    MARKETS,
)


class TestEndpoints:
    def test_ajax_endpoints_present(self):
        assert "trading_board" in ENDPOINTS
        assert "symbols" in ENDPOINTS
        assert "sector_summary" in ENDPOINTS
        assert "financial_reports" in ENDPOINTS
        assert "indices" in ENDPOINTS

    def test_ajax_endpoint_paths(self):
        assert ENDPOINTS["trading_board"] == "/trading-board"
        assert ENDPOINTS["symbols"] == "/symbols"
        assert ENDPOINTS["sector_summary"] == "/sector-summary/sectorwise"
        assert ENDPOINTS["financial_reports"] == "/financial-reports-list"
        assert ENDPOINTS["indices"] == "/indices"

    def test_page_endpoints_still_present(self):
        assert "historical" in ENDPOINTS
        assert "trading_panel" in ENDPOINTS
        assert "screener" in ENDPOINTS
        assert "debt_market" in ENDPOINTS
        assert "eligible_scrips" in ENDPOINTS


class TestBoardsAndMarkets:
    def test_boards(self):
        assert set(BOARDS) == {"main", "gem", "bnb"}

    def test_markets(self):
        assert set(MARKETS) == {"REG", "ODL", "DFC", "SQR", "CSF"}

    def test_index_names_contains_key_indices(self):
        assert "KSE100" in INDEX_NAMES
        assert "KSE30" in INDEX_NAMES
        assert "ALLSHR" in INDEX_NAMES
        assert "KMI30" in INDEX_NAMES
        assert len(INDEX_NAMES) == 18


class TestColumnMap:
    def test_trading_board_columns(self):
        assert COLUMN_MAP["BID VOL."] == "bid_vol"
        assert COLUMN_MAP["BID PRICE"] == "bid_price"
        assert COLUMN_MAP["OFFER VOL."] == "offer_vol"
        assert COLUMN_MAP["OFFER PRICE"] == "offer_price"

    def test_bnb_specific_columns(self):
        assert COLUMN_MAP["BID YIELD (%)"] == "bid_yield"
        assert COLUMN_MAP["OFFER YIELD (%)"] == "offer_yield"
        assert COLUMN_MAP["LTP"] == "ltp"
        assert COLUMN_MAP["LTY (%)"] == "lty"
        assert COLUMN_MAP["LDCY (%)"] == "ldcy"

    def test_index_constituent_columns(self):
        assert COLUMN_MAP["Current Index"] == "current_index"
        assert COLUMN_MAP["IDX WTG (%)"] == "idx_weight"
        assert COLUMN_MAP["IDX POINT"] == "idx_point"
        assert COLUMN_MAP["FREEFLOAT (M)"] == "freefloat_m"
        assert COLUMN_MAP["SHARES (M)"] == "shares_m"
        assert COLUMN_MAP["MARKET CAP (M)"] == "market_cap_m"

    def test_existing_entries_unchanged(self):
        assert COLUMN_MAP["DATE"] == "date"
        assert COLUMN_MAP["OPEN"] == "open"
        assert COLUMN_MAP["CLOSE"] == "close"
        assert COLUMN_MAP["LISTED IN"] == "listed_in"
