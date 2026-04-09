"""DebtMarketScraper — debt instrument listings from PSX.

Endpoint:  GET https://dps.psx.com.pk/debt-market
Method:    GET
Mode:      requests + BeautifulSoup (plain HTTP)

Returns 4 instrument category tables, separated by <h2> headings on the page.
Tables are parsed by heading, not by table index position.
"""
from __future__ import annotations

import logging

import pandas as pd

from psxdata.parsers.html import parse_tables_by_heading
from psxdata.parsers.normalizers import coerce_numeric, parse_date_safely
from psxdata.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class DebtMarketScraper(BaseScraper):
    """Fetch all debt market instrument categories from PSX."""

    def fetch(self) -> dict[str, pd.DataFrame]:
        """Fetch all debt market tables, keyed by instrument category.

        Returns:
            Dict mapping normalized category name -> DataFrame.
            4 categories: one per <h2> heading on the /debt-market page.
            Keys are normalized heading text (snake_case).
            Empty dict if no tables found.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        logger.debug("Fetching debt market data")
        resp = self._get("debt_market")
        tables = parse_tables_by_heading(resp.text)

        if not tables:
            logger.warning("Debt market returned no tables")
            return {}

        result: dict[str, pd.DataFrame] = {}
        for key, rows in tables.items():
            if not rows:
                result[key] = pd.DataFrame()
                continue
            df = pd.DataFrame(rows)
            logger.debug("Debt market table %r: %d rows", key, len(df))

            date_cols = ("listing_date", "issue_date", "maturity_date",
                         "prev_coupon_date", "next_coupon_date")
            for col in date_cols:
                if col in df.columns:
                    df[col] = df[col].apply(parse_date_safely)

            numeric_cols = ("face_value", "issue_size", "coupon_rate",
                            "outstanding_days", "remaining_years")
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].apply(coerce_numeric)

            result[key] = df

        return result
