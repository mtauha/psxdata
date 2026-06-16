"""Market router — /debt-market and /eligible-scrips endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import psxdata
from fastapi import APIRouter, Request

from api.dependencies import limiter
from api.schemas import MarketTablesResponse, MetaSingle

router = APIRouter(tags=["market"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame to JSON-safe records: Timestamps to ISO strings, NaN to None."""
    if df.empty:
        return []
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None)
    df = df.where(pd.notna(df), other=None)
    return df.to_dict("records")


def _serialize_tables(tables: dict[str, pd.DataFrame]) -> dict[str, list[dict[str, Any]]]:
    return {key: _df_to_records(df) for key, df in tables.items()}


@router.get("/debt-market", response_model=MarketTablesResponse)
@limiter.limit("60/minute")
def get_debt_market(request: Request) -> MarketTablesResponse:
    tables = psxdata.debt_market()
    return MarketTablesResponse(
        data=_serialize_tables(tables),
        meta=MetaSingle(timestamp=_now_iso(), cached=False),
    )


@router.get("/eligible-scrips", response_model=MarketTablesResponse)
@limiter.limit("60/minute")
def get_eligible_scrips(request: Request) -> MarketTablesResponse:
    tables = psxdata.eligible_scrips()
    return MarketTablesResponse(
        data=_serialize_tables(tables),
        meta=MetaSingle(timestamp=_now_iso(), cached=False),
    )
