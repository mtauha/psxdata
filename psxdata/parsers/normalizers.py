"""Data normalisation utilities for psxdata parsers.

No imports from the psxdata library — these are pure functions with no
dependencies on scraping, caching, or models. Third-party imports
(dateutil, datetime) are fine.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from dateutil import parser as dateutil_parser

_PSX_DATE_FORMATS = ["%b %d, %Y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y"]


def parse_date_safely(value: Any) -> datetime | None:
    """Parse a date string using known PSX formats, falling back to fuzzy parsing.

    Never raises. Returns None for any unparseable or non-string input.

    Args:
        value: The value to parse. Non-str inputs return None immediately.

    Returns:
        datetime if parseable, None otherwise.
    """
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    for fmt in _PSX_DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return dateutil_parser.parse(value, fuzzy=True)
    except Exception:
        return None


def coerce_numeric(value: Any) -> float | None:
    """Convert a raw PSX cell value to float, stripping formatting characters.

    Handles commas, percent signs, currency prefixes (PKR), and whitespace.
    Never raises. Returns None for unparseable input.

    Args:
        value: Raw cell string from PSX HTML table.

    Returns:
        float if parseable, None otherwise.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", "").replace("%", "").replace("PKR", "").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def normalize_column_name(name: str) -> str:
    """Normalize a raw PSX table header to a snake_case identifier.

    Used as fallback for headers not found in constants.COLUMN_MAP.
    Strips whitespace, lowercases, replaces spaces with underscores,
    removes non-alphanumeric characters (except underscores).

    Args:
        name: Raw header string from a PSX <th> tag.

    Returns:
        Normalized snake_case string.
    """
    name = name.strip().lower()
    name = name.replace(" ", "_")
    name = re.sub(r"[^\w]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    return name
