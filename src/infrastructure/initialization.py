"""Infrastructure initialization for FastAPI dependency injection."""

from __future__ import annotations

from config.settings import get_settings
from src.infrastructure.observability import configure_health_checker, get_logger
from src.infrastructure.persistence import configure_repository_factory
from src.infrastructure.security.api_key_validator import configure_api_key_validator
from src.infrastructure.security.rate_limiter import configure_rate_limiter


def initialize_infrastructure() -> None:
    """
    Initialize all infrastructure services using singleton configuration.

    With FastAPI dependency injection, most services are lazy-loaded,
    but we still need to configure some singletons for backward compatibility.
    """
    logger = get_logger(__name__)
    settings = get_settings()

    logger.info("Initializing infrastructure services", environment=settings.environment.value)

    try:
        # Configure health checker
        configure_health_checker(timeout=int(settings.observability.health_check_timeout))

        # Configure API key validator
        configure_api_key_validator(api_keys=settings.security.api_keys)

        # Configure rate limiter
        configure_rate_limiter(
            limit=settings.security.rate_limit_requests_per_minute,
            window_seconds=60,
        )

        # Configure repository factory
        configure_repository_factory()

        logger.info("Infrastructure initialization completed successfully")

    except Exception as e:
        logger.error("Infrastructure initialization failed", error=str(e))
        raise


def shutdown_infrastructure() -> None:
    """
    Shutdown infrastructure services gracefully.

    With FastAPI dependency injection, most cleanup is automatic,
    but this provides a hook for any necessary shutdown procedures.
    """
    logger = get_logger(__name__)
    logger.info("Infrastructure shutdown completed")
