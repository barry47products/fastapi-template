"""Health check dependencies for API endpoints."""

from typing import TYPE_CHECKING

from fastapi import Depends

from src.infrastructure.service_registry import get_service_registry, ServiceRegistry

if TYPE_CHECKING:
    from src.infrastructure.observability.health_checker import HealthChecker


def get_service_registry_dependency() -> ServiceRegistry:
    """Get service registry singleton instance."""
    return get_service_registry()


def get_health_checker(
    registry: ServiceRegistry = Depends(get_service_registry_dependency),
) -> "HealthChecker":
    """Dependency to get health checker service from registry."""
    return registry.get_health_checker()
