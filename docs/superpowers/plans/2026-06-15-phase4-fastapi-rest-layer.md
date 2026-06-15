# Phase 4 — FastAPI REST Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 11 REST endpoints across 4 routers that wrap the `psxdata` library, with slowapi rate limiting, full TDD coverage, and the existing error envelope preserved for all error codes including 429.

**Architecture:** Sync endpoints (`def`, not `async def`) so FastAPI runs them in a thread pool — correct for wrapping the blocking `psxdata` library. One router file per resource group. All new Pydantic response models in `api/schemas.py`, decoupled from `psxdata/models/schemas.py`. Rate limiting wired via `slowapi` with a custom 429 handler to preserve the `{"error": {...}}` envelope.

**Tech Stack:** FastAPI, Pydantic v2, slowapi, pytest + TestClient, pandas, psxdata library.

**Spec:** `docs/superpowers/specs/2026-06-03-phase4-fastapi-rest-layer-design.md`

---

## File Map

**Modified:**
- `api/dependencies.py` — replace `None`-returning stubs with real `Limiter` instance
- `api/main.py` — add slowapi middleware + custom 429 exception handler
- `api/schemas.py` — add 9 new response models
- `api/routers/__init__.py` — register 4 new routers as they are completed
- `psxdata/client.py` — add `PSXClient.symbols()` method
- `psxdata/__init__.py` — export module-level `symbols()`
- `tests/unit/api/test_error_envelope.py` — add 429 envelope test

**Created:**
- `api/routers/stocks.py`
- `api/routers/indices.py`
- `api/routers/sectors.py`
- `api/routers/market.py`
- `tests/unit/api/test_stocks.py`
- `tests/unit/api/test_indices.py`
- `tests/unit/api/test_sectors.py`
- `tests/unit/api/test_market.py`

---

## Task 1: Wire slowapi rate limiting

**Files:**
- Modify: `api/dependencies.py`
- Modify: `api/main.py`
- Modify: `tests/unit/api/test_error_envelope.py`

- [ ] **Step 1: Write the failing 429 test**

Add to the bottom of `tests/unit/api/test_error_envelope.py`. The module-level route definition and import must go at the top of the file alongside the existing sentinel routes:

```python
# Add these imports at the top of test_error_envelope.py
from fastapi import Request
from api.dependencies import limiter

# Add this sentinel route alongside the existing ones (module level, before any test functions)
@app.get("/__test_ratelimit_tight")
@limiter.limit("1/minute")
def _tight(request: Request):
    return {"ok": True}


# Add this test function at the bottom of the file
def test_rate_limited_uses_error_envelope(client: TestClient) -> None:
    client.get("/__test_ratelimit_tight")          # first request passes
    resp = client.get("/__test_ratelimit_tight")   # second request is rate limited
    assert resp.status_code == 429
    body = resp.json()
    assert "error" in body
    assert body["error"]["status"] == 429
    assert body["error"]["code"] == "rate_limited"
    assert "detail" not in body
```

- [ ] **Step 2: Run test to confirm it fails**

```
pytest tests/unit/api/test_error_envelope.py::test_rate_limited_uses_error_envelope -v
```

Expected: ImportError or AttributeError — `limiter` not yet defined in `dependencies.py`.

- [ ] **Step 3: Replace `api/dependencies.py` stubs with real Limiter**

Full file replacement:

```python
"""Shared FastAPI dependencies for the API layer."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


def get_rate_limiter() -> Limiter:
    return limiter


def get_cache() -> None:
    # TODO: return Redis client when Redis layer is added
    return None
```

- [ ] **Step 4: Add slowapi middleware and custom 429 handler to `api/main.py`**

Add these imports after the existing imports:

```python
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from api.dependencies import limiter
```

Add these two lines immediately after `app = FastAPI(title="psxdata", lifespan=lifespan)`:

```python
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
```

Add this exception handler alongside the existing handlers (before `for router in router_registry`):

```python
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": {"status": 429, "code": "rate_limited", "message": "Rate limit exceeded"}},
    )
```

- [ ] **Step 5: Run test to confirm it passes**

```
pytest tests/unit/api/test_error_envelope.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add api/dependencies.py api/main.py tests/unit/api/test_error_envelope.py
git commit -m "feat: wire slowapi rate limiting with custom 429 envelope handler"
```

---

## Task 2: Add `PSXClient.symbols()` for sector filtering

**Files:**
- Modify: `psxdata/client.py`
- Modify: `psxdata/__init__.py`
- Test: `tests/unit/test_client.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_client.py`:

