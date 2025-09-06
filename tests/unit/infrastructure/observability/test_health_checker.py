"""Unit tests for health checker observability component."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.observability.health_checker import (
    HealthChecker,
    HealthCheckError,
    HealthStatus,
    _HealthCheckerSingleton,
    check_system_health,
    configure_health_checker,
    get_health_checker,
)


class TestHealthStatus:
    """Test health status enumeration."""

    def test_has_correct_values(self) -> None:
        """Has correct health status values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.DEGRADED.value == "degraded"

    def test_is_string_enum(self) -> None:
        """Is string enumeration for JSON serialization."""
        assert isinstance(HealthStatus.HEALTHY, str)
        assert isinstance(HealthStatus.UNHEALTHY, str)
        assert isinstance(HealthStatus.DEGRADED, str)


class TestHealthCheckError:
    """Test health check error exception."""

    def test_creates_error_with_message(self) -> None:
        """Creates error with message."""
        error = HealthCheckError("Health check failed")

        assert str(error) == "Health check failed"
        assert error.message == "Health check failed"
        assert error.error_code == "HEALTH_CHECK_ERROR"

    def test_inherits_from_application_error(self) -> None:
        """Inherits from ApplicationError."""
        from src.shared.exceptions import ApplicationError

        error = HealthCheckError("Test error")
        assert isinstance(error, ApplicationError)


