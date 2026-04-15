"""PSXClient — high-level public API for psxdata.

Owns the DiskCache and all scraper instances. Scrapers are stateless
except for their requests.Session and never touch the cache directly.

Module-level convenience functions wrap a lazy default PSXClient so callers
can use ``import psxdata; psxdata.stocks("ENGRO")`` without instantiation.
"""
from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from psxdata.cache.disk_cache import DiskCache
from psxdata.constants import CACHE_DIR, CACHE_TTL_TODAY
from psxdata.scrapers.debt_market import DebtMarketScraper
from psxdata.scrapers.eligible_scrips import EligibleScripsScraper
from psxdata.scrapers.fundamentals import FundamentalsScraper
from psxdata.scrapers.historical import HistoricalScraper
from psxdata.scrapers.indices import IndicesScraper
from psxdata.scrapers.screener import ScreenerScraper
from psxdata.scrapers.sectors import SectorsScraper
from psxdata.scrapers.symbols import SymbolsScraper

logger = logging.getLogger(__name__)


def _today() -> pd.Timestamp:
    """Return today's date as a normalized Timestamp. Extracted for testability."""
    return pd.Timestamp.today().normalize()


class PSXClient:
    """Public Python API for Pakistan Stock Exchange data.

    All scrapers are instantiated once in ``__init__`` and reused across calls.
    Caching is managed here — scrapers never touch the cache.

    Args:
        cache_dir: Path to the cache directory. Tilde is expanded.
            Defaults to ``~/.psxdata/cache/``.

    Example::

        client = PSXClient()
        df = client.stocks("ENGRO", start="2024-01-01")
    """

    def __init__(self, cache_dir: str = CACHE_DIR) -> None:
        self._cache = DiskCache(cache_dir)
        self._historical = HistoricalScraper()
        self._screener = ScreenerScraper()
        self._symbols = SymbolsScraper()
        self._indices = IndicesScraper()
        self._sectors = SectorsScraper()
        self._fundamentals = FundamentalsScraper()
        self._debt_market = DebtMarketScraper()
        self._eligible_scrips = EligibleScripsScraper()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def stocks(
        self,
        symbol: str,
        start: date | str | None = None,
        end: date | str | None = None,
        cache: bool = True,
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data for a symbol.

        PSX returns all history in a single request. The response is split
        at today's boundary and stored under two cache keys:

        - ``{SYMBOL}_historical`` — rows before today, TTL=None (never expires)
        - ``{SYMBOL}_today`` — rows from today, TTL=15 min (intraday prices change)

        Args:
            symbol: PSX ticker, e.g. ``"ENGRO"``.
            start: Start date (inclusive). ``None`` means earliest available.
            end: End date (inclusive). ``None`` means today.
            cache: If ``False``, bypass cache and always fetch from PSX.

        Returns:
            DataFrame with columns: date, open, high, low, close, volume, is_anomaly.
            Empty DataFrame if no data is available for the given range.

        Raises:
            ValueError: If ``start`` is after ``end``.
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        sym = symbol.upper()
        today = _today()

        start_ts = pd.Timestamp(start) if start is not None else None
        end_ts = pd.Timestamp(end) if end is not None else today

        if start_ts is not None and start_ts > end_ts:
            raise ValueError(f"start ({start}) must not be after end ({end})")

        hist_key = f"{sym}_historical"
        today_key = f"{sym}_today"
        need_today = end_ts >= today

        if cache:
            hist_cached = self._cache.get(hist_key)
            # Always check — today cache may cover past dates after a day rollover.
            today_cached = self._cache.get(today_key)

            if hist_cached is not None:
                # Include any today-cache rows that fall on or before end_ts.
                # This handles the day-boundary case: after rollover, yesterday's
                # row may still be in {sym}_today but not yet in {sym}_historical.
                today_relevant = pd.DataFrame()
                if today_cached is not None and not today_cached.empty:
                    today_relevant = today_cached[today_cached["date"] <= end_ts].copy()

                hist_max = hist_cached["date"].max() if not hist_cached.empty else None
                today_max = today_relevant["date"].max() if not today_relevant.empty else None

                covered = (
                    (hist_max is not None and hist_max >= end_ts)
                    or (today_max is not None and today_max >= end_ts)
                    or (need_today and today_cached is not None)
                )

                if covered:
                    parts = [hist_cached]
                    if not today_relevant.empty:
                        parts.append(today_relevant)
                    df = pd.concat(parts, ignore_index=True)
                    return self._filter_date_range(df, start_ts, end_ts)

        logger.debug("Fetching historical data for %s from PSX", sym)
        raw = self._historical.fetch(sym, start=None, end=None)

        if raw.empty:
            return raw

        if cache:
            hist_df = raw[raw["date"] < today].copy()
            today_df = raw[raw["date"] >= today].copy()
            self._cache.set(hist_key, hist_df, ttl=None)
            if not today_df.empty:
                self._cache.set(today_key, today_df, ttl=CACHE_TTL_TODAY)

        return self._filter_date_range(raw, start_ts, end_ts)

    def quote(self, symbol: str, cache: bool = True) -> pd.DataFrame:
        """Fetch the latest screener snapshot for a symbol.

        The full screener (~729 symbols) is fetched once and cached for 15 minutes.
        Successive calls for different symbols reuse the same cached screener.

        Args:
            symbol: PSX ticker, e.g. ``"ENGRO"``.
            cache: If ``False``, bypass cache and always fetch the screener.

        Returns:
            Single-row DataFrame with screener columns (symbol, sector, price, …).
            Empty DataFrame if the symbol is not present in the screener.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        cache_key = "screener_all"
        screener_df: pd.DataFrame | None = None

        if cache:
            screener_df = self._cache.get(cache_key)

        if screener_df is None:
            logger.debug("Fetching screener from PSX")
            screener_df = self._screener.fetch()
            if cache and not screener_df.empty:
                self._cache.set(cache_key, screener_df, ttl=CACHE_TTL_TODAY)

        if screener_df.empty or "symbol" not in screener_df.columns:
            return pd.DataFrame()

        match = screener_df[screener_df["symbol"] == symbol.upper()]
        return match.reset_index(drop=True)

    def tickers(self, index: str | None = None, cache: bool = True) -> list[str]:
        """Return PSX ticker symbols, optionally filtered to an index.

        Args:
            index: Index name, e.g. ``"KSE100"``. ``None`` returns all listed
                symbols. See ``constants.INDEX_NAMES`` for valid names.
            cache: If ``False``, bypass cache.

        Returns:
            List of ticker strings, e.g. ``["ENGRO", "LUCK", ...]``.
            Empty list if no symbols are found.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
            PSXParseError: PSX returned 4xx for the given index name.
        """
        if index is None:
            cache_key = "symbols_all"
            df: pd.DataFrame | None = None

            if cache:
                df = self._cache.get(cache_key)

            if df is None:
                logger.debug("Fetching all symbols from PSX")
                df = self._symbols.fetch()
                if cache and not df.empty:
                    self._cache.set(cache_key, df, ttl=CACHE_TTL_TODAY)
        else:
            df = self._get_index_df(index.upper(), cache=cache)

        if df is None or df.empty or "symbol" not in df.columns:
            return []
        return df["symbol"].tolist()

    def indices(self, name: str, cache: bool = True) -> pd.DataFrame:
        """Fetch constituent data for a PSX index.

        ``tickers(index="KSE100")`` and ``indices("KSE100")`` share the same
        cache key (``indices_KSE100``), so the two methods never double-fetch.

        Args:
            name: Index name, e.g. ``"KSE100"``. See ``constants.INDEX_NAMES``.
            cache: If ``False``, bypass cache.

        Returns:
            DataFrame with columns: symbol, current_index, idx_weight,
            idx_point, market_cap_m, and either freefloat_m or shares_m.
            Empty DataFrame if PSX returns no data.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
            PSXParseError: PSX returned 4xx for the given index name.
        """
        df = self._get_index_df(name.upper(), cache=cache)
        return df if df is not None else pd.DataFrame()

    def sectors(self, cache: bool = True) -> pd.DataFrame:
        """Fetch the PSX sector summary.

        Args:
            cache: If ``False``, bypass cache.

        Returns:
            DataFrame with columns: sector_code, sector_name, advance, decline,
            unchanged, turnover, market_cap_b.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        cache_key = "sectors_all"
        df: pd.DataFrame | None = None

        if cache:
            df = self._cache.get(cache_key)

        if df is None:
            logger.debug("Fetching sectors from PSX")
            df = self._sectors.fetch()
            if cache and not df.empty:
                self._cache.set(cache_key, df, ttl=CACHE_TTL_TODAY)

        return df if df is not None else pd.DataFrame()

    def fundamentals(self, symbol: str | None = None, cache: bool = True) -> pd.DataFrame:
        """Fetch the PSX financial reports filing list.

        PSX returns all filings in a single request. When ``symbol`` is given,
        the result is filtered in memory.

        Args:
            symbol: If provided, return only filings for this ticker.
            cache: If ``False``, bypass cache.

        Returns:
            DataFrame with columns: symbol, year, type, period_ended,
            posting_date, posting_time, document.
            Empty DataFrame if outside reporting season or no data returned.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        cache_key = "fundamentals_all"
        df: pd.DataFrame | None = None

        if cache:
            df = self._cache.get(cache_key)

        if df is None:
            logger.debug("Fetching financial reports from PSX")
            df = self._fundamentals.fetch()
            if cache and not df.empty:
                self._cache.set(cache_key, df, ttl=CACHE_TTL_TODAY)

        if df is None or df.empty:
            return pd.DataFrame()

        if symbol is not None and "symbol" in df.columns:
            df = df[df["symbol"] == symbol.upper()].reset_index(drop=True)

        return df

    def debt_market(self, cache: bool = True) -> dict[str, pd.DataFrame]:
        """Fetch all PSX debt market instrument tables.

        Returns 4 tables. Keys are ``table_0`` through ``table_3`` (fallback
        index keys — the /debt-market page has no ``<h2>`` headings before its
        tables, so heading-based keys are not available). These key names are
        load-bearing: do not change them.

        Args:
            cache: If ``False``, bypass cache and always fetch from PSX.

        Returns:
            ``dict`` mapping ``table_0``..``table_3`` → DataFrame.
            Empty dict if no tables are found.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        cache_key = "debt_market_all"

        if cache:
            cached = self._cache.get_dict(cache_key)
            if cached is not None:
                return cached

        logger.debug("Fetching debt market data from PSX")
        data = self._debt_market.fetch()
        if cache and data:
            self._cache.set_dict(cache_key, data, ttl=CACHE_TTL_TODAY)
        return data

    def eligible_scrips(self, cache: bool = True) -> dict[str, pd.DataFrame]:
        """Fetch all PSX margin-trading eligible scrip tables.

        Returns 9 tables. Keys are ``table_0`` through ``table_8`` (fallback
        index keys — the /eligible-scrips ``<h2>`` headings are not direct
        siblings of ``<table>`` elements, so heading-based keys are not
        available). These key names are load-bearing: do not change them.

        Args:
            cache: If ``False``, bypass cache and always fetch from PSX.

        Returns:
            ``dict`` mapping ``table_0``..``table_8`` → DataFrame.
            Empty dict if no tables are found.

        Raises:
            PSXConnectionError: Network failure after retries.
            PSXServerError: 5xx after retries.
        """
        cache_key = "eligible_scrips_all"

        if cache:
            cached = self._cache.get_dict(cache_key)
            if cached is not None:
                return cached

        logger.debug("Fetching eligible scrips from PSX")
        data = self._eligible_scrips.fetch()
        if cache and data:
            self._cache.set_dict(cache_key, data, ttl=CACHE_TTL_TODAY)
        return data

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_index_df(self, name: str, cache: bool = True) -> pd.DataFrame | None:
        """Fetch or retrieve from cache the constituent DataFrame for *name*."""
        cache_key = f"indices_{name}"
        df: pd.DataFrame | None = None

        if cache:
            df = self._cache.get(cache_key)

        if df is None:
            logger.debug("Fetching index %s from PSX", name)
            df = self._indices.fetch(name)
            if cache and not df.empty:
                self._cache.set(cache_key, df, ttl=CACHE_TTL_TODAY)

        return df

    def _filter_date_range(
        self,
        df: pd.DataFrame,
        start: pd.Timestamp | None,
        end: pd.Timestamp | None,
    ) -> pd.DataFrame:
        """Apply an inclusive ``[start, end]`` filter on the ``date`` column."""
        if df.empty:
            return df
        mask = pd.Series(True, index=df.index)
        if start is not None:
            mask &= df["date"] >= start
        if end is not None:
            mask &= df["date"] <= end
        return df[mask].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Module-level convenience API
# ---------------------------------------------------------------------------

_default_client: PSXClient | None = None


def _client() -> PSXClient:
    global _default_client
    if _default_client is None:
        _default_client = PSXClient()
    return _default_client


def stocks(
    symbol: str,
    start: date | str | None = None,
    end: date | str | None = None,
    cache: bool = True,
) -> pd.DataFrame:
    """Fetch historical OHLCV data. See :class:`PSXClient.stocks` for full docs."""
    return _client().stocks(symbol, start=start, end=end, cache=cache)


def quote(symbol: str, cache: bool = True) -> pd.DataFrame:
    """Fetch screener snapshot for a symbol. See :class:`PSXClient.quote` for full docs."""
    return _client().quote(symbol, cache=cache)


def tickers(index: str | None = None, cache: bool = True) -> list[str]:
    """Return ticker symbols. See :class:`PSXClient.tickers` for full docs."""
    return _client().tickers(index=index, cache=cache)


def indices(name: str, cache: bool = True) -> pd.DataFrame:
    """Fetch index constituents. See :class:`PSXClient.indices` for full docs."""
    return _client().indices(name, cache=cache)


def sectors(cache: bool = True) -> pd.DataFrame:
    """Fetch sector summary. See :class:`PSXClient.sectors` for full docs."""
    return _client().sectors(cache=cache)


def fundamentals(symbol: str | None = None, cache: bool = True) -> pd.DataFrame:
    """Fetch financial reports list. See :class:`PSXClient.fundamentals` for full docs."""
    return _client().fundamentals(symbol=symbol, cache=cache)


def debt_market(cache: bool = True) -> dict[str, pd.DataFrame]:
    """Fetch debt market tables. See :class:`PSXClient.debt_market` for full docs."""
    return _client().debt_market(cache=cache)


def eligible_scrips(cache: bool = True) -> dict[str, pd.DataFrame]:
    """Fetch eligible scrip tables. See :class:`PSXClient.eligible_scrips` for full docs."""
    return _client().eligible_scrips(cache=cache)
