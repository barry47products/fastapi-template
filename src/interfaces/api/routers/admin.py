"""Administrative API router for operations and configuration."""

import sys
from datetime import datetime

from fastapi import APIRouter, Depends

from config.settings import get_settings
from src.infrastructure.security import check_rate_limit, verify_api_key
from src.infrastructure.service_registry import get_service_registry as _get_service_registry
from src.infrastructure.service_registry import ServiceRegistry
from src.interfaces.api.schemas import AdminInfoResponse, SafeConfigResponse, ServiceStatusResponse

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


def get_service_registry() -> ServiceRegistry:
    """Dependency to get service registry singleton instance."""
    return _get_service_registry()


@router.get("/info")
async def get_app_info(
    registry: ServiceRegistry = Depends(get_service_registry),
    _: str = Depends(verify_api_key),
    __: str = Depends(check_rate_limit),
) -> AdminInfoResponse:
    """Application metadata including version and environment."""
    return AdminInfoResponse(
        app_name="neighbour-approved",
        version="1.0.0",
        environment="development",
        build_timestamp=datetime.now().isoformat() + "Z",
        python_version=(
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ),
    )


@router.get("/config")
async def get_safe_config(
    registry: ServiceRegistry = Depends(get_service_registry),
    _: str = Depends(verify_api_key),
    __: str = Depends(check_rate_limit),
) -> SafeConfigResponse:
    """Safe configuration display without sensitive information."""
    settings = get_settings()
    return SafeConfigResponse(
        api_host=settings.api_host,
        api_port=settings.api_port,
        log_level=settings.log_level,
        metrics_enabled=settings.metrics_enabled,
        debug_mode=settings.debug,
        cors_origins=settings.api.cors_allowed_origins,
    )


@router.get("/services")
async def get_service_status(
    registry: ServiceRegistry = Depends(get_service_registry),
    _: str = Depends(verify_api_key),
    __: str = Depends(check_rate_limit),
) -> ServiceStatusResponse:
    """Service registry and infrastructure component status."""
    # Check if core services are available using registry methods
    metrics_collector_active = registry.has_metrics_collector()
    health_checker_active = registry.has_health_checker()
    api_key_validator_configured = registry.has_api_key_validator()
    rate_limiter_configured = registry.has_rate_limiter()
    webhook_verifier_configured = registry.has_webhook_verifier()

    # Count registered services
    services_count = (
        int(metrics_collector_active)
        + int(health_checker_active)
        + int(api_key_validator_configured)
        + int(rate_limiter_configured)
        + int(webhook_verifier_configured)
    )

    return ServiceStatusResponse(
        service_registry_active=True,  # Registry itself is active
        metrics_collector_active=metrics_collector_active,
        health_checker_active=health_checker_active,
        api_key_validator_configured=api_key_validator_configured,
        rate_limiter_configured=rate_limiter_configured,
        webhook_verifier_configured=webhook_verifier_configured,
        services_count=services_count,
    )
