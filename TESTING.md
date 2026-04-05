# Testing — psxdata

This document explains how the test suite is organized, how to run tests, and what is expected from contributors when adding or changing code.

---

## Test Pyramid

```
      /   API contract   \     ~5 tests  — full HTTP round-trips via TestClient
     /     Integration    \    ~30 tests — real PSX endpoints, network required
    /       Unit Tests     \   ~80+ tests — parsers, validators, cache, utils
```

Unit tests are the foundation. Integration tests verify we talk to PSX correctly. API contract tests verify the FastAPI layer behaves correctly over HTTP.

---

## Running Tests

### Setup

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/Mac
.venv\Scripts\activate          # Windows

pip install -e ".[dev]"
```

### Commands

```bash
# Unit tests only — fast, no network (use this while developing)
pytest tests/unit/ -v

# Everything except integration (default for CI)
pytest tests/ -v -m "not integration"

# Integration tests — hits real PSX servers (run before submitting a PR)
pytest -m integration -v

# Reliability tests — failure-mode tests using mocks
pytest -m reliability -v

# With coverage report
pytest tests/unit/ --cov=psxdata --cov=api --cov-report=term-missing

# Run a specific test by name
pytest tests/ -v -k "test_parse_date"
```

---

## Test Markers

| Marker | Meaning | Network? | Runs in CI? |
|---|---|---|---|
| *(none)* | Unit test | No | Yes |
| `@pytest.mark.integration` | Hits real PSX servers | Yes | No (nightly only) |
| `@pytest.mark.reliability` | Failure-mode tests with mocks | No | Yes |

Integration tests are excluded from CI by default because they hit real PSX servers and can be slow or flaky. They run nightly via GitHub Actions and should be run locally before submitting any scraper-related PR.

---

## Test Structure

```
tests/
├── unit/
│   ├── test_normalizers.py     # parse_date_safely(), type coercion
│   ├── test_html_parser.py     # dynamic column mapper
│   ├── test_validators.py      # OHLC, volume, date validators
│   ├── test_date_chunker.py    # date range splitting utility
│   ├── test_cache.py           # disk cache read/write/TTL/parquet round-trip
│   └── api/
│       └── test_routes.py      # FastAPI routes via TestClient (library mocked)
├── integration/
│   ├── test_historical.py      # real fetch from /historical
│   ├── test_realtime.py        # real fetch from /trading-panel
│   ├── test_indices.py         # real fetch from /indices
│   ├── test_sectors.py         # real fetch from /sector-summary
│   ├── test_fundamentals.py    # real fetch from /financial-reports
│   ├── test_screener.py        # real fetch from /screener
│   ├── test_debt_market.py     # real fetch from /debt-market
│   └── test_eligible_scrips.py # real fetch from /eligible-scrips
├── fixtures/
│   ├── historical_engro.html   # Recorded HTML snapshots from Phase 0
│   ├── trading_panel.html      # /trading-panel response
│   ├── screener.html           # /screener response
│   ├── sector_summary.html     # /sector-summary JS-rendered (Playwright fixture)
│   └── financial_reports.html  # /financial-reports JS-rendered (Playwright fixture)
└── conftest.py                 # Shared fixtures
```

---

## What to Test

### Unit Tests — `tests/unit/`

Fast, no network, no disk I/O. These must pass before every commit.

#### Date Parser (`normalizers.py::parse_date_safely`)

This is the most important unit to test. PSX has historically changed date formats without notice — the original `psx-data-reader` library hardcoded `%b %d, %Y` and broke when PSX changed it. Our parser must handle every known format and never raise an exception on bad input.

| Input | Expected output |
|---|---|
| `"Jan 05, 2024"` | `datetime(2024, 1, 5)` |
| `"05-Jan-2024"` | `datetime(2024, 1, 5)` |
| `"2024-01-05"` | `datetime(2024, 1, 5)` |
| `"05/01/2024"` | `datetime(2024, 1, 5)` |
| `"January 5 2024"` | `datetime(2024, 1, 5)` (fuzzy fallback) |
| `""` | `None` |
| `None` | `None` |
| `20240105` (integer) | `None` |
| `"   "` (whitespace) | `None` |
| `"not a date"` | `None` |
| *any input* | never raises — always returns `datetime \| None` |

#### Column Mapper (`html.py`)

PSX sometimes returns different column counts per company. We always map by header name, never by position.

| Scenario | Expected |
|---|---|
| All expected columns present | Correct mapping, no warnings |
| Missing column | Warning logged, no raise, partial mapping returned |
| Extra unexpected column | Warning logged, no raise, unknown column ignored |
| Mixed-case headers | Normalized to lowercase with underscores |
| Headers with leading/trailing spaces | Stripped correctly |
| Empty table | Empty mapping returned, no crash |

#### OHLC & Data Validators (`utils.py`)

| Scenario | Expected |
|---|---|
| Valid OHLC (`Low ≤ Open, Close ≤ High`) | Passes |
| `Low > Open` | Warning logged, row flagged |
| `Close > High` | Warning logged, row flagged |
| Negative volume | Warning logged, row flagged |
| NaN in Close or Volume | Warning logged, row flagged |
| Future date in index | Warning logged |
| Duplicate dates | Warning logged |
| Non-chronological order | Warning logged |
| Completely corrupt row | Row dropped, warning logged |
| Partially corrupt DataFrame | Clean rows returned, warnings for bad rows |

#### Date Range Chunker (`utils.py`)

| Scenario | Expected |
|---|---|
| Single year range | 1 chunk |
| 5-year range | 5 chunks |
| Sub-year range | 1 chunk |
| Single day | 1 chunk |
| `start > end` | Raises `ValueError` |

#### Cache (`cache/disk_cache.py`)

| Scenario | Expected |
|---|---|
| Cache miss | Returns `None`, no error |
| Write then read | Returns identical DataFrame |
| Historical data TTL | Never expires |
| Today's data TTL | Expires after 15 min (mock `time`) |
| Parquet round-trip | dtypes preserved (dates, floats, ints) |

---

### Integration Tests — `tests/integration/`

These hit real PSX servers. Run them locally before any scraper-related PR. Canonical tickers used: `ENGRO`, `LUCK`, `HBL` (blue chips, least likely to be delisted).

| Test | Key assertions |
|---|---|
| `test_historical_single_ticker` | DataFrame has `[Open, High, Low, Close, Volume]`; DatetimeIndex; no NaN in Close/Volume; dates within requested range |
| `test_historical_multi_ticker` | Returns dict keyed by ticker; each value passes single-ticker assertions |
| `test_historical_cache_hit` | Second identical call returns faster and `meta.cached == True` |
| `test_realtime_quote` | Returns dict with `price`, `change`, `pct_change`, `volume`; `price` is a positive float |
| `test_tickers_list` | DataFrame has ≥ 400 rows; `ENGRO` is present |
| `test_tickers_kse100_filter` | `tickers(index="KSE-100")` returns ≤ 100 rows |
| `test_indices_current` | Returns KSE-100 value as a positive float |
| `test_sectors_list` | Returns ≥ 10 sectors; `CEMENT` is present |
| `test_fundamentals_engro` | Returns `pe_ratio`, `eps`, `book_value` as floats |
| `test_debt_market` | Non-empty DataFrame; no crash |
| `test_eligible_scrips` | Non-empty DataFrame; `ENGRO` present |

---

### Reliability Tests — failure-mode tests using mocks

These test that the system degrades gracefully when things go wrong. No real network calls.

| Test | What's mocked | Assertion |
|---|---|---|
| Timeout — retry succeeds | `Session.post` raises `Timeout` on attempt 1, succeeds on 2 | Retry fires; correct result returned |
| Timeout — all retries fail | All 3 attempts raise `Timeout` | `PSXUnavailableError` raised; cache not written |
| Unexpected HTML structure | `<th>` tags contain unrecognised column names | Warning logged; no crash; partial DataFrame returned |
| Partial chunk failure | 2 of 5 futures raise exceptions | Data from 3 successful chunks returned; warnings logged |
| PSX 503 on all requests | All requests return 503 | `PSXUnavailableError` raised |
| Playwright timeout | `page.goto` raises `TimeoutError` | Warning logged; empty result; no unhandled exception |
| Empty HTML response | Response body is `<html></html>` | Warning logged; empty DataFrame; no crash |
| Rate limiter | 10 requests with mocked clock | ≤ 2 requests pass per simulated second |

---

### API Contract Tests — `tests/unit/api/`

Uses FastAPI `TestClient`. The `psxdata` library layer is fully mocked — these test HTTP behavior only: routing, status codes, response schema, error handling.

| Test | Assertion |
|---|---|
| `GET /health` | 200, `{"status": "ok"}` |
| `GET /stocks/ENGRO/historical?start=...&end=...` | 200, response matches `{"data": [...], "meta": {"timestamp": ..., "cached": bool}}` |
| `GET /stocks/INVALIDTICKER/historical` | 404 with structured error body |
| Library raises exception | 503 with structured error body |
| 61st request from same IP within 60s | 429 |
| CORS preflight | `Access-Control-Allow-Origin: *` present |
| `GET /docs` | 200 (Swagger UI) |
| `GET /redoc` | 200 (ReDoc) |

---

## Coverage Targets

| Module | Target | Rationale |
|---|---|---|
| `parsers/` | 95% | Pure functions — no excuse for gaps |
| `utils.py` | 95% | Pure functions |
| `cache/` | 85% | Disk I/O paths harder to cover in unit tests |
| `scrapers/` | 70% unit + integration covers remainder | Network-dependent paths covered by integration tests |
| `api/routers/` | 80% | Via TestClient with mocked library layer |
| `models/schemas.py` | 90% | Test all Pydantic validators |

---

## Testing Playwright Scrapers

`sectors.py` and `fundamentals.py` use Playwright (headless Chromium) and cannot be driven in unit tests. The approach:

1. During Phase 0, record real HTML responses from `/sector-summary` and `/financial-reports` using a live browser session
2. Save them as fixtures in `tests/fixtures/`
3. Unit tests feed these fixtures directly to the parser — fast, deterministic, no browser required

This keeps parser tests independent of Playwright entirely.

---

## Contributor Checklist

Before submitting a PR that touches scrapers or parsers:

- [ ] `pytest tests/unit/ -v` passes with no failures
- [ ] `pytest -m reliability -v` passes
- [ ] `pytest -m integration -v` passes locally (run against real PSX)
- [ ] Coverage did not drop below the target for the module you changed
- [ ] If you added a new PSX endpoint interaction — add a fixture to `tests/fixtures/` and a corresponding integration test
