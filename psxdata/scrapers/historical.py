"""HistoricalScraper — OHLCV price history for a single PSX symbol.

Endpoint:  POST https://dps.psx.com.pk/historical
Method:    POST with form data {symbol: <ticker>}
Mode:      requests + BeautifulSoup (plain HTTP AJAX)

Quirk:     PSX ignores date params server-side — the POST always returns ALL
           available history for the symbol. Date filtering is applied in memory
           after the response is parsed.
"""
from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from psxdata.parsers.html import parse_html_table
from psxdata.parsers.normalizers import coerce_numeric, parse_date_safely
from psxdata.scrapers.base import BaseScraper
from psxdata.utils import validate_ohlc_dataframe

logger = logging.getLogger(__name__)


class HistoricalScraper(BaseScraper):
    """Fetch OHLCV price history for a PSX-listed symbol."""

    def fetch(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        """Fetch all available OHLCV history for symbol, optionally filtered.

        PSX returns ALL historical data in one POST regardless of any date
        parameters. Filtering is applied in memory after parsing.

        Args:
            symbol: PSX ticker (e.g. "ENGRO", "LUCK").
            start: First date (inclusive). None = no lower bound.
            end:   Last date (inclusive). None = no upper bound.

        Returns:
            DataFrame with columns: date, open, high, low, close, volume, is_anomaly.
            Empty DataFrame if PSX returns no table data.

        Raises:
            ValueError: If start > end.
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        if start is not None and end is not None and start > end:
            raise ValueError(f"start ({start}) must be <= end ({end})")

        logger.debug("Fetching historical data for %s", symbol)
        resp = self._post("historical", data={"symbol": symbol})
        rows = parse_html_table(resp.text)

        if not rows:
            logger.warning("No historical data returned for %s", symbol)
            return pd.DataFrame(
                columns=["date", "open", "high", "low", "close", "volume", "is_anomaly"]
            )

        df = pd.DataFrame(rows)
        logger.debug("Parsed %d raw rows for %s", len(df), symbol)

        # Coerce types
        df["date"] = df["date"].apply(parse_date_safely)
        for col in ("open", "high", "low", "close"):
            if col in df.columns:
                df[col] = df[col].apply(coerce_numeric).astype(float)
        if "volume" in df.columns:
            df["volume"] = df["volume"].apply(coerce_numeric)
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("Int64")

        # Drop rows where date parsing failed
        df = df.dropna(subset=["date"])

        # In-memory date filter
        if start is not None:
            df = df[df["date"] >= pd.Timestamp(start)]
        if end is not None:
            df = df[df["date"] <= pd.Timestamp(end)]

        logger.debug("After date filter: %d rows for %s", len(df), symbol)

        df = df.reset_index(drop=True)
        return validate_ohlc_dataframe(df)
