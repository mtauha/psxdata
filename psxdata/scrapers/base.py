"""BaseScraper — foundation class for all psxdata scrapers.

Scraping mode:
  - requests + BeautifulSoup: via _get() / _post()

All PSX endpoints are accessible via plain HTTP requests to AJAX endpoints.
Playwright is not used — all scrapers use requests only.

All Phase 3 scrapers inherit from BaseScraper.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests
from psxdata.constants import (
    BASE_URL,
    ENDPOINTS,
    MAX_REQUESTS_PER_SECOND,
    MAX_RETRIES,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
    RETRY_DELAYS,
)
from psxdata.exceptions import (
    PSXAuthError,
    PSXConnectionError,
    PSXParseError,
    PSXRateLimitError,
    PSXServerError,
)
from psxdata.utils import RateLimiter

logger = logging.getLogger(__name__)


class BaseScraper:
    """Foundation class for all psxdata scrapers.

    Provides:
    - Persistent requests.Session with standard PSX headers
    - Exponential backoff retry (MAX_RETRIES attempts, RETRY_DELAYS seconds)
    - Thread-safe rate limiter (MAX_REQUESTS_PER_SECOND)

    """

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(REQUEST_HEADERS)
        self._rate_limiter = RateLimiter(max_per_second=MAX_REQUESTS_PER_SECOND)

    def _build_url(self, endpoint: str) -> str:
        return BASE_URL + ENDPOINTS[endpoint]

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Execute an HTTP request with retry, rate limiting, and error mapping.

        Retries on 5xx and network errors up to MAX_RETRIES times with
        exponential backoff. Raises immediately (no retry) on 4xx.

        Args:
            method: HTTP method ("GET" or "POST").
            url: Full URL to request.
            **kwargs: Passed directly to requests.Session.request.

        Returns:
            requests.Response with 2xx status.

        Raises:
            PSXConnectionError: Network-level failure after all retries.
            PSXServerError: 5xx response after all retries.
            PSXRateLimitError: 429 response (no retry).
            PSXAuthError: 401/403 response (no retry).
            PSXParseError: Other 4xx response (no retry).
        """
        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                with self._rate_limiter:
                    logger.debug(
                        "attempt %d/%d %s %s", attempt, MAX_RETRIES, method, url
                    )
                    resp = self._session.request(
                        method, url, timeout=REQUEST_TIMEOUT, **kwargs
                    )

                if resp.status_code == 429:
                    raise PSXRateLimitError(
                        f"PSX rate limit exceeded (429) on {url}"
                    )
                if resp.status_code in (401, 403):
                    raise PSXAuthError(
                        f"PSX auth error ({resp.status_code}) on {url}"
                    )
                if resp.status_code >= 500:
                    last_exc = PSXServerError(
                        f"PSX server error ({resp.status_code}) on {url}, "
                        f"attempt {attempt}/{MAX_RETRIES}"
                    )
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAYS[attempt - 1])  # delays[0]=1s, delays[1]=2s
                        continue
                    raise last_exc  # final attempt — raise immediately, no sleep
                if 400 <= resp.status_code < 500:
                    raise PSXParseError(
                        f"Unexpected {resp.status_code} from {url}"
                    )
                return resp

            except requests.RequestException as exc:
                # Catches ConnectionError, Timeout, SSLError, ChunkedEncodingError, etc.
                last_exc = exc
                logger.debug(
                    "Network error on attempt %d/%d: %s", attempt, MAX_RETRIES, exc
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAYS[attempt - 1])
                    continue
                raise PSXConnectionError(
                    f"PSX unreachable after {MAX_RETRIES} attempts: {url}"
                ) from exc
            except (PSXRateLimitError, PSXAuthError, PSXParseError):
                raise  # no retry

        # Safety net — loop always returns or raises above
        raise PSXServerError(f"Exhausted retries for {url}")

    def _get(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """GET request to a named PSX endpoint."""
        return self._request("GET", self._build_url(endpoint), **kwargs)

    def _post(self, endpoint: str, data: dict[str, Any], **kwargs: Any) -> requests.Response:
        """POST request to a named PSX endpoint."""
        return self._request("POST", self._build_url(endpoint), data=data, **kwargs)


