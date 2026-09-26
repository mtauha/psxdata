"""Shared pytest fixtures.

The autouse fixture below keeps unit and reliability tests offline: it replaces
the process-wide PSX request-token provider with a stub. Integration tests
(``-m integration``) are exempt so they exercise the real token flow.
"""
import pytest

from psxdata.scrapers import token as token_module
from psxdata.scrapers.token import TokenProvider

STUB_TOKEN = "test-token-0123456789abcdef"


class StubTokenProvider(TokenProvider):
    """Offline provider: always returns STUB_TOKEN, never touches the network."""

    def get_token(self) -> str | None:
        return STUB_TOKEN

    def invalidate(self, token: str | None) -> None:
        return None


@pytest.fixture(autouse=True)
def _stub_default_token_provider(request, monkeypatch):
    if request.node.get_closest_marker("integration") is not None:
        yield
        return
    monkeypatch.setattr(token_module, "_default_provider", StubTokenProvider())
    yield
