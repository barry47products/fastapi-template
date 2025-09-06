"""API routers package."""

from . import admin, health, sample_routes

# Expose routers with consistent naming
admin_routes = admin
health_routes = health

__all__ = ["admin_routes", "health_routes", "sample_routes"]
