"""Shared FastAPI dependencies for the API layer."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


def get_rate_limiter() -> Limiter:
    return limiter


def get_cache() -> None:
    # TODO: return Redis client when Redis layer is added
    return None
