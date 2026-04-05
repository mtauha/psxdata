"""Unit tests for psxdata/parsers/normalizers.py."""
from datetime import datetime

import pytest

from psxdata.parsers.normalizers import coerce_numeric, normalize_column_name, parse_date_safely


class TestParseDateSafely:
    """parse_date_safely must never raise — always returns datetime | None."""

    def test_format_b_d_Y(self):
        assert parse_date_safely("Jan 05, 2024") == datetime(2024, 1, 5)

    def test_format_d_b_Y(self):
        assert parse_date_safely("05-Jan-2024") == datetime(2024, 1, 5)

    def test_format_Y_m_d(self):
        assert parse_date_safely("2024-01-05") == datetime(2024, 1, 5)

    def test_format_d_slash_m_slash_Y(self):
        assert parse_date_safely("05/01/2024") == datetime(2024, 1, 5)

    def test_fuzzy_fallback(self):
        result = parse_date_safely("January 5 2024")
        assert result == datetime(2024, 1, 5)

    def test_empty_string_returns_none(self):
        assert parse_date_safely("") is None

    def test_none_returns_none(self):
        assert parse_date_safely(None) is None  # type: ignore[arg-type]

    def test_int_returns_none(self):
        assert parse_date_safely(20240105) is None  # type: ignore[arg-type]

    def test_whitespace_only_returns_none(self):
        assert parse_date_safely("   ") is None

    def test_garbage_string_returns_none(self):
        assert parse_date_safely("not a date") is None

    def test_never_raises_for_any_input(self):
        """Exhaustive check — no input should ever raise."""
        inputs = [None, "", "   ", "abc", 12345, 3.14, [], {}, object()]
        for val in inputs:
            result = parse_date_safely(val)  # type: ignore[arg-type]
            assert result is None, f"Expected None for {val!r}, got {result!r}"

    def test_leading_trailing_whitespace_stripped(self):
        assert parse_date_safely("  2024-01-05  ") == datetime(2024, 1, 5)


class TestCoerceNumeric:
    def test_plain_float(self):
        assert coerce_numeric("481.99") == pytest.approx(481.99)

    def test_comma_separated(self):
        assert coerce_numeric("1,234.56") == pytest.approx(1234.56)

    def test_strip_percent(self):
        assert coerce_numeric("10.00%") == pytest.approx(10.0)

    def test_strip_pkr(self):
        assert coerce_numeric("PKR 500.00") == pytest.approx(500.0)

    def test_integer_string(self):
        assert coerce_numeric("4496408") == pytest.approx(4496408.0)

    def test_none_returns_none(self):
        assert coerce_numeric(None) is None  # type: ignore[arg-type]

    def test_empty_returns_none(self):
        assert coerce_numeric("") is None

    def test_non_numeric_returns_none(self):
        assert coerce_numeric("N/A") is None

    def test_never_raises(self):
        for val in [None, "", "abc", "N/A", object()]:
            result = coerce_numeric(val)  # type: ignore[arg-type]
            assert result is None


class TestNormalizeColumnName:
    def test_uppercase_to_lower(self):
        assert normalize_column_name("VOLUME") == "volume"

    def test_spaces_to_underscores(self):
        assert normalize_column_name("MARKET CAP") == "market_cap"

    def test_leading_trailing_whitespace(self):
        assert normalize_column_name("  DATE  ") == "date"

    def test_special_chars_removed(self):
        result = normalize_column_name("CHANGE (%)")
        # parens and % become underscores, then collapsed
        assert "change" in result

    def test_multiple_spaces_collapsed(self):
        assert normalize_column_name("SECTOR  NAME") == "sector_name"

    def test_already_normalized(self):
        assert normalize_column_name("close") == "close"