```python
def test_symbols_returns_dataframe(mock_cache):
    """symbols() returns the full DataFrame from SymbolsScraper."""
    expected = pd.DataFrame({
        "symbol": ["ENGRO", "LUCK"],
        "name": ["Engro Corporation", "Lucky Cement"],
        "sector_name": ["FERTILIZER", "CEMENT"],
        "is_etf": [False, False],
        "is_debt": [False, False],
        "is_gem": [False, False],
    })
    client = PSXClient()
    with patch.object(client._symbols, "fetch", return_value=expected):
        result = client.symbols(cache=False)
    assert list(result["symbol"]) == ["ENGRO", "LUCK"]
    assert "sector_name" in result.columns


def test_symbols_shares_cache_with_tickers(mock_cache):
    """symbols() and tickers(index=None) share the 'symbols_all' cache key."""
    symbols_df = pd.DataFrame({
        "symbol": ["ENGRO"],
        "name": ["Engro Corporation"],
        "sector_name": ["FERTILIZER"],
        "is_etf": [False],
        "is_debt": [False],
        "is_gem": [False],
    })
    client = PSXClient()
    with patch.object(client._symbols, "fetch", return_value=symbols_df) as mock_fetch:
        client.tickers()   # populates symbols_all cache
        client.symbols()   # should reuse cache, not call fetch again
    mock_fetch.assert_called_once()  # fetch called only once total
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/unit/test_client.py::test_symbols_returns_dataframe tests/unit/test_client.py::test_symbols_shares_cache_with_tickers -v
```

Expected: `AttributeError: 'PSXClient' object has no attribute 'symbols'`

- [ ] **Step 3: Add `symbols()` method to `PSXClient` in `psxdata/client.py`**

Add after the `eligible_scrips` method (before `_get_index_df`):

```python
def symbols(self, cache: bool = True) -> pd.DataFrame:
    """Return all listed PSX symbols with sector names.

    Reuses the 'symbols_all' cache key shared with tickers(index=None).

    Args:
        cache: If ``False``, bypass cache.

    Returns:
        DataFrame with columns: symbol, name, sector_name, is_etf, is_debt, is_gem.
        Empty DataFrame if PSX returns no data.

    Raises:
        PSXConnectionError: Network failure after retries.
        PSXServerError: 5xx after retries.
    """
    df: pd.DataFrame | None = None

    if cache:
        df = self._cache.get("symbols_all")

    if df is None:
        logger.debug("Fetching all symbols from PSX")
        df = self._symbols.fetch()
        if cache and not df.empty:
            self._cache.set("symbols_all", df, ttl=CACHE_TTL_TODAY)

    return df if df is not None else pd.DataFrame()
```

- [ ] **Step 4: Add module-level `symbols()` function to `psxdata/client.py`**

Add after the module-level `eligible_scrips()` function:

```python
def symbols(cache: bool = True) -> pd.DataFrame:
    """Return all listed PSX symbols with sector names.

    Args:
        cache: If ``False``, bypass cache.

    Returns:
        DataFrame with columns: symbol, name, sector_name, is_etf, is_debt, is_gem.
        Empty DataFrame if PSX returns no data.

    Raises:
        PSXConnectionError: Network failure after retries.
        PSXServerError: 5xx after retries.

    Example::

        import psxdata
        df = psxdata.symbols()
        cement = df[df["sector_name"] == "CEMENT"]["symbol"].tolist()
    """
    return _client().symbols(cache=cache)
```

- [ ] **Step 5: Export `symbols` from `psxdata/__init__.py`**

Full file replacement:

```python
"""psxdata — Python library for Pakistan Stock Exchange data."""
from psxdata.client import (
    PSXClient,
    debt_market,
    eligible_scrips,
    fundamentals,
    indices,
    quote,
    sectors,
    stocks,
    symbols,
    tickers,
)
from psxdata.scrapers.base import BaseScraper

__version__ = "0.1.0a3"

__all__ = [
    "BaseScraper",
    "PSXClient",
    "stocks",
    "tickers",
    "quote",
    "indices",
    "sectors",
    "fundamentals",
    "debt_market",
    "eligible_scrips",
    "symbols",
]
```

- [ ] **Step 6: Run tests to confirm they pass**

```
pytest tests/unit/test_client.py::test_symbols_returns_dataframe tests/unit/test_client.py::test_symbols_shares_cache_with_tickers -v
```

Expected: both PASS.

- [ ] **Step 7: Run full unit suite to check for regressions**

```
pytest tests/unit/ -v --ignore=tests/unit/api
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add psxdata/client.py psxdata/__init__.py tests/unit/test_client.py
git commit -m "feat: add PSXClient.symbols() and psxdata.symbols() for sector filtering"
```

---

## Task 3: Extend API schemas

**Files:**
- Modify: `api/schemas.py`
- Modify: `tests/unit/api/test_schemas.py`

- [ ] **Step 1: Write the failing schema tests**

Add to `tests/unit/api/test_schemas.py`:

