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
