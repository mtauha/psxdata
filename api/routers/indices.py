"""Indices router — /indices and /indices/{name} endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException, Request

import psxdata
from api.dependencies import limiter
from api.schemas import (
    IndexConstituentResponse,
    IndexConstituentRow,
    MetaList,
    StringListResponse,
)
from psxdata.constants import INDEX_NAMES
from psxdata.exceptions import PSXParseError

router = APIRouter(tags=["indices"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/indices", response_model=StringListResponse)
@limiter.limit("60/minute")
def list_indices(request: Request) -> StringListResponse:
    names = list(INDEX_NAMES)
    return StringListResponse(
        data=names,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(names)),
    )


@router.get("/indices/{name}", response_model=IndexConstituentResponse)
@limiter.limit("60/minute")
def get_index(request: Request, name: str) -> IndexConstituentResponse:
    try:
        df = psxdata.indices(name.upper())
    except PSXParseError:
        raise HTTPException(status_code=404, detail=f"Index {name.upper()} not found")

    rows: list[IndexConstituentRow] = []
    if not df.empty:
        df = df.where(pd.notna(df), other=None)
        for record in df.to_dict("records"):
            rows.append(
                IndexConstituentRow(
                    symbol=record.get("symbol", ""),
                    current_index=record.get("current_index", 0.0),
                    idx_weight=record.get("idx_weight", 0.0),
                    idx_point=record.get("idx_point", 0.0),
                    market_cap_m=record.get("market_cap_m", 0.0),
                    freefloat_m=record.get("freefloat_m"),
                    shares_m=record.get("shares_m"),
                )
            )
    return IndexConstituentResponse(
        data=rows,
        meta=MetaList(timestamp=_now_iso(), cached=False, count=len(rows)),
    )
