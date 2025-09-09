"""Unit tests for administrative API router."""

from __future__ import annotations

import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.interfaces.api.routers.admin import router
from src.interfaces.api.schemas.admin import (
    AdminInfoResponse,
    SafeConfigResponse,
    ServiceStatusResponse,
)


class TestAdminRouter:
    """Test admin router configuration."""

    def test_router_has_correct_configuration(self) -> None:
        """Router is configured with correct prefix and tags."""
        assert router.prefix == "/admin"
        assert router.tags == ["admin"]


class TestGetAppInfoEndpoint:
    """Test /admin/info endpoint behavior."""

    @patch("src.interfaces.api.routers.admin.get_settings")
    @patch("src.interfaces.api.routers.admin.datetime")
    @pytest.mark.asyncio
    async def test_returns_correct_app_info_structure(
        self, mock_datetime: MagicMock, mock_get_settings: MagicMock
    ) -> None:
        """Returns application info with correct structure."""
        # Mock settings
        from config.settings import Environment

        mock_settings = MagicMock()
        mock_settings.app_name = "test-app"
        mock_settings.environment = Environment.DEVELOPMENT
        mock_get_settings.return_value = mock_settings

        # Mock datetime to return consistent timestamp
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2024-01-01T12:00:00"
        mock_datetime.now.return_value = mock_now

        from src.interfaces.api.routers.admin import get_app_info

        result = await get_app_info(_="test-key", __="test-limit")

        # Verify result structure and content
        assert isinstance(result, AdminInfoResponse)
        assert result.app_name == "test-app"
        assert result.version == "1.0.0"
        assert result.environment == "development"
        assert result.build_timestamp == "2024-01-01T12:00:00Z"
        assert result.python_version == (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )

    @patch("src.interfaces.api.routers.admin.get_settings")
    @pytest.mark.asyncio
    async def test_uses_current_python_version(self, mock_get_settings: MagicMock) -> None:
        """Uses current Python version in response."""
        from config.settings import Environment

        mock_settings = MagicMock()
        mock_settings.app_name = "test-app"
        mock_settings.environment = Environment.DEVELOPMENT
        mock_get_settings.return_value = mock_settings

        from src.interfaces.api.routers.admin import get_app_info

        result = await get_app_info(_="test-key", __="test-limit")

        expected_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        assert result.python_version == expected_version

    @patch("src.interfaces.api.routers.admin.get_settings")
    @pytest.mark.asyncio
    async def test_generates_iso_timestamp_with_z_suffix(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Generates ISO timestamp with Z suffix."""
        from config.settings import Environment

        mock_settings = MagicMock()
        mock_settings.app_name = "test-app"
        mock_settings.environment = Environment.DEVELOPMENT
        mock_get_settings.return_value = mock_settings

        from src.interfaces.api.routers.admin import get_app_info

        result = await get_app_info(_="test-key", __="test-limit")

        # Verify timestamp format
        assert result.build_timestamp.endswith("Z")
        assert "T" in result.build_timestamp
        # Should be parsable as ISO format
        datetime.fromisoformat(result.build_timestamp.rstrip("Z"))


class TestGetSafeConfigEndpoint:
    """Test /admin/config endpoint behavior."""

    @patch("src.interfaces.api.routers.admin.get_settings")
    @pytest.mark.asyncio
    async def test_returns_safe_config_without_secrets(self, mock_get_settings: MagicMock) -> None:
        """Returns safe configuration without sensitive information."""
        # Mock settings object
        mock_settings = MagicMock()
        mock_settings.api.host = "0.0.0.0"
        mock_settings.api.port = 8000
        mock_settings.observability.log_level = "INFO"
        mock_settings.observability.metrics_enabled = True
        mock_settings.is_development.return_value = False
        mock_settings.security.cors_origins = ["http://localhost:3000"]
        mock_get_settings.return_value = mock_settings

        from src.interfaces.api.routers.admin import get_safe_config

        result = await get_safe_config(_="test-key", __="test-limit")

        # Verify result structure and content
        assert isinstance(result, SafeConfigResponse)
        assert result.api_host == "0.0.0.0"
        assert result.api_port == 8000
        assert result.log_level == "INFO"
        assert result.metrics_enabled is True
        assert result.debug_mode is False
        assert result.cors_origins == ["http://localhost:3000"]

        # Verify settings was called
        mock_get_settings.assert_called_once()

    @patch("src.interfaces.api.routers.admin.get_settings")
    @pytest.mark.asyncio
    async def test_handles_different_config_values(self, mock_get_settings: MagicMock) -> None:
        """Handles different configuration values correctly."""
        mock_settings = MagicMock()
        mock_settings.api.host = "127.0.0.1"
        mock_settings.api.port = 9000
        mock_settings.observability.log_level = "DEBUG"
        mock_settings.observability.metrics_enabled = False
        mock_settings.is_development.return_value = True
        mock_settings.security.cors_origins = ["https://example.com", "https://api.example.com"]
        mock_get_settings.return_value = mock_settings

        from src.interfaces.api.routers.admin import get_safe_config

        result = await get_safe_config(_="test-key", __="test-limit")

        assert result.api_host == "127.0.0.1"
        assert result.api_port == 9000
        assert result.log_level == "DEBUG"
        assert result.metrics_enabled is False
        assert result.debug_mode is True
        assert result.cors_origins == ["https://example.com", "https://api.example.com"]

    @patch("src.interfaces.api.routers.admin.get_settings")
    @pytest.mark.asyncio
    async def test_propagates_settings_errors(self, mock_get_settings: MagicMock) -> None:
        """Propagates settings loading errors."""
        mock_get_settings.side_effect = RuntimeError("Settings not found")

        from src.interfaces.api.routers.admin import get_safe_config

        with pytest.raises(RuntimeError, match="Settings not found"):
            await get_safe_config(_="test-key", __="test-limit")


class TestGetServiceStatusEndpoint:
    """Test /admin/services endpoint behavior."""

    @patch("src.interfaces.api.routers.admin.get_health_checker")
    @patch("src.interfaces.api.routers.admin.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_returns_service_status_all_active(
        self, mock_get_metrics: MagicMock, mock_get_health: MagicMock
    ) -> None:
        """Returns service status when all services are active."""
        # Mock successful dependency retrieval
        mock_get_metrics.return_value = MagicMock()
        mock_get_health.return_value = MagicMock()

        from src.interfaces.api.routers.admin import get_service_status

        result = await get_service_status(_="test-key", __="test-limit")

        assert isinstance(result, ServiceStatusResponse)
        assert result.service_registry_active is True
        assert result.metrics_collector_active is True
        assert result.health_checker_active is True
        assert result.api_key_validator_configured is True
        assert result.rate_limiter_configured is True
        assert result.webhook_verifier_configured is True
        assert result.services_count == 5

        # Verify dependency functions were called
        mock_get_metrics.assert_called_once()
        mock_get_health.assert_called_once()

    @patch("src.interfaces.api.routers.admin.get_health_checker")
    @patch("src.interfaces.api.routers.admin.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_returns_service_status_partial_active(
        self, mock_get_metrics: MagicMock, mock_get_health: MagicMock
    ) -> None:
        """Returns service status when some services are inactive."""
        # Mock metrics collector succeeding, health checker failing
        mock_get_metrics.return_value = MagicMock()
        mock_get_health.side_effect = Exception("Health checker not available")

        from src.interfaces.api.routers.admin import get_service_status

        result = await get_service_status(_="test-key", __="test-limit")

        assert result.service_registry_active is True  # Dependencies are active
        assert result.metrics_collector_active is True
        assert result.health_checker_active is False
        assert result.api_key_validator_configured is True
        assert result.rate_limiter_configured is True
        assert result.webhook_verifier_configured is True
        assert result.services_count == 4  # health_checker is inactive

    @patch("src.interfaces.api.routers.admin.get_health_checker")
    @patch("src.interfaces.api.routers.admin.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_returns_service_status_none_active(
        self, mock_get_metrics: MagicMock, mock_get_health: MagicMock
    ) -> None:
        """Returns service status when core services are inactive."""
        # Mock both core services failing
        mock_get_metrics.side_effect = Exception("Metrics not available")
        mock_get_health.side_effect = Exception("Health checker not available")

        from src.interfaces.api.routers.admin import get_service_status

        result = await get_service_status(_="test-key", __="test-limit")

        assert result.service_registry_active is True  # Dependencies are active
        assert result.metrics_collector_active is False
        assert result.health_checker_active is False
        assert result.api_key_validator_configured is True
        assert result.rate_limiter_configured is True
        assert result.webhook_verifier_configured is True
        assert result.services_count == 3  # Only settings-based services


class TestAdminRouterIntegration:
    """Test admin router integration aspects."""

    def test_all_endpoints_have_security_dependencies(self) -> None:
        """All endpoints require API key and rate limiting."""
        # Get all routes from the router
        routes = [route for route in router.routes if hasattr(route, "dependant")]

        # Verify we have the expected number of routes
        assert len(routes) == 3  # info, config, services

        for route in routes:
            if hasattr(route, "dependant") and route.dependant:
                # Check that security dependencies are present
                dependency_names = [
                    dep.call.__name__ if hasattr(dep.call, "__name__") else str(dep.call)
                    for dep in route.dependant.dependencies
                ]

                # Should have verify_api_key and check_rate_limit dependencies
                has_api_key_dep = any("verify_api_key" in name for name in dependency_names)
                has_rate_limit_dep = any("check_rate_limit" in name for name in dependency_names)

                route_path = getattr(route, "path", "unknown")
                assert has_api_key_dep, f"Route {route_path} missing API key dependency"
                assert has_rate_limit_dep, f"Route {route_path} missing rate limit dependency"

    @patch("src.interfaces.api.routers.admin.get_health_checker")
    @patch("src.interfaces.api.routers.admin.get_metrics_collector")
    @patch("src.interfaces.api.routers.admin.get_settings")
    @pytest.mark.asyncio
    async def test_typical_admin_workflow(
        self, mock_get_settings: MagicMock, mock_get_metrics: MagicMock, mock_get_health: MagicMock
    ) -> None:
        """Test typical admin workflow accessing all endpoints."""
        # Setup mocks
        from config.settings import Environment

        mock_settings = MagicMock()
        mock_settings.app_name = "test-app"
        mock_settings.environment = Environment.DEVELOPMENT
        mock_settings.api.host = "0.0.0.0"
        mock_settings.api.port = 8000
        mock_settings.observability.log_level = "INFO"
        mock_settings.observability.metrics_enabled = True
        mock_settings.is_development.return_value = False
        mock_settings.security.cors_origins = ["*"]
        mock_get_settings.return_value = mock_settings

        mock_get_metrics.return_value = MagicMock()
        mock_get_health.return_value = MagicMock()

        from src.interfaces.api.routers.admin import (
            get_app_info,
            get_safe_config,
            get_service_status,
        )

        # Test workflow: get info, then config, then service status
        info_result = await get_app_info(_="key", __="limit")
        config_result = await get_safe_config(_="key", __="limit")
        status_result = await get_service_status(_="key", __="limit")

        # Verify all results are correct types
        assert isinstance(info_result, AdminInfoResponse)
        assert isinstance(config_result, SafeConfigResponse)
        assert isinstance(status_result, ServiceStatusResponse)

        # Verify endpoints were called successfully (all results are correct types)
        assert mock_get_settings.call_count >= 1  # Called by config endpoints
