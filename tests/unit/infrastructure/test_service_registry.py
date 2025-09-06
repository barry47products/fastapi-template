"""Unit tests for service registry infrastructure."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.infrastructure.observability import MetricsCollector
from src.infrastructure.service_registry import (
    ServiceRegistry,
    clear_service_registry,
    get_service_registry,
    initialize_service_registry,
)
from src.shared.exceptions import ServiceNotConfiguredException


class TestServiceRegistry:
    """Test service registry functionality."""

    def test_should_create_service_registry(self) -> None:
        """Should create service registry instance."""
        # Act
        registry = ServiceRegistry()

        # Assert
        assert registry is not None

    def test_should_register_metrics_collector(self) -> None:
        """Should register metrics collector instance."""
        # Arrange
        registry = ServiceRegistry()
        collector = MetricsCollector()

        # Act
        registry.register_metrics_collector(collector)

        # Assert
        assert registry.has_metrics_collector()
        assert registry.get_metrics_collector() is collector

    def test_should_register_repository_factory(self) -> None:
        """Should register repository factory instance."""
        # Arrange
        registry = ServiceRegistry()
        factory = MagicMock()

        # Act
        registry.register_repository_factory(factory)

        # Assert
        assert registry.has_repository_factory()
        assert registry.get_repository_factory() is factory

    def test_should_handle_missing_metrics_collector(self) -> None:
        """Should handle case when metrics collector not registered."""
        # Arrange
        registry = ServiceRegistry()

        # Act & Assert
        assert not registry.has_metrics_collector()

        with pytest.raises(ServiceNotConfiguredException, match="MetricsCollector not registered"):
            registry.get_metrics_collector()

    def test_should_handle_missing_repository_factory(self) -> None:
        """Should handle case when repository factory not registered."""
        # Arrange
        registry = ServiceRegistry()

        # Act & Assert
        assert not registry.has_repository_factory()

        with pytest.raises(ServiceNotConfiguredException, match="RepositoryFactory not registered"):
            registry.get_repository_factory()

    def test_should_clear_all_services(self) -> None:
        """Should clear all registered services."""
        # Arrange
        registry = ServiceRegistry()
        collector = MetricsCollector()
        factory = MagicMock()

        registry.register_metrics_collector(collector)
        registry.register_repository_factory(factory)

        # Act
        registry.clear_all_services()

        # Assert
        assert not registry.has_metrics_collector()
        assert not registry.has_repository_factory()

    def test_should_check_registered_services_individually(self) -> None:
        """Should check registered services individually."""
        # Arrange
        registry = ServiceRegistry()
        collector = MetricsCollector()
        factory = MagicMock()

        registry.register_metrics_collector(collector)
        registry.register_repository_factory(factory)

        # Act & Assert
        assert registry.has_metrics_collector()
        assert registry.has_repository_factory()
        assert not registry.has_health_checker()
        assert not registry.has_api_key_validator()


class TestServiceRegistryFactoryFunction:
    """Test service registry factory function."""

    def setup_method(self) -> None:
        """Setup test by clearing service registry."""
        clear_service_registry()

    def teardown_method(self) -> None:
        """Cleanup test by clearing service registry."""
        clear_service_registry()

    def test_initialize_service_registry_should_create_instance(self) -> None:
        """Should create and return service registry instance."""
        # Act
        registry = initialize_service_registry()

        # Assert
        assert isinstance(registry, ServiceRegistry)

    def test_get_service_registry_should_return_initialized_instance(self) -> None:
        """Should return initialized service registry instance."""
        # Arrange
        initialize_service_registry()

        # Act
        registry1 = get_service_registry()
        registry2 = get_service_registry()

        # Assert
        assert registry1 is registry2
        assert isinstance(registry1, ServiceRegistry)

    def test_get_service_registry_should_raise_when_not_initialized(self) -> None:
        """Should raise error when service registry not initialized."""
        # Act & Assert
        with pytest.raises(ServiceNotConfiguredException, match="Service registry not initialized"):
            get_service_registry()

    def test_service_registry_should_persist_state_across_calls(self) -> None:
        """Should maintain state across multiple get_service_registry calls."""
        # Arrange
        initialize_service_registry()
        registry1 = get_service_registry()
        collector = MetricsCollector()
        registry1.register_metrics_collector(collector)

        # Act
        registry2 = get_service_registry()

        # Assert
        assert registry2.has_metrics_collector()
        assert registry2.get_metrics_collector() is collector

    def test_clear_service_registry_should_reset_global_state(self) -> None:
        """Should clear global service registry state."""
        # Arrange
        initialize_service_registry()
        registry = get_service_registry()
        collector = MetricsCollector()
        registry.register_metrics_collector(collector)

        # Act
        clear_service_registry()

        # Assert
        with pytest.raises(ServiceNotConfiguredException):
            get_service_registry()


class TestServiceRegistryIntegration:
    """Test service registry integration scenarios."""

    def test_should_support_dependency_injection_pattern(self) -> None:
        """Should support dependency injection for provider matching."""
        # Arrange
        registry = ServiceRegistry()
        collector = MetricsCollector()
        factory = MagicMock()

        # Act - Register dependencies used by provider matcher
        registry.register_metrics_collector(collector)
        registry.register_repository_factory(factory)

        # Assert - Dependencies are available for injection
        assert registry.has_metrics_collector()
        assert registry.has_repository_factory()

        # Simulate provider matcher dependency injection
        injected_collector = registry.get_metrics_collector()
        injected_factory = registry.get_repository_factory()

        assert injected_collector is collector
        assert injected_factory is factory

    def test_should_handle_partial_service_registration(self) -> None:
        """Should handle cases where only some services are registered."""
        # Arrange
        registry = ServiceRegistry()
        collector = MetricsCollector()

        # Act - Register only metrics collector
        registry.register_metrics_collector(collector)

        # Assert
        assert registry.has_metrics_collector()
        assert not registry.has_repository_factory()

        # Should be able to get metrics collector
        assert registry.get_metrics_collector() is collector

        # Should raise error for missing factory
        with pytest.raises(ServiceNotConfiguredException):
            registry.get_repository_factory()

    def test_should_support_service_replacement(self) -> None:
        """Should support replacing registered services."""
        # Arrange
        registry = ServiceRegistry()
        collector1 = MetricsCollector()
        collector2 = MetricsCollector()

        registry.register_metrics_collector(collector1)

        # Act - Replace with new collector
        registry.register_metrics_collector(collector2)

        # Assert
        assert registry.get_metrics_collector() is collector2
        assert registry.get_metrics_collector() is not collector1

    def test_should_register_multiple_service_types(self) -> None:
        """Should register and manage multiple service types."""
        # Arrange
        registry = ServiceRegistry()
        collector = MetricsCollector()
        factory = MagicMock()

        # Act
        registry.register_metrics_collector(collector)
        registry.register_repository_factory(factory)

        # Assert
        assert registry.has_metrics_collector()
        assert registry.has_repository_factory()

        assert registry.get_metrics_collector() is collector
        assert registry.get_repository_factory() is factory


class TestServiceRegistryHealthChecker:
    """Test service registry health checker functionality."""

    def test_register_and_get_health_checker(self) -> None:
        """Should register and retrieve health checker service."""
        registry = ServiceRegistry()
        health_checker = MagicMock()

        registry.register_health_checker(health_checker)

        assert registry.has_health_checker()
        assert registry.get_health_checker() is health_checker

    def test_get_health_checker_raises_when_not_registered(self) -> None:
        """Should raise error when health checker not registered."""
        registry = ServiceRegistry()

        assert not registry.has_health_checker()
        with pytest.raises(ServiceNotConfiguredException, match="HealthChecker not registered"):
            registry.get_health_checker()


class TestServiceRegistryAPIKeyValidator:
    """Test service registry API key validator functionality."""

    def test_register_and_get_api_key_validator(self) -> None:
        """Should register and retrieve API key validator service."""
        registry = ServiceRegistry()
        api_key_validator = MagicMock()

        registry.register_api_key_validator(api_key_validator)

        assert registry.has_api_key_validator()
        assert registry.get_api_key_validator() is api_key_validator

    def test_get_api_key_validator_raises_when_not_registered(self) -> None:
        """Should raise error when API key validator not registered."""
        registry = ServiceRegistry()

        assert not registry.has_api_key_validator()
        with pytest.raises(ServiceNotConfiguredException, match="APIKeyValidator not registered"):
            registry.get_api_key_validator()


class TestServiceRegistryRateLimiter:
    """Test service registry rate limiter functionality."""

    def test_register_and_get_rate_limiter(self) -> None:
        """Should register and retrieve rate limiter service."""
        registry = ServiceRegistry()
        rate_limiter = MagicMock()

        registry.register_rate_limiter(rate_limiter)

        assert registry.has_rate_limiter()
        assert registry.get_rate_limiter() is rate_limiter

    def test_get_rate_limiter_raises_when_not_registered(self) -> None:
        """Should raise error when rate limiter not registered."""
        registry = ServiceRegistry()

        assert not registry.has_rate_limiter()
        with pytest.raises(ServiceNotConfiguredException, match="RateLimiter not registered"):
            registry.get_rate_limiter()


class TestServiceRegistryWebhookVerifier:
    """Test service registry webhook verifier functionality."""

    def test_register_and_get_webhook_verifier(self) -> None:
        """Should register and retrieve webhook verifier service."""
        registry = ServiceRegistry()
        webhook_verifier = MagicMock()

        registry.register_webhook_verifier(webhook_verifier)

        assert registry.has_webhook_verifier()
        assert registry.get_webhook_verifier() is webhook_verifier

    def test_get_webhook_verifier_raises_when_not_registered(self) -> None:
        """Should raise error when webhook verifier not registered."""
        registry = ServiceRegistry()

        assert not registry.has_webhook_verifier()
        with pytest.raises(ServiceNotConfiguredException, match="WebhookVerifier not registered"):
            registry.get_webhook_verifier()


class TestServiceRegistryFeatureFlagManager:
    """Test service registry feature flag manager functionality."""

    def test_register_and_get_feature_flag_manager(self) -> None:
        """Should register and retrieve feature flag manager service."""
        registry = ServiceRegistry()
        feature_flag_manager = MagicMock()

        registry.register_feature_flag_manager(feature_flag_manager)

        assert registry.has_feature_flag_manager()
        assert registry.get_feature_flag_manager() is feature_flag_manager

    def test_get_feature_flag_manager_raises_when_not_registered(self) -> None:
        """Should raise error when feature flag manager not registered."""
        registry = ServiceRegistry()

        assert not registry.has_feature_flag_manager()
        with pytest.raises(
            ServiceNotConfiguredException, match="FeatureFlagManager not registered"
        ):
            registry.get_feature_flag_manager()


class TestServiceRegistryNotificationService:
    """Test service registry notification service functionality."""

    def test_register_and_get_notification_service(self) -> None:
        """Should register and retrieve notification service."""
        registry = ServiceRegistry()
        notification_service = MagicMock()

        registry.register_notification_service(notification_service)

        assert registry.has_notification_service()
        assert registry.get_notification_service() is notification_service

    def test_get_notification_service_raises_when_not_registered(self) -> None:
        """Should raise error when notification service not registered."""
        registry = ServiceRegistry()

        assert not registry.has_notification_service()
        with pytest.raises(
            ServiceNotConfiguredException, match="SampleNotificationService not registered"
        ):
            registry.get_notification_service()


class TestServiceRegistryClearAllServices:
    """Test service registry clear all services functionality."""

    def test_clear_all_services_resets_all_services(self) -> None:
        """Should clear all registered services."""
        registry = ServiceRegistry()

        # Register all types of services
        registry.register_metrics_collector(MetricsCollector())
        registry.register_health_checker(MagicMock())
        registry.register_api_key_validator(MagicMock())
        registry.register_rate_limiter(MagicMock())
        registry.register_webhook_verifier(MagicMock())
        registry.register_feature_flag_manager(MagicMock())
        registry.register_repository_factory(MagicMock())
        registry.register_notification_service(MagicMock())

        # Verify all are registered
        assert registry.has_metrics_collector()
        assert registry.has_health_checker()
        assert registry.has_api_key_validator()
        assert registry.has_rate_limiter()
        assert registry.has_webhook_verifier()
        assert registry.has_feature_flag_manager()
        assert registry.has_repository_factory()
        assert registry.has_notification_service()

        # Clear all services
        registry.clear_all_services()

        # Verify all are cleared
        assert not registry.has_metrics_collector()
        assert not registry.has_health_checker()
        assert not registry.has_api_key_validator()
        assert not registry.has_rate_limiter()
        assert not registry.has_webhook_verifier()
        assert not registry.has_feature_flag_manager()
        assert not registry.has_repository_factory()
        assert not registry.has_notification_service()


class TestServiceRegistryGlobalFunctions:
    """Test service registry global function edge cases."""

    def setup_method(self) -> None:
        """Setup test by clearing service registry."""
        clear_service_registry()

    def teardown_method(self) -> None:
        """Cleanup test by clearing service registry."""
        clear_service_registry()

    def test_clear_service_registry_with_none_registry(self) -> None:
        """Should handle clearing when registry is None."""
        # Ensure registry is None
        clear_service_registry()

        # Should not raise error when clearing None registry
        clear_service_registry()

        # Should still raise error when trying to get
        with pytest.raises(ServiceNotConfiguredException, match="Service registry not initialized"):
            get_service_registry()

    def test_clear_service_registry_clears_registered_services(self) -> None:
        """Should clear registered services when clearing registry."""
        # Initialize and register services
        registry = initialize_service_registry()
        registry.register_metrics_collector(MetricsCollector())
        registry.register_health_checker(MagicMock())

        # Verify services are registered
        assert registry.has_metrics_collector()
        assert registry.has_health_checker()

        # Clear registry
        clear_service_registry()

        # Should not be able to get registry anymore
        with pytest.raises(ServiceNotConfiguredException, match="Service registry not initialized"):
            get_service_registry()

    def test_initialize_service_registry_twice(self) -> None:
        """Should handle initializing service registry multiple times."""
        registry1 = initialize_service_registry()
        registry2 = initialize_service_registry()

        # Should create new instance each time
        assert isinstance(registry1, ServiceRegistry)
        assert isinstance(registry2, ServiceRegistry)

        # Latest initialization should be the active one
        current_registry = get_service_registry()
        assert current_registry is registry2


class TestServiceRegistryComprehensiveScenarios:
    """Test comprehensive service registry usage scenarios."""

    def test_all_services_registration_and_retrieval(self) -> None:
        """Should handle registration and retrieval of all service types."""
        registry = ServiceRegistry()

        # Create mock services
        metrics_collector = MetricsCollector()
        health_checker = MagicMock()
        api_key_validator = MagicMock()
        rate_limiter = MagicMock()
        webhook_verifier = MagicMock()
        feature_flag_manager = MagicMock()
        repository_factory = MagicMock()
        notification_service = MagicMock()

        # Register all services
        registry.register_metrics_collector(metrics_collector)
        registry.register_health_checker(health_checker)
        registry.register_api_key_validator(api_key_validator)
        registry.register_rate_limiter(rate_limiter)
        registry.register_webhook_verifier(webhook_verifier)
        registry.register_feature_flag_manager(feature_flag_manager)
        registry.register_repository_factory(repository_factory)
        registry.register_notification_service(notification_service)

        # Verify all services can be retrieved
        assert registry.get_metrics_collector() is metrics_collector
        assert registry.get_health_checker() is health_checker
        assert registry.get_api_key_validator() is api_key_validator
        assert registry.get_rate_limiter() is rate_limiter
        assert registry.get_webhook_verifier() is webhook_verifier
        assert registry.get_feature_flag_manager() is feature_flag_manager
        assert registry.get_repository_factory() is repository_factory
        assert registry.get_notification_service() is notification_service

        # Verify all has_* methods return True
        assert registry.has_metrics_collector()
        assert registry.has_health_checker()
        assert registry.has_api_key_validator()
        assert registry.has_rate_limiter()
        assert registry.has_webhook_verifier()
        assert registry.has_feature_flag_manager()
        assert registry.has_repository_factory()
        assert registry.has_notification_service()

    def test_service_replacement_scenarios(self) -> None:
        """Should handle service replacement for all service types."""
        registry = ServiceRegistry()

        # Register initial services
        registry.register_health_checker(MagicMock())
        registry.register_api_key_validator(MagicMock())
        registry.register_rate_limiter(MagicMock())
        registry.register_webhook_verifier(MagicMock())
        registry.register_feature_flag_manager(MagicMock())
        registry.register_notification_service(MagicMock())

        # Create replacement services
        new_health_checker = MagicMock()
        new_api_key_validator = MagicMock()
        new_rate_limiter = MagicMock()
        new_webhook_verifier = MagicMock()
        new_feature_flag_manager = MagicMock()
        new_notification_service = MagicMock()

        # Replace services
        registry.register_health_checker(new_health_checker)
        registry.register_api_key_validator(new_api_key_validator)
        registry.register_rate_limiter(new_rate_limiter)
        registry.register_webhook_verifier(new_webhook_verifier)
        registry.register_feature_flag_manager(new_feature_flag_manager)
        registry.register_notification_service(new_notification_service)

        # Verify new services are returned
        assert registry.get_health_checker() is new_health_checker
        assert registry.get_api_key_validator() is new_api_key_validator
        assert registry.get_rate_limiter() is new_rate_limiter
        assert registry.get_webhook_verifier() is new_webhook_verifier
        assert registry.get_feature_flag_manager() is new_feature_flag_manager
        assert registry.get_notification_service() is new_notification_service

    def test_mixed_service_states(self) -> None:
        """Should handle scenarios with mixed service registration states."""
        registry = ServiceRegistry()

        # Register only some services
        registry.register_metrics_collector(MetricsCollector())
        registry.register_api_key_validator(MagicMock())
        registry.register_feature_flag_manager(MagicMock())

        # Verify registered services are available
        assert registry.has_metrics_collector()
        assert registry.has_api_key_validator()
        assert registry.has_feature_flag_manager()

        # Verify unregistered services are not available
        assert not registry.has_health_checker()
        assert not registry.has_rate_limiter()
        assert not registry.has_webhook_verifier()
        assert not registry.has_repository_factory()
        assert not registry.has_notification_service()

        # Verify errors are raised for unregistered services
        with pytest.raises(ServiceNotConfiguredException, match="HealthChecker not registered"):
            registry.get_health_checker()
        with pytest.raises(ServiceNotConfiguredException, match="RateLimiter not registered"):
            registry.get_rate_limiter()
        with pytest.raises(ServiceNotConfiguredException, match="WebhookVerifier not registered"):
            registry.get_webhook_verifier()
        with pytest.raises(ServiceNotConfiguredException, match="RepositoryFactory not registered"):
            registry.get_repository_factory()
        with pytest.raises(
            ServiceNotConfiguredException, match="SampleNotificationService not registered"
        ):
            registry.get_notification_service()
