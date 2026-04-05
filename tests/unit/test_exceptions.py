"""Smoke tests for psxdata exception hierarchy."""
import pytest
from psxdata.exceptions import (
    PSXDataError,
    PSXUnavailableError,
    PSXConnectionError,
    PSXServerError,
    PSXAuthError,
    PSXRateLimitError,
    PSXParseError,
    InvalidSymbolError,
    DelistedSymbolError,
    DataNotAvailableError,
    CacheError,
)


def test_all_exceptions_importable():
    assert PSXDataError is not None


def test_hierarchy_base():
    assert issubclass(PSXUnavailableError, PSXDataError)
    assert issubclass(PSXConnectionError, PSXUnavailableError)
    assert issubclass(PSXServerError, PSXUnavailableError)
    assert issubclass(PSXAuthError, PSXDataError)
    assert issubclass(PSXRateLimitError, PSXDataError)
    assert issubclass(PSXParseError, PSXDataError)
    assert issubclass(InvalidSymbolError, PSXDataError)
    assert issubclass(DelistedSymbolError, InvalidSymbolError)
    assert issubclass(DataNotAvailableError, PSXDataError)
    assert issubclass(CacheError, PSXDataError)


def test_catch_base_catches_all():
    for exc_class in [
        PSXConnectionError, PSXServerError, PSXAuthError, PSXRateLimitError,
        PSXParseError, DelistedSymbolError, DataNotAvailableError, CacheError,
    ]:
        with pytest.raises(PSXDataError):
            raise exc_class("test")


def test_catch_unavailable_catches_subclasses():
    with pytest.raises(PSXUnavailableError):
        raise PSXConnectionError("connection refused")
    with pytest.raises(PSXUnavailableError):
        raise PSXServerError("503")


def test_catch_invalid_symbol_catches_delisted():
    with pytest.raises(InvalidSymbolError):
        raise DelistedSymbolError("XXXX was delisted")


def test_exceptions_have_messages():
    exc = PSXUnavailableError("PSX is down")
    assert str(exc) == "PSX is down"
