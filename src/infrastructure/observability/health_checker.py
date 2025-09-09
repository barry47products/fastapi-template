"""Health checking system for application monitoring and Kubernetes probes."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from src.infrastructure.observability.logger import get_logger
from src.infrastructure.observability.metrics import get_metrics_collector
from src.shared.exceptions import ApplicationError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class HealthStatus(str, Enum):
    """Health status enumeration for component and system health."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthCheckError(ApplicationError):
    """
    Exception raised when health check operations fail or configuration is invalid.
    """

    error_code: str = "HEALTH_CHECK_ERROR"


class HealthChecker:
    """Component health monitoring system with semantic naming for application observability."""

    def __init__(self, timeout: float, application_name: str = "fastapi_template") -> None:
        """Initialize health checker with configuration.

        Args:
            timeout: Maximum time in seconds to wait for health checks
            application_name: Application name for health check context

        Raises:
            HealthCheckError: If timeout is invalid
        """
        if timeout <= 0:
            raise HealthCheckError("Timeout must be positive")

        self.timeout = timeout
        self.application_name = application_name
        self._health_checks: dict[str, Callable[[], Awaitable[bool]]] = {}

    def _get_semantic_check_name(self, name: str) -> str:
        """Get semantic health check name with application context.

        Args:
            name: Base health check name

        Returns:
            Semantic health check name

        Examples:
            "database" -> "fastapi_template_postgresql_primary_connection"
            "cache" -> "fastapi_template_redis_cache_availability"
            "api" -> "fastapi_template_external_api_connectivity"
        """
        # Map common generic names to semantic names
        name_mappings = {
            "database": f"{self.application_name}_postgresql_primary_connection",
            "postgres": f"{self.application_name}_postgresql_primary_connection",
            "postgresql": f"{self.application_name}_postgresql_primary_connection",
            "cache": f"{self.application_name}_redis_cache_availability",
            "redis": f"{self.application_name}_redis_cache_availability",
            "firestore": f"{self.application_name}_firestore_document_store_connectivity",
            "api": f"{self.application_name}_external_api_connectivity",
            "external_api": f"{self.application_name}_external_api_connectivity",
            "queue": f"{self.application_name}_message_queue_connectivity",
            "webhook": f"{self.application_name}_webhook_endpoint_accessibility",
        }

        # Return mapped name or construct semantic name
        return name_mappings.get(name.lower(), f"{self.application_name}_{name}_health_check")

    def register_health_check(
        self,
        name: str,
        check_func: Callable[[], Awaitable[bool]],
        use_semantic_naming: bool = True,
    ) -> str:
        """Register a health check function with semantic naming.

        Args:
            name: Base name for the health check (e.g., "database", "cache")
            check_func: Async function that returns True if healthy
            use_semantic_naming: Whether to use semantic naming (default True)

        Returns:
            The actual health check name that was registered

        Raises:
            HealthCheckError: If check already registered
        """
        # Use semantic naming by default for better observability
        actual_name = self._get_semantic_check_name(name) if use_semantic_naming else name

        if actual_name in self._health_checks:
            raise HealthCheckError(f"Health check '{actual_name}' already registered")

        self._health_checks[actual_name] = check_func
        return actual_name

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

        # Record metrics with semantic naming
        metrics_collector.increment_counter(
            "health_checks_completed_total",
            {
                "status": overall_status.value,
                "checks_total": str(total_checks),
                "checks_healthy": str(healthy_count),
            },
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


def configure_health_checker(timeout: int) -> None:
    """Configure the health checker with timeout.

    This function is kept for backward compatibility during initialization.
    With dependency injection, configuration is handled via get_health_checker().

    Args:
        timeout: Maximum time in seconds to wait for health checks
    """
    # Configuration is now handled via dependency injection
    # This function remains for backward compatibility with initialization code


@lru_cache
def get_health_checker() -> HealthChecker:
    """Get a health checker instance via dependency injection.

    Returns:
        HealthChecker instance with configured timeout and semantic naming (cached)

    Uses settings to determine timeout configuration and application name.
    """
    from config.settings import get_settings

    settings = get_settings()
    app_name = settings.app_name.replace("-", "_").replace(" ", "_").lower()

    return HealthChecker(
        timeout=int(settings.observability.health_check_timeout), application_name=app_name
    )


async def check_system_health() -> dict[str, Any]:
    """FastAPI dependency function for system health checking.

    Returns:
        System health status with component details

    Raises:
        HealthCheckError: If health checker not configured
    """
    checker = get_health_checker()
    return await checker.check_health()