```python
from api.schemas import (
    FundamentalsResponse,
    FundamentalsRow,
    HistoricalResponse,
    IndexConstituentResponse,
    IndexConstituentRow,
    MarketTablesResponse,
    OHLCVRow,
    QuoteData,
    QuoteResponse,
    SectorRow,
    SectorsResponse,
    StringListResponse,
)


def test_string_list_response() -> None:
    r = StringListResponse(
        data=["ENGRO", "LUCK"],
        meta=MetaList(timestamp="2026-01-01T00:00:00+00:00", cached=False, count=2),
    )
    assert r.data == ["ENGRO", "LUCK"]
    assert r.meta.count == 2


def test_ohlcv_row() -> None:
    row = OHLCVRow(
        date="2024-01-05", open=481.99, high=496.0,
        low=474.01, close=485.38, volume=4496408, is_anomaly=False,
    )
    assert row.date == "2024-01-05"
    assert row.is_anomaly is False


def test_quote_data_optional_fields_default_none() -> None:
    q = QuoteData(symbol="ENGRO", price=481.99)
    assert q.ldcp is None
    assert q.change is None
    assert q.pe_ratio is None


def test_fundamentals_row() -> None:
    row = FundamentalsRow(
        symbol="ENGRO", year="2024", type="Annual",
        period_ended="2024-12-31", posting_date="2025-01-15",
        document="https://psx.com/report.pdf",
    )
    assert row.symbol == "ENGRO"


def test_index_constituent_row_optional_defaults() -> None:
    row = IndexConstituentRow(
        symbol="ENGRO", current_index=47500.0,
        idx_weight=5.2, idx_point=2470.0, market_cap_m=500000.0,
    )
    assert row.freefloat_m is None
    assert row.shares_m is None


def test_sector_row() -> None:
    row = SectorRow(
        sector_code="0801", sector_name="CEMENT",
        advance=5, decline=2, unchanged=1,
        turnover=1200000, market_cap_b=450.5,
    )
    assert row.sector_code == "0801"


def test_market_tables_response() -> None:
    r = MarketTablesResponse(
        data={"table_0": [{"security_code": "P01", "name": "1Y GIS"}]},
        meta=MetaSingle(timestamp="2026-01-01T00:00:00+00:00", cached=False),
    )
    assert "table_0" in r.data
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/unit/api/test_schemas.py -v
```

Expected: ImportError — new schema classes don't exist yet.

- [ ] **Step 3: Add new models to `api/schemas.py`**

Add `from typing import Any` to the imports at the top of `api/schemas.py`.

Append after the existing `HealthResponse` class:

```python
class StringListResponse(BaseModel):
    """Response for endpoints returning a plain list of strings."""

    data: list[str]
    meta: MetaList


# ---------------------------------------------------------------------------
# Stocks
# ---------------------------------------------------------------------------

class OHLCVRow(BaseModel):
    """Single OHLCV candlestick row in the public API."""

    date: str  # ISO 8601 date string, e.g. "2024-01-05"
    open: float
    high: float
    low: float
    close: float
    volume: int
    is_anomaly: bool


class HistoricalResponse(BaseModel):
    data: list[OHLCVRow]
    meta: MetaList


class QuoteData(BaseModel):
    """Screener snapshot for a single symbol."""

    symbol: str
    price: float
    market_cap: float | None = None
    pe_ratio: float | None = None
    dividend_yield: float | None = None
    free_float: float | None = None
    volume_avg_30d: float | None = None
    change_1y_pct: float | None = None
    ldcp: float | None = None        # not present in all screener responses
    change: float | None = None      # not present in all screener responses
    change_pct: float | None = None  # not present in all screener responses


class QuoteResponse(BaseModel):
    data: QuoteData
    meta: MetaSingle


class FundamentalsRow(BaseModel):
    """Single financial report filing row."""

    symbol: str
    year: str
    type: str
    period_ended: str   # ISO date string
    posting_date: str   # ISO date string
    document: str


class FundamentalsResponse(BaseModel):
    data: list[FundamentalsRow]
    meta: MetaList


# ---------------------------------------------------------------------------
# Indices
# ---------------------------------------------------------------------------

class IndexConstituentRow(BaseModel):
    """Single constituent row for a PSX index."""

    symbol: str
    current_index: float
    idx_weight: float
    idx_point: float
    market_cap_m: float
    freefloat_m: float | None = None  # present only on some indices
    shares_m: float | None = None     # present only on some indices


class IndexConstituentResponse(BaseModel):
    data: list[IndexConstituentRow]
    meta: MetaList


# ---------------------------------------------------------------------------
# Sectors
# ---------------------------------------------------------------------------

class SectorRow(BaseModel):
    """Sector-level aggregate row."""

    sector_code: str
    sector_name: str
    advance: int
    decline: int
    unchanged: int
    turnover: int
    market_cap_b: float


class SectorsResponse(BaseModel):
    data: list[SectorRow]
    meta: MetaList


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------

class MarketTablesResponse(BaseModel):
    """Response for debt-market and eligible-scrips endpoints.

    data keys are 'table_0'..'table_N' — opaque keys from the PSX page.
    Column schemas vary per table.
    """

    data: dict[str, list[dict[str, Any]]]
    meta: MetaSingle
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/unit/api/test_schemas.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add api/schemas.py tests/unit/api/test_schemas.py
git commit -m "feat: add Phase 4 API response schemas"
```

