# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

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

### Changed

- Corrected `ARCHITECTURE.md` scraper→endpoint map: `/screener` and `/trading-panel` use `requests`+BeautifulSoup; `/sector-summary` and `/financial-reports` use Playwright.

---

[Unreleased]: https://github.com/mtauha/psxdata/commits/main
