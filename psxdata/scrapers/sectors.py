"""SectorsScraper — sector-level summary data from PSX.

Endpoint:  GET https://dps.psx.com.pk/sector-summary/sectorwise
Method:    GET
Mode:      requests + BeautifulSoup (plain HTTP AJAX)
"""
from __future__ import annotations

import logging

import pandas as pd

from psxdata.parsers.html import parse_html_table
from psxdata.parsers.normalizers import coerce_numeric
from psxdata.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class SectorsScraper(BaseScraper):
    """Fetch sector-level aggregate summary from PSX."""

    def fetch(self) -> pd.DataFrame:
        """Fetch all sector summaries.

        Returns:
            DataFrame with columns: sector_code, sector_name, advance, decline,
            unchanged, turnover, market_cap_b.
            Empty DataFrame if PSX returns no data.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        logger.debug("Fetching sector summary")
        resp = self._get("sector_summary")
        rows = parse_html_table(resp.text)

        if not rows:
            logger.warning("Sector summary returned no data")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        logger.debug("Parsed %d sector rows", len(df))

        numeric_cols = ("advance", "decline", "unchanged", "turnover", "market_cap_b")
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(coerce_numeric)

        return df
