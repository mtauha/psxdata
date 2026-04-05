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

### Changed

- Corrected `ARCHITECTURE.md` scraper→endpoint map: `/screener` and `/trading-panel` use `requests`+BeautifulSoup; `/sector-summary` and `/financial-reports` use Playwright.

---

[Unreleased]: https://github.com/mtauha/psxdata/commits/main
