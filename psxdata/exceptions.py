"""Custom exception hierarchy for psxdata.

All library exceptions inherit from PSXDataError, allowing callers to catch
any library error with a single except clause.
"""


class PSXDataError(Exception):
    """Base exception for all psxdata library errors."""


class PSXUnavailableError(PSXDataError):
    """PSX server is unreachable or returned a 5xx response."""


class PSXConnectionError(PSXUnavailableError):
    """Network-level failure — DNS resolution failed, connection refused, or timeout.

    The server was never reached.
    """


class PSXServerError(PSXUnavailableError):
    """PSX server was reached but returned a 5xx HTTP response."""


class PSXAuthError(PSXDataError):
    """PSX returned 401 or 403 — authentication or authorisation failure."""


class PSXRateLimitError(PSXDataError):
    """PSX returned 429 — rate limit exceeded."""


class PSXParseError(PSXDataError):
    """HTML structure changed or response could not be parsed.

    Also raised for unexpected 4xx responses (400, 404, etc.).
    """


class InvalidSymbolError(PSXDataError):
    """The requested ticker symbol does not exist on PSX."""


class DelistedSymbolError(InvalidSymbolError):
    """The requested ticker existed on PSX but has since been delisted."""


class DataNotAvailableError(PSXDataError):
    """Valid symbol requested but PSX returned no data for the given period."""


class CacheError(PSXDataError):
    """Disk cache read or write failure."""
