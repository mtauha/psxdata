# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0a3] - 2026-04-20

### Added

- Phase 7: MkDocs + Material documentation site at https://psxdata.readthedocs.io — 12 pages covering getting started, 6 tutorial guides, full API reference, changelog, and contributing.
- Phase 7: `.readthedocs.yaml` v2 build config for Read the Docs free-tier hosting.
- Phase 7: `examples/quickstart.py` — runnable demo script covering all 5 core functions.
- Phase 7: Expanded all 8 module-level function docstrings (Args, Returns, Raises, Example) for clean API reference rendering via mkdocstrings.

### Changed

- `pyproject.toml`: added `docs` optional dependency group (`mkdocs-material`, `mkdocstrings[python]`), `Documentation` URL, and updated package description.

---

## [Unreleased]

### Added

- Phase 4 API: Added GET `/health` through router registry wiring with explicit API docs metadata (`tags=["health"]`, `response_model=dict`) and unit API contract coverage.
- Phase 0: Probed all 8 PSX endpoints. Confirmed rendering modes — `/sector-summary` and `/financial-reports` require Playwright; all other endpoints work with plain `requests`.
- Phase 0: Captured HTML fixtures for all 5 key endpoints (`historical_engro`, `trading_panel`, `screener`, `sector_summary`, `financial_reports`).
- Phase 0: Added `tools/probe_endpoints.py` — reusable diagnostic that probes all PSX endpoints and writes `docs/PSX_ENDPOINTS.md`.
- Phase 0: Added `tools/capture_fixtures.py` — reusable fixture capture that saves stamped HTML snapshots to `tests/fixtures/`.
- Phase 0.5: Repository infrastructure — issue templates, PR template, CI/CD workflows, community files, GitHub labels, milestones, and development roadmap issues.
- Phase 2: Added `psxdata/exceptions.py` — 10-class exception hierarchy rooted at `PSXDataError`.
- Phase 2: Added `psxdata/constants.py` — all PSX endpoint URLs, request headers, retry/rate-limit config, cache settings, and full `COLUMN_MAP` from Phase 0 fixtures.
- Phase 2: Added `psxdata/utils.py` — `chunk_date_range` (configurable date splitter), `RateLimiter` (thread-safe, injectable clock), `validate_ohlc_dataframe` (flags/drops bad rows, adds `is_anomaly` column).
- Phase 2: Added `psxdata/parsers/normalizers.py` — `parse_date_safely` (never-raises, multi-format + fuzzy fallback), `coerce_numeric`, `normalize_column_name`.
- Phase 2: Added `psxdata/parsers/html.py` — dynamic HTML table parser using `COLUMN_MAP`; unknown headers fall back to `normalize_column_name` with a logged warning.
- Phase 2: Added `psxdata/cache/disk_cache.py` — `DiskCache` backed by `diskcache` + parquet; historical data never expires, today's data expires after 15 minutes.
- Phase 2: Added `psxdata/models/schemas.py` — 7 thin Pydantic v2 models: `OHLCVRow`, `Quote`, `IndexRecord`, `SectorSummary`, `TickerInfo`, `DebtInstrument`, `EligibleScrip`.
- Phase 2: Added `psxdata/scrapers/base.py` — `BaseScraper` with persistent session, exponential backoff retry, rate limiter, and Playwright context manager.
- Phase 3: Added scrapers for all 8 PSX endpoints — `historical.py` (POST, all-time OHLCV), `realtime.py` (15 trading-board combos), `indices.py` (18 indices), `sectors.py` (37 sectors), `fundamentals.py` (financial reports), `screener.py` (1000+ tickers with fundamentals), `debt_market.py` (4 instrument tables), `eligible_scrips.py` (9 category tables).
- Phase 3: Deprecated Playwright for scraping — all endpoints confirmed accessible via plain `requests`+BeautifulSoup. `_playwright_page()` retained in `BaseScraper` for tooling only.
- Phase 3 API: Added public package interface — `stocks()`, `tickers()`, `quote()`, `indices()`, `sectors()`, `fundamentals()`, `debt_market()`, `eligible_scrips()` exported from `psxdata/__init__.py`.
- Phase 5: Added full unit test suite — 80+ tests covering parsers, validators, cache, utils, and scraper reliability (mocked failure modes).
- Phase 5: Added integration test suite — real PSX endpoint tests for all 8 scrapers, marked `@pytest.mark.integration`.
- Phase 5: Added `tests/fixtures/` — static HTML/JSON snapshots for deterministic unit tests.
- Phase 6: Published to PyPI as `psxdata==0.1.0a1`.
- Phase 6: Added 5-job gated publish pipeline (`.github/workflows/publish.yml`) — tag verification → unit tests → build+twine check → TestPyPI → PyPI (manual approval gate).
- Phase 6: Removed `playwright` from core dependencies — optional tooling only.

### Changed

- Corrected `ARCHITECTURE.md` scraper→endpoint map: `/screener` and `/trading-panel` use `requests`+BeautifulSoup; `/sector-summary` and `/financial-reports` use Playwright.
- `CHANGELOG.md`: Added entries for Phases 3 through 6.

---

## [0.1.0a1] — 2026-04-19

First PyPI release. Core scraping library complete for all 8 PSX endpoints with caching, validation, and a clean public Python API.

---

[Unreleased]: https://github.com/mtauha/psxdata/compare/v0.1.0a3...HEAD
[0.1.0a3]: https://github.com/mtauha/psxdata/compare/v0.1.0a2...v0.1.0a3
[0.1.0a2]: https://github.com/mtauha/psxdata/compare/v0.1.0a1...v0.1.0a2
[0.1.0a1]: https://github.com/mtauha/psxdata/releases/tag/v0.1.0a1
