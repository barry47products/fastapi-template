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
    "api",
    "feature_flags",
    "observability",
    "persistence",
    "security",
    "ServiceRegistry",
    "get_service_registry",
    "initialize_service_registry",
    "clear_service_registry",
    "initialize_infrastructure",
    "shutdown_infrastructure",
]
