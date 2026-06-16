"""Unit tests for indices router."""
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from psxdata.exceptions import PSXParseError, PSXUnavailableError

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_list_indices_returns_all_index_names(client: TestClient) -> None:
    resp = client.get("/indices")
    assert resp.status_code == 200
    body = resp.json()
    assert "KSE100" in body["data"]
    assert "ALLSHR" in body["data"]
    assert body["meta"]["count"] == 18  # INDEX_NAMES has 18 entries
    assert "timestamp" in body["meta"]


def test_list_indices_makes_no_network_call(client: TestClient) -> None:
    with patch("psxdata.indices") as mock_indices:
        resp = client.get("/indices")
    mock_indices.assert_not_called()
    assert resp.status_code == 200


def test_get_index_constituents_returns_200(client: TestClient) -> None:
    df = pd.DataFrame({
        "symbol": ["ENGRO", "LUCK"],
        "current_index": [47500.0, 47500.0],
        "idx_weight": [5.2, 3.1],
        "idx_point": [2470.0, 1472.5],
        "market_cap_m": [500000.0, 300000.0],
        "freefloat_m": [250000.0, 150000.0],
    })
    with patch("psxdata.indices", return_value=df):
        resp = client.get("/indices/KSE100")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["data"][0]["symbol"] == "ENGRO"
    assert body["data"][0]["freefloat_m"] == pytest.approx(250000.0)
    assert body["data"][0]["shares_m"] is None
    assert body["meta"]["count"] == 2


def test_get_index_with_shares_m_column(client: TestClient) -> None:
    """Some indices use shares_m instead of freefloat_m."""
    df = pd.DataFrame({
        "symbol": ["ENGRO"],
        "current_index": [47500.0],
        "idx_weight": [5.2],
        "idx_point": [2470.0],
        "market_cap_m": [500000.0],
        "shares_m": [100000.0],
    })
    with patch("psxdata.indices", return_value=df):
        resp = client.get("/indices/KMI30")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"][0]["shares_m"] == pytest.approx(100000.0)
    assert body["data"][0]["freefloat_m"] is None


def test_get_index_unknown_returns_404(client: TestClient) -> None:
    with patch("psxdata.indices", side_effect=PSXParseError("404 for FAKE")):
        resp = client.get("/indices/FAKE")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_get_index_psx_unavailable_returns_503(client: TestClient) -> None:
    with patch("psxdata.indices", side_effect=PSXUnavailableError("PSX down")):
        resp = client.get("/indices/KSE100")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "psx_unavailable"
