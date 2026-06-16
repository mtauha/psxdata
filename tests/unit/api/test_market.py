"""Unit tests for market router."""
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from psxdata.exceptions import PSXUnavailableError

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_debt_tables() -> dict[str, pd.DataFrame]:
    return {
        "table_0": pd.DataFrame({
            "security_code": ["P01GIS080227"],
            "security_name": ["1 Year GIS"],
            "face_value": [5000.0],
            "maturity_date": [pd.Timestamp("2027-02-08")],
            "coupon_rate": [0.0],
        }),
        "table_1": pd.DataFrame(),
    }


def test_debt_market_returns_200(client: TestClient) -> None:
    with patch("psxdata.debt_market", return_value=_make_debt_tables()):
        resp = client.get("/debt-market")
    assert resp.status_code == 200
    body = resp.json()
    assert "table_0" in body["data"]
    assert "table_1" in body["data"]
    assert body["data"]["table_0"][0]["security_code"] == "P01GIS080227"
    assert "timestamp" in body["meta"]
    assert "count" not in body["meta"]


def test_debt_market_serializes_timestamps(client: TestClient) -> None:
    with patch("psxdata.debt_market", return_value=_make_debt_tables()):
        resp = client.get("/debt-market")
    assert resp.json()["data"]["table_0"][0]["maturity_date"] == "2027-02-08"


def test_debt_market_empty_table_returns_empty_list(client: TestClient) -> None:
    with patch("psxdata.debt_market", return_value={"table_0": pd.DataFrame()}):
        resp = client.get("/debt-market")
    assert resp.status_code == 200
    assert resp.json()["data"]["table_0"] == []


def test_debt_market_psx_unavailable_returns_503(client: TestClient) -> None:
    with patch("psxdata.debt_market", side_effect=PSXUnavailableError("PSX down")):
        resp = client.get("/debt-market")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "psx_unavailable"


def test_eligible_scrips_returns_200(client: TestClient) -> None:
    tables = {"table_0": pd.DataFrame({"symbol": ["ENGRO"], "name": ["Engro Corp"]})}
    with patch("psxdata.eligible_scrips", return_value=tables):
        resp = client.get("/eligible-scrips")
    assert resp.status_code == 200
    body = resp.json()
    assert "table_0" in body["data"]
    assert body["data"]["table_0"][0]["symbol"] == "ENGRO"


def test_eligible_scrips_psx_unavailable_returns_503(client: TestClient) -> None:
    with patch("psxdata.eligible_scrips", side_effect=PSXUnavailableError("PSX down")):
        resp = client.get("/eligible-scrips")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "psx_unavailable"
