"""SymbolsScraper — full instrument list from PSX.

Endpoint:  GET https://dps.psx.com.pk/symbols
Method:    GET
Mode:      requests — response is JSON, no HTML parsing

Returns all ~1029 PSX-listed instruments with sector names and type flags.
This is the sector enrichment source — bridges the numeric sector codes in
/screener to human-readable sector names. Joining is the API layer's job.
"""
from __future__ import annotations

import logging

import pandas as pd

from psxdata.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class SymbolsScraper(BaseScraper):
    """Fetch the full PSX instrument list as a DataFrame."""

    def fetch(self) -> pd.DataFrame:
        """Fetch all PSX symbols from the /symbols JSON endpoint.

        Returns:
            DataFrame with columns: symbol, name, sector_name, is_etf, is_debt, is_gem.
            Empty DataFrame if the endpoint returns an empty list.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        logger.debug("Fetching symbols list")
        resp = self._get("symbols")
        data = resp.json()

        if not data:
            logger.warning("Symbols endpoint returned empty list")
            return pd.DataFrame(
                columns=["symbol", "name", "sector_name", "is_etf", "is_debt", "is_gem"]
            )

        df = pd.DataFrame(data)
        logger.debug("Fetched %d symbols", len(df))

        # Normalize column names from PSX JSON keys
        rename_map = {
            "symbol": "symbol",
            "name": "name",
            "sectorName": "sector_name",
            "isETF": "is_etf",
            "isDebt": "is_debt",
            "isGEM": "is_gem",
        }
        df = df.rename(columns=rename_map)
        # PSX omits boolean flags for instruments where the flag is False;
        # normalise NaN → False and coerce to bool
        for bool_col in ("is_etf", "is_debt", "is_gem"):
            if bool_col in df.columns:
                df[bool_col] = df[bool_col].fillna(False).astype(bool)
        # Keep only known columns
        cols = [c for c in rename_map.values() if c in df.columns]
        return df[cols]
