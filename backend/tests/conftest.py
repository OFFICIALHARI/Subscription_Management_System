"""Test suite configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Test client fixture for invoking FastAPI endpoints."""
    with TestClient(app) as test_client:
        yield test_client
