"""All PSX endpoint URLs, timeouts, rate limits, cache config, and column mappings.

No magic numbers or hardcoded strings anywhere else in psxdata — import from here.
"""

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------
BASE_URL = "https://dps.psx.com.pk"

ENDPOINTS: dict[str, str] = {
    "historical": "/historical",
    "indices": "/indices",
    "sector_summary": "/sector-summary",
    "financial_reports": "/financial-reports",
    "screener": "/screener",
    "trading_panel": "/trading-panel",
    "debt_market": "/debt-market",
    "eligible_scrips": "/eligible-scrips",
}

REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://dps.psx.com.pk/",
    "X-Requested-With": "XMLHttpRequest",
}

REQUEST_TIMEOUT: int = 30  # seconds

# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------
MAX_RETRIES: int = 3
RETRY_DELAYS: tuple[int, ...] = (1, 2, 4)  # seconds, exponential backoff

# Invariant — uses explicit raise, not assert (assert is stripped with python -O)
if len(RETRY_DELAYS) != MAX_RETRIES:
    raise ValueError(
        f"constants.py misconfigured: len(RETRY_DELAYS)={len(RETRY_DELAYS)} "
        f"must equal MAX_RETRIES={MAX_RETRIES}"
    )

# ---------------------------------------------------------------------------
# Rate limiting & concurrency
# ---------------------------------------------------------------------------
MAX_REQUESTS_PER_SECOND: int = 2
MAX_WORKERS: int = 5
DEFAULT_CHUNK_DAYS: int = 365

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
CACHE_DIR: str = "~/.psxdata/cache/"
CACHE_TTL_TODAY: int = 900  # 15 minutes in seconds

# ---------------------------------------------------------------------------
# Column name mapping
# Raw PSX <th> header text -> internal snake_case name.
# Unknown headers fall back to normalize_column_name() + logged warning.
# ---------------------------------------------------------------------------
COLUMN_MAP: dict[str, str] = {
    "DATE": "date",
    "OPEN": "open",
    "HIGH": "high",
    "LOW": "low",
    "CLOSE": "close",
    "VOLUME": "volume",
    "CHANGE (%)": "change_pct",
    "CHANGE": "change",
    "% Change": "change_pct",
    "SYMBOL": "symbol",
    "NAME": "name",
    "SECTOR": "sector",
    "LISTED IN": "listed_in",
    "MARKET CAP.": "market_cap",
    "MARKET CAP. (B)": "market_cap_b",
    "PRICE": "price",
    "PE RATIO (TTM)": "pe_ratio",
    "DIVIDEND YIELD (%)": "dividend_yield",
    "FREE FLOAT": "free_float",
    "30D VOLUME AVG.": "volume_avg_30d",
    "1-YEAR CH. (%) *": "change_1y_pct",
    "LDCP": "ldcp",
    "CURRENT": "current",
    "Current": "current",
    "ADVANCE": "advance",
    "DECLINE": "decline",
    "UNCHANGE": "unchanged",
    "TURNOVER": "turnover",
    "SECTOR CODE": "sector_code",
    "Sector Code": "sector_code",
    "SECTOR NAME": "sector_name",
    "Sector Name": "sector_name",
    "Index": "index_name",
    "High": "high",
    "Low": "low",
    "YEAR": "year",
    "TYPE": "type",
    "PERIOD ENDED": "period_ended",
    "POSTING DATE": "posting_date",
    "POSTING TIME": "posting_time",
    "DOCUMENT": "document",
    "Security Code": "security_code",
    "Security Name": "security_name",
    "Face Value": "face_value",
    "Listing Date": "listing_date",
    "Issue Date": "issue_date",
    "Issue Size": "issue_size",
    "Maturity Date": "maturity_date",
    "Coupon/Rental Rate": "coupon_rate",
    "Previous Coupon/Rental Date": "prev_coupon_date",
    "Next Coupon/Rental Date": "next_coupon_date",
    "Outstanding Days": "outstanding_days",
    "Remaining Years": "remaining_years",
    "Advance": "advance",
    "Decline": "decline",
    "Unchange": "unchanged",
    "Turnover": "turnover",
    "Market Cap. (B)": "market_cap_b",
}
