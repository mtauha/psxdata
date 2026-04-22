"""Unit tests for GET /health."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_data_shape(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["data"] == {"status": "ok"}


def test_health_meta_shape(client: TestClient) -> None:
    meta = client.get("/health").json()["meta"]
    assert "timestamp" in meta
    assert "cached" in meta
    assert meta["cached"] is False


def test_health_meta_has_no_count(client: TestClient) -> None:
    meta = client.get("/health").json()["meta"]
    assert "count" not in meta


def test_health_timestamp_is_iso8601(client: TestClient) -> None:
    ts = client.get("/health").json()["meta"]["timestamp"]
    datetime.fromisoformat(ts)
