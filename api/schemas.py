"""Shared Pydantic models for psxdata API response envelopes."""
from __future__ import annotations

from pydantic import BaseModel


class MetaSingle(BaseModel):
    """Metadata block for single-item responses."""

    timestamp: str
    cached: bool


class MetaList(BaseModel):
    """Metadata block for list responses. Always includes count."""

    timestamp: str
    cached: bool
    count: int


class ErrorDetail(BaseModel):
    """Structured error payload."""

    status: int
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    """Top-level error response wrapper."""

    error: ErrorDetail


class HealthData(BaseModel):
    """Data payload for GET /health."""

    status: str


class HealthResponse(BaseModel):
    """Typed response model for GET /health."""

    data: HealthData
    meta: MetaSingle
