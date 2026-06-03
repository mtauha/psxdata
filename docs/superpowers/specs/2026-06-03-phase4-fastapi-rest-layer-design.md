# Phase 4 — FastAPI REST Layer Design

**Date:** 2026-06-03
**Issue:** [#8](https://github.com/mtauha/psxdata/issues/8)
**Status:** Approved

---

## Overview

Build the `api/` FastAPI service that wraps the `psxdata` Python library and exposes PSX data over HTTP. The API is deployed as a standalone remote service — anyone can call it without installing the Python package.

**Out of scope for this phase (kept in mind for architecture):**
- Redis caching layer (hook point reserved in `dependencies.py`)
- Dockerfile (no Playwright, Python 3.11-slim base — straightforward when endpoints are complete)

**Approach:** TDD — tests are written before each router implementation.

---

## What's Already Done

| Artifact | Status |
|---|---|
| `api/main.py` — FastAPI app, CORS, 5 error handlers | ✅ |
| `api/schemas.py` — `MetaSingle`, `MetaList`, `ErrorDetail`, `ErrorEnvelope`, `HealthData`, `HealthResponse` | ✅ |
| `api/routers/health.py` — `GET /health` | ✅ |
| `api/dependencies.py` — stubs for `get_cache()`, `get_rate_limiter()` | ✅ (stubs only) |
| `tests/unit/api/test_health.py` — 17 tests | ✅ |

---

## Architecture

### File Layout

```
api/
├── main.py              # app, CORS, error handlers, slowapi wiring
├── dependencies.py      # Limiter instance + get_limiter(); get_cache() stub retained
├── schemas.py           # all public response models (grows in place)
├── __init__.py
└── routers/
    ├── __init__.py      # router_registry — registers all 5 routers
    ├── health.py        # done
    ├── stocks.py        # new
    ├── indices.py       # new
    ├── sectors.py       # new
    └── market.py        # new

psxdata/
└── client.py            # add PSXClient.symbols() — thin wrapper needed for sectors/{name}/stocks

tests/unit/api/
    ├── test_health.py   # done
    ├── test_stocks.py   # new
    ├── test_indices.py  # new
    ├── test_sectors.py  # new
    └── test_market.py   # new
```

### Sync/Async

All endpoints are plain `def` (not `async def`). FastAPI automatically runs sync endpoints in a thread pool. This is the correct pattern for wrapping the `psxdata` library, which uses `requests.Session` and `time.sleep` — it is fully synchronous. Using `async def` with a blocking sync library would block the event loop.

### PSXClient singleton

Routers call the module-level convenience functions (`psxdata.stocks()`, `psxdata.tickers()`, etc.) which share a single lazy `PSXClient` instance. No dependency injection needed for the library layer — the client manages its own cache and scraper lifecycle.

---

## Library Change: `PSXClient.symbols()`

`GET /sectors/{name}/stocks` requires filtering symbols by sector name. The screener's `sector` column contains numeric codes (`0801`, `0804`), not names — direct filtering against `sectors()` output is impossible. `SymbolsScraper` returns all ~1029 listed instruments with string `sector_name` — this is the canonical join source.

Add one public method to `PSXClient`:

```python
def symbols(self, cache: bool = True) -> pd.DataFrame:
    """Return all listed PSX symbols with sector names.

    Reuses the 'symbols_all' cache key shared with tickers(index=None).
    Returns DataFrame with at minimum: symbol, sector_name columns.
    """
```

This reuses the `symbols_all` cache key already managed by `tickers(index=None)` — no double-fetch, no new cache key, no TTL change.

A corresponding module-level convenience function `psxdata.symbols()` is also added.

---

## Endpoints

### Stocks — `api/routers/stocks.py`

| Method | Path | Query params | Library call | Response model |
|---|---|---|---|---|
| GET | `/stocks` | `index=` (optional) | `tickers(index=...)` | `StringListResponse` |
| GET | `/stocks/{symbol}/historical` | `start=`, `end=` (YYYY-MM-DD, optional) | `stocks(symbol, start, end)` | `HistoricalResponse` |
| GET | `/stocks/{symbol}/quote` | — | `quote(symbol)` | `QuoteResponse` |
| GET | `/stocks/{symbol}/fundamentals` | — | `fundamentals(symbol)` | `FundamentalsResponse` |

**Error behaviour:**
- `GET /stocks/{symbol}/historical`: empty DataFrame → `200 data: []` (valid symbol with no data in range is indistinguishable from unknown symbol at the library level)
- `GET /stocks/{symbol}/quote`: empty DataFrame → `404` (symbol not in screener = does not exist)
- `GET /stocks/{symbol}/fundamentals`: empty DataFrame → `200 data: []` (outside reporting season is valid)

### Indices — `api/routers/indices.py`

| Method | Path | Library call | Response model |
|---|---|---|---|
| GET | `/indices` | `constants.INDEX_NAMES` (no network call) | `StringListResponse` |
| GET | `/indices/{name}` | `indices(name)` | `IndexConstituentResponse` |

**Note:** There is no historical index-level time series in the library. `IndicesScraper` returns current constituent snapshots only (symbol weights, market cap, etc.). Historical index levels would require a new scraper — deferred to a future phase.

**Error behaviour:**
- `GET /indices/{name}`: `PSXParseError` from PSX → `404`

### Sectors — `api/routers/sectors.py`

| Method | Path | Library call | Response model |
|---|---|---|---|
| GET | `/sectors` | `sectors()` | `SectorsResponse` |
| GET | `/sectors/{name}/stocks` | `symbols()` filtered by `sector_name` | `StringListResponse` |

**Error behaviour:**
- `GET /sectors/{name}/stocks`: no matching symbols → `200 data: []`

### Market — `api/routers/market.py`

| Method | Path | Library call | Response model |
|---|---|---|---|
| GET | `/debt-market` | `debt_market()` | `MarketTablesResponse` |
| GET | `/eligible-scrips` | `eligible_scrips()` | `MarketTablesResponse` |

Both return `dict[str, DataFrame]` with opaque `table_0..table_N` keys and varying column schemas per table. Serialized as `{"data": {"table_0": [...rows...], ...}}`.

---

## Schemas

All models in `api/schemas.py`. Separate from `psxdata/models/schemas.py` — the API contract must not be coupled to internal library models.

### Shared

```python
class StringListResponse(BaseModel):
    data: list[str]
    meta: MetaList
```

Used by: `GET /stocks`, `GET /indices`, `GET /sectors/{name}/stocks`.

### Stocks

```python
class OHLCVRow(BaseModel):
    date: str           # ISO 8601 date string
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
    symbol: str
    ldcp: float
    price: float
    change: float
    change_pct: float
    volume_avg_30d: float | None
    market_cap: float | None
    pe_ratio: float | None
    dividend_yield: float | None

class QuoteResponse(BaseModel):
    data: QuoteData
    meta: MetaSingle

class FundamentalsRow(BaseModel):
    symbol: str
    year: str
    type: str
    period_ended: str
    posting_date: str
    document: str

class FundamentalsResponse(BaseModel):
    data: list[FundamentalsRow]
    meta: MetaList
```

### Indices

```python
class IndexConstituentRow(BaseModel):
    symbol: str
    current_index: float
    idx_weight: float
    idx_point: float
    market_cap_m: float
    freefloat_m: float | None
    shares_m: float | None

class IndexConstituentResponse(BaseModel):
    data: list[IndexConstituentRow]
    meta: MetaList
```

### Sectors

```python
class SectorRow(BaseModel):
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
```

### Market

```python
class MarketTablesResponse(BaseModel):
    data: dict[str, list[dict[str, Any]]]
    meta: MetaSingle
```

---

## Rate Limiting

`slowapi` at 60 req/min per IP. Wired in three places:

**`api/dependencies.py`** — replace stubs:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
```

**`api/main.py`** — register limiter and 429 handler (additive to existing setup):
```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from api.dependencies import limiter

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Each endpoint** — `Request` parameter required by slowapi for IP extraction:
```python
@router.get("/stocks")
@limiter.limit("60/minute")
def list_stocks(request: Request, index: str | None = None) -> StringListResponse:
    ...
```

**Redis hook:** `Limiter(storage_uri="redis://...")` — one-line change in `dependencies.py` when Redis lands. No router changes needed.

---

## Testing (TDD)

One test file per router in `tests/unit/api/`. Tests use FastAPI `TestClient` with `psxdata` library calls mocked — no real PSX network calls in unit tests.

**Coverage target per router:**
- `200` happy path (nominal data)
- `200` empty list (valid empty result)
- `404` for applicable endpoints
- `503` when `PSXUnavailableError` raised
- `429` rate limit (mock limiter)
- CORS header present

**Test fixture pattern** (matches existing `test_health.py`):
```python
@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)
```

---

## Error Response Envelope

Already implemented in `api/main.py`. All errors return:
```json
{"error": {"status": 404, "code": "not_found", "message": "..."}}
```

No changes needed. The existing 5 handlers cover all cases:
- `PSXUnavailableError` → 503 `psx_unavailable`
- `InvalidSymbolError` → 404 `not_found`
- `StarletteHTTPException` → mapped via `_ERROR_CODES`
- `RequestValidationError` → 422 `bad_request`
- `Exception` → 500 `internal_error`

---

## Implementation Order

Recommended sequence for TDD:

1. `api/dependencies.py` — wire `slowapi` Limiter (enables rate limit tests)
2. `api/main.py` — register limiter + middleware
3. `psxdata/client.py` — add `symbols()` method + module-level convenience function
4. `api/schemas.py` — add all new models
5. For each router (tests first, then implementation):
   - `stocks.py` + `test_stocks.py`
   - `indices.py` + `test_indices.py`
   - `sectors.py` + `test_sectors.py`
   - `market.py` + `test_market.py`
6. `api/routers/__init__.py` — register each router as it's completed
