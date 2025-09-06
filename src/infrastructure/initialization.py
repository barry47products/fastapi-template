"""Infrastructure initialization for service registry and dependency injection."""

from typing import TYPE_CHECKING

from config.settings import get_settings

if TYPE_CHECKING:
    from src.infrastructure.service_registry import ServiceRegistry
#  pylint: disable=C0413
from src.infrastructure.messaging import SampleNotificationService
from src.infrastructure.observability import (
    configure_health_checker,
    get_health_checker,
    get_logger,
    get_metrics_collector,
)
from src.infrastructure.persistence import configure_repository_factory, SampleRepositoryFactory
from src.infrastructure.security.api_key_validator import configure_api_key_validator
from src.infrastructure.security.rate_limiter import configure_rate_limiter
from src.infrastructure.service_registry import get_service_registry, initialize_service_registry

#  pylint: enable=C0413


def initialize_infrastructure() -> None:
    """
    Initialize all infrastructure services in the correct order.

    This function sets up the complete infrastructure layer:
    1. Service registry
    2. Settings and configuration
    3. Observability (logging, metrics, health)
    4. Persistence layer (sample repositories)
    5. Messaging services
    6. Cross-service wiring
    """
    logger = get_logger(__name__)
    logger.info("Starting infrastructure initialization")

    try:
        # 1. Initialize service registry
        service_registry = initialize_service_registry()
        logger.debug("Service registry initialized")

        # 2. Get application settings (validates configuration)
        get_settings()
        logger.debug("Application settings loaded")

        # 3. Initialize observability services
        # First configure the health checker with default timeout
        configure_health_checker(timeout=10)

        metrics_collector = get_metrics_collector()
        health_checker = get_health_checker()

        # Initialize rate limiter
        configure_rate_limiter(limit=100, window_seconds=60)  # 100 requests per minute

        # Initialize API key validator
        # For development, use a simple default key. In production, load from environment
        configure_api_key_validator(api_keys=["dev-api-key-123"])

        # Register observability services
        service_registry.register_metrics_collector(metrics_collector)
        service_registry.register_health_checker(health_checker)
        logger.debug("Observability services registered")

        # 4. Initialize persistence layer
        _initialize_persistence_layer(service_registry)

        # 5. Initialize messaging services
        _initialize_messaging_services(service_registry)

        # 6. Verify all services are registered (health checks can be run async later)
        logger.info(
            "Infrastructure services registered",
            metrics=service_registry.has_metrics_collector(),
            health_checker=service_registry.has_health_checker(),
            repository_factory=service_registry.has_repository_factory(),
            notification_service=service_registry.has_notification_service(),
        )

        logger.info("Infrastructure initialization completed successfully")

    except Exception as e:
        logger.error("Infrastructure initialization failed", error=str(e))
        raise


def _initialize_persistence_layer(service_registry: "ServiceRegistry") -> None:
    """Initialize persistence layer with sample repositories."""
    logger = get_logger(__name__)

    try:
        # Create and configure repository factory
        repository_factory = SampleRepositoryFactory()

        # Register with service registry
        service_registry.register_repository_factory(repository_factory)

        # Also configure the module-level factory for backward compatibility
        configure_repository_factory(repository_factory)

        logger.info("Persistence layer initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize persistence layer", error=str(e))
        raise


def _initialize_messaging_services(service_registry: "ServiceRegistry") -> None:
    """Initialize messaging and notification services."""
    logger = get_logger(__name__)

    try:
        # Create and configure notification service
        notification_service = SampleNotificationService()

        # Register with service registry
        service_registry.register_notification_service(notification_service)

        logger.info("Messaging services initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize messaging services", error=str(e))
        raise


def shutdown_infrastructure() -> None:
    """Clean shutdown of infrastructure services."""
    logger = get_logger(__name__)

    try:
        logger.info("Starting infrastructure shutdown")

        # Get service registry
        service_registry = get_service_registry()

        # Perform any cleanup needed for registered services
        # (Future: Add cleanup methods to services)

        # Clear the service registry
        service_registry.clear_all_services()

        logger.info("Infrastructure shutdown completed")

    except Exception as e:
        logger.error("Infrastructure shutdown failed", error=str(e))
        raise
