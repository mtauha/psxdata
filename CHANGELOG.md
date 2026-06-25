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

- Phase 4: Added multi-stage `Dockerfile` for the `api/` service — `builder` stage installs dependencies into a venv, `runtime` stage copies only the venv and `api/` source, resulting in a minimal image with no build tools.
- Phase 4: Added `.dockerignore` — strips all non-essential paths (`psxdata/`, `tests/`, `docs/`, `tools/`, `examples/`, build artifacts, config files) from the Docker build context.
- Phase 4: `Dockerfile` runs as non-root user `psxuser` with a pre-created `~/.psxdata/cache/` directory for psxdata's disk cache.
- Phase 4: `Dockerfile` supports a configurable `PORT` environment variable (default `8000`) via shell-form `CMD exec uvicorn ...` for correct signal handling.
- Phase 4: Added `HEALTHCHECK` (`GET /health`, 30s interval, 60s start period, 5 retries) to the `Dockerfile`.
- Phase 4: Added `.github/workflows/docker-publish.yml` — builds and pushes the `api/` Docker image to Docker Hub (`mtauha/psxdata-api`) as `latest` and the tag's version on every `v*` tag push, using `docker/login-action`, `docker/setup-buildx-action`, and `docker/build-push-action` with GitHub Actions layer caching.

- Phase 4: Added `CONTRIBUTING.md` guide for adding new API endpoints — router pattern, registry wiring, response envelope, typed `response_model`, error codes, `Depends()` injection, and `TestClient` fixture conventions.
- Phase 4: Added `test-api` CI job that installs `.[dev,api]` and runs `tests/unit/api/` in isolation from the core test environment.
- Phase 4: Added `api/schemas.py` — six Pydantic v2 models (`MetaSingle`, `MetaList`, `ErrorDetail`, `ErrorEnvelope`, `HealthData`, `HealthResponse`) forming the standardized response envelope.
- Phase 4: Added `GET /health` endpoint returning `{"data": {"status": "ok"}, "meta": {"timestamp": ..., "cached": false}}` using typed `response_model=HealthResponse`.
- Phase 4: Added 17 unit tests covering schemas, error envelope paths, and the health route.
- Phase 4: Added `GET /stocks`, `GET /stocks/{symbol}` endpoints — paginated list and per-symbol OHLCV history, backed by `PSXClient.historical()` with typed `response_model`.
- Phase 4: Added `GET /indices`, `GET /indices/{name}` endpoints — full index list and filtered records by index name.
- Phase 4: Added `GET /sectors`, `GET /sectors/{sector}` endpoints — sector summary list and per-sector filtering.
- Phase 4: Added `GET /market` endpoint — combined real-time trading panel data across all 15 board combinations.
- Phase 4: Added `PSXClient.symbols()` and top-level `psxdata.symbols()` for sector-filtered symbol lookup, used by the stocks router for symbol validation.
- Phase 4: Added 9 new Pydantic v2 response models to `api/schemas.py`: `StocksRow`, `StocksResponse`, `IndexRecord`, `IndicesResponse`, `SectorSummary`, `SectorsResponse`, `MarketRow`, `MarketResponse`, `SymbolsResponse`.

### Changed

- CI `lint` job now installs `.[dev,api]` so mypy can resolve FastAPI imports when checking `api/`.
- CI `test` job now ignores `tests/unit/api/` — API tests require FastAPI extras and run in the dedicated `test-api` job.
- `.gitignore` — fixed self-ignoring pattern; contributors now receive the file on clone. Personal paths moved to maintainer's global gitignore.
- `api/main.py` — replaced three ad-hoc exception handlers with five spec-compliant handlers; `PSXUnavailableError` → 503, `InvalidSymbolError` → 404, all errors return `{"error": {"status", "code", "message"}}` envelope.
- `api/routers/__init__.py` — registered `health_router`; switched from relative to absolute imports.
- `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md` — updated API response envelope documentation to include `count` on list responses and the error envelope shape.
- `api/main.py` — registered all four new routers (`stocks`, `indices`, `sectors`, `market`) via `app.include_router()`.
- `api/requirements.txt` — pinned `psxdata==0.1.0a3` (exact prerelease pin required for pip to install without `--pre`); tightened all other deps to compatible-release specifiers (`~=`).
- `README.md` — added "Running the API with Docker" section with build, run, port-override, and health-check examples.

---

## [Unreleased — pre-Phase 4]

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
