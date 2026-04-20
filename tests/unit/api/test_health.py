from fastapi.testclient import TestClient

from api.main import app


def test_health_endpoint_returns_expected_contract() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
