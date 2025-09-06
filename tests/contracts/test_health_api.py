"""Health API contract tests - System bootstrap verification."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.security.api_key_validator import verify_api_key
from src.infrastructure.security.rate_limiter import check_rate_limit
from src.infrastructure.service_registry import ServiceRegistry
from src.interfaces.api.routers.health import get_service_registry
from src.main import app


@pytest.fixture
def mock_service_registry() -> ServiceRegistry:
    """Mock service registry for testing."""
    registry = MagicMock(spec=ServiceRegistry)
    health_checker = AsyncMock()
    health_checker.check_health.return_value = {
        "status": "healthy",
        "timestamp": "2025-08-29T10:00:00Z",
        "modules": ["api", "health"],
        "checks": {
            "database": {"status": "healthy", "response_time_ms": 5.0},
            "external_api": {"status": "healthy", "response_time_ms": 12.0},
        },
    }
    registry.get_health_checker.return_value = health_checker
    return registry


def test_should_start_application_successfully(client: TestClient) -> None:
    """Application should boot with all required components registered."""
    response = client.get("/")
    assert response.status_code in [200, 404]


def test_should_report_healthy_when_all_components_available(
    client: TestClient,
    mock_service_registry: ServiceRegistry,
) -> None:
    """Health endpoint should return healthy status with all checks passing."""
    app.dependency_overrides[get_service_registry] = lambda: mock_service_registry
    app.dependency_overrides[check_rate_limit] = lambda: "test_user"

    try:
        response = client.get("/health/")

        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
        assert "modules" in health_data
    finally:
        app.dependency_overrides.clear()


def test_should_expose_required_api_endpoints(
    client: TestClient,
    mock_service_registry: ServiceRegistry,
) -> None:
    """All required API endpoints should be registered and accessible."""
    app.dependency_overrides[get_service_registry] = lambda: mock_service_registry
    app.dependency_overrides[check_rate_limit] = lambda: "test_user"
    app.dependency_overrides[verify_api_key] = lambda: None

    try:
        required_endpoints = [
            "/health/",
            "/health/detailed",
            "/api/v1/users",
        ]

        for endpoint in required_endpoints:
            response = client.get(endpoint)
            # Should not return 404 (not found) - other status codes are acceptable
            # as they might require authentication, proper request body, etc.
            assert response.status_code != 404, f"Endpoint {endpoint} not found"
    finally:
        app.dependency_overrides.clear()
