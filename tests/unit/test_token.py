"""Unit tests for psxdata.scrapers.token - network-free."""
import logging
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
import requests

from psxdata.constants import (
    MAX_RETRIES,
    REQUEST_HEADERS,
    RETRY_DELAYS,
    TOKEN_RETRY_BACKOFF,
    TOKEN_TTL,
)
from psxdata.scrapers import token as token_module
from psxdata.scrapers.token import TokenProvider, extract_token, get_default_provider

FIXTURES = Path(__file__).parent.parent / "fixtures"
FIXTURE_TOKEN = "JPlHf0jIKj_s7l-A_KlM4gGDz651a_5sknoT4WozNjM"


class TestExtractToken:
    def test_extracts_token_from_fixture(self):
        html = (FIXTURES / "home_with_token.html").read_text(encoding="utf-8")
        assert extract_token(html) == FIXTURE_TOKEN

    def test_extract_token_tolerates_whitespace_and_newlines(self):
        html = (
            "<script>\n  window.__ps  =  {\n  \"lc\": \"en\",\n"
            f"  \"_k\": \"{FIXTURE_TOKEN}\"\n}} ;\n</script>"
        )
        assert extract_token(html) == FIXTURE_TOKEN

    def test_extract_token_without_semicolon(self):
        html = f'<script>window.__ps = {{"_k":"{FIXTURE_TOKEN}"}}</script>'
        assert extract_token(html) == FIXTURE_TOKEN

    def test_returns_none_when_script_missing(self):
        assert extract_token("<html><head></head><body></body></html>") is None

    def test_returns_none_when_k_missing(self):
        assert extract_token('<script>window.__ps = {"lc":"en"};</script>') is None

    def test_returns_none_on_malformed_json(self):
        assert extract_token("<script>window.__ps = {_k: broken};</script>") is None

    @pytest.mark.parametrize("bad", ["short", "has spaces in it here!!", "", "x" * 15])
    def test_returns_none_when_token_fails_format_check(self, bad):
        assert extract_token(f'<script>window.__ps = {{"_k":"{bad}"}};</script>') is None

    def test_returns_none_when_k_not_a_string(self):
        html = '<script>window.__ps = {"_k": 12345678901234567890};</script>'
        assert extract_token(html) is None

    def test_returns_none_when_token_has_trailing_newline(self):
        html = f'<script>window.__ps = {{"_k":"{FIXTURE_TOKEN}\\n"}};</script>'
        assert extract_token(html) is None


PAGE = f'<script>window.__ps = {{"_k":"{FIXTURE_TOKEN}"}};</script>'
OTHER_TOKEN = "k0JLxybjAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAjG0"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _page_response(status: int = 200, text: str = PAGE) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.text = text
    return resp


def _provider(*responses, clock=None, sleep_func=None):
    session = MagicMock(spec=requests.Session)
    session.get.side_effect = list(responses)
    sleep = sleep_func or MagicMock()
    return (
        TokenProvider(session=session, time_func=clock or FakeClock(), sleep_func=sleep),
        session,
        sleep,
    )


