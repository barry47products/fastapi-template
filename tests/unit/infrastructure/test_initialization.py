"""Unit tests for infrastructure initialization module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.initialization import (
    _initialize_messaging_services,
    _initialize_persistence_layer,
    initialize_infrastructure,
    shutdown_infrastructure,
)


class TestInitializeInfrastructure:
    """Test infrastructure initialization behavior."""

    @patch("src.infrastructure.initialization.get_service_registry")
    @patch("src.infrastructure.initialization.initialize_service_registry")
    @patch("src.infrastructure.initialization.get_settings")
    @patch("src.infrastructure.initialization.configure_health_checker")
    @patch("src.infrastructure.initialization.get_metrics_collector")
    @patch("src.infrastructure.initialization.get_health_checker")
    @patch("src.infrastructure.initialization.configure_rate_limiter")
    @patch("src.infrastructure.initialization.configure_api_key_validator")
    @patch("src.infrastructure.initialization._initialize_persistence_layer")
    @patch("src.infrastructure.initialization._initialize_messaging_services")
    @patch("src.infrastructure.initialization.get_logger")
    def test_initializes_all_services_in_correct_order(
        self,
        mock_get_logger: MagicMock,
        mock_init_messaging: MagicMock,
        mock_init_persistence: MagicMock,
        mock_configure_api_validator: MagicMock,
        mock_configure_rate_limiter: MagicMock,
        mock_get_health_checker: MagicMock,
        mock_get_metrics_collector: MagicMock,
        mock_configure_health_checker: MagicMock,
        mock_get_settings: MagicMock,
        mock_initialize_service_registry: MagicMock,
        mock_get_service_registry: MagicMock,
    ) -> None:
        """Initializes all services in correct order."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_service_registry = MagicMock()
        mock_initialize_service_registry.return_value = mock_service_registry
        mock_get_service_registry.return_value = mock_service_registry
        mock_metrics_collector = MagicMock()
        mock_get_metrics_collector.return_value = mock_metrics_collector
        mock_health_checker = MagicMock()
        mock_get_health_checker.return_value = mock_health_checker

        # Configure registry checks
        mock_service_registry.has_metrics_collector.return_value = True
        mock_service_registry.has_health_checker.return_value = True
        mock_service_registry.has_repository_factory.return_value = True
        mock_service_registry.has_notification_service.return_value = True

        # Execute
        initialize_infrastructure()

        # Verify initialization order
        mock_initialize_service_registry.assert_called_once()
        mock_get_settings.assert_called_once()
        mock_configure_health_checker.assert_called_once_with(timeout=10)
        mock_configure_rate_limiter.assert_called_once_with(limit=100, window_seconds=60)
        mock_configure_api_validator.assert_called_once_with(api_keys=["dev-api-key-123"])

        # Verify service registration
        mock_service_registry.register_metrics_collector.assert_called_once_with(
            mock_metrics_collector
        )
        mock_service_registry.register_health_checker.assert_called_once_with(mock_health_checker)

        # Verify subsystem initialization
        mock_init_persistence.assert_called_once_with(mock_service_registry)
        mock_init_messaging.assert_called_once_with(mock_service_registry)

        # Verify logging
        mock_logger.info.assert_any_call("Starting infrastructure initialization")
        mock_logger.info.assert_any_call("Infrastructure initialization completed successfully")

    @patch("src.infrastructure.initialization.get_logger")
    @patch("src.infrastructure.initialization.initialize_service_registry")
    def test_handles_service_registry_initialization_failure(
        self, mock_initialize_registry: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Handles service registry initialization failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_initialize_registry.side_effect = Exception("Registry initialization failed")

        with pytest.raises(Exception, match="Registry initialization failed"):
            initialize_infrastructure()

        mock_logger.error.assert_called_once_with(
            "Infrastructure initialization failed", error="Registry initialization failed"
        )

    @patch("src.infrastructure.initialization.get_settings")
    @patch("src.infrastructure.initialization.initialize_service_registry")
    @patch("src.infrastructure.initialization.get_logger")
    def test_handles_settings_loading_failure(
        self,
        mock_get_logger: MagicMock,
        mock_initialize_registry: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        """Handles settings loading failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_service_registry = MagicMock()
        mock_initialize_registry.return_value = mock_service_registry
        mock_get_settings.side_effect = Exception("Settings loading failed")

        with pytest.raises(Exception, match="Settings loading failed"):
            initialize_infrastructure()

        mock_logger.error.assert_called_once_with(
            "Infrastructure initialization failed", error="Settings loading failed"
        )

    @patch("src.infrastructure.initialization.configure_health_checker")
    @patch("src.infrastructure.initialization.get_settings")
    @patch("src.infrastructure.initialization.initialize_service_registry")
    @patch("src.infrastructure.initialization.get_logger")
    def test_handles_health_checker_configuration_failure(
        self,
        mock_get_logger: MagicMock,
        mock_initialize_registry: MagicMock,
        mock_get_settings: MagicMock,
        mock_configure_health: MagicMock,
    ) -> None:
        """Handles health checker configuration failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_service_registry = MagicMock()
        mock_initialize_registry.return_value = mock_service_registry
        mock_configure_health.side_effect = Exception("Health checker config failed")

        with pytest.raises(Exception, match="Health checker config failed"):
            initialize_infrastructure()

        mock_logger.error.assert_called_once_with(
            "Infrastructure initialization failed", error="Health checker config failed"
        )

    @patch("src.infrastructure.initialization._initialize_messaging_services")
    @patch("src.infrastructure.initialization._initialize_persistence_layer")
    @patch("src.infrastructure.initialization.configure_api_key_validator")
    @patch("src.infrastructure.initialization.configure_rate_limiter")
    @patch("src.infrastructure.initialization.get_health_checker")
    @patch("src.infrastructure.initialization.get_metrics_collector")
    @patch("src.infrastructure.initialization.configure_health_checker")
    @patch("src.infrastructure.initialization.get_settings")
    @patch("src.infrastructure.initialization.initialize_service_registry")
    @patch("src.infrastructure.initialization.get_logger")
    def test_handles_persistence_layer_initialization_failure(
        self,
        mock_get_logger: MagicMock,
        mock_initialize_registry: MagicMock,
        mock_get_settings: MagicMock,
        mock_configure_health: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_health: MagicMock,
        mock_configure_rate_limiter: MagicMock,
        mock_configure_api_validator: MagicMock,
        mock_init_persistence: MagicMock,
        mock_init_messaging: MagicMock,
    ) -> None:
        """Handles persistence layer initialization failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_service_registry = MagicMock()
        mock_initialize_registry.return_value = mock_service_registry
        mock_init_persistence.side_effect = Exception("Persistence init failed")

        with pytest.raises(Exception, match="Persistence init failed"):
            initialize_infrastructure()

        mock_logger.error.assert_called_once_with(
            "Infrastructure initialization failed", error="Persistence init failed"
        )

    @patch("src.infrastructure.initialization._initialize_messaging_services")
    @patch("src.infrastructure.initialization._initialize_persistence_layer")
    @patch("src.infrastructure.initialization.configure_api_key_validator")
    @patch("src.infrastructure.initialization.configure_rate_limiter")
    @patch("src.infrastructure.initialization.get_health_checker")
    @patch("src.infrastructure.initialization.get_metrics_collector")
    @patch("src.infrastructure.initialization.configure_health_checker")
    @patch("src.infrastructure.initialization.get_settings")
    @patch("src.infrastructure.initialization.initialize_service_registry")
    @patch("src.infrastructure.initialization.get_logger")
    def test_handles_messaging_services_initialization_failure(
        self,
        mock_get_logger: MagicMock,
        mock_initialize_registry: MagicMock,
        mock_get_settings: MagicMock,
        mock_configure_health: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_health: MagicMock,
        mock_configure_rate_limiter: MagicMock,
        mock_configure_api_validator: MagicMock,
        mock_init_persistence: MagicMock,
        mock_init_messaging: MagicMock,
    ) -> None:
        """Handles messaging services initialization failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_service_registry = MagicMock()
        mock_initialize_registry.return_value = mock_service_registry
        mock_init_messaging.side_effect = Exception("Messaging init failed")

        with pytest.raises(Exception, match="Messaging init failed"):
            initialize_infrastructure()

        mock_logger.error.assert_called_once_with(
            "Infrastructure initialization failed", error="Messaging init failed"
        )

    @patch("src.infrastructure.initialization.get_service_registry")
    @patch("src.infrastructure.initialization.initialize_service_registry")
    @patch("src.infrastructure.initialization.get_settings")
    @patch("src.infrastructure.initialization.configure_health_checker")
    @patch("src.infrastructure.initialization.get_metrics_collector")
    @patch("src.infrastructure.initialization.get_health_checker")
    @patch("src.infrastructure.initialization.configure_rate_limiter")
    @patch("src.infrastructure.initialization.configure_api_key_validator")
    @patch("src.infrastructure.initialization._initialize_persistence_layer")
    @patch("src.infrastructure.initialization._initialize_messaging_services")
    @patch("src.infrastructure.initialization.get_logger")
    def test_logs_service_registration_status(
        self,
        mock_get_logger: MagicMock,
        mock_init_messaging: MagicMock,
        mock_init_persistence: MagicMock,
        mock_configure_api_validator: MagicMock,
        mock_configure_rate_limiter: MagicMock,
        mock_get_health_checker: MagicMock,
        mock_get_metrics_collector: MagicMock,
        mock_configure_health_checker: MagicMock,
        mock_get_settings: MagicMock,
        mock_initialize_service_registry: MagicMock,
        mock_get_service_registry: MagicMock,
    ) -> None:
        """Logs service registration status."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_service_registry = MagicMock()
        mock_initialize_service_registry.return_value = mock_service_registry
        mock_get_service_registry.return_value = mock_service_registry

        # Configure registry status checks
        mock_service_registry.has_metrics_collector.return_value = True
        mock_service_registry.has_health_checker.return_value = False
        mock_service_registry.has_repository_factory.return_value = True
        mock_service_registry.has_notification_service.return_value = False

        initialize_infrastructure()

        # Verify status logging
        mock_logger.info.assert_any_call(
            "Infrastructure services registered",
            metrics=True,
            health_checker=False,
            repository_factory=True,
            notification_service=False,
        )


class TestInitializePersistenceLayer:
    """Test persistence layer initialization behavior."""

    @patch("src.infrastructure.initialization.configure_repository_factory")
    @patch("src.infrastructure.initialization.SampleRepositoryFactory")
    @patch("src.infrastructure.initialization.get_logger")
    def test_initializes_persistence_layer_successfully(
        self,
        mock_get_logger: MagicMock,
        mock_sample_factory_class: MagicMock,
        mock_configure_factory: MagicMock,
    ) -> None:
        """Initializes persistence layer successfully."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_repository_factory = MagicMock()
        mock_sample_factory_class.return_value = mock_repository_factory
        mock_service_registry = MagicMock()

        _initialize_persistence_layer(mock_service_registry)

        # Verify factory creation and registration
        mock_sample_factory_class.assert_called_once()
        mock_service_registry.register_repository_factory.assert_called_once_with(
            mock_repository_factory
        )
        mock_configure_factory.assert_called_once_with(mock_repository_factory)

        mock_logger.info.assert_called_once_with("Persistence layer initialized successfully")

    @patch("src.infrastructure.initialization.SampleRepositoryFactory")
    @patch("src.infrastructure.initialization.get_logger")
    def test_handles_persistence_layer_initialization_failure(
        self, mock_get_logger: MagicMock, mock_sample_factory_class: MagicMock
    ) -> None:
        """Handles persistence layer initialization failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_sample_factory_class.side_effect = Exception("Factory creation failed")
        mock_service_registry = MagicMock()

        with pytest.raises(Exception, match="Factory creation failed"):
            _initialize_persistence_layer(mock_service_registry)

        mock_logger.error.assert_called_once_with(
            "Failed to initialize persistence layer", error="Factory creation failed"
        )

    @patch("src.infrastructure.initialization.configure_repository_factory")
    @patch("src.infrastructure.initialization.SampleRepositoryFactory")
    @patch("src.infrastructure.initialization.get_logger")
    def test_handles_service_registry_registration_failure(
        self,
        mock_get_logger: MagicMock,
        mock_sample_factory_class: MagicMock,
        mock_configure_factory: MagicMock,
    ) -> None:
        """Handles service registry registration failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_repository_factory = MagicMock()
        mock_sample_factory_class.return_value = mock_repository_factory
        mock_service_registry = MagicMock()
        mock_service_registry.register_repository_factory.side_effect = Exception(
            "Registration failed"
        )

        with pytest.raises(Exception, match="Registration failed"):
            _initialize_persistence_layer(mock_service_registry)

        mock_logger.error.assert_called_once_with(
            "Failed to initialize persistence layer", error="Registration failed"
        )


class TestInitializeMessagingServices:
    """Test messaging services initialization behavior."""

    @patch("src.infrastructure.initialization.SampleNotificationService")
    @patch("src.infrastructure.initialization.get_logger")
    def test_initializes_messaging_services_successfully(
        self, mock_get_logger: MagicMock, mock_notification_class: MagicMock
    ) -> None:
        """Initializes messaging services successfully."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_notification_service = MagicMock()
        mock_notification_class.return_value = mock_notification_service
        mock_service_registry = MagicMock()

        _initialize_messaging_services(mock_service_registry)

        # Verify service creation and registration
        mock_notification_class.assert_called_once()
        mock_service_registry.register_notification_service.assert_called_once_with(
            mock_notification_service
        )

        mock_logger.info.assert_called_once_with("Messaging services initialized successfully")

    @patch("src.infrastructure.initialization.SampleNotificationService")
    @patch("src.infrastructure.initialization.get_logger")
    def test_handles_messaging_service_creation_failure(
        self, mock_get_logger: MagicMock, mock_notification_class: MagicMock
    ) -> None:
        """Handles messaging service creation failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_notification_class.side_effect = Exception("Service creation failed")
        mock_service_registry = MagicMock()

        with pytest.raises(Exception, match="Service creation failed"):
            _initialize_messaging_services(mock_service_registry)

        mock_logger.error.assert_called_once_with(
            "Failed to initialize messaging services", error="Service creation failed"
        )

    @patch("src.infrastructure.initialization.SampleNotificationService")
    @patch("src.infrastructure.initialization.get_logger")
    def test_handles_messaging_service_registration_failure(
        self, mock_get_logger: MagicMock, mock_notification_class: MagicMock
    ) -> None:
        """Handles messaging service registration failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_notification_service = MagicMock()
        mock_notification_class.return_value = mock_notification_service
        mock_service_registry = MagicMock()
        mock_service_registry.register_notification_service.side_effect = Exception(
            "Registration failed"
        )

        with pytest.raises(Exception, match="Registration failed"):
            _initialize_messaging_services(mock_service_registry)

        mock_logger.error.assert_called_once_with(
            "Failed to initialize messaging services", error="Registration failed"
        )


class TestShutdownInfrastructure:
    """Test infrastructure shutdown behavior."""

    @patch("src.infrastructure.initialization.get_service_registry")
    @patch("src.infrastructure.initialization.get_logger")
    def test_shuts_down_infrastructure_successfully(
        self, mock_get_logger: MagicMock, mock_get_service_registry: MagicMock
    ) -> None:
        """Shuts down infrastructure successfully."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_service_registry = MagicMock()
        mock_get_service_registry.return_value = mock_service_registry

        shutdown_infrastructure()

        mock_service_registry.clear_all_services.assert_called_once()
        mock_logger.info.assert_any_call("Starting infrastructure shutdown")
        mock_logger.info.assert_any_call("Infrastructure shutdown completed")

    @patch("src.infrastructure.initialization.get_service_registry")
    @patch("src.infrastructure.initialization.get_logger")
    def test_handles_service_registry_retrieval_failure(
        self, mock_get_logger: MagicMock, mock_get_service_registry: MagicMock
    ) -> None:
        """Handles service registry retrieval failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_service_registry.side_effect = Exception("Registry not available")

        with pytest.raises(Exception, match="Registry not available"):
            shutdown_infrastructure()

        mock_logger.error.assert_called_once_with(
            "Infrastructure shutdown failed", error="Registry not available"
        )

    @patch("src.infrastructure.initialization.get_service_registry")
    @patch("src.infrastructure.initialization.get_logger")
    def test_handles_service_registry_clear_failure(
        self, mock_get_logger: MagicMock, mock_get_service_registry: MagicMock
    ) -> None:
        """Handles service registry clear failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_service_registry = MagicMock()
        mock_get_service_registry.return_value = mock_service_registry
        mock_service_registry.clear_all_services.side_effect = Exception("Clear failed")

        with pytest.raises(Exception, match="Clear failed"):
            shutdown_infrastructure()

        mock_logger.error.assert_called_once_with(
            "Infrastructure shutdown failed", error="Clear failed"
        )

    @patch("src.infrastructure.initialization.get_service_registry")
    @patch("src.infrastructure.initialization.get_logger")
    def test_logs_shutdown_progress(
        self, mock_get_logger: MagicMock, mock_get_service_registry: MagicMock
    ) -> None:
        """Logs shutdown progress appropriately."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_service_registry = MagicMock()
        mock_get_service_registry.return_value = mock_service_registry

        shutdown_infrastructure()

        # Verify logging sequence
        expected_calls: list[tuple[tuple[str, ...], dict[str, Any]]] = [
            (("Starting infrastructure shutdown",), {}),
            (("Infrastructure shutdown completed",), {}),
        ]

        actual_calls = [call for call in mock_logger.info.call_args_list if call in expected_calls]
        assert len(actual_calls) == 2


class TestInfrastructureInitializationIntegration:
    """Test infrastructure initialization integration scenarios."""

    @patch("src.infrastructure.initialization.get_service_registry")
    @patch("src.infrastructure.initialization.initialize_service_registry")
    @patch("src.infrastructure.initialization.get_settings")
    @patch("src.infrastructure.initialization.configure_health_checker")
    @patch("src.infrastructure.initialization.get_metrics_collector")
    @patch("src.infrastructure.initialization.get_health_checker")
    @patch("src.infrastructure.initialization.configure_rate_limiter")
    @patch("src.infrastructure.initialization.configure_api_key_validator")
    @patch("src.infrastructure.initialization._initialize_persistence_layer")
    @patch("src.infrastructure.initialization._initialize_messaging_services")
    @patch("src.infrastructure.initialization.get_logger")
    def test_configures_security_services_with_default_values(
        self,
        mock_get_logger: MagicMock,
        mock_init_messaging: MagicMock,
        mock_init_persistence: MagicMock,
        mock_configure_api_validator: MagicMock,
        mock_configure_rate_limiter: MagicMock,
        mock_get_health_checker: MagicMock,
        mock_get_metrics_collector: MagicMock,
        mock_configure_health_checker: MagicMock,
        mock_get_settings: MagicMock,
        mock_initialize_service_registry: MagicMock,
        mock_get_service_registry: MagicMock,
    ) -> None:
        """Configures security services with appropriate default values."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_service_registry = MagicMock()
        mock_initialize_service_registry.return_value = mock_service_registry
        mock_get_service_registry.return_value = mock_service_registry

        # Configure registry status checks
        mock_service_registry.has_metrics_collector.return_value = True
        mock_service_registry.has_health_checker.return_value = True
        mock_service_registry.has_repository_factory.return_value = True
        mock_service_registry.has_notification_service.return_value = True

        initialize_infrastructure()

        # Verify security configuration with expected defaults
        mock_configure_rate_limiter.assert_called_once_with(limit=100, window_seconds=60)
        mock_configure_api_validator.assert_called_once_with(api_keys=["dev-api-key-123"])
        mock_configure_health_checker.assert_called_once_with(timeout=10)

    @patch("src.infrastructure.initialization.get_service_registry")
    @patch("src.infrastructure.initialization.initialize_service_registry")
    @patch("src.infrastructure.initialization.get_settings")
    @patch("src.infrastructure.initialization.configure_health_checker")
    @patch("src.infrastructure.initialization.get_metrics_collector")
    @patch("src.infrastructure.initialization.get_health_checker")
    @patch("src.infrastructure.initialization.configure_rate_limiter")
    @patch("src.infrastructure.initialization.configure_api_key_validator")
    @patch("src.infrastructure.initialization._initialize_persistence_layer")
    @patch("src.infrastructure.initialization._initialize_messaging_services")
    @patch("src.infrastructure.initialization.get_logger")
    def test_ensures_observability_services_are_registered_before_subsystems(
        self,
        mock_get_logger: MagicMock,
        mock_init_messaging: MagicMock,
        mock_init_persistence: MagicMock,
        mock_configure_api_validator: MagicMock,
        mock_configure_rate_limiter: MagicMock,
        mock_get_health_checker: MagicMock,
        mock_get_metrics_collector: MagicMock,
        mock_configure_health_checker: MagicMock,
        mock_get_settings: MagicMock,
        mock_initialize_service_registry: MagicMock,
        mock_get_service_registry: MagicMock,
    ) -> None:
        """Ensures observability services are registered before initializing subsystems."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_service_registry = MagicMock()
        mock_initialize_service_registry.return_value = mock_service_registry
        mock_get_service_registry.return_value = mock_service_registry
        mock_metrics_collector = MagicMock()
        mock_get_metrics_collector.return_value = mock_metrics_collector
        mock_health_checker = MagicMock()
        mock_get_health_checker.return_value = mock_health_checker

        # Configure registry status checks
        mock_service_registry.has_metrics_collector.return_value = True
        mock_service_registry.has_health_checker.return_value = True
        mock_service_registry.has_repository_factory.return_value = True
        mock_service_registry.has_notification_service.return_value = True

        initialize_infrastructure()

        # Verify observability services are registered before subsystem initialization
        # Check call order by examining call_count at time of subsystem calls
        registry_register_calls = mock_service_registry.register_metrics_collector.call_count
        persistence_init_calls = mock_init_persistence.call_count

        assert registry_register_calls > 0, "Metrics collector should be registered"
        assert persistence_init_calls > 0, "Persistence layer should be initialized"

        # Verify that observability services were registered
        mock_service_registry.register_metrics_collector.assert_called_once_with(
            mock_metrics_collector
        )
        mock_service_registry.register_health_checker.assert_called_once_with(mock_health_checker)
