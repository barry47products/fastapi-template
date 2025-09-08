"""Infrastructure modules for the application."""

# Use lazy imports to avoid circular dependencies
# The observability module is imported by domain, so we need to be careful
from __future__ import annotations

from . import (
    api,
    dependencies,
    feature_flags,
    observability,  # Import this first as it has no domain dependencies
    persistence,
    security,
)
from .initialization import initialize_infrastructure, shutdown_infrastructure

__all__ = [
    "api",
    "dependencies",
    "feature_flags",
    "initialize_infrastructure",
    "observability",
    "persistence",
    "security",
    "shutdown_infrastructure",
]
