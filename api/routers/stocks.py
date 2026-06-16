"""Stocks router — /stocks and /stocks/{symbol}/* endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException, Request

import psxdata
from api.dependencies import limiter
from api.schemas import (
    FundamentalsResponse,
    FundamentalsRow,
    HistoricalResponse,
    MetaList,
    MetaSingle,
    OHLCVRow,
    QuoteData,
    QuoteResponse,
    StringListResponse,
)

router = APIRouter(tags=["stocks"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to JSON-safe records: Timestamps to ISO strings, NaN to None."""
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else None)
    df = df.where(pd.notna(df), other=None)
    return df.to_dict("records")


@router.get("/stocks", response_model=StringListResponse)
@limiter.limit("60/minute")
def list_stocks(request: Request, index: str | None = None) -> StringListResponse:
    tickers = psxdata.tickers(index=index)
    return StringListResponse(
        data=tickers,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(tickers)),
    )


@router.get("/stocks/{symbol}/historical", response_model=HistoricalResponse)
@limiter.limit("60/minute")
def get_historical(
    request: Request,
    symbol: str,
    start: str | None = None,
    end: str | None = None,
) -> HistoricalResponse:
    df = psxdata.stocks(symbol.upper(), start=start, end=end)
    rows: list[OHLCVRow] = []
    if not df.empty:
        rows = [OHLCVRow.model_validate(r) for r in _df_to_records(df)]
    return HistoricalResponse(
        data=rows,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(rows)),
    )


@router.get("/stocks/{symbol}/quote", response_model=QuoteResponse)
@limiter.limit("60/minute")
def get_quote(request: Request, symbol: str) -> QuoteResponse:
    df = psxdata.quote(symbol.upper())
    if df.empty:
        raise HTTPException(status_code=404, detail=f"{symbol.upper()} not found")
    row = _df_to_records(df)[0]
    data = QuoteData.model_validate(row)
    return QuoteResponse(
        data=data,
        meta=MetaSingle(timestamp=_now_iso(), cached=False),
    )


@router.get("/stocks/{symbol}/fundamentals", response_model=FundamentalsResponse)
@limiter.limit("60/minute")
def get_fundamentals(request: Request, symbol: str) -> FundamentalsResponse:
    df = psxdata.fundamentals(symbol=symbol.upper())
    rows: list[FundamentalsRow] = []
    if not df.empty:
        rows = [FundamentalsRow.model_validate(r) for r in _df_to_records(df)]
    return FundamentalsResponse(
        data=rows,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(rows)),
    )
