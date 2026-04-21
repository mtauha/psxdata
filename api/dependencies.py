"""Shared FastAPI dependency stubs for the API layer."""


# TODO: Replace None return types when wiring real dependencies so
# typed Depends(...) injection remains correct.
def get_cache() -> None:
    return None


def get_rate_limiter() -> None:
    return None
