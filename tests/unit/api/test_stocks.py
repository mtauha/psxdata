"""Unit tests for stocks router."""
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from psxdata.exceptions import PSXUnavailableError

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_list_stocks_returns_200(client: TestClient) -> None:
    with patch("psxdata.tickers", return_value=["ENGRO", "LUCK"]):
        resp = client.get("/stocks")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == ["ENGRO", "LUCK"]
    assert body["meta"]["count"] == 2
    assert "timestamp" in body["meta"]


def test_list_stocks_with_index_passes_index_param(client: TestClient) -> None:
    with patch("psxdata.tickers", return_value=["ENGRO"]) as mock_tickers:
        resp = client.get("/stocks?index=KSE100")
    assert resp.status_code == 200
    mock_tickers.assert_called_once_with(index="KSE100")


def test_list_stocks_empty_returns_200(client: TestClient) -> None:
    with patch("psxdata.tickers", return_value=[]):
        resp = client.get("/stocks")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
    assert resp.json()["meta"]["count"] == 0


def test_historical_returns_200_with_data(client: TestClient) -> None:
    df = pd.DataFrame({
        "date": [pd.Timestamp("2024-01-05")],
        "open": [481.99], "high": [496.0], "low": [474.01],
        "close": [485.38], "volume": [4496408], "is_anomaly": [False],
    })
    with patch("psxdata.stocks", return_value=df):
        resp = client.get("/stocks/ENGRO/historical")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["date"] == "2024-01-05"
    assert body["data"][0]["open"] == pytest.approx(481.99)
    assert body["meta"]["count"] == 1


def test_historical_empty_returns_200_not_404(client: TestClient) -> None:
    """Unknown symbol returns 200 with empty list — library cannot distinguish from empty range."""
    with patch("psxdata.stocks", return_value=pd.DataFrame()):
        resp = client.get("/stocks/UNKNOWN/historical")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_historical_passes_date_params(client: TestClient) -> None:
    with patch("psxdata.stocks", return_value=pd.DataFrame()) as mock_stocks:
        client.get("/stocks/ENGRO/historical?start=2024-01-01&end=2024-12-31")
    mock_stocks.assert_called_once_with("ENGRO", start="2024-01-01", end="2024-12-31")


def test_quote_returns_200(client: TestClient) -> None:
    df = pd.DataFrame({"symbol": ["ENGRO"], "price": [481.99]})
    with patch("psxdata.quote", return_value=df):
        resp = client.get("/stocks/ENGRO/quote")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["symbol"] == "ENGRO"
    assert body["data"]["price"] == pytest.approx(481.99)
    assert "timestamp" in body["meta"]
    assert "count" not in body["meta"]


def test_quote_returns_404_for_unknown_symbol(client: TestClient) -> None:
    with patch("psxdata.quote", return_value=pd.DataFrame()):
        resp = client.get("/stocks/FAKE/quote")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "not_found"


def test_fundamentals_returns_200_with_data(client: TestClient) -> None:
    df = pd.DataFrame({
        "symbol": ["ENGRO"], "year": ["2024"], "type": ["Annual"],
        "period_ended": [pd.Timestamp("2024-12-31")],
        "posting_date": [pd.Timestamp("2025-01-15")],
        "document": ["https://psx.com/report.pdf"],
    })
    with patch("psxdata.fundamentals", return_value=df):
        resp = client.get("/stocks/ENGRO/fundamentals")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["period_ended"] == "2024-12-31"
    assert body["data"][0]["posting_date"] == "2025-01-15"


def test_fundamentals_empty_returns_200(client: TestClient) -> None:
    with patch("psxdata.fundamentals", return_value=pd.DataFrame()):
        resp = client.get("/stocks/ENGRO/fundamentals")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_stocks_psx_unavailable_returns_503(client: TestClient) -> None:
    with patch("psxdata.tickers", side_effect=PSXUnavailableError("PSX down")):
        resp = client.get("/stocks")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "psx_unavailable"


def test_stocks_cors_header_present(client: TestClient) -> None:
    with patch("psxdata.tickers", return_value=[]):
        resp = client.get("/stocks", headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" in resp.headers
