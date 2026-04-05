"""Shared utilities for psxdata.

- chunk_date_range: split a date range into fixed-size chunks
- RateLimiter: token-bucket rate limiter with injectable clock (thread-safe)
- validate_ohlc_dataframe: validate OHLCV DataFrame, flag/drop bad rows
"""
from __future__ import annotations

import logging
import threading
import time as _time
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pandas as pd

from psxdata.constants import DEFAULT_CHUNK_DAYS, MAX_REQUESTS_PER_SECOND

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Date range chunker
# ---------------------------------------------------------------------------

def chunk_date_range(
    start: date,
    end: date,
    chunk_days: int = DEFAULT_CHUNK_DAYS,
) -> list[tuple[date, date]]:
    """Split [start, end] into non-overlapping chunks of at most chunk_days days.

    The last chunk may be shorter. Future-date clamping is the caller's
    responsibility — this function is pure date arithmetic.

    Args:
        start: First date (inclusive).
        end: Last date (inclusive).
        chunk_days: Maximum days per chunk. Defaults to DEFAULT_CHUNK_DAYS (365).

    Returns:
        List of (chunk_start, chunk_end) tuples covering [start, end] exactly.

    Raises:
        ValueError: If start > end.
    """
    if start > end:
        raise ValueError(f"start ({start}) must be <= end ({end})")
    chunks: list[tuple[date, date]] = []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    return chunks


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Thread-safe token-bucket rate limiter.

    Args:
        max_per_second: Maximum requests allowed per second.
        time_func: Callable returning current time in seconds. Defaults to
            time.monotonic. Inject a fake for deterministic tests.
        sleep_func: Callable to sleep N seconds. Defaults to time.sleep.
            Inject a fake for deterministic tests.

    Usage::

        limiter = RateLimiter(max_per_second=2)
        with limiter:
            response = session.get(url)
    """

    def __init__(
        self,
        max_per_second: int = MAX_REQUESTS_PER_SECOND,
        time_func: Callable[[], float] = _time.monotonic,
        sleep_func: Callable[[float], None] = _time.sleep,
    ) -> None:
        self._interval = 1.0 / max_per_second
        self._time = time_func
        self._sleep = sleep_func
        self._lock = threading.Lock()
        self._last_request: float | None = None

    def __enter__(self) -> "RateLimiter":
        with self._lock:
            if self._last_request is not None:
                elapsed = self._time() - self._last_request
                deficit = self._interval - elapsed
                if deficit > 0:
                    self._sleep(deficit)
            self._last_request = self._time()
        return self

    def __exit__(self, *args: Any) -> None:
        pass


# ---------------------------------------------------------------------------
# OHLC DataFrame validator
# ---------------------------------------------------------------------------

def validate_ohlc_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validate an OHLCV DataFrame against business rules.

    Adds an ``is_anomaly`` boolean column (True = flagged but retained).
    Rows with NaN in critical columns (close, volume) or all-NaN rows are
    dropped. All other anomalies are flagged and retained for caller inspection.

    Args:
        df: DataFrame with columns: date, open, high, low, close, volume.

    Returns:
        Cleaned DataFrame with ``is_anomaly`` column added.
    """
    if df.empty:
        df = df.copy()
        df["is_anomaly"] = pd.Series(dtype=bool)
        return df

    df = df.copy()
    df["is_anomaly"] = False

    # Drop rows with NaN in critical columns
    critical_null = df["close"].isna() | df["volume"].isna()
    if critical_null.any():
        count = int(critical_null.sum())
        logger.warning("Dropping %d row(s) with NaN in close or volume", count)
        df = df[~critical_null].copy()

    # Drop all-NaN rows (completely corrupt)
    all_null = df.isna().all(axis=1)
    if all_null.any():
        logger.warning("Dropping %d completely corrupt row(s)", int(all_null.sum()))
        df = df[~all_null].copy()

    if df.empty:
        return df

    # OHLC constraint: low <= open, close <= high
    ohlc_bad = (
        (df["low"] > df["open"])
        | (df["low"] > df["close"])
        | (df["open"] > df["high"])
        | (df["close"] > df["high"])
    )
    if ohlc_bad.any():
        logger.warning("OHLC constraint violated in %d row(s) — flagged", int(ohlc_bad.sum()))
        df.loc[ohlc_bad, "is_anomaly"] = True

    # Negative volume
    neg_vol = df["volume"] < 0
    if neg_vol.any():
        logger.warning("Negative volume in %d row(s) — flagged", int(neg_vol.sum()))
        df.loc[neg_vol, "is_anomaly"] = True

    # Date-based checks
    if "date" in df.columns:
        dates = pd.to_datetime(df["date"])

        # Future dates
        today = pd.Timestamp.now().normalize()
        future = dates > today
        if future.any():
            logger.warning("Future date(s) found in %d row(s)", int(future.sum()))

        # Duplicate dates
        dupes = df["date"].duplicated(keep=False)
        if dupes.any():
            logger.warning("Duplicate date(s) found in %d row(s)", int(dupes.sum()))

        # Non-chronological order
        if not dates.is_monotonic_increasing:
            logger.warning("Dates are not in chronological order")

    return df