---

## Task 4: Stocks router (TDD)

**Files:**
- Create: `api/routers/stocks.py`
- Create: `tests/unit/api/test_stocks.py`
- Modify: `api/routers/__init__.py`

- [ ] **Step 1: Write the failing tests — create `tests/unit/api/test_stocks.py`**

```python
"""Unit tests for stocks router."""
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from psxdata.exceptions import PSXUnavailableError

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_list_stocks_returns_200(client: TestClient) -> None:
    with patch("psxdata.tickers", return_value=["ENGRO", "LUCK"]):
        resp = client.get("/stocks")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == ["ENGRO", "LUCK"]
    assert body["meta"]["count"] == 2
    assert "timestamp" in body["meta"]


def test_list_stocks_with_index_passes_index_param(client: TestClient) -> None:
    with patch("psxdata.tickers", return_value=["ENGRO"]) as mock_tickers:
        resp = client.get("/stocks?index=KSE100")
    assert resp.status_code == 200
    mock_tickers.assert_called_once_with(index="KSE100")


def test_list_stocks_empty_returns_200(client: TestClient) -> None:
    with patch("psxdata.tickers", return_value=[]):
        resp = client.get("/stocks")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
    assert resp.json()["meta"]["count"] == 0


def test_historical_returns_200_with_data(client: TestClient) -> None:
    df = pd.DataFrame({
        "date": [pd.Timestamp("2024-01-05")],
        "open": [481.99], "high": [496.0], "low": [474.01],
        "close": [485.38], "volume": [4496408], "is_anomaly": [False],
    })
    with patch("psxdata.stocks", return_value=df):
        resp = client.get("/stocks/ENGRO/historical")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["date"] == "2024-01-05"
    assert body["data"][0]["open"] == pytest.approx(481.99)
    assert body["meta"]["count"] == 1


def test_historical_empty_returns_200_not_404(client: TestClient) -> None:
    """Unknown symbol returns 200 with empty list — library cannot distinguish from empty range."""
    with patch("psxdata.stocks", return_value=pd.DataFrame()):
        resp = client.get("/stocks/UNKNOWN/historical")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_historical_passes_date_params(client: TestClient) -> None:
    with patch("psxdata.stocks", return_value=pd.DataFrame()) as mock_stocks:
        client.get("/stocks/ENGRO/historical?start=2024-01-01&end=2024-12-31")
    mock_stocks.assert_called_once_with("ENGRO", start="2024-01-01", end="2024-12-31")


def test_quote_returns_200(client: TestClient) -> None:
    df = pd.DataFrame({"symbol": ["ENGRO"], "price": [481.99]})
    with patch("psxdata.quote", return_value=df):
        resp = client.get("/stocks/ENGRO/quote")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["symbol"] == "ENGRO"
    assert body["data"]["price"] == pytest.approx(481.99)
    assert "timestamp" in body["meta"]
    assert "count" not in body["meta"]


def test_quote_returns_404_for_unknown_symbol(client: TestClient) -> None:
    with patch("psxdata.quote", return_value=pd.DataFrame()):
        resp = client.get("/stocks/FAKE/quote")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "not_found"


def test_fundamentals_returns_200_with_data(client: TestClient) -> None:
    df = pd.DataFrame({
        "symbol": ["ENGRO"], "year": ["2024"], "type": ["Annual"],
        "period_ended": [pd.Timestamp("2024-12-31")],
        "posting_date": [pd.Timestamp("2025-01-15")],
        "document": ["https://psx.com/report.pdf"],
    })
    with patch("psxdata.fundamentals", return_value=df):
        resp = client.get("/stocks/ENGRO/fundamentals")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["period_ended"] == "2024-12-31"
    assert body["data"][0]["posting_date"] == "2025-01-15"


def test_fundamentals_empty_returns_200(client: TestClient) -> None:
    with patch("psxdata.fundamentals", return_value=pd.DataFrame()):
        resp = client.get("/stocks/ENGRO/fundamentals")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_stocks_psx_unavailable_returns_503(client: TestClient) -> None:
    with patch("psxdata.tickers", side_effect=PSXUnavailableError("PSX down")):
        resp = client.get("/stocks")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "psx_unavailable"


def test_stocks_cors_header_present(client: TestClient) -> None:
    with patch("psxdata.tickers", return_value=[]):
        resp = client.get("/stocks", headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" in resp.headers
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/unit/api/test_stocks.py -v
```

