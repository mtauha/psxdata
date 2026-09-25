"""Reliability tests for BaseScraper — mocked network, no real HTTP calls.

Marked @pytest.mark.reliability — excluded from CI by default but run locally.
All network I/O is mocked via unittest.mock.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from psxdata.exceptions import (
    PSXAuthError,
    PSXConnectionError,
    PSXParseError,
    PSXRateLimitError,
    PSXServerError,
)
from psxdata.scrapers.base import BaseScraper
from psxdata.scrapers.token import TokenProvider
from tests.conftest import STUB_TOKEN

pytestmark = pytest.mark.reliability


def _mock_response(status_code: int, text: str = "") -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


class TestBaseScraper:
    def test_successful_get_returns_response(self):
        scraper = BaseScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(200, "ok")):
            resp = scraper._get("historical")
        assert resp.status_code == 200

    def test_timeout_retries_and_succeeds(self):
        scraper = BaseScraper()
        calls = [requests.Timeout("timeout"), _mock_response(200, "ok")]
        with patch.object(scraper._session, "request", side_effect=calls):
            with patch("psxdata.scrapers.base.time.sleep"):
                resp = scraper._get("historical")
        assert resp.status_code == 200

    def test_all_retries_timeout_raises_connection_error(self):
        scraper = BaseScraper()
        with patch.object(scraper._session, "request", side_effect=requests.Timeout("timeout")):
            with patch("psxdata.scrapers.base.time.sleep"):
                with pytest.raises(PSXConnectionError):
                    scraper._get("historical")

    def test_503_retries_then_raises_server_error(self):
        scraper = BaseScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(503)):
            with patch("psxdata.scrapers.base.time.sleep"):
                with pytest.raises(PSXServerError):
                    scraper._get("historical")

    def test_429_raises_rate_limit_error_no_retry(self):
        scraper = BaseScraper()
        call_count = {"n": 0}

        def mock_req(*args, **kwargs):
            call_count["n"] += 1
            return _mock_response(429)

        with patch.object(scraper._session, "request", side_effect=mock_req):
            with pytest.raises(PSXRateLimitError):
                scraper._get("historical")
        assert call_count["n"] == 1

    def test_401_raises_auth_error_no_retry(self):
        scraper = BaseScraper()
        call_count = {"n": 0}

        def mock_req(*args, **kwargs):
            call_count["n"] += 1
            return _mock_response(401)

        with patch.object(scraper._session, "request", side_effect=mock_req):
            with pytest.raises(PSXAuthError):
                scraper._get("historical")
        assert call_count["n"] == 1

    def test_404_raises_parse_error_no_retry(self):
        scraper = BaseScraper()
        call_count = {"n": 0}

        def mock_req(*args, **kwargs):
            call_count["n"] += 1
            return _mock_response(404)

        with patch.object(scraper._session, "request", side_effect=mock_req):
            with pytest.raises(PSXParseError):
                scraper._get("historical")
        assert call_count["n"] == 1

    def test_post_sends_data(self):
        scraper = BaseScraper()
        with patch.object(
            scraper._session, "request", return_value=_mock_response(200, "ok")
        ) as mock_req:
            scraper._post("historical", data={"symbol": "ENGRO"})
        _, kwargs = mock_req.call_args
        assert kwargs.get("data") == {"symbol": "ENGRO"}

    def test_rate_limiter_called_on_each_request(self):
        """RateLimiter.__enter__ is called for every request."""
        from psxdata.utils import RateLimiter
        scraper = BaseScraper()
        enter_calls = []
        original_enter = RateLimiter.__enter__

        def tracking_enter(self_):
            enter_calls.append(1)
            return original_enter(self_)

        with patch.object(RateLimiter, "__enter__", tracking_enter):
            with patch.object(scraper._session, "request", return_value=_mock_response(200)):
                scraper._get("historical")
                scraper._get("indices")
        assert len(enter_calls) == 2


TOKEN_A = "tokenAAAAAAAAAAAAAAAAAAAAA"
TOKEN_B = "tokenBBBBBBBBBBBBBBBBBBBBB"


def _provider_mock(*tokens: str | None) -> MagicMock:
    """TokenProvider double whose get_token() yields `tokens` in order (last one repeats)."""
    provider = MagicMock(spec=TokenProvider)
    seq = list(tokens)

    def next_token():
        return seq.pop(0) if len(seq) > 1 else seq[0]

    provider.get_token.side_effect = next_token
    return provider


class TestRequestToken:
    def test_default_provider_used_and_header_sent(self):
        scraper = BaseScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(200)) as req:
            scraper._get("symbols")
        assert req.call_args.kwargs["headers"]["X-Req-Id"] == STUB_TOKEN

    def test_token_never_written_to_session_headers(self):
        scraper = BaseScraper()
        with patch.object(scraper._session, "request", return_value=_mock_response(200)):
            scraper._get("symbols")
        assert "X-Req-Id" not in scraper._session.headers

    def test_caller_headers_merged_and_not_mutated(self):
        scraper = BaseScraper(token_provider=_provider_mock(TOKEN_A))
        caller = {"X-Custom": "1"}
        with patch.object(scraper._session, "request", return_value=_mock_response(200)) as req:
            scraper._request("GET", "https://dps.psx.com.pk/symbols", headers=caller)
        assert req.call_args.kwargs["headers"] == {"X-Custom": "1", "X-Req-Id": TOKEN_A}
        assert caller == {"X-Custom": "1"}

    def test_headers_none_is_accepted(self):
        scraper = BaseScraper(token_provider=_provider_mock(TOKEN_A))
        with patch.object(scraper._session, "request", return_value=_mock_response(200)) as req:
            scraper._request("GET", "https://dps.psx.com.pk/symbols", headers=None)
        assert req.call_args.kwargs["headers"] == {"X-Req-Id": TOKEN_A}

    def test_no_token_sends_request_without_header(self):
        scraper = BaseScraper(token_provider=_provider_mock(None))
        with patch.object(scraper._session, "request", return_value=_mock_response(200)) as req:
            scraper._get("symbols")
        assert "X-Req-Id" not in req.call_args.kwargs["headers"]

    def test_403_refreshes_token_and_retries_once(self):
        provider = _provider_mock(TOKEN_A, TOKEN_B)
        scraper = BaseScraper(token_provider=provider)
        responses = [_mock_response(403), _mock_response(200, "ok")]
        with patch.object(scraper._session, "request", side_effect=responses) as req:
            resp = scraper._get("symbols")
        assert resp.status_code == 200
        assert req.call_count == 2
        provider.invalidate.assert_called_once_with(TOKEN_A)
        assert req.call_args_list[1].kwargs["headers"]["X-Req-Id"] == TOKEN_B

    def test_403_twice_raises_auth_error_after_two_requests(self):
        scraper = BaseScraper(token_provider=_provider_mock(TOKEN_A, TOKEN_B))
        with patch.object(scraper._session, "request", return_value=_mock_response(403)) as req:
            with pytest.raises(PSXAuthError, match="refreshed once"):
                scraper._get("symbols")
        assert req.call_count == 2

    def test_403_without_token_raises_without_retry(self):
        provider = _provider_mock(None)
        scraper = BaseScraper(token_provider=provider)
        with patch.object(scraper._session, "request", return_value=_mock_response(403)) as req:
            with pytest.raises(PSXAuthError, match="no X-Req-Id token could be obtained"):
                scraper._get("symbols")
        assert req.call_count == 1
        provider.invalidate.assert_not_called()

    def test_403_refresh_fails_raises_without_retry(self):
        provider = _provider_mock(TOKEN_A, None)
        scraper = BaseScraper(token_provider=provider)
        with patch.object(scraper._session, "request", return_value=_mock_response(403)) as req:
            with pytest.raises(PSXAuthError, match="could not be refreshed"):
                scraper._get("symbols")
        assert req.call_count == 1

    def test_401_does_not_refresh(self):
        provider = _provider_mock(TOKEN_A)
        scraper = BaseScraper(token_provider=provider)
        with patch.object(scraper._session, "request", return_value=_mock_response(401)) as req:
            with pytest.raises(PSXAuthError):
                scraper._get("symbols")
        assert req.call_count == 1
        provider.invalidate.assert_not_called()

    def test_5xx_retries_reread_token_each_attempt(self):
        provider = _provider_mock(TOKEN_A)
        scraper = BaseScraper(token_provider=provider)
        responses = [_mock_response(503), _mock_response(503), _mock_response(200)]
        with patch.object(scraper._session, "request", side_effect=responses) as req:
            with patch("psxdata.scrapers.base.time.sleep"):
                scraper._get("symbols")
        assert req.call_count == 3
        assert provider.get_token.call_count == 3

    def test_403_retry_does_not_consume_5xx_attempts(self):
        scraper = BaseScraper(token_provider=_provider_mock(TOKEN_A, TOKEN_B))
        responses = [
            _mock_response(403),
            _mock_response(503),
            _mock_response(503),
            _mock_response(200),
        ]
        with patch.object(scraper._session, "request", side_effect=responses) as req:
            with patch("psxdata.scrapers.base.time.sleep") as sleep:
                resp = scraper._get("symbols")
        assert resp.status_code == 200
        assert req.call_count == 4
        assert sleep.call_count == 2  # the 403 retry itself never sleeps

    def test_scraper_subclass_without_args_still_constructs(self):
        from psxdata.scrapers.symbols import SymbolsScraper

        scraper = SymbolsScraper()
        assert scraper._get_token_provider().get_token() == STUB_TOKEN
