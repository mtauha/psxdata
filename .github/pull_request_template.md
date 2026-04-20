## Summary

<!-- What does this PR do and why? 1-3 sentences. -->

## Related Issue

Closes #65

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor (no behavior change)
- [ ] Documentation
- [ ] Infrastructure / CI

## Testing Done

- [ ] `pytest tests/unit/ -v` passes
- [ ] `pytest -m reliability -v` passes
- [ ] `pytest -m integration -v` passes locally (required for scraper changes)
- [ ] Manually tested against live PSX endpoint (required for scraper changes)

## Checklist

- [ ] Type hints on all new public functions
- [ ] Docstrings on all new public functions
- [ ] No hardcoded date formats (use `parse_date_safely()`)
- [ ] No fixed column position assumptions (map by `<th>` name)
- [ ] `ruff check psxdata/ api/` passes
- [ ] `mypy psxdata/ api/` passes
- [ ] `CHANGELOG.md` updated (if breaking change or new user-facing feature)
- [ ] New HTML fixture captured if a new PSX endpoint interaction was added