Expected: 404 errors — `/stocks` route does not exist yet.

- [ ] **Step 3: Create `api/routers/stocks.py`**

```python
"""Stocks router — /stocks and /stocks/{symbol}/* endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import psxdata
from fastapi import APIRouter, HTTPException, Request

from api.dependencies import limiter
from api.schemas import (
    FundamentalsResponse,
    FundamentalsRow,
    HistoricalResponse,
    MetaList,
    MetaSingle,
    OHLCVRow,
    QuoteData,
    QuoteResponse,
    StringListResponse,
)

router = APIRouter(tags=["stocks"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to JSON-safe records: Timestamps to ISO strings, NaN to None."""
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None)
    df = df.where(pd.notna(df), other=None)
    return df.to_dict("records")


@router.get("/stocks", response_model=StringListResponse)
@limiter.limit("60/minute")
def list_stocks(request: Request, index: str | None = None) -> StringListResponse:
    tickers = psxdata.tickers(index=index)
    return StringListResponse(
        data=tickers,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(tickers)),
    )


@router.get("/stocks/{symbol}/historical", response_model=HistoricalResponse)
@limiter.limit("60/minute")
def get_historical(
    request: Request,
    symbol: str,
    start: str | None = None,
    end: str | None = None,
) -> HistoricalResponse:
    df = psxdata.stocks(symbol.upper(), start=start, end=end)
    rows: list[OHLCVRow] = []
    if not df.empty:
        rows = [OHLCVRow(**{k: r.get(k) for k in OHLCVRow.model_fields}) for r in _df_to_records(df)]
    return HistoricalResponse(
        data=rows,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(rows)),
    )


@router.get("/stocks/{symbol}/quote", response_model=QuoteResponse)
@limiter.limit("60/minute")
def get_quote(request: Request, symbol: str) -> QuoteResponse:
    df = psxdata.quote(symbol.upper())
    if df.empty:
        raise HTTPException(status_code=404, detail=f"{symbol.upper()} not found")
    row = _df_to_records(df)[0]
    data = QuoteData(**{k: row.get(k) for k in QuoteData.model_fields})
    return QuoteResponse(
        data=data,
        meta=MetaSingle(timestamp=_now_iso(), cached=False),
    )


@router.get("/stocks/{symbol}/fundamentals", response_model=FundamentalsResponse)
@limiter.limit("60/minute")
def get_fundamentals(request: Request, symbol: str) -> FundamentalsResponse:
    df = psxdata.fundamentals(symbol=symbol.upper())
    rows: list[FundamentalsRow] = []
    if not df.empty:
        rows = [
            FundamentalsRow(**{k: r.get(k) for k in FundamentalsRow.model_fields})
            for r in _df_to_records(df)
        ]
    return FundamentalsResponse(
        data=rows,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(rows)),
    )
```

- [ ] **Step 4: Register stocks router in `api/routers/__init__.py`**

```python
from fastapi import APIRouter

from api.routers.health import router as health_router
from api.routers.stocks import router as stocks_router

router_registry: list[APIRouter] = [health_router, stocks_router]
```

- [ ] **Step 5: Run tests to confirm they pass**

```
pytest tests/unit/api/test_stocks.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Run full API test suite to check for regressions**

```
pytest tests/unit/api/ -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add api/routers/stocks.py api/routers/__init__.py tests/unit/api/test_stocks.py
git commit -m "feat: add stocks router with TDD coverage"
```

---

## Task 5: Indices router (TDD)

**Files:**
- Create: `api/routers/indices.py`
- Create: `tests/unit/api/test_indices.py`
- Modify: `api/routers/__init__.py`

- [ ] **Step 1: Write the failing tests — create `tests/unit/api/test_indices.py`**

```python
"""Unit tests for indices router."""
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from psxdata.exceptions import PSXParseError, PSXUnavailableError

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_list_indices_returns_all_index_names(client: TestClient) -> None:
    resp = client.get("/indices")
    assert resp.status_code == 200
    body = resp.json()
    assert "KSE100" in body["data"]
    assert "ALLSHR" in body["data"]
    assert body["meta"]["count"] == 18  # INDEX_NAMES has 18 entries
    assert "timestamp" in body["meta"]


def test_list_indices_makes_no_network_call(client: TestClient) -> None:
    with patch("psxdata.indices") as mock_indices:
        resp = client.get("/indices")
    mock_indices.assert_not_called()
    assert resp.status_code == 200


