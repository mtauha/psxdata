# Contributing to psxdata

Thank you for your interest in contributing. This guide covers everything you need to get started.

---

## Getting Started

```bash
git clone https://github.com/mtauha/psxdata.git
cd psxdata

python -m venv .venv
source .venv/bin/activate       # Linux/Mac
.venv\Scripts\activate          # Windows

pip install -e ".[dev]"
```

Verify your setup:

```bash
pytest tests/unit/ -v           # Should pass (no network required)
ruff check psxdata/ api/        # Should return no errors
```

---

## Local Development

The FastAPI app expects package-style imports. When working on the REST API layer, ensure the package is installed in editable mode:

```bash
pip install -e .
```

**Do not add `sys.path` import fallbacks in `api/main.py`.** The editable install handles module discovery correctly.

---

## Issue First Policy

Before starting any non-trivial change, open a GitHub issue. This prevents duplicate work and lets maintainers give early feedback on direction. Issues are free — PRs without a linked issue may be closed without review.

Exceptions: typo fixes, documentation corrections, and test-only changes that fix an already-filed bug.

---

## Branch Naming

```
feat/short-description      # new feature
fix/short-description       # bug fix
docs/short-description      # documentation only
chore/short-description     # maintenance, refactor, infra
```

Always branch from `main`:

```bash
git checkout main
git pull
git checkout -b feat/your-feature
```

Never commit directly to `main`.

---

## PR Process

1. Fork the repository (external contributors) or branch directly (maintainers)
2. Make your changes on a feature branch
3. Run the test suite locally — see [TESTING.md](TESTING.md)
4. Open a PR targeting `main`
5. Fill in the PR template completely
6. Link the related issue with `Closes #N` in the PR body

PRs require at least one approving review and passing CI (`lint` + `test` jobs) before merge.

---

## Commit Messages

Conventional commits are encouraged but not enforced:

```
feat: add historical data caching
fix: handle empty table response from /screener
docs: update endpoint map in ARCHITECTURE.md
chore: bump ruff to 0.5
```

Keep the subject line under 72 characters. Use the body to explain *why*, not *what*.

---

## Testing

Unit tests are required for any new utility, parser, or validator function. Integration tests are required for any new scraper. See [TESTING.md](TESTING.md) for the full guide.

```bash
pytest tests/unit/ -v                   # unit tests — run before every commit
pytest -m integration -v               # integration — run before scraper PRs
pytest tests/unit/ --cov=psxdata --cov-report=term-missing
```

---

## Code Standards

- Type hints on all public functions
- Docstrings on all public functions (one-line minimum)
- `ruff check` must pass with zero errors
- `mypy` must pass with zero errors on the modules you changed
- No hardcoded date formats — always use `parse_date_safely()` from `parsers/normalizers.py`
- No fixed column positions — always map by `<th>` name, never by index

---

## Adding a New Scraper

1. Inherit from `BaseScraper` in `psxdata/scrapers/base.py`
2. Add a comment at the top declaring the scraping mode and why
3. Use `parse_date_safely()` — never hardcode date formats
4. Extract columns dynamically from `<th>` tags — never assume fixed positions
5. Validate returned data using the validators in `utils.py`
6. Write unit tests for any new helper functions first
7. Write an integration test hitting the real PSX endpoint
8. If using Playwright: capture an HTML fixture with `python tools/capture_fixtures.py`

---

## Raising a PSX Endpoint Change

If PSX changes a page structure and a scraper breaks, open an issue using the **Endpoint Change** template. Include the endpoint URL, what changed, and which scraper is affected. Add an inline comment to the broken code referencing the issue number: `# TODO(#N): brief description`.
