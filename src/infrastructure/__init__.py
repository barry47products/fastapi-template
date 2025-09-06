"""Infrastructure modules for the application."""

# Use lazy imports to avoid circular dependencies
# The observability module is imported by domain, so we need to be careful
from . import observability  # Import this first as it has no domain dependencies
from . import api, feature_flags, persistence, security
from .initialization import initialize_infrastructure, shutdown_infrastructure
from .service_registry import (
    clear_service_registry,
    get_service_registry,
    initialize_service_registry,
    ServiceRegistry,
)

__all__ = [
    "ServiceRegistry",
    "api",
    "clear_service_registry",
    "feature_flags",
    "get_service_registry",
    "initialize_infrastructure",
    "initialize_service_registry",
    "observability",
    "persistence",
    "security",
    "shutdown_infrastructure",
]