def test_get_index_constituents_returns_200(client: TestClient) -> None:
    df = pd.DataFrame({
        "symbol": ["ENGRO", "LUCK"],
        "current_index": [47500.0, 47500.0],
        "idx_weight": [5.2, 3.1],
        "idx_point": [2470.0, 1472.5],
        "market_cap_m": [500000.0, 300000.0],
        "freefloat_m": [250000.0, 150000.0],
    })
    with patch("psxdata.indices", return_value=df):
        resp = client.get("/indices/KSE100")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["data"][0]["symbol"] == "ENGRO"
    assert body["data"][0]["freefloat_m"] == pytest.approx(250000.0)
    assert body["data"][0]["shares_m"] is None
    assert body["meta"]["count"] == 2


def test_get_index_with_shares_m_column(client: TestClient) -> None:
    """Some indices use shares_m instead of freefloat_m."""
    df = pd.DataFrame({
        "symbol": ["ENGRO"],
        "current_index": [47500.0],
        "idx_weight": [5.2],
        "idx_point": [2470.0],
        "market_cap_m": [500000.0],
        "shares_m": [100000.0],
    })
    with patch("psxdata.indices", return_value=df):
        resp = client.get("/indices/KMI30")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"][0]["shares_m"] == pytest.approx(100000.0)
    assert body["data"][0]["freefloat_m"] is None


def test_get_index_unknown_returns_404(client: TestClient) -> None:
    with patch("psxdata.indices", side_effect=PSXParseError("404 for FAKE")):
        resp = client.get("/indices/FAKE")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_get_index_psx_unavailable_returns_503(client: TestClient) -> None:
    with patch("psxdata.indices", side_effect=PSXUnavailableError("PSX down")):
        resp = client.get("/indices/KSE100")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "psx_unavailable"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/unit/api/test_indices.py -v
```

Expected: 404 errors — `/indices` route does not exist yet.

- [ ] **Step 3: Create `api/routers/indices.py`**

```python
"""Indices router — /indices and /indices/{name} endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import psxdata
from fastapi import APIRouter, HTTPException, Request
from psxdata.constants import INDEX_NAMES
from psxdata.exceptions import PSXParseError

from api.dependencies import limiter
from api.schemas import (
    IndexConstituentResponse,
    IndexConstituentRow,
    MetaList,
    StringListResponse,
)

router = APIRouter(tags=["indices"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/indices", response_model=StringListResponse)
@limiter.limit("60/minute")
def list_indices(request: Request) -> StringListResponse:
    names = list(INDEX_NAMES)
    return StringListResponse(
        data=names,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(names)),
    )


@router.get("/indices/{name}", response_model=IndexConstituentResponse)
@limiter.limit("60/minute")
def get_index(request: Request, name: str) -> IndexConstituentResponse:
    try:
        df = psxdata.indices(name.upper())
    except PSXParseError:
        raise HTTPException(status_code=404, detail=f"Index {name.upper()} not found")

    rows: list[IndexConstituentRow] = []
    if not df.empty:
        df = df.where(pd.notna(df), other=None)
        for record in df.to_dict("records"):
            rows.append(
                IndexConstituentRow(
                    symbol=record.get("symbol", ""),
                    current_index=record.get("current_index", 0.0),
                    idx_weight=record.get("idx_weight", 0.0),
                    idx_point=record.get("idx_point", 0.0),
                    market_cap_m=record.get("market_cap_m", 0.0),
                    freefloat_m=record.get("freefloat_m"),
                    shares_m=record.get("shares_m"),
                )
            )
    return IndexConstituentResponse(
        data=rows,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(rows)),
    )
```

- [ ] **Step 4: Register indices router in `api/routers/__init__.py`**

```python
from fastapi import APIRouter

from api.routers.health import router as health_router
from api.routers.indices import router as indices_router
from api.routers.stocks import router as stocks_router

router_registry: list[APIRouter] = [health_router, stocks_router, indices_router]
```

- [ ] **Step 5: Run tests to confirm they pass**

```
pytest tests/unit/api/test_indices.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Run full API test suite**

```
pytest tests/unit/api/ -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add api/routers/indices.py api/routers/__init__.py tests/unit/api/test_indices.py
git commit -m "feat: add indices router with TDD coverage"
```

---

## Task 6: Sectors router (TDD)

**Files:**
- Create: `api/routers/sectors.py`
- Create: `tests/unit/api/test_sectors.py`
- Modify: `api/routers/__init__.py`

- [ ] **Step 1: Write the failing tests — create `tests/unit/api/test_sectors.py`**

```python
"""Unit tests for sectors router."""
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from psxdata.exceptions import PSXUnavailableError

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_list_sectors_returns_200(client: TestClient) -> None:
    df = pd.DataFrame({
        "sector_code": ["0801", "0804"],
        "sector_name": ["CEMENT", "FERTILIZER"],
        "advance": [5, 2], "decline": [2, 1], "unchanged": [1, 0],
        "turnover": [1200000, 800000], "market_cap_b": [450.5, 320.1],
    })
    with patch("psxdata.sectors", return_value=df):
        resp = client.get("/sectors")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["data"][0]["sector_name"] == "CEMENT"
    assert body["meta"]["count"] == 2


def test_list_sectors_empty_returns_200(client: TestClient) -> None:
    with patch("psxdata.sectors", return_value=pd.DataFrame()):
        resp = client.get("/sectors")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_get_sector_stocks_returns_matching_symbols(client: TestClient) -> None:
    symbols_df = pd.DataFrame({
        "symbol": ["LUCK", "DGKC", "ENGRO"],
        "sector_name": ["CEMENT", "CEMENT", "FERTILIZER"],
    })
    with patch("psxdata.symbols", return_value=symbols_df):
        resp = client.get("/sectors/CEMENT/stocks")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["data"]) == {"LUCK", "DGKC"}
    assert body["meta"]["count"] == 2


def test_get_sector_stocks_case_insensitive(client: TestClient) -> None:
    symbols_df = pd.DataFrame({"symbol": ["LUCK"], "sector_name": ["CEMENT"]})
    with patch("psxdata.symbols", return_value=symbols_df):
        resp = client.get("/sectors/cement/stocks")
    assert resp.status_code == 200
    assert resp.json()["data"] == ["LUCK"]


def test_get_sector_stocks_unknown_returns_empty(client: TestClient) -> None:
    symbols_df = pd.DataFrame({"symbol": ["LUCK"], "sector_name": ["CEMENT"]})
    with patch("psxdata.symbols", return_value=symbols_df):
        resp = client.get("/sectors/UNKNOWN/stocks")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
    assert resp.json()["meta"]["count"] == 0


def test_sectors_psx_unavailable_returns_503(client: TestClient) -> None:
    with patch("psxdata.sectors", side_effect=PSXUnavailableError("PSX down")):
        resp = client.get("/sectors")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "psx_unavailable"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/unit/api/test_sectors.py -v
```

Expected: 404 errors — `/sectors` route does not exist yet.

- [ ] **Step 3: Create `api/routers/sectors.py`**

```python
"""Sectors router — /sectors and /sectors/{name}/stocks endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import psxdata
from fastapi import APIRouter, Request