class TestHealthChecker:
    """Test health checker behavior."""

    def test_creates_checker_with_valid_timeout(self) -> None:
        """Creates checker with valid timeout."""
        checker = HealthChecker(timeout=30)

        assert checker.timeout == 30
        assert checker._health_checks == {}

    def test_raises_error_for_invalid_timeout(self) -> None:
        """Raises error for invalid timeout."""
        with pytest.raises(HealthCheckError, match="Timeout must be positive"):
            HealthChecker(timeout=0)

        with pytest.raises(HealthCheckError, match="Timeout must be positive"):
            HealthChecker(timeout=-5)

    def test_registers_health_check_successfully(self) -> None:
        """Registers health check successfully."""
        checker = HealthChecker(timeout=10)
        check_func = AsyncMock(return_value=True)

        checker.register_health_check("database", check_func)

        assert "database" in checker._health_checks
        assert checker._health_checks["database"] is check_func

    def test_raises_error_for_duplicate_registration(self) -> None:
        """Raises error for duplicate health check registration."""
        checker = HealthChecker(timeout=10)
        check_func = AsyncMock(return_value=True)

        checker.register_health_check("database", check_func)

        with pytest.raises(HealthCheckError, match="Health check 'database' already registered"):
            checker.register_health_check("database", check_func)

    @pytest.mark.asyncio
    async def test_returns_healthy_when_no_checks_registered(self) -> None:
        """Returns healthy status when no checks registered."""
        checker = HealthChecker(timeout=10)

        result = await checker.check_health()

        assert result["status"] == HealthStatus.HEALTHY
        assert result["checks"] == {}
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_runs_single_healthy_check(self) -> None:
        """Runs single healthy check successfully."""
        checker = HealthChecker(timeout=10)
        check_func = AsyncMock(return_value=True)
        checker.register_health_check("database", check_func)

        result = await checker.check_health()

        assert result["status"] == HealthStatus.HEALTHY
        assert "database" in result["checks"]
        assert result["checks"]["database"]["status"] == HealthStatus.HEALTHY
        assert "response_time_ms" in result["checks"]["database"]
        check_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_runs_single_unhealthy_check(self) -> None:
        """Runs single unhealthy check."""
        checker = HealthChecker(timeout=10)
        check_func = AsyncMock(return_value=False)
        checker.register_health_check("cache", check_func)

        result = await checker.check_health()

        assert result["status"] == HealthStatus.UNHEALTHY
        assert result["checks"]["cache"]["status"] == HealthStatus.UNHEALTHY
        assert result["checks"]["cache"]["error"] == "Health check returned false"
        assert "response_time_ms" in result["checks"]["cache"]

    @pytest.mark.asyncio
    async def test_handles_check_timeout(self) -> None:
        """Handles health check timeout."""
        checker = HealthChecker(timeout=1)

        async def slow_check() -> bool:
            await asyncio.sleep(1)  # Longer than timeout
            return True

        checker.register_health_check("slow_service", slow_check)

        result = await checker.check_health()

        assert result["status"] == HealthStatus.UNHEALTHY
        assert result["checks"]["slow_service"]["status"] == HealthStatus.UNHEALTHY
        assert "timed out after 1s" in result["checks"]["slow_service"]["error"]

    @pytest.mark.asyncio
    async def test_handles_check_exception(self) -> None:
        """Handles health check exception."""
        checker = HealthChecker(timeout=10)

        async def failing_check() -> bool:
            raise ValueError("Database connection failed")

        checker.register_health_check("database", failing_check)

        result = await checker.check_health()

        assert result["status"] == HealthStatus.UNHEALTHY
        assert result["checks"]["database"]["status"] == HealthStatus.UNHEALTHY
        assert result["checks"]["database"]["error"] == "Database connection failed"

    @pytest.mark.asyncio
    async def test_determines_overall_status_all_healthy(self) -> None:
        """Determines overall status when all checks healthy."""
        checker = HealthChecker(timeout=10)
        checker.register_health_check("database", AsyncMock(return_value=True))
        checker.register_health_check("cache", AsyncMock(return_value=True))
        checker.register_health_check("queue", AsyncMock(return_value=True))

        result = await checker.check_health()

        assert result["status"] == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_determines_overall_status_all_unhealthy(self) -> None:
        """Determines overall status when all checks unhealthy."""
        checker = HealthChecker(timeout=10)
        checker.register_health_check("database", AsyncMock(return_value=False))
        checker.register_health_check("cache", AsyncMock(return_value=False))

        result = await checker.check_health()

        assert result["status"] == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_determines_overall_status_mixed(self) -> None:
        """Determines overall status when checks are mixed."""
        checker = HealthChecker(timeout=10)
        checker.register_health_check("database", AsyncMock(return_value=True))
        checker.register_health_check("cache", AsyncMock(return_value=False))
        checker.register_health_check("queue", AsyncMock(return_value=True))

        result = await checker.check_health()

        assert result["status"] == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    @patch("src.infrastructure.observability.health_checker.get_logger")
    @patch("src.infrastructure.observability.health_checker.get_metrics_collector")
    async def test_logs_and_records_metrics(
        self, mock_metrics: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Logs health check activity and records metrics."""
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        checker = HealthChecker(timeout=10)
        checker.register_health_check("database", AsyncMock(return_value=True))

        await checker.check_health()

        # Verify logging calls
        mock_logger.assert_called_with("src.infrastructure.observability.health_checker")
        mock_logger_instance.debug.assert_called()
        mock_logger_instance.info.assert_called()

        # Verify metrics recording
        mock_metrics_instance.increment_counter.assert_called_with(
            "health_checks_completed_total", {"status": "healthy"}
        )

    @pytest.mark.asyncio
    async def test_includes_timestamp_in_result(self) -> None:
        """Includes timestamp in health check result."""
        checker = HealthChecker(timeout=10)

        result = await checker.check_health()

        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)
        # Should be ISO format
        assert "T" in result["timestamp"]


class TestHealthCheckerSingleton:
    """Test health checker singleton behavior."""

    def setup_method(self) -> None:
        """Clear singleton before each test."""
        _HealthCheckerSingleton._instance = None

    def teardown_method(self) -> None:
        """Clear singleton after each test."""
        _HealthCheckerSingleton._instance = None

    def test_raises_error_when_not_configured(self) -> None:
        """Raises error when health checker not configured."""
        with pytest.raises(HealthCheckError, match="Health checker not configured"):
            _HealthCheckerSingleton.get_instance()

    def test_returns_configured_instance(self) -> None:
        """Returns configured instance."""
        checker = HealthChecker(timeout=15)
        _HealthCheckerSingleton.set_instance(checker)

        result = _HealthCheckerSingleton.get_instance()
        assert result is checker

    def test_sets_singleton_instance(self) -> None:
        """Sets singleton instance."""
        checker = HealthChecker(timeout=20)

        _HealthCheckerSingleton.set_instance(checker)

        assert _HealthCheckerSingleton._instance is checker


class TestConfigureHealthChecker:
    """Test health checker configuration function."""

    def setup_method(self) -> None:
        """Clear singleton before each test."""
        _HealthCheckerSingleton._instance = None

    def teardown_method(self) -> None:
        """Clear singleton after each test."""
        _HealthCheckerSingleton._instance = None

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_registers_with_service_registry(self, mock_get_registry: MagicMock) -> None:
        """Registers health checker with service registry."""
        mock_registry = MagicMock()
        mock_get_registry.return_value = mock_registry

        configure_health_checker(timeout=25)

        mock_registry.register_health_checker.assert_called_once()
        checker_arg = mock_registry.register_health_checker.call_args[0][0]
        assert isinstance(checker_arg, HealthChecker)
        assert checker_arg.timeout == 25

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_handles_service_registry_import_error(self, mock_get_registry: MagicMock) -> None:
        """Handles service registry import error gracefully."""
        mock_get_registry.side_effect = ImportError("Module not found")

        # Should not raise exception
        configure_health_checker(timeout=30)

        # Should still set singleton
        checker = _HealthCheckerSingleton.get_instance()
        assert checker.timeout == 30

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_handles_service_registry_runtime_error(self, mock_get_registry: MagicMock) -> None:
        """Handles service registry runtime error gracefully."""
        mock_get_registry.side_effect = RuntimeError("Registry not initialized")

        # Should not raise exception
        configure_health_checker(timeout=35)

        # Should still set singleton
        checker = _HealthCheckerSingleton.get_instance()
        assert checker.timeout == 35

    def test_sets_singleton_instance(self) -> None:
        """Sets singleton instance."""
        configure_health_checker(timeout=40)

        checker = _HealthCheckerSingleton.get_instance()
        assert checker.timeout == 40


class TestGetHealthChecker:
    """Test get health checker function."""

    def setup_method(self) -> None:
        """Clear singleton before each test."""
        _HealthCheckerSingleton._instance = None

    def teardown_method(self) -> None:
        """Clear singleton after each test."""
        _HealthCheckerSingleton._instance = None

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_returns_checker_from_service_registry(self, mock_get_registry: MagicMock) -> None:
        """Returns health checker from service registry when available."""
        mock_checker = HealthChecker(timeout=45)
        mock_registry = MagicMock()
        mock_registry.has_health_checker.return_value = True
        mock_registry.get_health_checker.return_value = mock_checker
        mock_get_registry.return_value = mock_registry

        result = get_health_checker()

        assert result is mock_checker
        mock_registry.has_health_checker.assert_called_once()
        mock_registry.get_health_checker.assert_called_once()

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_falls_back_to_singleton_when_registry_unavailable(
        self, mock_get_registry: MagicMock
    ) -> None:
        """Falls back to singleton when service registry unavailable."""
        mock_get_registry.side_effect = ImportError("Registry not available")
        singleton_checker = HealthChecker(timeout=50)
        _HealthCheckerSingleton.set_instance(singleton_checker)

        result = get_health_checker()

        assert result is singleton_checker

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_falls_back_to_singleton_when_checker_not_in_registry(
        self, mock_get_registry: MagicMock
    ) -> None:
        """Falls back to singleton when health checker not in registry."""
        mock_registry = MagicMock()
        mock_registry.has_health_checker.return_value = False
        mock_get_registry.return_value = mock_registry
        singleton_checker = HealthChecker(timeout=55)
        _HealthCheckerSingleton.set_instance(singleton_checker)

        result = get_health_checker()

        assert result is singleton_checker

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_raises_error_when_no_checker_available(self, mock_get_registry: MagicMock) -> None:
        """Raises error when no health checker available."""
        mock_get_registry.side_effect = ImportError("Registry not available")

        with pytest.raises(HealthCheckError, match="Health checker not configured"):
            get_health_checker()


class TestCheckSystemHealth:
    """Test check system health FastAPI dependency function."""

    def setup_method(self) -> None:
        """Clear singleton before each test."""
        _HealthCheckerSingleton._instance = None

    def teardown_method(self) -> None:
        """Clear singleton after each test."""
        _HealthCheckerSingleton._instance = None

    @pytest.mark.asyncio
    async def test_calls_health_checker_check_health(self) -> None:
        """Calls health checker check_health method."""
        checker = HealthChecker(timeout=10)
        _HealthCheckerSingleton.set_instance(checker)

        result = await check_system_health()

        assert result["status"] == HealthStatus.HEALTHY
        assert "checks" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_propagates_health_check_error(self) -> None:
        """Propagates health check error when checker not configured."""
        with pytest.raises(HealthCheckError, match="Health checker not configured"):
            await check_system_health()
