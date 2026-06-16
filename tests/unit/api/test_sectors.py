"""Unit tests for sectors router."""
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from psxdata.exceptions import PSXUnavailableError

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_list_sectors_returns_200(client: TestClient) -> None:
    df = pd.DataFrame({
        "sector_code": ["0801", "0804"],
        "sector_name": ["CEMENT", "FERTILIZER"],
        "advance": [5, 2], "decline": [2, 1], "unchanged": [1, 0],
        "turnover": [1200000, 800000], "market_cap_b": [450.5, 320.1],
    })
    with patch("psxdata.sectors", return_value=df):
        resp = client.get("/sectors")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["data"][0]["sector_name"] == "CEMENT"
    assert body["meta"]["count"] == 2


def test_list_sectors_empty_returns_200(client: TestClient) -> None:
    with patch("psxdata.sectors", return_value=pd.DataFrame()):
        resp = client.get("/sectors")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_get_sector_stocks_returns_matching_symbols(client: TestClient) -> None:
    symbols_df = pd.DataFrame({
        "symbol": ["LUCK", "DGKC", "ENGRO"],
        "sector_name": ["CEMENT", "CEMENT", "FERTILIZER"],
    })
    with patch("psxdata.symbols", return_value=symbols_df):
        resp = client.get("/sectors/CEMENT/stocks")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["data"]) == {"LUCK", "DGKC"}
    assert body["meta"]["count"] == 2


def test_get_sector_stocks_case_insensitive(client: TestClient) -> None:
    symbols_df = pd.DataFrame({"symbol": ["LUCK"], "sector_name": ["CEMENT"]})
    with patch("psxdata.symbols", return_value=symbols_df):
        resp = client.get("/sectors/cement/stocks")
    assert resp.status_code == 200
    assert resp.json()["data"] == ["LUCK"]


def test_get_sector_stocks_unknown_returns_empty(client: TestClient) -> None:
    symbols_df = pd.DataFrame({"symbol": ["LUCK"], "sector_name": ["CEMENT"]})
    with patch("psxdata.symbols", return_value=symbols_df):
        resp = client.get("/sectors/UNKNOWN/stocks")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
    assert resp.json()["meta"]["count"] == 0


def test_sectors_psx_unavailable_returns_503(client: TestClient) -> None:
    with patch("psxdata.sectors", side_effect=PSXUnavailableError("PSX down")):
        resp = client.get("/sectors")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "psx_unavailable"
