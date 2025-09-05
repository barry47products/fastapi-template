"""Health checking system for application monitoring and Kubernetes probes."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, UTC
from enum import Enum
from typing import Any

from src.infrastructure.observability.logger import get_logger
from src.infrastructure.observability.metrics import get_metrics_collector
from src.shared.exceptions import NeighbourApprovedError


class HealthStatus(str, Enum):
    """Health status enumeration for component and system health."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthCheckError(NeighbourApprovedError):
    """
    Exception raised when health check operations fail or configuration is invalid.
    """

    error_code: str = "HEALTH_CHECK_ERROR"


class HealthChecker:
    """Component health monitoring system for application observability."""

    def __init__(self, timeout: int) -> None:
        """Initialize health checker with configuration.

        Args:
            timeout: Maximum time in seconds to wait for health checks

        Raises:
            HealthCheckError: If timeout is invalid
        """
        if timeout <= 0:
            raise HealthCheckError("Timeout must be positive")

        self.timeout = timeout
        self._health_checks: dict[str, Callable[[], Awaitable[bool]]] = {}

    def register_health_check(
        self,
        name: str,
        check_func: Callable[[], Awaitable[bool]],
    ) -> None:
        """Register a health check function.

        Args:
            name: Unique name for the health check
            check_func: Async function that returns True if healthy

        Raises:
            HealthCheckError: If check already registered
        """
        if name in self._health_checks:
            raise HealthCheckError(f"Health check '{name}' already registered")

        self._health_checks[name] = check_func

    async def check_health(self) -> dict[str, Any]:
        """Perform all registered health checks.

        Returns:
            Dictionary with overall status and individual check results
        """
        logger = get_logger(__name__)
        metrics_collector = get_metrics_collector()

        # Record timestamp
        timestamp = datetime.now(UTC).isoformat()

        # If no checks registered, system is healthy
        if not self._health_checks:
            logger.info("Health check completed - no checks registered")
            return {
                "status": HealthStatus.HEALTHY,
                "checks": {},
                "timestamp": timestamp,
            }

        check_results = {}
        healthy_count = 0

        # Run all health checks
        for name, check_func in self._health_checks.items():
            start_time = time.time()

            try:
                # Run check with timeout
                result = await asyncio.wait_for(check_func(), timeout=self.timeout)
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

                if result:
                    check_results[name] = {
                        "status": HealthStatus.HEALTHY,
                        "response_time_ms": response_time,
                    }
                    healthy_count += 1
                    logger.debug(
                        "Health check passed",
                        component=name,
                        response_time_ms=response_time,
                    )
                else:
                    check_results[name] = {
                        "status": HealthStatus.UNHEALTHY,
                        "response_time_ms": response_time,
                        "error": "Health check returned false",
                    }
                    logger.warning(
                        "Health check failed",
                        component=name,
                        response_time_ms=response_time,
                    )

            except TimeoutError:
                response_time = (time.time() - start_time) * 1000
                check_results[name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "response_time_ms": response_time,
                    "error": f"Health check timed out after {self.timeout}s",
                }
                logger.warning(
                    "Health check timed out",
                    component=name,
                    timeout_seconds=self.timeout,
                )

            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                check_results[name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "response_time_ms": response_time,
                    "error": str(e),
                }
                logger.error(
                    "Health check failed with exception",
                    component=name,
                    error=str(e),
                )

        # Determine overall system status
        total_checks = len(self._health_checks)
        if healthy_count == total_checks:
            overall_status = HealthStatus.HEALTHY
        elif healthy_count == 0:
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED

        # Record metrics
        metrics_collector.increment_counter(
            "health_checks_completed_total",
            {"status": overall_status.value},
        )

        logger.info(
            "Health check completed",
            status=overall_status.value,
            healthy_count=healthy_count,
            total_count=total_checks,
        )

        return {
            "status": overall_status,
            "checks": check_results,
            "timestamp": timestamp,
        }


class _HealthCheckerSingleton:
    """Singleton for health checker configuration."""

    _instance: HealthChecker | None = None

    @classmethod
    def set_instance(cls, checker: HealthChecker) -> None:
        """Set the singleton health checker instance."""
        cls._instance = checker

    @classmethod
    def get_instance(cls) -> HealthChecker:
        """Get the singleton health checker instance.

        Returns:
            Health checker instance

        Raises:
            HealthCheckError: If health checker not configured
        """
        if cls._instance is None:
            raise HealthCheckError("Health checker not configured")
        return cls._instance


def configure_health_checker(timeout: int) -> None:
    """Configure the health checker with timeout.

    Args:
        timeout: Maximum time in seconds to wait for health checks
    """
    checker = HealthChecker(timeout=timeout)

    # Register with service registry (primary method)
    try:
        from src.infrastructure.service_registry import get_service_registry

        service_registry = get_service_registry()
        service_registry.register_health_checker(checker)
    except Exception:
        # Service registry might not be initialized yet
        pass

    # Also set in singleton for backward compatibility during transition
    _HealthCheckerSingleton.set_instance(checker)


def get_health_checker() -> HealthChecker:
    """Get the configured health checker instance via service registry.

    Returns:
        Configured health checker

    Raises:
        HealthCheckError: If health checker not configured
    """
    # Try to get from service registry first (new DI pattern)
    try:
        from src.infrastructure.service_registry import get_service_registry

        service_registry = get_service_registry()
        if service_registry.has_health_checker():
            return service_registry.get_health_checker()
    except Exception:
        # Fall back to singleton pattern for backward compatibility
        pass

    # Fallback to singleton for backward compatibility during transition
    return _HealthCheckerSingleton.get_instance()


async def check_system_health() -> dict[str, Any]:
    """FastAPI dependency function for system health checking.

    Returns:
        System health status with component details

    Raises:
        HealthCheckError: If health checker not configured
    """
    checker = get_health_checker()
    return await checker.check_health()
