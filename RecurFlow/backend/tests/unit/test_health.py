"""Unit tests for service health, configuration, and security validations."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import validate_password_strength


def test_health_endpoint(client: TestClient) -> None:
    """Verify /health returns 200 OK and expected process status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "RecurFlow"
    assert "environment" in data


def test_password_policy_enforcement() -> None:
    """Verify password policy enforces >8 chars, upper, lower, and special/digit."""
    # Too short (<= 8 chars)
    is_valid, err = validate_password_strength("Ab1!")
    assert not is_valid
    assert "longer than 8 characters" in err

    # Exactly 8 chars (fails)
    is_valid, err = validate_password_strength("Abcdef1!")
    assert not is_valid
    assert "longer than 8 characters" in err

    # Missing uppercase
    is_valid, err = validate_password_strength("password123!")
    assert not is_valid
    assert "uppercase" in err

    # Missing lowercase
    is_valid, err = validate_password_strength("PASSWORD123!")
    assert not is_valid
    assert "lowercase" in err

    # Missing special character or digit
    is_valid, err = validate_password_strength("PasswordOnly")
    assert not is_valid
    assert "special character or digit" in err

    # Valid password (9+ chars, upper, lower, special)
    is_valid, err = validate_password_strength("SuperSecret1!")
    assert is_valid
    assert err is None


def test_cors_origin_parsing() -> None:
    """Verify CORS origin string is split into clean list of URLs."""
    s = Settings(CORS_ORIGINS="http://localhost:5173, http://127.0.0.1:5173")
    assert s.CORS_ORIGINS == ["http://localhost:5173", "http://127.0.0.1:5173"]
