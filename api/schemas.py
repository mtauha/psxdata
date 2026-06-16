"""Shared Pydantic models for psxdata API response envelopes."""
from __future__ import annotations

from typing import Any

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


class StringListResponse(BaseModel):
    data: list[str]
    meta: MetaList


# ---------------------------------------------------------------------------
# Stocks
# ---------------------------------------------------------------------------

class OHLCVRow(BaseModel):
    date: str  # ISO 8601 date string
    open: float
    high: float
    low: float
    close: float
    volume: int
    is_anomaly: bool


class HistoricalResponse(BaseModel):
    data: list[OHLCVRow]
    meta: MetaList


class QuoteData(BaseModel):
    symbol: str
    price: float
    market_cap: float | None = None
    pe_ratio: float | None = None
    dividend_yield: float | None = None
    free_float: float | None = None
    volume_avg_30d: float | None = None
    change_1y_pct: float | None = None
    ldcp: float | None = None
    change: float | None = None
    change_pct: float | None = None


class QuoteResponse(BaseModel):
    data: QuoteData
    meta: MetaSingle


class FundamentalsRow(BaseModel):
    symbol: str
    year: str
    type: str
    period_ended: str
    posting_date: str
    document: str


class FundamentalsResponse(BaseModel):
    data: list[FundamentalsRow]
    meta: MetaList


# ---------------------------------------------------------------------------
# Indices
# ---------------------------------------------------------------------------

class IndexConstituentRow(BaseModel):
    symbol: str
    current_index: float
    idx_weight: float
    idx_point: float
    market_cap_m: float
    freefloat_m: float | None = None
    shares_m: float | None = None


class IndexConstituentResponse(BaseModel):
    data: list[IndexConstituentRow]
    meta: MetaList


# ---------------------------------------------------------------------------
# Sectors
# ---------------------------------------------------------------------------

class SectorRow(BaseModel):
    sector_code: str
    sector_name: str
    advance: int
    decline: int
    unchanged: int
    turnover: int
    market_cap_b: float


class SectorsResponse(BaseModel):
    data: list[SectorRow]
    meta: MetaList


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------

class MarketTablesResponse(BaseModel):
    data: dict[str, list[dict[str, Any]]]
    meta: MetaSingle