from api.dependencies import limiter
from api.schemas import (
    MetaList,
    SectorRow,
    SectorsResponse,
    StringListResponse,
)

router = APIRouter(tags=["sectors"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/sectors", response_model=SectorsResponse)
@limiter.limit("60/minute")
def list_sectors(request: Request) -> SectorsResponse:
    df = psxdata.sectors()
    rows: list[SectorRow] = []
    if not df.empty:
        df = df.where(pd.notna(df), other=None)
        rows = [SectorRow(**{k: r.get(k) for k in SectorRow.model_fields}) for r in df.to_dict("records")]
    return SectorsResponse(
        data=rows,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(rows)),
    )


@router.get("/sectors/{name}/stocks", response_model=StringListResponse)
@limiter.limit("60/minute")
def get_sector_stocks(request: Request, name: str) -> StringListResponse:
    df = psxdata.symbols()
    tickers: list[str] = []
    if not df.empty and "sector_name" in df.columns and "symbol" in df.columns:
        matched = df[df["sector_name"].str.upper() == name.upper()]
        tickers = matched["symbol"].tolist()
    return StringListResponse(
        data=tickers,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(tickers)),
    )
```

- [ ] **Step 4: Register sectors router in `api/routers/__init__.py`**

```python
from fastapi import APIRouter

from api.routers.health import router as health_router
from api.routers.indices import router as indices_router
from api.routers.sectors import router as sectors_router
from api.routers.stocks import router as stocks_router

router_registry: list[APIRouter] = [health_router, stocks_router, indices_router, sectors_router]
```

- [ ] **Step 5: Run tests to confirm they pass**

```
pytest tests/unit/api/test_sectors.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Run full API test suite**

```
pytest tests/unit/api/ -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add api/routers/sectors.py api/routers/__init__.py tests/unit/api/test_sectors.py
git commit -m "feat: add sectors router with TDD coverage"
```

---

## Task 7: Market router (TDD)

**Files:**
- Create: `api/routers/market.py`
- Create: `tests/unit/api/test_market.py`
- Modify: `api/routers/__init__.py`

- [ ] **Step 1: Write the failing tests — create `tests/unit/api/test_market.py`**

