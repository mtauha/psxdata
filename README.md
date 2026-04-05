# psxdata

[![CI](https://github.com/mtauha/psxdata/actions/workflows/ci.yml/badge.svg)](https://github.com/mtauha/psxdata/actions/workflows/ci.yml)
![PyPI](https://img.shields.io/badge/pypi-not%20yet%20published-lightgrey)
![Status](https://img.shields.io/badge/status-in%20development-orange)

> **⚠ This package is under active development and is not yet usable.**
> No PyPI release exists. The library, scrapers, and REST API are being built in phases — see the [development roadmap](https://github.com/mtauha/psxdata/issues/4) for current status.

**Python library and REST API for Pakistan Stock Exchange (PSX) data** — being built from scratch to be resilient to PSX's frequent HTML changes.

---

## Why psxdata

The existing [`psx-data-reader`](https://github.com/FarhanZizvi/psx-data-reader) library hardcodes date formats and column positions that break silently when PSX changes its HTML. `psxdata` is designed differently: dynamic column extraction from `<th>` tags, multi-format date parsing with fuzzy fallback, exponential backoff retries, and a disk cache that keeps historical data forever.

---

## Planned API

> These signatures are the target interface. They do not work yet — implementation starts in Phase 2.

```python
import psxdata

# Historical OHLCV data for ENGRO
df = psxdata.stocks("ENGRO", start="2024-01-01", end="2024-12-31")

# All listed tickers
tickers = psxdata.tickers()

# KSE-100 constituents only
kse100 = psxdata.tickers(index="KSE-100")

# Current index values
indices = psxdata.indices()
```

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

## Planned REST API

> The FastAPI layer is planned for Phase 4 and does not exist yet.

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

All responses will follow: `{"data": ..., "meta": {"timestamp": "...", "cached": bool}}`

---

## Development Status

See the [roadmap issue](https://github.com/mtauha/psxdata/issues/4) for the full phase breakdown. Current state:

- ✅ Phase 0 — PSX endpoint research and HTML fixture capture
- ✅ Phase 0.5 — Repository setup, CI/CD, community files
- 🔲 Phase 2 — Core engineering (BaseScraper, parsers, cache, utils)
- 🔲 Phase 3 — Scrapers
- 🔲 Phase 3 API — Public Python package interface
- 🔲 Phase 4 — FastAPI REST layer
- 🔲 Phase 5 — Full test suite
- 🔲 Phase 6 — Packaging & PyPI publish
- 🔲 Phase 7 — Documentation

---

## Contributing

Contributions are welcome once Phase 2 is underway. See [CONTRIBUTING.md](CONTRIBUTING.md) and open an issue before starting non-trivial work.

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the component diagram, data flow, and design decisions.