class TestTokenProvider:
    def test_fetches_once_then_serves_from_cache(self):
        provider, session, _ = _provider(_page_response())
        assert provider.get_token() == FIXTURE_TOKEN
        assert provider.get_token() == FIXTURE_TOKEN
        assert session.get.call_count == 1

    def test_fetch_uses_token_page_url_and_timeout(self):
        provider, session, _ = _provider(_page_response())
        provider.get_token()
        args, kwargs = session.get.call_args
        assert args[0] == "https://dps.psx.com.pk/"
        assert kwargs["timeout"] == 30

    def test_refetches_after_ttl(self):
        clock = FakeClock()
        provider, session, _ = _provider(
            _page_response(),
            _page_response(text=PAGE.replace(FIXTURE_TOKEN, OTHER_TOKEN)),
            clock=clock,
        )
        assert provider.get_token() == FIXTURE_TOKEN
        clock.now += TOKEN_TTL + 1
        assert provider.get_token() == OTHER_TOKEN
        assert session.get.call_count == 2

    def test_token_refetched_exactly_at_ttl(self):
        clock = FakeClock()
        provider, session, _ = _provider(_page_response(), _page_response(), clock=clock)
        provider.get_token()
        clock.now += TOKEN_TTL
        provider.get_token()
        assert session.get.call_count == 2

    def test_token_cached_just_before_ttl(self):
        clock = FakeClock()
        provider, session, _ = _provider(_page_response(), clock=clock)
        provider.get_token()
        clock.now += TOKEN_TTL - 0.001
        provider.get_token()
        assert session.get.call_count == 1

    @pytest.mark.parametrize("status", [403, 503])
    def test_non_200_page_returns_none_and_warns(self, status, caplog):
        if status == 503:
            responses = [_page_response(status=503, text="") for _ in range(MAX_RETRIES)]
        else:
            responses = [_page_response(status=403, text="")]
        provider, session, _ = _provider(*responses)
        with caplog.at_level(logging.WARNING, logger="psxdata.scrapers.token"):
            assert provider.get_token() is None
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1
        assert session.get.call_count == (1 if status == 403 else MAX_RETRIES)

    def test_network_error_returns_none_and_warns(self, caplog):
        provider, session, _ = _provider(*[requests.ConnectionError("down")] * MAX_RETRIES)
        with caplog.at_level(logging.WARNING, logger="psxdata.scrapers.token"):
            assert provider.get_token() is None
        assert any("X-Req-Id" in r.getMessage() for r in caplog.records)
        assert session.get.call_count == MAX_RETRIES

    def test_page_without_token_returns_none(self):
        provider, _, _ = _provider(_page_response(text="<html></html>"))
        assert provider.get_token() is None

    def test_no_refetch_during_backoff_then_refetch_after(self):
        clock = FakeClock()
        provider, session, _ = _provider(
            _page_response(status=403, text=""), _page_response(), clock=clock
        )
        assert provider.get_token() is None
        clock.now += TOKEN_RETRY_BACKOFF - 1
        assert provider.get_token() is None
        assert session.get.call_count == 1
        clock.now += 2
        assert provider.get_token() == FIXTURE_TOKEN
        assert session.get.call_count == 2

    def test_invalidate_matching_token_forces_refetch(self):
        provider, session, _ = _provider(_page_response(), _page_response())
        tok = provider.get_token()
        provider.invalidate(tok)
        provider.get_token()
        assert session.get.call_count == 2

    def test_invalidate_stale_token_is_noop(self):
        provider, session, _ = _provider(_page_response())
        provider.get_token()
        provider.invalidate(OTHER_TOKEN)
        provider.invalidate(None)
        provider.get_token()
        assert session.get.call_count == 1

    def test_concurrent_callers_trigger_single_fetch(self):
        session = MagicMock(spec=requests.Session)

        def slow_get(*args, **kwargs):
            time.sleep(0.05)
            return _page_response()

        session.get.side_effect = slow_get
        provider = TokenProvider(session=session, sleep_func=lambda s: None)
        results: list[str | None] = []
        threads = [
            threading.Thread(target=lambda: results.append(provider.get_token()))
            for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert session.get.call_count == 1
        assert results == [FIXTURE_TOKEN] * 10

    def test_default_session_headers(self):
        provider = TokenProvider(sleep_func=lambda s: None)
        headers = provider._session.headers
        assert "X-Requested-With" not in headers
        assert headers["User-Agent"] == REQUEST_HEADERS["User-Agent"]

    def test_logs_never_contain_full_token(self, caplog):
        provider, _, _ = _provider(_page_response())
        with caplog.at_level(logging.DEBUG, logger="psxdata.scrapers.token"):
            provider.get_token()
        assert FIXTURE_TOKEN not in caplog.text

    def test_transient_5xx_then_success_returns_token(self):
        provider, session, sleep = _provider(
            _page_response(status=503, text=""), _page_response()
        )
        assert provider.get_token() == FIXTURE_TOKEN
        assert session.get.call_count == 2
        sleep.assert_called_once_with(RETRY_DELAYS[0])

    def test_transient_network_error_then_success_returns_token(self):
        provider, session, _ = _provider(requests.ConnectionError("down"), _page_response())
        assert provider.get_token() == FIXTURE_TOKEN
        assert session.get.call_count == 2

    def test_non_retryable_status_is_not_retried(self):
        provider, session, _ = _provider(_page_response(status=404, text=""))
        assert provider.get_token() is None
        assert session.get.call_count == 1

    def test_unexpected_exception_during_parse_fails_open(self, caplog):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        type(resp).text = PropertyMock(side_effect=RuntimeError("boom"))
        provider, session, _ = _provider(resp)
        with caplog.at_level(logging.WARNING, logger="psxdata.scrapers.token"):
            assert provider.get_token() is None
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1
        assert session.get.call_count == 1


class TestDefaultProvider:
    def test_returns_same_instance(self, monkeypatch):
        monkeypatch.setattr(token_module, "_default_provider", None)
        first = get_default_provider()
        assert first is get_default_provider()
        assert type(first) is TokenProvider