```python
"""Unit tests for market router."""
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from psxdata.exceptions import PSXUnavailableError

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_debt_tables() -> dict[str, pd.DataFrame]:
    return {
        "table_0": pd.DataFrame({
            "security_code": ["P01GIS080227"],
            "security_name": ["1 Year GIS"],
            "face_value": [5000.0],
            "maturity_date": [pd.Timestamp("2027-02-08")],
            "coupon_rate": [0.0],
        }),
        "table_1": pd.DataFrame(),
    }


def test_debt_market_returns_200(client: TestClient) -> None:
    with patch("psxdata.debt_market", return_value=_make_debt_tables()):
        resp = client.get("/debt-market")
    assert resp.status_code == 200
    body = resp.json()
    assert "table_0" in body["data"]
    assert "table_1" in body["data"]
    assert body["data"]["table_0"][0]["security_code"] == "P01GIS080227"
    assert "timestamp" in body["meta"]
    assert "count" not in body["meta"]


def test_debt_market_serializes_timestamps(client: TestClient) -> None:
    with patch("psxdata.debt_market", return_value=_make_debt_tables()):
        resp = client.get("/debt-market")
    assert resp.json()["data"]["table_0"][0]["maturity_date"] == "2027-02-08"


def test_debt_market_empty_table_returns_empty_list(client: TestClient) -> None:
    with patch("psxdata.debt_market", return_value={"table_0": pd.DataFrame()}):
        resp = client.get("/debt-market")
    assert resp.status_code == 200
    assert resp.json()["data"]["table_0"] == []


def test_debt_market_psx_unavailable_returns_503(client: TestClient) -> None:
    with patch("psxdata.debt_market", side_effect=PSXUnavailableError("PSX down")):
        resp = client.get("/debt-market")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "psx_unavailable"


def test_eligible_scrips_returns_200(client: TestClient) -> None:
    tables = {"table_0": pd.DataFrame({"symbol": ["ENGRO"], "name": ["Engro Corp"]})}
    with patch("psxdata.eligible_scrips", return_value=tables):
        resp = client.get("/eligible-scrips")
    assert resp.status_code == 200
    body = resp.json()
    assert "table_0" in body["data"]
    assert body["data"]["table_0"][0]["symbol"] == "ENGRO"


def test_eligible_scrips_psx_unavailable_returns_503(client: TestClient) -> None:
    with patch("psxdata.eligible_scrips", side_effect=PSXUnavailableError("PSX down")):
        resp = client.get("/eligible-scrips")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "psx_unavailable"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/unit/api/test_market.py -v
```

Expected: 404 errors — `/debt-market` route does not exist yet.

- [ ] **Step 3: Create `api/routers/market.py`**

```python
"""Market router — /debt-market and /eligible-scrips endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import psxdata
from fastapi import APIRouter, Request

from api.dependencies import limiter
from api.schemas import MarketTablesResponse, MetaSingle

router = APIRouter(tags=["market"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame to JSON-safe records: Timestamps to ISO strings, NaN to None."""
    if df.empty:
        return []
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None)
    df = df.where(pd.notna(df), other=None)
    return df.to_dict("records")


def _serialize_tables(tables: dict[str, pd.DataFrame]) -> dict[str, list[dict[str, Any]]]:
    return {key: _df_to_records(df) for key, df in tables.items()}


@router.get("/debt-market", response_model=MarketTablesResponse)
@limiter.limit("60/minute")
def get_debt_market(request: Request) -> MarketTablesResponse:
    tables = psxdata.debt_market()
    return MarketTablesResponse(
        data=_serialize_tables(tables),
        meta=MetaSingle(timestamp=_now_iso(), cached=False),
    )


@router.get("/eligible-scrips", response_model=MarketTablesResponse)
@limiter.limit("60/minute")
def get_eligible_scrips(request: Request) -> MarketTablesResponse:
    tables = psxdata.eligible_scrips()
    return MarketTablesResponse(
        data=_serialize_tables(tables),
        meta=MetaSingle(timestamp=_now_iso(), cached=False),
    )
```

- [ ] **Step 4: Register market router in `api/routers/__init__.py`**

```python
from fastapi import APIRouter

from api.routers.health import router as health_router
from api.routers.indices import router as indices_router
from api.routers.market import router as market_router
from api.routers.sectors import router as sectors_router
from api.routers.stocks import router as stocks_router

router_registry: list[APIRouter] = [
    health_router,
    stocks_router,
    indices_router,
    sectors_router,
    market_router,
]
```

- [ ] **Step 5: Run tests to confirm they pass**

```
pytest tests/unit/api/test_market.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Run the complete test suite**

```
pytest tests/unit/ -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add api/routers/market.py api/routers/__init__.py tests/unit/api/test_market.py
git commit -m "feat: add market router with TDD coverage — Phase 4 complete"
```
