"""Dynamic HTML table parser for PSX pages.

Extracts table data without assuming fixed column positions. Headers are
mapped via COLUMN_MAP; unknown headers fall back to normalize_column_name
with a logged warning.
"""
from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from psxdata.constants import COLUMN_MAP
from psxdata.parsers.normalizers import normalize_column_name

logger = logging.getLogger(__name__)


def extract_table_headers(soup: BeautifulSoup) -> list[str]:
    """Extract and normalise column headers from the first table in soup.

    Applies COLUMN_MAP first; unknown headers fall back to
    normalize_column_name with a warning logged.

    Args:
        soup: Parsed HTML document.

    Returns:
        List of normalised column name strings.
    """
    th_tags = soup.find_all("th")
    if not th_tags:
        return []
    headers: list[str] = []
    for th in th_tags:
        raw = th.get_text(strip=True)
        if raw in COLUMN_MAP:
            headers.append(COLUMN_MAP[raw])
        else:
            normalised = normalize_column_name(raw)
            if raw:
                logger.warning(
                    "Unknown PSX column header %r — using fallback name %r. "
                    "Add to constants.COLUMN_MAP if this is a new PSX column.",
                    raw,
                    normalised,
                )
            headers.append(normalised)
    return headers


def parse_table_rows(soup: BeautifulSoup, headers: list[str]) -> list[dict[str, str]]:
    """Map <tr><td> rows to dicts keyed by normalised header name.

    Rows with a different cell count than headers get a warning logged but
    are still returned with available cells mapped.

    Args:
        soup: Parsed HTML document.
        headers: Normalised column names from extract_table_headers.

    Returns:
        List of row dicts mapping header name -> raw cell text.
    """
    rows: list[dict[str, str]] = []
    tbody = soup.find("tbody")
    tr_tags = tbody.find_all("tr") if tbody else soup.find_all("tr")

    for tr in tr_tags:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cells:
            continue
        if len(cells) != len(headers):
            logger.warning(
                "Row has %d cells but expected %d — partial mapping applied",
                len(cells),
                len(headers),
            )
        row = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
        rows.append(row)
    return rows


def parse_html_table(html: str) -> list[dict[str, str]]:
    """Parse the first HTML table in html, returning rows as normalised dicts.

    Returns an empty list for empty or malformed HTML with a warning logged.
    All values are raw strings — callers apply coerce_numeric / parse_date_safely.

    Args:
        html: Raw HTML string from a PSX endpoint response.

    Returns:
        List of row dicts. Each dict maps normalised column name -> raw string value.
    """
    soup = BeautifulSoup(html, "lxml")
    headers = extract_table_headers(soup)
    if not headers:
        logger.warning("No table headers found in HTML — returning empty result")
        return []
    return parse_table_rows(soup, headers)
