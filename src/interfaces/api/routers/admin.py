"""Administrative API router for operations and configuration."""

from __future__ import annotations

import sys
from datetime import datetime

from fastapi import APIRouter, Depends

from config.settings import get_settings
from src.infrastructure.dependencies import (
    get_health_checker,
    get_metrics_collector,
)
from src.infrastructure.security import check_rate_limit, verify_api_key
from src.interfaces.api.schemas import AdminInfoResponse, SafeConfigResponse, ServiceStatusResponse

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/info")
async def get_app_info(
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
    _: str = Depends(verify_api_key),
    __: str = Depends(check_rate_limit),
) -> SafeConfigResponse:
    """Safe configuration display without sensitive information."""
    settings = get_settings()
    return SafeConfigResponse(
        api_host=settings.api.host,
        api_port=settings.api.port,
        log_level=settings.observability.log_level,
        metrics_enabled=settings.observability.metrics_enabled,
        debug_mode=settings.is_development(),
        cors_origins=settings.security.cors_origins,
    )


@router.get("/services")
async def get_service_status(
    _: str = Depends(verify_api_key),
    __: str = Depends(check_rate_limit),
) -> ServiceStatusResponse:
    """Infrastructure component status via dependency injection."""
    # Check if core services are available by attempting to retrieve them
    try:
        get_metrics_collector()
        metrics_collector_active = True
    except Exception:
        metrics_collector_active = False

    try:
        get_health_checker()
        health_checker_active = True
    except Exception:
        health_checker_active = False

    # These services are always configured since they use settings
    api_key_validator_configured = True
    rate_limiter_configured = True
    webhook_verifier_configured = True

    # Count active services
    services_count = sum(
        [
            metrics_collector_active,
            health_checker_active,
            api_key_validator_configured,
            rate_limiter_configured,
            webhook_verifier_configured,
        ]
    )

    return ServiceStatusResponse(
        service_registry_active=True,  # Dependencies are active
        metrics_collector_active=metrics_collector_active,
        health_checker_active=health_checker_active,
        api_key_validator_configured=api_key_validator_configured,
        rate_limiter_configured=rate_limiter_configured,
        webhook_verifier_configured=webhook_verifier_configured,
        services_count=services_count,
    )
