"""FundamentalsScraper — financial report filings list from PSX.

Endpoint:  GET https://dps.psx.com.pk/financial-reports-list
Method:    GET
Mode:      requests + BeautifulSoup (plain HTTP AJAX)

Quirk:     Returns an empty table outside reporting season. This is normal —
           return an empty DataFrame without raising any exception.
"""
from __future__ import annotations

import logging

import pandas as pd

from psxdata.parsers.html import parse_html_table
from psxdata.parsers.normalizers import parse_date_safely
from psxdata.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class FundamentalsScraper(BaseScraper):
    """Fetch the PSX financial reports list."""

    def fetch(self) -> pd.DataFrame:
        """Fetch the financial reports filing list.

        Returns:
            DataFrame with columns: symbol, year, type, period_ended,
            posting_date, posting_time, document.
            Empty DataFrame if outside reporting season or no data returned.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        logger.debug("Fetching financial reports list")
        resp = self._get("financial_reports")
        rows = parse_html_table(resp.text)

        if not rows:
            logger.info("Financial reports list returned no data (may be outside reporting season)")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        logger.debug("Parsed %d financial report rows", len(df))

        for col in ("period_ended", "posting_date"):
            if col in df.columns:
                df[col] = df[col].apply(parse_date_safely)

        return df
