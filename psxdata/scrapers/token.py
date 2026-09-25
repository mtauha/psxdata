"""PSX request token (``X-Req-Id``) - extraction, caching and refresh.

Since 2026-09-24 PSX rejects data (XHR) requests with 403 unless they carry an
``X-Req-Id`` header equal to ``window.__ps._k``, which PSX embeds in every HTML
page (issue #161). This module obtains that token and shares it process-wide.

It fails open: when no token can be obtained, callers send requests without the
header, so the SDK keeps working if PSX ever removes the mechanism.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time as _time
from collections.abc import Callable

import requests

from psxdata.constants import (
    BASE_URL,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
    TOKEN_HEADER,
    TOKEN_PAGE,
    TOKEN_RETRY_BACKOFF,
    TOKEN_TTL,
)

logger = logging.getLogger(__name__)

_PS_SCRIPT_RE = re.compile(r"window\.__ps\s*=\s*(\{.*?\})\s*(?:;|</script>)", re.DOTALL)
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,}$")


def extract_token(html: str) -> str | None:
    """Return the ``window.__ps._k`` token embedded in a PSX HTML page.

    Args:
        html: Raw HTML of any PSX page.

    Returns:
        The token string, or ``None`` if the script is absent, is not valid
        JSON, or ``_k`` is missing or does not look like a token.
    """
    match = _PS_SCRIPT_RE.search(html)
    if match is None:
        return None
    try:
        payload = json.loads(match.group(1))
    except ValueError:
        return None
    token = payload.get("_k") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not _TOKEN_RE.match(token):
        return None
    return token


def _redact(token: str) -> str:
    return token[:6] + "..."


class TokenProvider:
    """Obtain, cache and refresh the PSX ``X-Req-Id`` request token.

    Thread-safe. One fetch of ``TOKEN_PAGE`` per ``TOKEN_TTL`` seconds; after a
    failed fetch, no new attempt for ``TOKEN_RETRY_BACKOFF`` seconds. Never
    raises - failures log a warning and yield ``None`` (fail-open).

    Args:
        session: Session used for the page fetch. Defaults to a new session with
            ``REQUEST_HEADERS`` minus ``X-Requested-With`` (a plain page load).
        time_func: Monotonic clock. Inject a fake for deterministic tests.
    """

    def __init__(
        self,
        session: requests.Session | None = None,
        time_func: Callable[[], float] = _time.monotonic,
    ) -> None:
        if session is None:
            session = requests.Session()
            session.headers.update(
                {k: v for k, v in REQUEST_HEADERS.items() if k != "X-Requested-With"}
            )
        self._session = session
        self._time = time_func
        self._lock = threading.Lock()
        self._token: str | None = None
        self._fetched_at: float | None = None
        self._failed_at: float | None = None

    def get_token(self) -> str | None:
        """Return a fresh-enough token, fetching one if needed; ``None`` if unavailable."""
        token = self._cached()
        if token is not None:
            return token
        with self._lock:
            token = self._cached()  # another thread may have just refreshed it
            if token is not None:
                return token
            if (
                self._failed_at is not None
                and self._time() - self._failed_at < TOKEN_RETRY_BACKOFF
            ):
                return None
            return self._fetch()

    def invalidate(self, token: str | None) -> None:
        """Drop the cached token, but only if it is still ``token``.

        A no-op when another thread has already replaced it, so N concurrent
        403s cause a single refetch.
        """
        with self._lock:
            if token is not None and token == self._token:
                self._token = None
                self._fetched_at = None

    def _cached(self) -> str | None:
        if (
            self._token is not None
            and self._fetched_at is not None
            and self._time() - self._fetched_at < TOKEN_TTL
        ):
            return self._token
        return None

    def _fetch(self) -> str | None:
        url = BASE_URL + TOKEN_PAGE
        try:
            resp = self._session.get(url, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            self._fail(url, f"request failed: {exc}")
            return None
        if resp.status_code != 200:
            self._fail(url, f"HTTP {resp.status_code}")
            return None
        token = extract_token(resp.text)
        if token is None:
            self._fail(url, "window.__ps._k not found in page")
            return None
        self._token = token
        self._fetched_at = self._time()
        self._failed_at = None
        logger.debug("Fetched PSX request token %s", _redact(token))
        return token

    def _fail(self, url: str, reason: str) -> None:
        self._token = None
        self._fetched_at = None
        self._failed_at = self._time()
        logger.warning(
            "Could not obtain PSX request token from %s (%s); sending requests without %s",
            url,
            reason,
            TOKEN_HEADER,
        )
        return None


_default_provider: TokenProvider | None = None
_default_lock = threading.Lock()


def get_default_provider() -> TokenProvider:
    """Return the process-wide TokenProvider shared by all scrapers (created lazily)."""
    global _default_provider
    with _default_lock:
        if _default_provider is None:
            _default_provider = TokenProvider()
        return _default_provider
