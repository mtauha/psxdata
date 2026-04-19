# psxdata

[![CI](https://github.com/mtauha/psxdata/actions/workflows/ci.yml/badge.svg)](https://github.com/mtauha/psxdata/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/psxdata)](https://pypi.org/project/psxdata/)
[![Python](https://img.shields.io/pypi/pyversions/psxdata)](https://pypi.org/project/psxdata/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Python library for Pakistan Stock Exchange (PSX) data** — resilient to PSX's frequent HTML changes, with a disk cache, exponential backoff retries, and a clean public API.

> **Alpha release (`0.1.0a1`):** Core scraping, caching, and public API are complete. The FastAPI REST layer and full documentation are in progress.

---

## Installation

```bash
pip install psxdata
```

Requires Python 3.11+.

---

## Quick Start

```python
import psxdata

# Historical OHLCV data
df = psxdata.stocks("ENGRO", start="2024-01-01", end="2024-12-31")

# All listed tickers
all_tickers = psxdata.tickers()

# KSE-100 index constituents
kse100 = psxdata.indices("KSE100")

# Live quote
q = psxdata.quote("LUCK")

# Sector summary
sectors = psxdata.sectors()

# Debt market instruments
debt = psxdata.debt_market()

# Margin-eligible stocks
scrips = psxdata.eligible_scrips()
```

---

## API Reference

| Function | Description |
|---|---|
| `psxdata.stocks(symbol, start, end)` | Historical OHLCV DataFrame for a ticker |
| `psxdata.tickers()` | All listed tickers (1000+) |
| `psxdata.quote(symbol)` | Live quote row for a ticker |
| `psxdata.indices(name)` | Constituents of a named index (e.g. `"KSE100"`) |
| `psxdata.sectors()` | Sector aggregates DataFrame (37 sectors) |
| `psxdata.fundamentals(symbol)` | Financial reports for a ticker |
| `psxdata.debt_market()` | Debt market instruments (TFCs, Sukuks, etc.) |
| `psxdata.eligible_scrips()` | Margin trading eligible stocks |

---

## Why psxdata

The existing [`psx-data-reader`](https://github.com/FarhanZizvi/psx-data-reader) library hardcodes date formats and column positions that break silently when PSX changes its HTML. `psxdata` is designed differently:

- **Dynamic column extraction** from `<th>` tags — survives column reordering
- **Multi-format date parsing** with fuzzy fallback via `dateutil`
- **Exponential backoff retries** — 3 attempts, 1s/2s delays
- **Disk cache** (`~/.psxdata/cache/`) — historical data cached forever, live data for 15 min
- **Data validation** — OHLC constraint checks, duplicate/future date detection

---

## Planned REST API

> The FastAPI layer is planned for Phase 4.

| Endpoint | Description |
|---|---|
| `GET /health` | Health check |
| `GET /stocks` | All tickers |
| `GET /stocks/{symbol}/historical?start=&end=` | Historical OHLCV |
| `GET /stocks/{symbol}/quote` | Real-time quote |
| `GET /stocks/{symbol}/fundamentals` | Fundamentals |
| `GET /indices/{name}` | Index constituents |
| `GET /sectors` | Sector aggregates |
| `GET /debt-market` | Debt instruments |
| `GET /eligible-scrips` | Margin eligible stocks |

All responses: `{"data": ..., "meta": {"timestamp": "...", "cached": bool}}`

---

## Development Status

See the [roadmap issue](https://github.com/mtauha/psxdata/issues/4) for the full phase breakdown.

- ✅ Phase 0 — PSX endpoint research and HTML fixture capture
- ✅ Phase 0.5 — Repository setup, CI/CD, community files
- ✅ Phase 2 — Core engineering (BaseScraper, parsers, cache, utils)
- ✅ Phase 3 — Scrapers (historical, real-time, indices, sectors, fundamentals, screener, debt, eligible scrips)
- ✅ Phase 3 API — Public Python package interface
- 🔲 Phase 4 — FastAPI REST layer
- ✅ Phase 5 — Full test suite
- ✅ Phase 6 — Packaging & PyPI publish
- 🔲 Phase 7 — Documentation

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and open an issue before starting non-trivial work.

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the component diagram, data flow, and design decisions.
