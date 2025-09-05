"""Administrative dependencies for API endpoints."""

from src.infrastructure.service_registry import get_service_registry, ServiceRegistry


def get_service_registry_dependency() -> ServiceRegistry:
    """Dependency to get service registry singleton instance."""
    return get_service_registry()
