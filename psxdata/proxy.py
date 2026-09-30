"""Proxy configuration - validation, normalisation and credential redaction (#162).

A proxy is given either as one URL string, applied to both ``http`` and
``https`` traffic, or as a ``requests``-style dict mapping scheme to URL.
Supported URL schemes are ``http``, ``https`` and, with the optional
``psxdata[socks]`` extra installed, ``socks4``/``socks4a``/``socks5``/``socks5h``.
Credentials go in the URL (``http://user:pass@host:port``) and are never
logged: every proxy URL that reaches a log line or an exception message is
passed through :func:`redact_url` first.
"""
from __future__ import annotations

import importlib.util
from collections.abc import Mapping
from urllib.parse import unquote, urlsplit

ProxyConfig = str | Mapping[str, str] | None

SUPPORTED_SCHEMES = frozenset({"http", "https", "socks4", "socks4a", "socks5", "socks5h"})
_SOCKS_SCHEMES = frozenset(s for s in SUPPORTED_SCHEMES if s.startswith("socks"))


def normalize_proxy(proxy: ProxyConfig) -> dict[str, str] | None:
    """Validate *proxy* and return it as a ``requests`` ``proxies`` dict.

    Args:
        proxy: ``None`` (no explicit proxy), a single proxy URL used for both
            ``http`` and ``https``, or a dict mapping scheme (``"http"``,
            ``"https"``, ...) to proxy URL.

    Returns:
        ``None`` when *proxy* is ``None``, otherwise a new dict.

    Raises:
        TypeError: *proxy* is not a string, a mapping of strings, or ``None``.
        ValueError: A URL is malformed, has no host, or uses an unsupported
            scheme; or the dict is empty.
        ImportError: A SOCKS proxy was given but PySocks is not installed.
    """
    if proxy is None:
        return None
    if isinstance(proxy, str):
        _validate_url(proxy)
        return {"http": proxy, "https": proxy}
    if isinstance(proxy, Mapping):
        if not proxy:
            raise ValueError("proxy dict must not be empty; pass proxy=None for no proxy")
        proxies: dict[str, str] = {}
        for key, url in proxy.items():
            if not isinstance(key, str) or not isinstance(url, str):
                raise TypeError("proxy dict keys and values must be strings")
            _validate_url(url)
            proxies[key] = url
        return proxies
    raise TypeError(
        f"proxy must be a URL string, a dict of scheme -> URL, or None; got {type(proxy).__name__}"
    )


def _validate_url(url: str) -> None:
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in SUPPORTED_SCHEMES:
        raise ValueError(
            f"Unsupported proxy URL {redact_url(url)!r}; expected a scheme of "
            f"{', '.join(sorted(SUPPORTED_SCHEMES))} (e.g. 'http://host:8080')"
        )
    try:
        parts.port  # noqa: B018 - raises ValueError on a non-numeric/out-of-range port
    except ValueError as exc:
        raise ValueError(f"Invalid port in proxy URL {redact_url(url)!r}") from exc
    if not parts.hostname:
        raise ValueError(f"Proxy URL {redact_url(url)!r} has no host")
    if scheme in _SOCKS_SCHEMES and importlib.util.find_spec("socks") is None:
        raise ImportError(
            "SOCKS proxies need the optional PySocks dependency: pip install 'psxdata[socks]'"
        )


def redact_url(url: str) -> str:
    """Return *url* with any ``user:pass@`` userinfo replaced by ``***@``."""
    parts = urlsplit(url)
    if "@" not in parts.netloc:
        return url
    host = parts.netloc.rpartition("@")[2]
    return parts._replace(netloc=f"***@{host}").geturl()


def describe_proxies(proxies: Mapping[str, str]) -> str:
    """Return a credential-free, human-readable summary of a ``proxies`` dict."""
    urls = {redact_url(u) for u in proxies.values()}
    if len(urls) == 1:
        return urls.pop()
    return ", ".join(f"{key}={redact_url(url)}" for key, url in proxies.items())


def redact_text(text: str, proxies: Mapping[str, str] | None) -> str:
    """Remove the credentials of every proxy in *proxies* from free text.

    Used on exception messages before they are logged, since those can echo
    the proxy URL back.
    """
    if not proxies:
        return text
    for url in proxies.values():
        parts = urlsplit(url)
        if "@" not in parts.netloc:
            continue
        userinfo = parts.netloc.rpartition("@")[0]
        text = text.replace(url, redact_url(url)).replace(userinfo + "@", "***@")
        if parts.password:
            for secret in {parts.password, unquote(parts.password)}:
                text = text.replace(secret, "***")
    return text
