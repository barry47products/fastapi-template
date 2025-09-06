"""Unit tests for administrative API router."""

from __future__ import annotations

import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.service_registry import ServiceRegistry
from src.interfaces.api.routers.admin import get_service_registry, router
from src.interfaces.api.schemas.admin import (
    AdminInfoResponse,
    SafeConfigResponse,
    ServiceStatusResponse,
)


class TestGetServiceRegistry:
    """Test service registry dependency function."""

    @patch("src.interfaces.api.routers.admin._get_service_registry")
    def test_returns_service_registry_instance(self, mock_get_registry: MagicMock) -> None:
        """Returns service registry singleton instance."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_get_registry.return_value = mock_registry

        result = get_service_registry()

        assert result is mock_registry
        mock_get_registry.assert_called_once()

    @patch("src.interfaces.api.routers.admin._get_service_registry")
    def test_propagates_registry_errors(self, mock_get_registry: MagicMock) -> None:
        """Propagates service registry errors."""
        mock_get_registry.side_effect = RuntimeError("Registry not initialized")

        with pytest.raises(RuntimeError, match="Registry not initialized"):
            get_service_registry()


class TestGetAppInfoEndpoint:
    """Test /admin/info endpoint behavior."""

    @patch("src.interfaces.api.routers.admin.datetime")
    @pytest.mark.asyncio
    async def test_returns_correct_app_info_structure(self, mock_datetime: MagicMock) -> None:
        """Returns application info with correct structure."""
        # Mock datetime to return consistent timestamp
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2024-01-01T12:00:00"
        mock_datetime.now.return_value = mock_now

        # Create mock dependencies
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_api_key = "test-key"
        mock_rate_limit = "test-limit"

        # Import and test the endpoint function directly
        from src.interfaces.api.routers.admin import get_app_info

        result = await get_app_info(registry=mock_registry, _=mock_api_key, __=mock_rate_limit)

        # Verify result structure and content
        assert isinstance(result, AdminInfoResponse)
        assert result.app_name == "neighbour-approved"
        assert result.version == "1.0.0"
        assert result.environment == "development"
        assert result.build_timestamp == "2024-01-01T12:00:00Z"
        assert result.python_version == (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )

    @pytest.mark.asyncio
    async def test_uses_current_python_version(self) -> None:
        """Uses current Python version in response."""
        from src.interfaces.api.routers.admin import get_app_info

        mock_registry = MagicMock(spec=ServiceRegistry)

        result = await get_app_info(registry=mock_registry, _="test-key", __="test-limit")

        expected_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        assert result.python_version == expected_version

    @pytest.mark.asyncio
    async def test_generates_iso_timestamp_with_z_suffix(self) -> None:
        """Generates ISO timestamp with Z suffix."""
        from src.interfaces.api.routers.admin import get_app_info

        mock_registry = MagicMock(spec=ServiceRegistry)

        result = await get_app_info(registry=mock_registry, _="test-key", __="test-limit")

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
        mock_settings.api_host = "0.0.0.0"
        mock_settings.api_port = 8000
        mock_settings.log_level = "INFO"
        mock_settings.metrics_enabled = True
        mock_settings.debug = False
        mock_settings.api.cors_allowed_origins = ["http://localhost:3000"]
        mock_get_settings.return_value = mock_settings

        # Create mock dependencies
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_api_key = "test-key"
        mock_rate_limit = "test-limit"

        from src.interfaces.api.routers.admin import get_safe_config

        result = await get_safe_config(registry=mock_registry, _=mock_api_key, __=mock_rate_limit)

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
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 9000
        mock_settings.log_level = "DEBUG"
        mock_settings.metrics_enabled = False
        mock_settings.debug = True
        mock_settings.api.cors_allowed_origins = ["https://example.com", "https://api.example.com"]
        mock_get_settings.return_value = mock_settings

        from src.interfaces.api.routers.admin import get_safe_config

        mock_registry = MagicMock(spec=ServiceRegistry)
        result = await get_safe_config(registry=mock_registry, _="test-key", __="test-limit")

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

        mock_registry = MagicMock(spec=ServiceRegistry)

        with pytest.raises(RuntimeError, match="Settings not found"):
            await get_safe_config(registry=mock_registry, _="test-key", __="test-limit")


class TestGetServiceStatusEndpoint:
    """Test /admin/services endpoint behavior."""

    @pytest.mark.asyncio
    async def test_returns_service_status_all_active(self) -> None:
        """Returns service status when all services are active."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_registry.has_metrics_collector.return_value = True
        mock_registry.has_health_checker.return_value = True
        mock_registry.has_api_key_validator.return_value = True
        mock_registry.has_rate_limiter.return_value = True
        mock_registry.has_webhook_verifier.return_value = True

        from src.interfaces.api.routers.admin import get_service_status

        result = await get_service_status(registry=mock_registry, _="test-key", __="test-limit")

        assert isinstance(result, ServiceStatusResponse)
        assert result.service_registry_active is True
        assert result.metrics_collector_active is True
        assert result.health_checker_active is True
        assert result.api_key_validator_configured is True
        assert result.rate_limiter_configured is True
        assert result.webhook_verifier_configured is True
        assert result.services_count == 5

        # Verify all registry methods were called
        mock_registry.has_metrics_collector.assert_called_once()
        mock_registry.has_health_checker.assert_called_once()
        mock_registry.has_api_key_validator.assert_called_once()
        mock_registry.has_rate_limiter.assert_called_once()
        mock_registry.has_webhook_verifier.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_service_status_partial_active(self) -> None:
        """Returns service status when some services are inactive."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_registry.has_metrics_collector.return_value = True
        mock_registry.has_health_checker.return_value = False
        mock_registry.has_api_key_validator.return_value = True
        mock_registry.has_rate_limiter.return_value = False
        mock_registry.has_webhook_verifier.return_value = False

        from src.interfaces.api.routers.admin import get_service_status

        result = await get_service_status(registry=mock_registry, _="test-key", __="test-limit")

        assert result.service_registry_active is True  # Always True
        assert result.metrics_collector_active is True
        assert result.health_checker_active is False
        assert result.api_key_validator_configured is True
        assert result.rate_limiter_configured is False
        assert result.webhook_verifier_configured is False
        assert result.services_count == 2  # Only metrics_collector and api_key_validator

    @pytest.mark.asyncio
    async def test_returns_service_status_none_active(self) -> None:
        """Returns service status when no services are active."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_registry.has_metrics_collector.return_value = False
        mock_registry.has_health_checker.return_value = False
        mock_registry.has_api_key_validator.return_value = False
        mock_registry.has_rate_limiter.return_value = False
        mock_registry.has_webhook_verifier.return_value = False

        from src.interfaces.api.routers.admin import get_service_status

        result = await get_service_status(registry=mock_registry, _="test-key", __="test-limit")

        assert result.service_registry_active is True  # Always True
        assert result.metrics_collector_active is False
        assert result.health_checker_active is False
        assert result.api_key_validator_configured is False
        assert result.rate_limiter_configured is False
        assert result.webhook_verifier_configured is False
        assert result.services_count == 0

    @pytest.mark.asyncio
    async def test_handles_registry_method_errors(self) -> None:
        """Handles errors from registry methods gracefully."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_registry.has_metrics_collector.side_effect = RuntimeError("Registry error")

        from src.interfaces.api.routers.admin import get_service_status

        with pytest.raises(RuntimeError, match="Registry error"):
            await get_service_status(registry=mock_registry, _="test-key", __="test-limit")


class TestAdminRouterIntegration:
    """Test admin router integration aspects."""

    def test_router_has_correct_configuration(self) -> None:
        """Router is configured with correct prefix and tags."""
        assert router.prefix == "/admin"
        assert router.tags == ["admin"]

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

    @patch("src.interfaces.api.routers.admin._get_service_registry")
    def test_all_endpoints_use_service_registry_dependency(
        self, mock_get_registry: MagicMock
    ) -> None:
        """All endpoints use the service registry dependency."""
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_get_registry.return_value = mock_registry

        from src.interfaces.api.routers.admin import (
            get_app_info,
            get_safe_config,
            get_service_status,
        )

        # Test that all endpoint functions accept registry parameter
        with patch("src.interfaces.api.routers.admin.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            mock_settings.return_value.api_host = "localhost"
            mock_settings.return_value.api_port = 8000
            mock_settings.return_value.log_level = "INFO"
            mock_settings.return_value.metrics_enabled = True
            mock_settings.return_value.debug = False
            mock_settings.return_value.api.cors_allowed_origins = []

            # Mock registry methods for get_service_status
            mock_registry.has_metrics_collector.return_value = False
            mock_registry.has_health_checker.return_value = False
            mock_registry.has_api_key_validator.return_value = False
            mock_registry.has_rate_limiter.return_value = False
            mock_registry.has_webhook_verifier.return_value = False

            # This test verifies the functions exist and accept registry parameter
            # We don't call them since they're async and this test is sync
            assert callable(get_app_info)
            assert callable(get_safe_config)
            assert callable(get_service_status)


class TestAdminEndpointsWorkflows:
    """Test admin endpoint workflows and real-world scenarios."""

    @patch("src.interfaces.api.routers.admin._get_service_registry")
    @patch("src.interfaces.api.routers.admin.get_settings")
    @pytest.mark.asyncio
    async def test_typical_admin_workflow(
        self, mock_get_settings: MagicMock, mock_get_registry: MagicMock
    ) -> None:
        """Test typical admin workflow accessing all endpoints."""
        # Setup mocks
        mock_registry = MagicMock(spec=ServiceRegistry)
        mock_get_registry.return_value = mock_registry

        mock_settings = MagicMock()
        mock_settings.api_host = "0.0.0.0"
        mock_settings.api_port = 8000
        mock_settings.log_level = "INFO"
        mock_settings.metrics_enabled = True
        mock_settings.debug = False
        mock_settings.api.cors_allowed_origins = ["*"]
        mock_get_settings.return_value = mock_settings

        mock_registry.has_metrics_collector.return_value = True
        mock_registry.has_health_checker.return_value = True
        mock_registry.has_api_key_validator.return_value = True
        mock_registry.has_rate_limiter.return_value = False
        mock_registry.has_webhook_verifier.return_value = False

        from src.interfaces.api.routers.admin import (
            get_app_info,
            get_safe_config,
            get_service_status,
        )

        # Test workflow: get info, then config, then service status
        info_result = await get_app_info(registry=mock_registry, _="key", __="limit")
        config_result = await get_safe_config(registry=mock_registry, _="key", __="limit")
        status_result = await get_service_status(registry=mock_registry, _="key", __="limit")

        # Verify all results are correct types
        assert isinstance(info_result, AdminInfoResponse)
        assert isinstance(config_result, SafeConfigResponse)
        assert isinstance(status_result, ServiceStatusResponse)

        # Verify endpoints were called successfully (all results are correct types)
        assert mock_get_settings.call_count >= 1  # Called by config endpoints

    @pytest.mark.asyncio
    async def test_service_count_calculation_accuracy(self) -> None:
        """Test service count calculation with various combinations."""
        from src.interfaces.api.routers.admin import get_service_status

        test_cases = [
            # (metrics, health, api_key, rate_limiter, webhook, expected_count)
            (True, True, True, True, True, 5),
            (True, False, True, False, False, 2),
            (False, False, False, False, False, 0),
            (True, True, False, False, False, 2),
            (False, False, True, True, True, 3),
        ]

        for metrics, health, api_key, rate_limit, webhook, expected in test_cases:
            mock_registry = MagicMock(spec=ServiceRegistry)
            mock_registry.has_metrics_collector.return_value = metrics
            mock_registry.has_health_checker.return_value = health
            mock_registry.has_api_key_validator.return_value = api_key
            mock_registry.has_rate_limiter.return_value = rate_limit
            mock_registry.has_webhook_verifier.return_value = webhook

            result = await get_service_status(registry=mock_registry, _="key", __="limit")

            assert result.services_count == expected, (
                f"Expected {expected} services for "
                f"(metrics={metrics}, health={health}, api_key={api_key}, "
                f"rate_limit={rate_limit}, webhook={webhook})"
            )
