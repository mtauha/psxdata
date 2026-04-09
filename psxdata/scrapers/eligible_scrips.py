"""EligibleScripsScraper — margin-trading eligible stocks by market category.

Endpoint:  GET https://dps.psx.com.pk/eligible-scrips
Method:    GET
Mode:      requests + BeautifulSoup (plain HTTP)

Returns 9 market category tables, separated by <h2> headings on the page.
Tables are parsed by heading, not by table index position.
"""
from __future__ import annotations

import logging

import pandas as pd

from psxdata.parsers.html import parse_tables_by_heading
from psxdata.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class EligibleScripsScraper(BaseScraper):
    """Fetch all eligible scrip categories from PSX."""

    def fetch(self) -> dict[str, pd.DataFrame]:
        """Fetch all eligible scrip tables, keyed by market category.

        Returns:
            Dict mapping normalized category name -> DataFrame.
            9 categories: one per <h2> heading on the /eligible-scrips page.
            Each DataFrame has columns: symbol, name.
            Empty dict if no tables found.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        logger.debug("Fetching eligible scrips data")
        resp = self._get("eligible_scrips")
        tables = parse_tables_by_heading(resp.text)

        if not tables:
            logger.warning("Eligible scrips returned no tables")
            return {}

        result: dict[str, pd.DataFrame] = {}
        for key, rows in tables.items():
            if not rows:
                result[key] = pd.DataFrame()
                continue
            df = pd.DataFrame(rows)
            logger.debug("Eligible scrips table %r: %d rows", key, len(df))
            result[key] = df

        return result
