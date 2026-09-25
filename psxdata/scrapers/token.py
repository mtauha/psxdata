"""PSX request token (``X-Req-Id``) - extraction, caching and refresh.

Since 2026-09-24 PSX rejects data (XHR) requests with 403 unless they carry an
``X-Req-Id`` header equal to ``window.__ps._k``, which PSX embeds in every HTML
page (issue #161). This module obtains that token and shares it process-wide.

It fails open: when no token can be obtained, callers send requests without the
header, so the SDK keeps working if PSX ever removes the mechanism.
"""
from __future__ import annotations

import json
import re

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
