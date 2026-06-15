"""Unit tests for api/schemas.py response envelope models."""
from api.schemas import (
    ErrorDetail,
    ErrorEnvelope,
    FundamentalsResponse,
    FundamentalsRow,
    HealthData,
    HealthResponse,
    HistoricalResponse,
    IndexConstituentResponse,
    IndexConstituentRow,
    MarketTablesResponse,
    MetaList,
    MetaSingle,
    OHLCVRow,
    QuoteData,
    QuoteResponse,
    SectorRow,
    SectorsResponse,
    StringListResponse,
)


def test_meta_single_fields() -> None:
    m = MetaSingle(timestamp="2026-04-21T12:00:00Z", cached=False)
    assert m.timestamp == "2026-04-21T12:00:00Z"
    assert m.cached is False


def test_meta_list_fields() -> None:
    m = MetaList(timestamp="2026-04-21T12:00:00Z", cached=True, count=42)
    assert m.count == 42
    assert m.cached is True


def test_error_detail_fields() -> None:
    e = ErrorDetail(status=404, code="not_found", message="Symbol XYZ not found")
    assert e.status == 404
    assert e.code == "not_found"
    assert e.message == "Symbol XYZ not found"


def test_error_envelope_nests_detail() -> None:
    detail = ErrorDetail(status=503, code="psx_unavailable", message="PSX unreachable")
    env = ErrorEnvelope(error=detail)
    assert env.error.status == 503


def test_meta_single_model_dump() -> None:
    m = MetaSingle(timestamp="2026-04-21T12:00:00Z", cached=False)
    d = m.model_dump()
    assert set(d.keys()) == {"timestamp", "cached"}


def test_meta_list_model_dump() -> None:
    m = MetaList(timestamp="2026-04-21T12:00:00Z", cached=False, count=10)
    d = m.model_dump()
    assert set(d.keys()) == {"timestamp", "cached", "count"}


def test_health_response_shape() -> None:
    resp = HealthResponse(
        data=HealthData(status="ok"),
        meta=MetaSingle(timestamp="2026-04-21T12:00:00Z", cached=False),
    )
    assert resp.data.status == "ok"
    assert resp.meta.cached is False


def test_string_list_response() -> None:
    r = StringListResponse(
        data=["ENGRO", "LUCK"],
        meta=MetaList(timestamp="2026-01-01T00:00:00+00:00", cached=False, count=2),
    )
    assert r.data == ["ENGRO", "LUCK"]
    assert r.meta.count == 2


def test_ohlcv_row() -> None:
    row = OHLCVRow(
        date="2024-01-05", open=481.99, high=496.0,
        low=474.01, close=485.38, volume=4496408, is_anomaly=False,
    )
    assert row.date == "2024-01-05"
    assert row.is_anomaly is False


def test_quote_data_optional_fields_default_none() -> None:
    q = QuoteData(symbol="ENGRO", price=481.99)
    assert q.ldcp is None
    assert q.change is None
    assert q.pe_ratio is None


def test_fundamentals_row() -> None:
    row = FundamentalsRow(
        symbol="ENGRO", year="2024", type="Annual",
        period_ended="2024-12-31", posting_date="2025-01-15",
        document="https://psx.com/report.pdf",
    )
    assert row.symbol == "ENGRO"


def test_index_constituent_row_optional_defaults() -> None:
    row = IndexConstituentRow(
        symbol="ENGRO", current_index=47500.0,
        idx_weight=5.2, idx_point=2470.0, market_cap_m=500000.0,
    )
    assert row.freefloat_m is None
    assert row.shares_m is None


def test_sector_row() -> None:
    row = SectorRow(
        sector_code="0801", sector_name="CEMENT",
        advance=5, decline=2, unchanged=1,
        turnover=1200000, market_cap_b=450.5,
    )
    assert row.sector_code == "0801"


def test_market_tables_response() -> None:
    r = MarketTablesResponse(
        data={"table_0": [{"security_code": "P01", "name": "1Y GIS"}]},
        meta=MetaSingle(timestamp="2026-01-01T00:00:00+00:00", cached=False),
    )
    assert "table_0" in r.data
