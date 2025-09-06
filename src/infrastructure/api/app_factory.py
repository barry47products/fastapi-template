"""FastAPI application factory with configuration-driven setup."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import ApplicationSettings, get_settings
from src.domain.events import DomainEventRegistry
from src.infrastructure import initialize_infrastructure
from src.infrastructure.api.exception_handlers import (
    infrastructure_exception_handler,
    not_found_exception_handler,
    rate_limit_exception_handler,
    validation_exception_handler,
)
from src.infrastructure.events import ObservabilityEventPublisher
from src.infrastructure.observability import (
    get_logger,
    get_metrics_collector,
)
from src.interfaces.api.routers import admin_routes, health_routes, sample_routes
from src.shared.exceptions import (
    AuthenticationException,
    AuthorizationException,
    EntityNotFoundException,
    ExternalAPIException,
    MessageDeliveryException,
    RateLimitExceededException,
    ValidationException,
)


def create_lifespan_manager(
    app_settings: ApplicationSettings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """
    Create application lifespan manager for startup and shutdown.

    Args:
        app_settings: Application settings for infrastructure initialization

    Returns:
        Async context manager for FastAPI lifespan
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """
        Manage application lifecycle with proper startup and shutdown.

        Handles:
        - Infrastructure initialization and cleanup
        - Service registry management
        - Health check configuration
        - Event publisher setup
        """
        logger = get_logger(__name__)
        metrics = get_metrics_collector()

        try:
            logger.info(
                "Starting FastAPI template application", environment=app_settings.environment.value
            )

            # Initialize all infrastructure services
            initialize_infrastructure()

            # Configure event publishing for domain events
            event_publisher = ObservabilityEventPublisher()
            DomainEventRegistry.register_publisher(event_publisher)

            metrics.increment_counter("app_startup_total", {})
            logger.info("FastAPI template startup completed successfully")

            yield

        except Exception as e:
            logger.error("FastAPI template startup failed", error=str(e))
            metrics.increment_counter("app_startup_failures_total", {})
            raise

        finally:
            logger.info("Starting FastAPI template shutdown")
            try:
                # Clean up resources
                DomainEventRegistry.clear_publisher()
                metrics.increment_counter("app_shutdown_total", {})
                logger.info("FastAPI template shutdown completed")
            except Exception as e:
                logger.error("Error during shutdown", error=str(e))
                metrics.increment_counter("app_shutdown_failures_total", {})

    return lifespan


def add_exception_handlers(app: FastAPI) -> None:
    """
    Add domain and infrastructure exception handlers to FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Domain exception handlers
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(EntityNotFoundException, not_found_exception_handler)
    app.add_exception_handler(RateLimitExceededException, rate_limit_exception_handler)

    # Infrastructure exception handlers
    app.add_exception_handler(ExternalAPIException, infrastructure_exception_handler)
    app.add_exception_handler(
        MessageDeliveryException,
        infrastructure_exception_handler,
    )
    app.add_exception_handler(AuthenticationException, infrastructure_exception_handler)
    app.add_exception_handler(AuthorizationException, infrastructure_exception_handler)


def configure_middleware(app: FastAPI, settings: ApplicationSettings) -> None:
    """
    Configure FastAPI middleware based on settings.

    Args:
        app: FastAPI application instance
        settings: Application settings
    """

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=settings.security.cors_allow_credentials,
        allow_methods=settings.security.cors_allow_methods,
        allow_headers=settings.security.cors_allow_headers,
    )


def add_api_routes(app: FastAPI) -> None:
    """
    Add API routes to the FastAPI application.

    Args:
        app: FastAPI application instance
    """

    # Core system routes
    app.include_router(health_routes.router)
    app.include_router(admin_routes.router)

    # Business/sample routes
    app.include_router(sample_routes.router)


def create_app(settings: ApplicationSettings | None = None) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        settings: Optional application settings (defaults to global settings)

    Returns:
        Configured FastAPI application instance
    """
    if settings is None:
        settings = get_settings()

    # Create FastAPI app with settings
    app = FastAPI(
        title=settings.api.title,
        description=settings.api.description,
        version=settings.api.version,
        docs_url=settings.api.docs_url,
        redoc_url=settings.api.redoc_url,
        openapi_url=settings.api.openapi_url,
        lifespan=create_lifespan_manager(settings),
    )

    # Configure application
    configure_middleware(app, settings)
    add_exception_handlers(app)
    add_api_routes(app)

    return app


def create_development_server_config(
    settings: ApplicationSettings | None = None,
) -> dict[str, Any]:
    """
    Create development server configuration for uvicorn.

    Args:
        settings: Optional application settings

    Returns:
        Dictionary of uvicorn configuration options
    """
    if settings is None:
        settings = get_settings()

    return {
        "host": settings.api.host,
        "port": settings.api.port,
        "reload": settings.is_development(),
        "log_level": "info" if settings.is_production() else "debug",
        "access_log": True,
    }
