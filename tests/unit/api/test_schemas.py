"""Unit tests for api/schemas.py response envelope models."""
from api.schemas import (
    ErrorDetail,
    ErrorEnvelope,
    HealthData,
    HealthResponse,
    MetaList,
    MetaSingle,
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
