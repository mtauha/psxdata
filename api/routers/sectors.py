"""Sectors router — /sectors and /sectors/{name}/stocks endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import psxdata
from fastapi import APIRouter, Request

from api.dependencies import limiter
from api.schemas import (
    MetaList,
    SectorRow,
    SectorsResponse,
    StringListResponse,
)

router = APIRouter(tags=["sectors"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/sectors", response_model=SectorsResponse)
@limiter.limit("60/minute")
def list_sectors(request: Request) -> SectorsResponse:
    df = psxdata.sectors()
    rows: list[SectorRow] = []
    if not df.empty:
        df = df.where(pd.notna(df), other=None)
        rows = [SectorRow(**{k: r.get(k) for k in SectorRow.model_fields}) for r in df.to_dict("records")]
    return SectorsResponse(
        data=rows,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(rows)),
    )


@router.get("/sectors/{name}/stocks", response_model=StringListResponse)
@limiter.limit("60/minute")
def get_sector_stocks(request: Request, name: str) -> StringListResponse:
    df = psxdata.symbols()
    tickers: list[str] = []
    if not df.empty and "sector_name" in df.columns and "symbol" in df.columns:
        matched = df[df["sector_name"].str.upper() == name.upper()]
        tickers = matched["symbol"].tolist()
    return StringListResponse(
        data=tickers,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(tickers)),
    )
