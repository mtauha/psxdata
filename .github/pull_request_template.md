## Summary

<!-- What does this PR do and why? 1-3 sentences. -->
FastAPI Skeleton, base for the Phase 4

## Related Issue
#65 [Phase 4] Setup FastAPI app skeleton (main.py, lifespan, middleware, error handlers)

Closes #65

## Type of Change

- [ ] Bug fix
- [X] New feature
- [ ] Refactor (no behavior change)
- [ ] Documentation
- [X] Infrastructure / CI

Acceptance Criteria

- [X] uvicorn api.main:app starts without errors
- [X] GET /docs returns 200
- [X] ruff check api/ passes

## Testing Done

- [X] `pytest tests/unit/ -v` passes
- [X] `pytest -m reliability -v` passes
- [X] `pytest -m integration -v` passes locally (required for scraper changes)
- [X] Manually tested against live PSX endpoint (required for scraper changes)

## Checklist

- [X] Type hints on all new public functions
- [X] Docstrings on all new public functions
- [ ] No hardcoded date formats (use `parse_date_safely()`)
- [ ] No fixed column position assumptions (map by `<th>` name)
- [X] `ruff check psxdata/ api/` passes
- [X] `mypy psxdata/ api/` passes
- [X] `CHANGELOG.md` updated (if breaking change or new user-facing feature)
- [ ] New HTML fixture captured if a new PSX endpoint interaction was added
