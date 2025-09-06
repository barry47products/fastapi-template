"""Unit tests for FastAPI app factory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import (
    APISettings,
    ApplicationSettings,
    Environment,
    ObservabilitySettings,
    SecuritySettings,
)
from src.infrastructure.api.app_factory import (
    add_api_routes,
    add_exception_handlers,
    configure_middleware,
    create_app,
    create_development_server_config,
    create_lifespan_manager,
)


class TestCreateLifespanManager:
    """Test lifespan manager creation and lifecycle."""

    @pytest.fixture
    def mock_settings(self) -> ApplicationSettings:
        """Create mock application settings."""
        return ApplicationSettings(
            environment=Environment.DEVELOPMENT,
            debug=True,
            api=APISettings(
                title="Test API",
                description="Test API Description",
                version="1.0.0",
                host="0.0.0.0",
                port=8000,
                docs_url="/docs",
                redoc_url="/redoc",
                openapi_url="/openapi.json",
            ),
            security=SecuritySettings(
                api_keys=["test-key"],
                webhook_secret="test-secret",
                rate_limit_requests_per_minute=100,
                cors_origins=["*"],
                cors_allow_credentials=True,
                cors_allow_methods=["*"],
                cors_allow_headers=["*"],
            ),
            observability=ObservabilitySettings(
                metrics_enabled=True,
                metrics_port=9090,
                log_level="INFO",
            ),
        )

    @patch("src.infrastructure.api.app_factory.get_logger")
    @patch("src.infrastructure.api.app_factory.get_metrics_collector")
    @patch("src.infrastructure.api.app_factory.initialize_infrastructure")
    @patch("src.infrastructure.api.app_factory.ObservabilityEventPublisher")
    @patch("src.infrastructure.api.app_factory.DomainEventRegistry")
    @pytest.mark.asyncio
    async def test_lifespan_startup_success(
        self,
        mock_registry: MagicMock,
        mock_event_publisher_class: MagicMock,
        mock_initialize: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_settings: ApplicationSettings,
    ) -> None:
        """Lifespan manager starts up successfully."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_event_publisher = MagicMock()
        mock_app = MagicMock(spec=FastAPI)

        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_event_publisher_class.return_value = mock_event_publisher

        lifespan_manager = create_lifespan_manager(mock_settings)

        async with lifespan_manager(mock_app):
            pass

        mock_initialize.assert_called_once()
        mock_registry.register_publisher.assert_called_once_with(mock_event_publisher)
        mock_metrics.increment_counter.assert_any_call("app_startup_total", {})
        mock_logger.info.assert_any_call(
            "Starting FastAPI template application", environment=mock_settings.environment.value
        )

    @patch("src.infrastructure.api.app_factory.get_logger")
    @patch("src.infrastructure.api.app_factory.get_metrics_collector")
    @patch("src.infrastructure.api.app_factory.initialize_infrastructure")
    @patch("src.infrastructure.api.app_factory.ObservabilityEventPublisher")
    @patch("src.infrastructure.api.app_factory.DomainEventRegistry")
    @pytest.mark.asyncio
    async def test_lifespan_startup_failure(
        self,
        mock_registry: MagicMock,
        mock_event_publisher_class: MagicMock,
        mock_initialize: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_settings: ApplicationSettings,
    ) -> None:
        """Lifespan manager handles startup failure."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_app = MagicMock(spec=FastAPI)

        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_initialize.side_effect = Exception("Startup failed")

        lifespan_manager = create_lifespan_manager(mock_settings)

        with pytest.raises(Exception, match="Startup failed"):
            async with lifespan_manager(mock_app):
                pass

        mock_metrics.increment_counter.assert_any_call("app_startup_failures_total", {})
        mock_logger.error.assert_called_with(
            "FastAPI template startup failed", error="Startup failed"
        )

    @patch("src.infrastructure.api.app_factory.get_logger")
    @patch("src.infrastructure.api.app_factory.get_metrics_collector")
    @patch("src.infrastructure.api.app_factory.initialize_infrastructure")
    @patch("src.infrastructure.api.app_factory.ObservabilityEventPublisher")
    @patch("src.infrastructure.api.app_factory.DomainEventRegistry")
    @pytest.mark.asyncio
    async def test_lifespan_shutdown_success(
        self,
        mock_registry: MagicMock,
        mock_event_publisher_class: MagicMock,
        mock_initialize: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_settings: ApplicationSettings,
    ) -> None:
        """Lifespan manager shuts down successfully."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_app = MagicMock(spec=FastAPI)

        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        lifespan_manager = create_lifespan_manager(mock_settings)

        async with lifespan_manager(mock_app):
            pass

        mock_registry.clear_publisher.assert_called_once()
        mock_metrics.increment_counter.assert_any_call("app_shutdown_total", {})
        mock_logger.info.assert_any_call("FastAPI template shutdown completed")

    @patch("src.infrastructure.api.app_factory.get_logger")
    @patch("src.infrastructure.api.app_factory.get_metrics_collector")
    @patch("src.infrastructure.api.app_factory.initialize_infrastructure")
    @patch("src.infrastructure.api.app_factory.ObservabilityEventPublisher")
    @patch("src.infrastructure.api.app_factory.DomainEventRegistry")
    @pytest.mark.asyncio
    async def test_lifespan_shutdown_failure(
        self,
        mock_registry: MagicMock,
        mock_event_publisher_class: MagicMock,
        mock_initialize: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_settings: ApplicationSettings,
    ) -> None:
        """Lifespan manager handles shutdown failure."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_app = MagicMock(spec=FastAPI)

        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_registry.clear_publisher.side_effect = Exception("Shutdown failed")

        lifespan_manager = create_lifespan_manager(mock_settings)

        async with lifespan_manager(mock_app):
            pass

        mock_metrics.increment_counter.assert_any_call("app_shutdown_failures_total", {})
        mock_logger.error.assert_called_with("Error during shutdown", error="Shutdown failed")


class TestAddExceptionHandlers:
    """Test exception handler registration."""

    @patch("src.infrastructure.api.app_factory.validation_exception_handler")
    @patch("src.infrastructure.api.app_factory.not_found_exception_handler")
    @patch("src.infrastructure.api.app_factory.rate_limit_exception_handler")
    @patch("src.infrastructure.api.app_factory.infrastructure_exception_handler")
    def test_adds_all_exception_handlers(
        self,
        mock_infra_handler: MagicMock,
        mock_rate_limit_handler: MagicMock,
        mock_not_found_handler: MagicMock,
        mock_validation_handler: MagicMock,
    ) -> None:
        """Adds all domain and infrastructure exception handlers."""
        mock_app = MagicMock(spec=FastAPI)

        add_exception_handlers(mock_app)

        assert mock_app.add_exception_handler.call_count == 7

    def test_registers_domain_exception_handlers(self) -> None:
        """Registers domain exception handlers."""
        mock_app = MagicMock(spec=FastAPI)

        add_exception_handlers(mock_app)

        calls = mock_app.add_exception_handler.call_args_list
        exception_types = [call[0][0].__name__ for call in calls]

        assert "ValidationException" in exception_types
        assert "EntityNotFoundException" in exception_types
        assert "RateLimitExceededException" in exception_types

    def test_registers_infrastructure_exception_handlers(self) -> None:
        """Registers infrastructure exception handlers."""
        mock_app = MagicMock(spec=FastAPI)

        add_exception_handlers(mock_app)

        calls = mock_app.add_exception_handler.call_args_list
        exception_types = [call[0][0].__name__ for call in calls]

        assert "ExternalAPIException" in exception_types
        assert "MessageDeliveryException" in exception_types
        assert "AuthenticationException" in exception_types
        assert "AuthorizationException" in exception_types


class TestConfigureMiddleware:
    """Test middleware configuration."""

    @pytest.fixture
    def mock_settings(self) -> ApplicationSettings:
        """Create mock application settings."""
        return ApplicationSettings(
            environment=Environment.DEVELOPMENT,
            debug=True,
            api=APISettings(
                title="Test API",
                description="Test API Description",
                version="1.0.0",
                host="0.0.0.0",
                port=8000,
                docs_url="/docs",
                redoc_url="/redoc",
                openapi_url="/openapi.json",
            ),
            security=SecuritySettings(
                api_keys=["test-key"],
                webhook_secret="test-secret",
                rate_limit_requests_per_minute=100,
                cors_origins=["http://localhost:3000", "https://example.com"],
                cors_allow_credentials=True,
                cors_allow_methods=["GET", "POST"],
                cors_allow_headers=["Content-Type", "Authorization"],
            ),
            observability=ObservabilitySettings(
                metrics_enabled=True,
                metrics_port=9090,
                log_level="INFO",
            ),
        )

    def test_configures_cors_middleware(self, mock_settings: ApplicationSettings) -> None:
        """Configures CORS middleware with settings."""
        mock_app = MagicMock(spec=FastAPI)

        configure_middleware(mock_app, mock_settings)

        mock_app.add_middleware.assert_called_once()
        call_args = mock_app.add_middleware.call_args

        assert call_args[0][0] == CORSMiddleware
        assert call_args[1]["allow_origins"] == mock_settings.security.cors_origins
        assert call_args[1]["allow_credentials"] == mock_settings.security.cors_allow_credentials
        assert call_args[1]["allow_methods"] == mock_settings.security.cors_allow_methods
        assert call_args[1]["allow_headers"] == mock_settings.security.cors_allow_headers

    def test_cors_middleware_uses_security_settings(
        self, mock_settings: ApplicationSettings
    ) -> None:
        """CORS middleware uses values from security settings."""
        mock_app = MagicMock(spec=FastAPI)

        configure_middleware(mock_app, mock_settings)

        call_args = mock_app.add_middleware.call_args[1]
        assert call_args["allow_origins"] == ["http://localhost:3000", "https://example.com"]
        assert call_args["allow_credentials"] is True
        assert call_args["allow_methods"] == ["GET", "POST"]
        assert call_args["allow_headers"] == ["Content-Type", "Authorization"]


class TestAddAPIRoutes:
    """Test API route registration."""

    @patch("src.infrastructure.api.app_factory.health_routes")
    @patch("src.infrastructure.api.app_factory.admin_routes")
    @patch("src.infrastructure.api.app_factory.sample_routes")
    def test_includes_all_router_modules(
        self,
        mock_sample_routes: MagicMock,
        mock_admin_routes: MagicMock,
        mock_health_routes: MagicMock,
    ) -> None:
        """Includes all router modules."""
        mock_app = MagicMock(spec=FastAPI)
        mock_health_router = MagicMock()
        mock_admin_router = MagicMock()
        mock_sample_router = MagicMock()

        mock_health_routes.router = mock_health_router
        mock_admin_routes.router = mock_admin_router
        mock_sample_routes.router = mock_sample_router

        add_api_routes(mock_app)

        mock_app.include_router.assert_any_call(mock_health_router)
        mock_app.include_router.assert_any_call(mock_admin_router)
        mock_app.include_router.assert_any_call(mock_sample_router)
        assert mock_app.include_router.call_count == 3

    @patch("src.infrastructure.api.app_factory.health_routes")
    @patch("src.infrastructure.api.app_factory.admin_routes")
    @patch("src.infrastructure.api.app_factory.sample_routes")
    def test_includes_routers_in_correct_order(
        self,
        mock_sample_routes: MagicMock,
        mock_admin_routes: MagicMock,
        mock_health_routes: MagicMock,
    ) -> None:
        """Includes routers in the correct order (core system first, then business)."""
        mock_app = MagicMock(spec=FastAPI)
        mock_health_router = MagicMock()
        mock_admin_router = MagicMock()
        mock_sample_router = MagicMock()

        mock_health_routes.router = mock_health_router
        mock_admin_routes.router = mock_admin_router
        mock_sample_routes.router = mock_sample_router

        add_api_routes(mock_app)

        calls = mock_app.include_router.call_args_list
        assert calls[0][0][0] == mock_health_router  # Health first
        assert calls[1][0][0] == mock_admin_router  # Admin second
        assert calls[2][0][0] == mock_sample_router  # Sample last


class TestCreateApp:
    """Test FastAPI application creation."""

    @pytest.fixture
    def mock_settings(self) -> ApplicationSettings:
        """Create mock application settings."""
        return ApplicationSettings(
            environment=Environment.PRODUCTION,
            debug=False,
            api=APISettings(
                title="Production API",
                description="Production API Description",
                version="2.0.0",
                host="127.0.0.1",
                port=9000,
                docs_url="/api/docs",
                redoc_url="/api/redoc",
                openapi_url="/api/openapi.json",
            ),
            security=SecuritySettings(
                api_keys=["prod-key"],
                webhook_secret="prod-secret",
                rate_limit_requests_per_minute=50,
                cors_origins=["https://production.com"],
                cors_allow_credentials=False,
                cors_allow_methods=["GET"],
                cors_allow_headers=["Content-Type"],
            ),
            observability=ObservabilitySettings(
                metrics_enabled=True,
                metrics_port=9091,
                log_level="ERROR",
            ),
        )

    @patch("src.infrastructure.api.app_factory.get_settings")
    @patch("src.infrastructure.api.app_factory.create_lifespan_manager")
    @patch("src.infrastructure.api.app_factory.configure_middleware")
    @patch("src.infrastructure.api.app_factory.add_exception_handlers")
    @patch("src.infrastructure.api.app_factory.add_api_routes")
    def test_creates_app_with_default_settings(
        self,
        mock_add_routes: MagicMock,
        mock_add_handlers: MagicMock,
        mock_configure_middleware: MagicMock,
        mock_create_lifespan: MagicMock,
        mock_get_settings: MagicMock,
        mock_settings: ApplicationSettings,
    ) -> None:
        """Creates app with default settings when none provided."""
        mock_get_settings.return_value = mock_settings
        mock_lifespan = MagicMock()
        mock_create_lifespan.return_value = mock_lifespan

        app = create_app()

        assert isinstance(app, FastAPI)
        mock_get_settings.assert_called_once()
        mock_create_lifespan.assert_called_once_with(mock_settings)

    @patch("src.infrastructure.api.app_factory.create_lifespan_manager")
    @patch("src.infrastructure.api.app_factory.configure_middleware")
    @patch("src.infrastructure.api.app_factory.add_exception_handlers")
    @patch("src.infrastructure.api.app_factory.add_api_routes")
    def test_creates_app_with_provided_settings(
        self,
        mock_add_routes: MagicMock,
        mock_add_handlers: MagicMock,
        mock_configure_middleware: MagicMock,
        mock_create_lifespan: MagicMock,
        mock_settings: ApplicationSettings,
    ) -> None:
        """Creates app with provided settings."""
        mock_lifespan = MagicMock()
        mock_create_lifespan.return_value = mock_lifespan

        app = create_app(mock_settings)

        assert isinstance(app, FastAPI)
        assert app.title == "Production API"
        assert app.description == "Production API Description"
        assert app.version == "2.0.0"
        assert app.docs_url == "/api/docs"
        assert app.redoc_url == "/api/redoc"
        assert app.openapi_url == "/api/openapi.json"

    @patch("src.infrastructure.api.app_factory.create_lifespan_manager")
    @patch("src.infrastructure.api.app_factory.configure_middleware")
    @patch("src.infrastructure.api.app_factory.add_exception_handlers")
    @patch("src.infrastructure.api.app_factory.add_api_routes")
    def test_configures_app_components(
        self,
        mock_add_routes: MagicMock,
        mock_add_handlers: MagicMock,
        mock_configure_middleware: MagicMock,
        mock_create_lifespan: MagicMock,
        mock_settings: ApplicationSettings,
    ) -> None:
        """Configures all app components in correct order."""
        mock_lifespan = MagicMock()
        mock_create_lifespan.return_value = mock_lifespan

        app = create_app(mock_settings)

        mock_configure_middleware.assert_called_once_with(app, mock_settings)
        mock_add_handlers.assert_called_once_with(app)
        mock_add_routes.assert_called_once_with(app)

    @patch("src.infrastructure.api.app_factory.create_lifespan_manager")
    @patch("src.infrastructure.api.app_factory.configure_middleware")
    @patch("src.infrastructure.api.app_factory.add_exception_handlers")
    @patch("src.infrastructure.api.app_factory.add_api_routes")
    def test_uses_lifespan_manager(
        self,
        mock_add_routes: MagicMock,
        mock_add_handlers: MagicMock,
        mock_configure_middleware: MagicMock,
        mock_create_lifespan: MagicMock,
        mock_settings: ApplicationSettings,
    ) -> None:
        """Uses lifespan manager for app lifecycle."""
        mock_lifespan = MagicMock()
        mock_create_lifespan.return_value = mock_lifespan

        app = create_app(mock_settings)

        mock_create_lifespan.assert_called_once_with(mock_settings)
        assert app.router.lifespan_context == mock_lifespan


class TestCreateDevelopmentServerConfig:
    """Test development server configuration creation."""

    @pytest.fixture
    def development_settings(self) -> ApplicationSettings:
        """Create development application settings."""
        return ApplicationSettings(
            environment=Environment.DEVELOPMENT,
            debug=True,
            api=APISettings(
                title="Dev API",
                description="Dev API Description",
                version="1.0.0-dev",
                host="localhost",
                port=8080,
                docs_url="/docs",
                redoc_url="/redoc",
                openapi_url="/openapi.json",
            ),
            security=SecuritySettings(
                api_keys=["dev-key"],
                webhook_secret="dev-secret",
                rate_limit_requests_per_minute=1000,
                cors_origins=["*"],
                cors_allow_credentials=True,
                cors_allow_methods=["*"],
                cors_allow_headers=["*"],
            ),
            observability=ObservabilitySettings(
                metrics_enabled=False,
                metrics_port=9090,
                log_level="DEBUG",
            ),
        )

    @pytest.fixture
    def production_settings(self) -> ApplicationSettings:
        """Create production application settings."""
        return ApplicationSettings(
            environment=Environment.PRODUCTION,
            debug=False,
            api=APISettings(
                title="Prod API",
                description="Prod API Description",
                version="1.0.0",
                host="0.0.0.0",
                port=8000,
                docs_url=None,
                redoc_url=None,
                openapi_url=None,
            ),
            security=SecuritySettings(
                api_keys=["prod-key"],
                webhook_secret="prod-secret",
                rate_limit_requests_per_minute=100,
                cors_origins=["https://example.com"],
                cors_allow_credentials=False,
                cors_allow_methods=["GET", "POST"],
                cors_allow_headers=["Content-Type"],
            ),
            observability=ObservabilitySettings(
                metrics_enabled=True,
                metrics_port=9090,
                log_level="INFO",
            ),
        )

    @patch("src.infrastructure.api.app_factory.get_settings")
    def test_creates_config_with_default_settings(
        self, mock_get_settings: MagicMock, development_settings: ApplicationSettings
    ) -> None:
        """Creates server config with default settings when none provided."""
        mock_get_settings.return_value = development_settings

        config = create_development_server_config()

        assert config["host"] == "localhost"
        assert config["port"] == 8080
        assert config["reload"] is True
        assert config["log_level"] == "debug"
        assert config["access_log"] is True
        mock_get_settings.assert_called_once()

    def test_creates_config_with_provided_settings(
        self, development_settings: ApplicationSettings
    ) -> None:
        """Creates server config with provided settings."""
        config = create_development_server_config(development_settings)

        assert config["host"] == "localhost"
        assert config["port"] == 8080
        assert config["reload"] is True
        assert config["log_level"] == "debug"
        assert config["access_log"] is True

    def test_development_config_enables_reload_and_debug_logging(
        self, development_settings: ApplicationSettings
    ) -> None:
        """Development config enables reload and debug logging."""
        config = create_development_server_config(development_settings)

        assert config["reload"] is True
        assert config["log_level"] == "debug"

    def test_production_config_disables_reload_and_uses_info_logging(
        self, production_settings: ApplicationSettings
    ) -> None:
        """Production config disables reload and uses info logging."""
        config = create_development_server_config(production_settings)

        assert config["reload"] is False
        assert config["log_level"] == "info"

    def test_config_includes_host_and_port_from_settings(
        self, production_settings: ApplicationSettings
    ) -> None:
        """Config includes host and port from API settings."""
        config = create_development_server_config(production_settings)

        assert config["host"] == "0.0.0.0"
        assert config["port"] == 8000

    def test_config_always_enables_access_log(
        self, production_settings: ApplicationSettings
    ) -> None:
        """Config always enables access log."""
        config = create_development_server_config(production_settings)

        assert config["access_log"] is True
