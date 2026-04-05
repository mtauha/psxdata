"""Unit tests for psxdata/utils.py — date chunker, RateLimiter, OHLC validator."""
import threading
from datetime import date, timedelta

import pandas as pd
import pytest

from psxdata.utils import RateLimiter, chunk_date_range, validate_ohlc_dataframe


# ---------------------------------------------------------------------------
# chunk_date_range
# ---------------------------------------------------------------------------

class TestChunkDateRange:
    def test_single_year_range(self):
        chunks = chunk_date_range(date(2023, 1, 1), date(2023, 12, 31))
        assert chunks == [(date(2023, 1, 1), date(2023, 12, 31))]

    def test_multi_year_range(self):
        # 3 years of 365-day chunks: 2020 is a leap year so chunks don't align
        # to calendar year boundaries — the chunker is pure date arithmetic
        chunks = chunk_date_range(date(2020, 1, 1), date(2022, 12, 31), chunk_days=365)
        # First chunk: 2020-01-01 to 2020-12-30 (365 days, 2020 has 366)
        assert chunks[0] == (date(2020, 1, 1), date(2020, 12, 30))
        # Contiguous and covers the full range
        assert chunks[0][0] == date(2020, 1, 1)
        assert chunks[-1][1] == date(2022, 12, 31)
        # All chunks are at most 365 days
        for s, e in chunks:
            assert (e - s).days < 365

    def test_sub_year_range(self):
        chunks = chunk_date_range(date(2024, 1, 1), date(2024, 3, 15))
        assert chunks == [(date(2024, 1, 1), date(2024, 3, 15))]

    def test_single_day(self):
        chunks = chunk_date_range(date(2024, 6, 1), date(2024, 6, 1))
        assert chunks == [(date(2024, 6, 1), date(2024, 6, 1))]

    def test_start_gt_end_raises(self):
        with pytest.raises(ValueError, match="start"):
            chunk_date_range(date(2024, 12, 31), date(2024, 1, 1))

    def test_chunk_does_not_overshoot_end(self):
        chunks = chunk_date_range(date(2024, 1, 1), date(2024, 6, 30), chunk_days=365)
        assert chunks == [(date(2024, 1, 1), date(2024, 6, 30))]

    def test_chunks_are_contiguous_no_gaps(self):
        chunks = chunk_date_range(date(2020, 1, 1), date(2022, 6, 15), chunk_days=365)
        for i in range(len(chunks) - 1):
            assert chunks[i][1] + timedelta(days=1) == chunks[i + 1][0]

    def test_chunks_cover_full_range(self):
        start, end = date(2020, 1, 1), date(2022, 6, 15)
        chunks = chunk_date_range(start, end, chunk_days=365)
        assert chunks[0][0] == start
        assert chunks[-1][1] == end

    def test_custom_chunk_days(self):
        chunks = chunk_date_range(date(2024, 1, 1), date(2024, 3, 31), chunk_days=30)
        assert len(chunks) == 4  # 90 days / 30 = 3 full + 1 partial


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

class TestRateLimiter:
    def test_allows_first_request_immediately(self):
        calls = []
        mock_time = [0.0]
        slept = []

        def t(): return mock_time[0]
        def s(sec): slept.append(sec); mock_time[0] += sec

        limiter = RateLimiter(max_per_second=2, time_func=t, sleep_func=s)
        with limiter:
            calls.append(1)
        assert calls == [1]
        assert slept == []  # no sleep on first request

    def test_enforces_rate_limit(self):
        mock_time = [0.0]
        slept = []

        def t(): return mock_time[0]
        def s(sec): slept.append(sec); mock_time[0] += sec

        limiter = RateLimiter(max_per_second=2, time_func=t, sleep_func=s)
        with limiter:
            pass
        # Second request immediately — should sleep 0.5s (1/2 req/sec interval)
        with limiter:
            pass
        assert len(slept) == 1
        assert abs(slept[0] - 0.5) < 1e-9

    def test_no_sleep_when_enough_time_elapsed(self):
        mock_time = [0.0]
        slept = []

        def t(): return mock_time[0]
        def s(sec): slept.append(sec); mock_time[0] += sec

        limiter = RateLimiter(max_per_second=2, time_func=t, sleep_func=s)
        with limiter:
            pass
        mock_time[0] = 1.0  # 1 second has passed — well above 0.5s interval
        with limiter:
            pass
        assert slept == []

    def test_thread_safety(self):
        """Multiple threads using the same limiter don't crash."""
        limiter = RateLimiter(max_per_second=100)  # high limit so test is fast
        errors = []

        def use():
            try:
                with limiter:
                    pass
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=use) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []


# ---------------------------------------------------------------------------
# validate_ohlc_dataframe
# ---------------------------------------------------------------------------

def _make_df(rows):
    """Helper — build OHLCV DataFrame from list of dicts."""
    return pd.DataFrame(rows)


class TestValidateOHLCDataframe:
    def _valid_row(self, date_str="2024-01-01"):
        return {
            "date": pd.Timestamp(date_str),
            "open": 100.0,
            "high": 110.0,
            "low": 90.0,
            "close": 105.0,
            "volume": 1000,
        }

    def test_valid_dataframe_passes(self):
        df = _make_df([self._valid_row("2024-01-01"), self._valid_row("2024-01-02")])
        result = validate_ohlc_dataframe(df)
        assert len(result) == 2
        assert "is_anomaly" in result.columns
        assert not result["is_anomaly"].any()

    def test_low_gt_open_flags_row(self):
        row = self._valid_row()
        row["low"] = 200.0  # low > open — anomaly
        df = _make_df([row])
        result = validate_ohlc_dataframe(df)
        assert len(result) == 1
        assert bool(result.iloc[0]["is_anomaly"]) is True

    def test_close_gt_high_flags_row(self):
        row = self._valid_row()
        row["close"] = 200.0  # close > high — anomaly
        df = _make_df([row])
        result = validate_ohlc_dataframe(df)
        assert bool(result.iloc[0]["is_anomaly"]) is True

    def test_negative_volume_flags_row(self):
        row = self._valid_row()
        row["volume"] = -1
        df = _make_df([row])
        result = validate_ohlc_dataframe(df)
        assert bool(result.iloc[0]["is_anomaly"]) is True

    def test_nan_close_drops_row(self):
        row = self._valid_row()
        row["close"] = float("nan")
        df = _make_df([row])
        result = validate_ohlc_dataframe(df)
        assert len(result) == 0

    def test_nan_volume_drops_row(self):
        row = self._valid_row()
        row["volume"] = float("nan")
        df = _make_df([row])
        result = validate_ohlc_dataframe(df)
        assert len(result) == 0

    def test_future_date_warns_retains_row(self, caplog):
        import logging
        row = self._valid_row("2099-01-01")
        df = _make_df([row])
        with caplog.at_level(logging.WARNING):
            result = validate_ohlc_dataframe(df)
        assert len(result) == 1
        assert "future" in caplog.text.lower()

    def test_duplicate_dates_warns_retains_both(self, caplog):
        import logging
        df = _make_df([self._valid_row("2024-01-01"), self._valid_row("2024-01-01")])
        with caplog.at_level(logging.WARNING):
            result = validate_ohlc_dataframe(df)
        assert len(result) == 2
        assert "duplicate" in caplog.text.lower()

    def test_non_chronological_warns_retains(self, caplog):
        import logging
        df = _make_df([self._valid_row("2024-01-02"), self._valid_row("2024-01-01")])
        with caplog.at_level(logging.WARNING):
            result = validate_ohlc_dataframe(df)
        assert len(result) == 2
        assert "chronolog" in caplog.text.lower()

    def test_partially_corrupt_df_clean_rows_returned(self):
        rows = [
            self._valid_row("2024-01-01"),
            {**self._valid_row("2024-01-02"), "close": float("nan")},  # dropped
            self._valid_row("2024-01-03"),
        ]
        df = _make_df(rows)
        result = validate_ohlc_dataframe(df)
        assert len(result) == 2
