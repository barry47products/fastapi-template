"""Unit tests for health checker observability component."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.observability.health_checker import (
    HealthChecker,
    HealthCheckError,
    HealthStatus,
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
        checker = HealthChecker(timeout=0.05)  # 50ms timeout

        async def slow_check() -> bool:
            await asyncio.sleep(0.1)  # 100ms > 50ms timeout
            return True

        checker.register_health_check("slow_service", slow_check)

        result = await checker.check_health()

        assert result["status"] == HealthStatus.UNHEALTHY
        assert result["checks"]["slow_service"]["status"] == HealthStatus.UNHEALTHY
        assert "timed out after 0.05s" in result["checks"]["slow_service"]["error"]

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


class TestConfigureHealthChecker:
    """Test health checker configuration function."""

    def test_configuration_is_backward_compatible(self) -> None:
        """Configuration function is maintained for backward compatibility."""
        # Should not raise any exceptions
        configure_health_checker(timeout=25)


class TestGetHealthChecker:
    """Test get health checker dependency injection pattern."""

    def test_creates_new_instance_with_default_timeout(self) -> None:
        """Creates new HealthChecker instance with default timeout from dependencies."""
        result = get_health_checker()

        assert isinstance(result, HealthChecker)
        assert result.timeout == 5.0  # Default timeout from settings

    def test_returns_singleton_instance(self) -> None:
        """Returns same instance on multiple calls (cached)."""
        checker1 = get_health_checker()
        checker2 = get_health_checker()

        assert checker1 is checker2


class TestCheckSystemHealth:
    """Test check system health FastAPI dependency function."""

    @pytest.mark.asyncio
    async def test_calls_health_checker_check_health(self) -> None:
        """Calls health checker check_health method and returns expected structure."""
        result = await check_system_health()

        assert result["status"] == HealthStatus.HEALTHY
        assert "checks" in result
        assert "timestamp" in result
