"""Tests that all HTTP errors return the standardized error envelope."""
import pytest
from fastapi.testclient import TestClient
from psxdata.exceptions import InvalidSymbolError, PSXUnavailableError

from api.main import app

# Register sentinel routes at module level to avoid mutating `app` inside test bodies.
# These routes exist only to trigger specific exception types for testing.
@app.get("/__test_500")
def _boom():
    raise Exception("deliberate")


@app.get("/__test_503")
def _psx_down():
    raise PSXUnavailableError("PSX server unreachable")


@app.get("/__test_404_symbol")
def _bad_symbol():
    raise InvalidSymbolError("FAKESYM not found on PSX")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_404_uses_error_envelope(client: TestClient) -> None:
    resp = client.get("/nonexistent-route-xyz")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["status"] == 404
    assert body["error"]["code"] == "not_found"
    assert "message" in body["error"]


def test_error_envelope_has_no_detail_key(client: TestClient) -> None:
    resp = client.get("/nonexistent-route-xyz")
    body = resp.json()
    assert "detail" not in body


def test_500_uses_error_envelope(client: TestClient) -> None:
    resp = client.get("/__test_500")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["status"] == 500
    assert body["error"]["code"] == "internal_error"


def test_psx_unavailable_maps_to_503(client: TestClient) -> None:
    resp = client.get("/__test_503")
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["status"] == 503
    assert body["error"]["code"] == "psx_unavailable"
    assert "PSX server unreachable" in body["error"]["message"]


def test_invalid_symbol_maps_to_404(client: TestClient) -> None:
    resp = client.get("/__test_404_symbol")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["status"] == 404
    assert body["error"]["code"] == "not_found"
