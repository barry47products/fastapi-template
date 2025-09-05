"""Unit tests for service registry infrastructure."""

# pylint: disable=redefined-outer-name

from unittest.mock import MagicMock

import pytest

from src.infrastructure.observability import MetricsCollector
from src.infrastructure.service_registry import (
    clear_service_registry,
    get_service_registry,
    initialize_service_registry,
    ServiceRegistry,
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
        client = MagicMock()

        # Act
        registry.register_metrics_collector(collector)
        registry.register_repository_factory(factory)
        registry.register_firestore_client(client)

        # Assert
        assert registry.has_metrics_collector()
        assert registry.has_repository_factory()
        assert registry.has_firestore_client()

        assert registry.get_metrics_collector() is collector
        assert registry.get_repository_factory() is factory
        assert registry.get_firestore_client() is client
