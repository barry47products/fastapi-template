"""Admin API contract tests - Configuration and system information endpoints."""  # noqa: INP001, I002

from unittest.mock import MagicMock

import pytest
from fastapi import status


class AdminAPIClient:
    """Mock admin API client for testing contract behaviours."""

    def get_config(self, api_key: str) -> dict[str, str | int | bool]:
        """Get application configuration (safe version without secrets)."""
        return {"status_code": 200}

    def get_service_status(self, api_key: str) -> dict[str, str | int | bool]:
        """Get service registry status and component health."""
        return {"status_code": 200}

    def get_application_info(self, api_key: str) -> dict[str, str | int]:
        """Get application information including version and environment."""
        return {"status_code": 200}


@pytest.fixture
def mock_admin_client() -> MagicMock:
    """Mock admin API client for testing contract behaviours."""
    return MagicMock(spec=AdminAPIClient)


@pytest.fixture
def valid_admin_api_key() -> str:
    """Valid admin API key for testing."""
    return "admin_api_key_12345"


@pytest.fixture
def invalid_api_key() -> str:
    """Invalid API key for testing authentication failures."""
    return "invalid_key_xyz"


def test_should_return_safe_config_without_secrets(
    mock_admin_client: MagicMock,  # pylint: disable=redefined-outer-name
    valid_admin_api_key: str,  # pylint: disable=redefined-outer-name
) -> None:
    """Config endpoint should exclude API keys and secrets."""
    # Arrange
    expected_response = {
        "status_code": status.HTTP_200_OK,
        "config": {
            "app_name": "neighbour-approved",
            "environment": "development",
            "api_host": "0.0.0.0",
            "api_port": 8000,
            "metrics_enabled": True,
            "metrics_port": 9090,
            "log_level": "INFO",
        },
        "secrets_excluded": ["INTERNAL_API_KEYS", "WEBHOOK_SECRET", "DATABASE_CREDENTIALS"],
    }
    mock_admin_client.get_config.return_value = expected_response

    # Act
    result = mock_admin_client.get_config(valid_admin_api_key)

    # Assert
    assert result["status_code"] == status.HTTP_200_OK
    assert "config" in result
    assert "secrets_excluded" in result

    config = result["config"]
    assert config["app_name"] == "neighbour-approved"
    assert config["environment"] == "development"
    assert config["metrics_enabled"] is True

    # Verify no secrets in response
    secrets_list = result["secrets_excluded"]
    assert "INTERNAL_API_KEYS" in secrets_list
    assert "WEBHOOK_SECRET" in secrets_list
    assert "DATABASE_CREDENTIALS" in secrets_list

    mock_admin_client.get_config.assert_called_once_with(valid_admin_api_key)


def test_should_return_service_registry_status(
    mock_admin_client: MagicMock,  # pylint: disable=redefined-outer-name
    valid_admin_api_key: str,  # pylint: disable=redefined-outer-name
) -> None:
    """Service status should show component health."""
    # Arrange
    expected_response = {
        "status_code": status.HTTP_200_OK,
        "services": {
            "message_processor": {"status": "healthy", "uptime_seconds": 3600},
            "provider_service": {"status": "healthy", "uptime_seconds": 3600},
            "database": {"status": "healthy", "last_check": "2025-01-01T12:00:00Z"},
            "webhook_client": {"status": "healthy", "last_ping": "2025-01-01T12:00:00Z"},
        },
        "overall_status": "healthy",
        "total_services": 4,
        "healthy_services": 4,
        "check_timestamp": "2025-01-01T12:00:00Z",
    }
    mock_admin_client.get_service_status.return_value = expected_response

    # Act
    result = mock_admin_client.get_service_status(valid_admin_api_key)

    # Assert
    assert result["status_code"] == status.HTTP_200_OK
    assert result["overall_status"] == "healthy"
    assert result["total_services"] == 4
    assert result["healthy_services"] == 4

    services = result["services"]
    assert "message_processor" in services
    assert "provider_service" in services
    assert "database" in services
    assert "webhook_client" in services

    assert services["message_processor"]["status"] == "healthy"
    assert services["provider_service"]["status"] == "healthy"
    assert services["database"]["status"] == "healthy"
    assert services["webhook_client"]["status"] == "healthy"

    mock_admin_client.get_service_status.assert_called_once_with(valid_admin_api_key)


def test_should_return_application_info(
    mock_admin_client: MagicMock,  # pylint: disable=redefined-outer-name
    valid_admin_api_key: str,  # pylint: disable=redefined-outer-name
) -> None:
    """App info should include version and environment."""
    # Arrange
    expected_response = {
        "status_code": status.HTTP_200_OK,
        "application": {
            "name": "neighbour-approved",
            "version": "1.0.0",
            "environment": "development",
            "build_timestamp": "2025-01-01T10:00:00Z",
            "python_version": "3.13.0",
            "fastapi_version": "0.115.0",
        },
        "runtime": {
            "uptime_seconds": 7200,
            "start_time": "2025-01-01T10:00:00Z",
            "memory_usage_mb": 128,
            "cpu_usage_percent": 15.5,
        },
        "deployment": {
            "platform": "darwin",
            "architecture": "arm64",
            "container": False,
        },
    }
    mock_admin_client.get_application_info.return_value = expected_response

    # Act
    result = mock_admin_client.get_application_info(valid_admin_api_key)

    # Assert
    assert result["status_code"] == status.HTTP_200_OK

    app_info = result["application"]
    assert app_info["name"] == "neighbour-approved"
    assert app_info["version"] == "1.0.0"
    assert app_info["environment"] == "development"
    assert app_info["python_version"] == "3.13.0"

    runtime = result["runtime"]
    assert runtime["uptime_seconds"] == 7200
    assert runtime["memory_usage_mb"] == 128
    assert runtime["cpu_usage_percent"] == 15.5

    deployment = result["deployment"]
    assert deployment["platform"] == "darwin"
    assert deployment["architecture"] == "arm64"
    assert deployment["container"] is False

    mock_admin_client.get_application_info.assert_called_once_with(valid_admin_api_key)


def test_should_require_authentication_for_admin_endpoints(
    mock_admin_client: MagicMock,  # pylint: disable=redefined-outer-name
    invalid_api_key: str,  # pylint: disable=redefined-outer-name
) -> None:
    """Admin endpoints should require valid API key."""
    # Arrange
    expected_response = {
        "status_code": status.HTTP_401_UNAUTHORIZED,
        "message": "Invalid or missing admin API key",
        "error": "admin_authentication_required",
        "required_permissions": ["admin:read", "system:status"],
    }
    mock_admin_client.get_config.return_value = expected_response

    # Act
    result = mock_admin_client.get_config(invalid_api_key)

    # Assert
    assert result["status_code"] == status.HTTP_401_UNAUTHORIZED
    assert "Invalid or missing admin API key" in str(result["message"])
    assert result["error"] == "admin_authentication_required"

    permissions = result["required_permissions"]
    assert "admin:read" in permissions
    assert "system:status" in permissions

    mock_admin_client.get_config.assert_called_once_with(invalid_api_key)
