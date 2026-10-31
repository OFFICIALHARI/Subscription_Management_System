"""Integration tests for /ready endpoint and database connectivity."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_ready_endpoint_success(client: TestClient) -> None:
    """Verify /ready returns 200 OK when database connectivity is verified."""
    with patch("app.main.check_db_connection", return_value=(True, None)):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"


def test_ready_endpoint_database_failure(client: TestClient) -> None:
    """Verify /ready returns 503 Service Unavailable when database connection fails."""
    with patch("app.main.check_db_connection", return_value=(False, "Connection refused")):
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "unreachable"
        assert data["details"] == "Connection refused"


def test_ready_endpoint_live_database(client: TestClient) -> None:
    """Verify /ready returns 200 OK against the live running PostgreSQL server."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
