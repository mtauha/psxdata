"""Reliability tests for proxy routing (#162) — mocked network, no real HTTP calls.

Covers: session.proxies wiring, per-request precedence over HTTP(S)_PROXY,
the token fetch going through the same proxy, PSXClient/configure plumbing,
and credentials never reaching logs or error messages.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

import psxdata
from psxdata import client as client_module
from psxdata.exceptions import PSXConnectionError
from psxdata.scrapers import token as token_module
from psxdata.scrapers.base import BaseScraper
from psxdata.scrapers.token import TokenProvider, get_default_provider

pytestmark = pytest.mark.reliability

PROXY = "http://alice:s3cret@proxy.example.com:8080"
PROXIES = {"http": PROXY, "https": PROXY}


def _mock_response(status_code: int, text: str = "") -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


@pytest.fixture
def real_proxy_providers(monkeypatch):
    """Undo conftest's stub so proxied scrapers get real TokenProviders."""
    monkeypatch.setattr(token_module, "_make_provider", lambda p: TokenProvider(proxies=p))


class TestScraperProxy:
    def test_no_proxy_keeps_default_behaviour(self):
        scraper = BaseScraper()
        assert scraper._session.proxies == {}
        with patch.object(scraper._session, "request", return_value=_mock_response(200)) as req:
            scraper._get("historical")
        assert "proxies" not in req.call_args.kwargs

    def test_proxy_sets_session_proxies_and_is_sent_per_request(self):
        scraper = BaseScraper(proxy=PROXY)
        assert scraper._session.proxies == PROXIES
        with patch.object(scraper._session, "request", return_value=_mock_response(200)) as req:
            scraper._get("historical")
        assert req.call_args.kwargs["proxies"] == PROXIES

    def test_per_scheme_dict(self):
        proxies = {"http": "http://p:8080", "https": "http://p:8443"}
        scraper = BaseScraper(proxy=proxies)
        assert scraper._session.proxies == proxies

    def test_invalid_proxy_raises_at_construction(self):
        with pytest.raises(ValueError):
            BaseScraper(proxy="not-a-url")

    def test_explicit_proxy_wins_over_env_vars(self, monkeypatch):
        monkeypatch.setenv("HTTPS_PROXY", "http://env-proxy:3128")
        monkeypatch.setenv("HTTP_PROXY", "http://env-proxy:3128")
        scraper = BaseScraper(proxy="http://explicit:8080")
        with patch("requests.adapters.HTTPAdapter.send", return_value=MagicMock(
            status_code=200, headers={}, is_redirect=False, history=[]
        )) as send:
            scraper._get("historical")
        assert send.call_args.kwargs["proxies"]["https"] == "http://explicit:8080"

    def test_env_vars_still_honoured_without_proxy(self, monkeypatch):
        monkeypatch.setenv("HTTPS_PROXY", "http://env-proxy:3128")
        monkeypatch.delenv("NO_PROXY", raising=False)
        monkeypatch.delenv("no_proxy", raising=False)
        scraper = BaseScraper()
        with patch("requests.adapters.HTTPAdapter.send", return_value=MagicMock(
            status_code=200, headers={}, is_redirect=False, history=[]
        )) as send:
            scraper._get("historical")
        assert send.call_args.kwargs["proxies"]["https"] == "http://env-proxy:3128"


class TestTokenFetchUsesSameProxy:
    def test_proxied_scraper_gets_provider_with_same_proxy(self, real_proxy_providers):
        scraper = BaseScraper(proxy=PROXY)
        provider = scraper._get_token_provider()
        assert provider is not get_default_provider()
        assert provider._session.proxies == PROXIES

    def test_token_page_fetched_through_proxy(self):
        provider = TokenProvider(proxies=PROXIES, sleep_func=lambda s: None)
        with patch.object(provider._session, "get", return_value=_mock_response(200, "")) as get:
            provider.get_token()
        assert get.call_args.kwargs["proxies"] == PROXIES

    def test_token_fetch_without_proxy_passes_no_proxies(self):
        provider = TokenProvider(sleep_func=lambda s: None)
        with patch.object(provider._session, "get", return_value=_mock_response(200, "")) as get:
            provider.get_token()
        assert get.call_args.kwargs["proxies"] is None

    def test_providers_shared_per_proxy_config(self, real_proxy_providers):
        other = {"http": "http://other:8080", "https": "http://other:8080"}
        a = get_default_provider(PROXIES)
        assert get_default_provider(dict(PROXIES)) is a
        assert get_default_provider(other) is not a
        assert get_default_provider(None) is not a


class TestCredentialsHidden:
    def test_connection_error_mentions_proxy_without_credentials(self, caplog):
        scraper = BaseScraper(proxy=PROXY)
        err = requests.exceptions.ProxyError(f"Cannot connect to proxy {PROXY}")
        caplog.set_level(logging.DEBUG, logger="psxdata")
        with patch.object(scraper._session, "request", side_effect=err):
            with patch("psxdata.scrapers.base.time.sleep"):
                with pytest.raises(PSXConnectionError) as excinfo:
                    scraper._get("historical")
        assert "via proxy http://***@proxy.example.com:8080" in str(excinfo.value)
        assert "s3cret" not in str(excinfo.value)
        assert "via proxy" in caplog.text
        assert "s3cret" not in caplog.text
        assert "alice" not in caplog.text

    def test_token_fetch_failure_warning_hides_credentials(self, caplog):
        provider = TokenProvider(proxies=PROXIES, sleep_func=lambda s: None)
        err = requests.exceptions.ProxyError(f"Cannot connect to proxy {PROXY}")
        caplog.set_level(logging.DEBUG, logger="psxdata")
        with patch.object(provider._session, "get", side_effect=err):
            assert provider.get_token() is None
        assert "via proxy http://***@proxy.example.com:8080" in caplog.text
        assert "s3cret" not in caplog.text

    def test_client_debug_log_hides_credentials(self, tmp_path, caplog):
        caplog.set_level(logging.DEBUG, logger="psxdata")
        psxdata.PSXClient(cache_dir=str(tmp_path), proxy=PROXY)
        assert "http://***@proxy.example.com:8080" in caplog.text
        assert "s3cret" not in caplog.text


class TestClientProxy:
    SCRAPERS = (
        "_historical", "_screener", "_symbols", "_indices",
        "_sectors", "_fundamentals", "_debt_market", "_eligible_scrips",
    )

    def test_proxy_applied_to_every_scraper(self, tmp_path):
        client = psxdata.PSXClient(cache_dir=str(tmp_path), proxy=PROXY)
        for name in self.SCRAPERS:
            assert getattr(client, name)._session.proxies == PROXIES, name

    def test_default_client_has_no_proxy(self, tmp_path):
        client = psxdata.PSXClient(cache_dir=str(tmp_path))
        for name in self.SCRAPERS:
            assert getattr(client, name)._session.proxies == {}, name

    def test_configure_sets_module_level_proxy(self, monkeypatch):
        monkeypatch.setattr(client_module, "_default_client", None)
        psxdata.configure(proxy=PROXY)
        assert client_module._client()._historical._session.proxies == PROXIES
        psxdata.configure()
        assert client_module._client()._historical._session.proxies == {}

    def test_configure_invalid_proxy_keeps_current_client(self, monkeypatch):
        sentinel = object()
        monkeypatch.setattr(client_module, "_default_client", sentinel)
        with pytest.raises(ValueError):
            psxdata.configure(proxy="nope")
        assert client_module._default_client is sentinel
