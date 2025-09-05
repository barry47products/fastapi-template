"""FastAPI application factory with configuration-driven setup."""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from fastapi import FastAPI

from config.settings import get_settings, Settings, validate_startup_configuration
from src.domain.events import DomainEventRegistry
from src.infrastructure import initialize_service_registry
from src.infrastructure.api.exception_handlers import (
    infrastructure_exception_handler,
    not_found_exception_handler,
    rate_limit_exception_handler,
    validation_exception_handler,
)
from src.infrastructure.events import ObservabilityEventPublisher
from src.infrastructure.feature_flags import configure_feature_flags
from src.infrastructure.observability import (
    configure_health_checker,
    get_logger,
    get_metrics_collector,
)
from src.infrastructure.security import (
    configure_api_key_validator,
    configure_rate_limiter,
    configure_webhook_verifier,
)
from src.shared.exceptions import (
    ConfigurationException,
    DatabaseException,
    EndorsementNotFoundException,
    ExternalAPIException,
    MissingEnvironmentVariableException,
    ProviderNotFoundException,
    RateLimitExceededException,
    ValidationException,
    WhatsAppDeliveryException,
    WhatsAppException,
)


def create_lifespan(
    app_settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Create lifespan context manager with settings."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Manage application lifespan with proper startup/shutdown sequences."""
        startup_logger = get_logger(__name__)

        try:
            # Initialize basic logging early with minimal configuration
            # This ensures consistent formatting from the very beginning
            import os

            from src.infrastructure.observability import configure_logging

            # Get basic settings for early logging setup
            log_level = os.getenv("LOG_LEVEL", "INFO")
            environment = os.getenv("ENVIRONMENT", "development")
            configure_logging(log_level, environment)
            startup_logger = get_logger(__name__)

            # Startup - Initialize all foundation modules
            startup_logger.info("Starting Neighbour Approved application")

            # Initialize service registry for dependency injection
            services = initialize_service_registry()
            startup_logger.info("Service registry initialized for dependency injection")

            # Validate configuration at startup (fail fast)
            settings = validate_startup_configuration(app_settings)
            startup_logger.info("Configuration validation completed successfully")
            startup_logger.info("Structured logging configured")

            # Initialize metrics collection (if enabled)
            if settings.metrics_enabled:
                # Use configure_metrics to properly initialize the metrics system
                from src.infrastructure.observability import configure_metrics

                configure_metrics(
                    enabled=settings.metrics_enabled,
                    port=settings.metrics_port,
                )

                # Get the configured metrics collector
                metrics = get_metrics_collector()
                # Register metrics collector with service registry
                # (already done in configure_metrics)  # noqa: E501
                services.register_metrics_collector(metrics)
                # Add a basic startup metric to validate metrics are working
                metrics.increment_counter(
                    "application_starts_total",
                    {"version": "0.1.0"},
                )
                startup_logger.info(
                    "Metrics initialized and registered with service registry",
                )
            else:
                startup_logger.info("Metrics collection disabled by configuration")

            # Initialize domain event publisher for observability
            event_publisher = ObservabilityEventPublisher()
            DomainEventRegistry.register_publisher(event_publisher)
            startup_logger.info("Domain event publisher registered for observability")

            # Initialize feature flags (if enabled)
            if settings.feature_flags_enabled:
                configure_feature_flags()
                # Get and register feature flag manager with service registry
                from src.infrastructure.feature_flags import get_feature_flag_manager

                feature_flag_manager = get_feature_flag_manager()
                services.register_feature_flag_manager(feature_flag_manager)
                startup_logger.info(
                    "Feature flags initialized and registered with service registry",
                )
            else:
                startup_logger.info("Feature flags system disabled by configuration")

            # Initialize API key validator
            api_keys_str: str = getattr(settings, "api_keys", "")
            api_keys = api_keys_str.split(",") if api_keys_str else []
            configure_api_key_validator(api_keys)
            # Get and register API key validator with service registry
            from src.infrastructure.security import get_api_key_validator

            api_key_validator = get_api_key_validator()
            services.register_api_key_validator(api_key_validator)
            startup_logger.info(
                "API key validator configured and registered with service registry",
                key_count=len(api_keys),
            )

            # Initialize rate limiter
            configure_rate_limiter(
                limit=settings.rate_limit_requests,
                window_seconds=settings.rate_limit_window_seconds,
            )
            # Get and register rate limiter with service registry
            from src.infrastructure.security import get_rate_limiter

            rate_limiter = get_rate_limiter()
            services.register_rate_limiter(rate_limiter)
            startup_logger.info(
                "Rate limiter configured and registered with service registry",
                limit=settings.rate_limit_requests,
                window_seconds=settings.rate_limit_window_seconds,
            )

            # Initialize webhook verifier
            webhook_secret = getattr(settings, "webhook_secret_key", "")
            if webhook_secret:
                configure_webhook_verifier(webhook_secret)
                # Get and register webhook verifier with service registry
                from src.infrastructure.security import get_webhook_verifier

                webhook_verifier = get_webhook_verifier()
                services.register_webhook_verifier(webhook_verifier)
                startup_logger.info(
                    "Webhook verifier configured and registered with registry",
                )
            else:
                startup_logger.warning(
                    "Webhook verifier not configured - missing secret key",
                )

            # Initialize health checker
            configure_health_checker(timeout=settings.health_check_timeout_seconds)
            # Get and register health checker with service registry
            from src.domain.health import check_domain_layer_health
            from src.infrastructure.observability import get_health_checker

            health_checker = get_health_checker()
            services.register_health_checker(health_checker)
            startup_logger.info(
                "Health checker configured and registered with service registry",
                timeout_seconds=settings.health_check_timeout_seconds,
            )

            # Register domain layer health checks
            async def domain_health_check() -> bool:
                result = await check_domain_layer_health()
                return bool(result["healthy"])

            health_checker.register_health_check("domain_layer", domain_health_check)
            startup_logger.info("Domain layer health checks registered")

            # Initialize repository factory and Firestore client
            from src.infrastructure.persistence.repository_factory import FirestoreRepositoryFactory

            repository_factory = FirestoreRepositoryFactory()
            services.register_repository_factory(repository_factory)

            # Initialize Firestore client by creating a repository (lazy initialization)
            try:
                _ = repository_factory.firestore_client
                startup_logger.info(
                    "Repository factory and Firestore client initialized successfully",
                )
            except Exception as e:
                startup_logger.warning("Failed to initialize Firestore client", error=str(e))
                startup_logger.info(
                    "Repository factory registered (Firestore client will be initialized"
                    "on first use)",
                )

            startup_logger.info("All foundation modules initialized successfully")

            yield

        except Exception as e:
            startup_logger.error("Failed to initialize application", error=str(e))
            raise
        finally:
            # Shutdown
            startup_logger.info("Shutting down Neighbour Approved application")

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create FastAPI application with configuration-driven setup."""
    if settings is None:
        settings = get_settings()

    # Create FastAPI application with configuration
    app = FastAPI(
        title=settings.app_name,
        description="WhatsApp-based local service endorsement platform",
        version="0.1.0",
        debug=settings.debug,
        lifespan=create_lifespan(settings),
    )

    # Register Exception Handlers
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(ProviderNotFoundException, not_found_exception_handler)
    app.add_exception_handler(EndorsementNotFoundException, not_found_exception_handler)
    app.add_exception_handler(RateLimitExceededException, rate_limit_exception_handler)
    app.add_exception_handler(ConfigurationException, infrastructure_exception_handler)
    app.add_exception_handler(
        MissingEnvironmentVariableException,
        infrastructure_exception_handler,
    )
    app.add_exception_handler(DatabaseException, infrastructure_exception_handler)
    app.add_exception_handler(ExternalAPIException, infrastructure_exception_handler)
    app.add_exception_handler(WhatsAppException, infrastructure_exception_handler)
    app.add_exception_handler(
        WhatsAppDeliveryException,
        infrastructure_exception_handler,
    )

    # Include API routers
    from src.interfaces.api.routers import admin, health, webhooks

    app.include_router(health.router)
    app.include_router(admin.router)
    app.include_router(webhooks.router)

    # Add metrics endpoint if metrics are enabled
    if settings.metrics_enabled:
        from fastapi import Response
        from prometheus_client import generate_latest

        @app.get("/metrics")
        async def metrics_endpoint() -> Response:
            """Prometheus metrics endpoint."""
            metrics_collector = get_metrics_collector()
            content = generate_latest(metrics_collector.registry).decode("utf-8")
            return Response(content=content, media_type="text/plain; charset=utf-8")

    return app


def create_development_server_config(
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Create uvicorn server configuration using settings."""
    if settings is None:
        settings = get_settings()

    return {
        "app": "src.main:app",
        "host": settings.api_host,
        "port": settings.api_port,
        "reload": True,
        "log_level": "info",
    }
