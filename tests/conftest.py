"""Test configuration for behaviour-driven tests."""  # noqa: I002

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Provide a FastAPI test client with proper setup."""
    return TestClient(app)
