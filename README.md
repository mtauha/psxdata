# psxdata

[![CI](https://github.com/mtauha/psxdata/actions/workflows/ci.yml/badge.svg)](https://github.com/mtauha/psxdata/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/psxdata)](https://pypi.org/project/psxdata/)
[![Python](https://img.shields.io/pypi/pyversions/psxdata)](https://pypi.org/project/psxdata/)

**Python library and REST API for Pakistan Stock Exchange (PSX) data.**

Fetch historical OHLCV data, real-time quotes, sector aggregates, and financial reports from PSX — with automatic caching, retry logic, and a clean pandas DataFrame interface.

---

## Why psxdata

The existing [`psx-data-reader`](https://github.com/FarhanZizvi/psx-data-reader) library hardcodes date formats and column positions that break silently when PSX changes its HTML. `psxdata` was built from scratch to be resilient: dynamic column extraction from `<th>` tags, multi-format date parsing with fuzzy fallback, exponential backoff retries, and a disk cache that keeps historical data forever.

---

## Installation

```bash
pip install psxdata           # Python library only
pip install psxdata[api]      # Library + FastAPI REST server
```

Playwright (for JS-rendered PSX endpoints) is installed automatically. You also need the Chromium browser:

```bash
playwright install chromium
```

---

## Quick Start

```python
import psxdata

# Historical OHLCV data for ENGRO
df = psxdata.stocks("ENGRO", start="2024-01-01", end="2024-12-31")
print(df.head())

# All listed tickers
tickers = psxdata.tickers()

# KSE-100 constituents only
kse100 = psxdata.tickers(index="KSE-100")

# Current index values
indices = psxdata.indices()
```

---

## API Reference

> Full reference coming in Phase 7. Signatures are stable from Phase 3 onward.

| Function | Description |
|---|---|
| `psxdata.stocks(symbol, start, end)` | Historical OHLCV DataFrame for one or more tickers |
| `psxdata.tickers(index=None)` | All listed tickers, optionally filtered by index |
| `psxdata.indices()` | Current index values (KSE-100, KSE-30, KMI-30) |
| `psxdata.sectors()` | Sector aggregates DataFrame |
| `psxdata.fundamentals(symbol)` | P/E ratio, EPS, book value for a ticker |
| `psxdata.market.debt()` | Debt market instruments (TFCs, Sukuks) |
| `psxdata.market.eligible_scrips()` | Margin trading eligible stocks |

---

## REST API

Run the server:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

| Endpoint | Description |
|---|---|
| `GET /health` | Health check |
| `GET /stocks` | All tickers |
| `GET /stocks/{symbol}/historical?start=&end=` | Historical OHLCV |
| `GET /stocks/{symbol}/quote` | Real-time quote |
| `GET /stocks/{symbol}/fundamentals` | Fundamentals |
| `GET /indices` | Index values |
| `GET /sectors` | Sector aggregates |
| `GET /debt-market` | Debt instruments |
| `GET /eligible-scrips` | Margin eligible stocks |

All responses: `{"data": ..., "meta": {"timestamp": "...", "cached": true}}`

Swagger UI: `http://localhost:8000/docs` · ReDoc: `http://localhost:8000/redoc`

Rate limit: 60 requests/min per IP.

---

## Known Limitations

- PSX can change HTML structure at any time. If a scraper breaks, open an [Endpoint Change issue](.github/ISSUE_TEMPLATE/endpoint_change.yml).
- `/sector-summary` and `/financial-reports` require Playwright (headless Chromium). This adds ~2s cold-start on first use.
- `/financial-reports` returned an empty table during Phase 0 testing. The parser handles it gracefully but no financial report data may be available.
- No real-time guaranteed — PSX does not publish a streaming feed. Quotes are scraped on demand and cached for 15 minutes.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Open an issue before starting non-trivial work.

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full component diagram, data flow, and design decisions.
