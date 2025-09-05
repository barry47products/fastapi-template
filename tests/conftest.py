"""Test configuration for behaviour-driven tests."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Provide a FastAPI test client with proper setup."""
    return TestClient(app)
