"""Health check router — GET /health."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from api.schemas import HealthData, HealthResponse, MetaSingle

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return API liveness status."""
    return HealthResponse(
        data=HealthData(status="ok"),
        meta=MetaSingle(
            timestamp=datetime.now(timezone.utc).isoformat(),
            cached=False,
        ),
    )
