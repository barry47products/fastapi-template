"""Unit tests for repository factory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.persistence.repositories import (
    InMemoryProductRepository,
    InMemoryUserRepository,
)
from src.infrastructure.persistence.repository_factory import (
    RepositoryFactoryRegistry,
    SampleRepositoryFactory,
    configure_repository_factory,
    get_product_repository,
    get_repository_factory,
    get_user_repository,
)


class MockRepositoryFactory:
    """Mock repository factory for testing."""

    def __init__(self, should_fail: bool = False) -> None:
        """Initialize mock factory."""
        self.should_fail = should_fail
        self.create_user_repository_called = False
        self.create_product_repository_called = False

    def create_user_repository(self) -> InMemoryUserRepository:
        """Create mock user repository."""
        self.create_user_repository_called = True
        if self.should_fail:
            raise RuntimeError("Mock user repository creation failed")
        return InMemoryUserRepository()

    def create_product_repository(self) -> InMemoryProductRepository:
        """Create mock product repository."""
        self.create_product_repository_called = True
        if self.should_fail:
            raise RuntimeError("Mock product repository creation failed")
        return InMemoryProductRepository()


class TestSampleRepositoryFactory:
    """Test SampleRepositoryFactory class functionality."""

    @patch("src.infrastructure.persistence.repository_factory.get_logger")
    def test_initializes_with_logger_and_none_repositories(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Factory initializes with logger and repositories as None."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        factory = SampleRepositoryFactory()

        assert factory.logger is mock_logger
        assert factory._user_repository is None
        assert factory._product_repository is None

    @patch("src.infrastructure.persistence.repository_factory.get_logger")
    def test_creates_user_repository_on_first_call(self, mock_get_logger: MagicMock) -> None:
        """Creates user repository on first call and logs success."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        factory = SampleRepositoryFactory()

        user_repo = factory.create_user_repository()

        assert isinstance(user_repo, InMemoryUserRepository)
        assert factory._user_repository is user_repo
        mock_logger.debug.assert_called_once_with("User repository created successfully")

    @patch("src.infrastructure.persistence.repository_factory.get_logger")
    def test_returns_same_user_repository_instance_on_subsequent_calls(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Returns same user repository instance on subsequent calls."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        factory = SampleRepositoryFactory()

        user_repo1 = factory.create_user_repository()
        user_repo2 = factory.create_user_repository()

        assert user_repo1 is user_repo2
        # Should be called twice (once per call)
        assert mock_logger.debug.call_count == 2

    @patch("src.infrastructure.persistence.repository_factory.get_logger")
    def test_creates_product_repository_on_first_call(self, mock_get_logger: MagicMock) -> None:
        """Creates product repository on first call and logs success."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        factory = SampleRepositoryFactory()

        product_repo = factory.create_product_repository()

        assert isinstance(product_repo, InMemoryProductRepository)
        assert factory._product_repository is product_repo
        mock_logger.debug.assert_called_once_with("Product repository created successfully")

    @patch("src.infrastructure.persistence.repository_factory.get_logger")
    def test_returns_same_product_repository_instance_on_subsequent_calls(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Returns same product repository instance on subsequent calls."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        factory = SampleRepositoryFactory()

        product_repo1 = factory.create_product_repository()
        product_repo2 = factory.create_product_repository()

        assert product_repo1 is product_repo2
        assert mock_logger.debug.call_count == 2

    @patch("src.infrastructure.persistence.repository_factory.InMemoryUserRepository")
    @patch("src.infrastructure.persistence.repository_factory.get_logger")
    def test_logs_error_and_reraises_user_repository_creation_failure(
        self, mock_get_logger: MagicMock, mock_user_repo_class: MagicMock
    ) -> None:
        """Logs error and re-raises exception when user repository creation fails."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_user_repo_class.side_effect = RuntimeError("Database connection failed")

        factory = SampleRepositoryFactory()

        with pytest.raises(RuntimeError, match="Database connection failed"):
            factory.create_user_repository()

        mock_logger.error.assert_called_once_with(
            "Failed to create user repository", error="Database connection failed"
        )

    @patch("src.infrastructure.persistence.repository_factory.InMemoryProductRepository")
    @patch("src.infrastructure.persistence.repository_factory.get_logger")
    def test_logs_error_and_reraises_product_repository_creation_failure(
        self, mock_get_logger: MagicMock, mock_product_repo_class: MagicMock
    ) -> None:
        """Logs error and re-raises exception when product repository creation fails."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_product_repo_class.side_effect = RuntimeError("Connection timeout")

        factory = SampleRepositoryFactory()

        with pytest.raises(RuntimeError, match="Connection timeout"):
            factory.create_product_repository()

        mock_logger.error.assert_called_once_with(
            "Failed to create product repository", error="Connection timeout"
        )

    @patch("src.infrastructure.persistence.repository_factory.get_logger")
    def test_health_check_returns_true_when_repositories_created_successfully(
        self, mock_get_logger: MagicMock
    ) -> None:
        """Health check returns True when repositories are created successfully."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        factory = SampleRepositoryFactory()

        result = factory.health_check()

        assert result is True
        mock_logger.debug.assert_called_with("Repository factory health check passed")

    @patch("src.infrastructure.persistence.repository_factory.InMemoryUserRepository")
    @patch("src.infrastructure.persistence.repository_factory.get_logger")
    def test_health_check_returns_false_and_logs_error_on_user_repository_failure(
        self, mock_get_logger: MagicMock, mock_user_repo_class: MagicMock
    ) -> None:
        """Health check returns False and logs error when user repository creation fails."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_user_repo_class.side_effect = RuntimeError("User repository failed")

        factory = SampleRepositoryFactory()

        result = factory.health_check()

        assert result is False
        # Health check logs both repository creation failure AND health check failure
        assert mock_logger.error.call_count == 2
        mock_logger.error.assert_any_call(
            "Failed to create user repository", error="User repository failed"
        )
        mock_logger.error.assert_any_call(
            "Repository factory health check failed", error="User repository failed"
        )

    @patch("src.infrastructure.persistence.repository_factory.InMemoryProductRepository")
    @patch("src.infrastructure.persistence.repository_factory.get_logger")
    def test_health_check_returns_false_and_logs_error_on_product_repository_failure(
        self, mock_get_logger: MagicMock, mock_product_repo_class: MagicMock
    ) -> None:
        """Health check returns False and logs error when product repository creation fails."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        # Mock user repository to succeed, product to fail
        factory = SampleRepositoryFactory()
        factory._user_repository = InMemoryUserRepository()  # Set up successful user repo
        mock_product_repo_class.side_effect = RuntimeError("Product repository failed")

        result = factory.health_check()

        assert result is False
        # Health check logs both repository creation failure AND health check failure
        assert mock_logger.error.call_count == 2
        mock_logger.error.assert_any_call(
            "Failed to create product repository", error="Product repository failed"
        )
        mock_logger.error.assert_any_call(
            "Repository factory health check failed", error="Product repository failed"
        )

    @patch("src.infrastructure.persistence.repository_factory.get_logger")
    def test_health_check_repository_instances_isolation(self, mock_get_logger: MagicMock) -> None:
        """Health check doesn't interfere with existing repository instances."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        factory = SampleRepositoryFactory()

        # Create repositories first
        user_repo = factory.create_user_repository()
        product_repo = factory.create_product_repository()

        # Health check should work with existing instances
        result = factory.health_check()

        assert result is True
        # Repositories should be the same instances
        assert factory._user_repository is user_repo
        assert factory._product_repository is product_repo


class TestRepositoryFactoryRegistry:
    """Test RepositoryFactoryRegistry singleton management."""

    def setup_method(self) -> None:
        """Reset registry state before each test."""
        RepositoryFactoryRegistry._instance = None

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_configure_with_provided_factory(self, mock_get_service_registry: MagicMock) -> None:
        """Configure sets provided factory and registers with service registry."""
        mock_registry = MagicMock()
        mock_registry.register_repository_factory = MagicMock()
        mock_get_service_registry.return_value = mock_registry

        mock_factory = MockRepositoryFactory()
        RepositoryFactoryRegistry.configure(mock_factory)

        assert RepositoryFactoryRegistry._instance is mock_factory
        mock_registry.register_repository_factory.assert_called_once_with(mock_factory)

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_configure_with_none_creates_sample_factory(
        self, mock_get_service_registry: MagicMock
    ) -> None:
        """Configure with None creates SampleRepositoryFactory."""
        mock_registry = MagicMock()
        mock_registry.register_repository_factory = MagicMock()
        mock_get_service_registry.return_value = mock_registry

        RepositoryFactoryRegistry.configure(None)

        assert isinstance(RepositoryFactoryRegistry._instance, SampleRepositoryFactory)
        mock_registry.register_repository_factory.assert_called_once()

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_configure_ignores_service_registry_errors(
        self, mock_get_service_registry: MagicMock
    ) -> None:
        """Configure ignores service registry errors gracefully."""
        mock_get_service_registry.side_effect = ImportError("Service registry not available")

        mock_factory = MockRepositoryFactory()
        RepositoryFactoryRegistry.configure(mock_factory)

        # Should still set the instance despite service registry error
        assert RepositoryFactoryRegistry._instance is mock_factory

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_configure_handles_service_registry_without_method(
        self, mock_get_service_registry: MagicMock
    ) -> None:
        """Configure handles service registry that doesn't have register method."""
        mock_registry = MagicMock()
        # Don't add the register_repository_factory method
        mock_registry.configure_mock()
        mock_get_service_registry.return_value = mock_registry

        mock_factory = MockRepositoryFactory()
        RepositoryFactoryRegistry.configure(mock_factory)

        assert RepositoryFactoryRegistry._instance is mock_factory

    def test_get_instance_returns_configured_factory(self) -> None:
        """Get instance returns previously configured factory."""
        mock_factory = MockRepositoryFactory()
        RepositoryFactoryRegistry._instance = mock_factory

        result = RepositoryFactoryRegistry.get_instance()

        assert result is mock_factory

    def test_get_instance_auto_configures_when_none_set(self) -> None:
        """Get instance auto-configures with SampleRepositoryFactory when none set."""
        result = RepositoryFactoryRegistry.get_instance()

        assert isinstance(result, SampleRepositoryFactory)
        assert RepositoryFactoryRegistry._instance is result

    def test_get_instance_raises_when_configuration_fails(self) -> None:
        """Get instance raises RuntimeError when configuration fails."""
        RepositoryFactoryRegistry._instance = None

        # Mock configure to fail in setting the instance
        with patch.object(RepositoryFactoryRegistry, "configure") as mock_configure:
            mock_configure.return_value = None  # Simulate failure to set instance

            with pytest.raises(RuntimeError, match="Repository factory not configured"):
                RepositoryFactoryRegistry.get_instance()


class TestConfigureRepositoryFactory:
    """Test configure_repository_factory function."""

    def setup_method(self) -> None:
        """Reset registry state before each test."""
        RepositoryFactoryRegistry._instance = None

    def test_configure_repository_factory_delegates_to_registry(self) -> None:
        """configure_repository_factory delegates to RepositoryFactoryRegistry.configure."""
        mock_factory = MockRepositoryFactory()

        with patch.object(RepositoryFactoryRegistry, "configure") as mock_configure:
            configure_repository_factory(mock_factory)
            mock_configure.assert_called_once_with(mock_factory)

    def test_configure_repository_factory_with_none(self) -> None:
        """configure_repository_factory with None creates default factory."""
        with patch.object(RepositoryFactoryRegistry, "configure") as mock_configure:
            configure_repository_factory(None)
            mock_configure.assert_called_once_with(None)


class TestGetRepositoryFactory:
    """Test get_repository_factory function."""

    def setup_method(self) -> None:
        """Reset registry state before each test."""
        RepositoryFactoryRegistry._instance = None

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_returns_factory_from_service_registry_when_available(
        self, mock_get_service_registry: MagicMock
    ) -> None:
        """Returns factory from service registry when available and valid."""
        mock_factory = MockRepositoryFactory()
        mock_registry = MagicMock()
        mock_registry.get_repository_factory.return_value = mock_factory
        mock_get_service_registry.return_value = mock_registry

        result = get_repository_factory()

        assert result is mock_factory

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_falls_back_to_registry_when_service_registry_unavailable(
        self, mock_get_service_registry: MagicMock
    ) -> None:
        """Falls back to registry when service registry is unavailable."""
        mock_get_service_registry.side_effect = ImportError("No service registry")

        result = get_repository_factory()

        # Should get SampleRepositoryFactory from registry fallback
        assert isinstance(result, SampleRepositoryFactory)

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_falls_back_when_service_registry_has_no_method(
        self, mock_get_service_registry: MagicMock
    ) -> None:
        """Falls back when service registry doesn't have get_repository_factory method."""
        mock_registry = MagicMock()
        # Remove the get_repository_factory method
        del mock_registry.get_repository_factory
        mock_get_service_registry.return_value = mock_registry

        result = get_repository_factory()

        assert isinstance(result, SampleRepositoryFactory)

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_falls_back_when_service_registry_method_fails(
        self, mock_get_service_registry: MagicMock
    ) -> None:
        """Falls back when service registry method raises exception."""
        mock_registry = MagicMock()
        mock_registry.get_repository_factory.side_effect = RuntimeError("Registry error")
        mock_get_service_registry.return_value = mock_registry

        result = get_repository_factory()

        assert isinstance(result, SampleRepositoryFactory)

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_falls_back_when_service_registry_returns_none(
        self, mock_get_service_registry: MagicMock
    ) -> None:
        """Falls back when service registry returns None."""
        mock_registry = MagicMock()
        mock_registry.get_repository_factory.return_value = None
        mock_get_service_registry.return_value = mock_registry

        result = get_repository_factory()

        assert isinstance(result, SampleRepositoryFactory)

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_falls_back_when_service_registry_returns_invalid_factory(
        self, mock_get_service_registry: MagicMock
    ) -> None:
        """Falls back when service registry returns object without required methods."""
        invalid_factory = MagicMock()
        # Remove the required methods
        # Remove the required methods to make factory invalid
        if hasattr(invalid_factory, "create_user_repository"):
            del invalid_factory.create_user_repository
        if hasattr(invalid_factory, "create_product_repository"):
            del invalid_factory.create_product_repository
        mock_registry = MagicMock()
        mock_registry.get_repository_factory.return_value = invalid_factory
        mock_get_service_registry.return_value = mock_registry

        result = get_repository_factory()

        # Should fall back to creating a new SampleRepositoryFactory
        assert isinstance(result, SampleRepositoryFactory)

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_validates_factory_protocol_compliance(
        self, mock_get_service_registry: MagicMock
    ) -> None:
        """Validates that factory from service registry implements RepositoryFactory protocol."""
        # Create factory with required methods
        valid_factory = MagicMock()
        valid_factory.create_user_repository = MagicMock()
        valid_factory.create_product_repository = MagicMock()

        mock_registry = MagicMock()
        mock_registry.get_repository_factory.return_value = valid_factory
        mock_get_service_registry.return_value = mock_registry

        result = get_repository_factory()

        assert result is valid_factory

    def test_integration_with_configure_and_get(self) -> None:
        """Integration test: configure factory then retrieve it."""
        mock_factory = MockRepositoryFactory()

        configure_repository_factory(mock_factory)
        result = get_repository_factory()

        assert result is mock_factory


class TestConvenienceFunctions:
    """Test convenience functions for direct repository access."""

    def setup_method(self) -> None:
        """Reset registry state before each test."""
        RepositoryFactoryRegistry._instance = None

    def test_get_user_repository_returns_user_repository_from_factory(self) -> None:
        """get_user_repository returns user repository from configured factory."""
        mock_factory = MockRepositoryFactory()
        configure_repository_factory(mock_factory)

        result = get_user_repository()

        assert isinstance(result, InMemoryUserRepository)
        assert mock_factory.create_user_repository_called

    def test_get_product_repository_returns_product_repository_from_factory(self) -> None:
        """get_product_repository returns product repository from configured factory."""
        mock_factory = MockRepositoryFactory()
        configure_repository_factory(mock_factory)

        result = get_product_repository()

        assert isinstance(result, InMemoryProductRepository)
        assert mock_factory.create_product_repository_called

    def test_convenience_functions_work_with_default_factory(self) -> None:
        """Convenience functions work with auto-configured default factory."""
        user_repo = get_user_repository()
        product_repo = get_product_repository()

        assert isinstance(user_repo, InMemoryUserRepository)
        assert isinstance(product_repo, InMemoryProductRepository)

    def test_convenience_functions_propagate_factory_failures(self) -> None:
        """Convenience functions propagate exceptions from factory methods."""
        failing_factory = MockRepositoryFactory(should_fail=True)
        configure_repository_factory(failing_factory)

        with pytest.raises(RuntimeError, match="Mock user repository creation failed"):
            get_user_repository()

        with pytest.raises(RuntimeError, match="Mock product repository creation failed"):
            get_product_repository()


class TestRepositoryFactoryWorkflows:
    """Test complete repository factory workflows and use cases."""

    def setup_method(self) -> None:
        """Reset registry state before each test."""
        RepositoryFactoryRegistry._instance = None

    def test_typical_factory_lifecycle(self) -> None:
        """Test complete lifecycle of repository factory configuration and usage."""
        # Start with no factory configured
        assert RepositoryFactoryRegistry._instance is None

        # Configure factory
        configure_repository_factory()

        # Verify factory is configured
        factory = get_repository_factory()
        assert isinstance(factory, SampleRepositoryFactory)

        # Use repositories through factory
        user_repo1 = factory.create_user_repository()
        user_repo2 = factory.create_user_repository()
        product_repo1 = factory.create_product_repository()
        product_repo2 = factory.create_product_repository()

        # Verify singleton behavior
        assert user_repo1 is user_repo2
        assert product_repo1 is product_repo2

        # Verify health check
        assert factory.health_check() is True

    def test_factory_replacement_workflow(self) -> None:
        """Test replacing factory configuration during runtime."""
        # Configure initial factory
        initial_factory = SampleRepositoryFactory()
        configure_repository_factory(initial_factory)

        # Verify initial factory is configured
        assert get_repository_factory() is initial_factory

        # Replace with new factory
        replacement_factory = MockRepositoryFactory()
        configure_repository_factory(replacement_factory)

        # Verify replacement took effect
        assert get_repository_factory() is replacement_factory

    def test_factory_error_handling_workflow(self) -> None:
        """Test error handling throughout factory workflow."""
        failing_factory = MockRepositoryFactory(should_fail=True)
        configure_repository_factory(failing_factory)

        # Repository creation should fail
        with pytest.raises(RuntimeError):
            get_user_repository()

        # But factory retrieval should still work
        retrieved_factory = get_repository_factory()
        assert retrieved_factory is failing_factory

    @patch("src.infrastructure.persistence.repository_factory.get_service_registry")
    def test_service_registry_integration_workflow(
        self, mock_get_service_registry: MagicMock
    ) -> None:
        """Test complete workflow with service registry integration."""
        mock_registry = MagicMock()
        mock_factory = MockRepositoryFactory()

        # Setup service registry to return factory
        mock_registry.get_repository_factory.return_value = mock_factory
        mock_get_service_registry.return_value = mock_registry

        # Get factory should return from service registry
        result = get_repository_factory()
        assert result is mock_factory

        # Use the factory
        user_repo = result.create_user_repository()
        assert isinstance(user_repo, InMemoryUserRepository)
        assert mock_factory.create_user_repository_called

    def test_concurrent_factory_usage_simulation(self) -> None:
        """Simulate concurrent usage of factory (testing singleton behavior)."""
        configure_repository_factory()

        # Simulate multiple "threads" getting repositories
        factories = [get_repository_factory() for _ in range(5)]
        user_repos = [factory.create_user_repository() for factory in factories]
        product_repos = [factory.create_product_repository() for factory in factories]

        # All factories should be the same instance
        assert all(factory is factories[0] for factory in factories)

        # All repositories of same type should be the same instance
        assert all(repo is user_repos[0] for repo in user_repos)
        assert all(repo is product_repos[0] for repo in product_repos)

    def test_factory_protocol_compliance_validation(self) -> None:
        """Test that factory implements RepositoryFactory protocol correctly."""
        factory = SampleRepositoryFactory()

        # Should have required methods
        assert hasattr(factory, "create_user_repository")
        assert hasattr(factory, "create_product_repository")
        assert callable(factory.create_user_repository)
        assert callable(factory.create_product_repository)

        # Methods should return correct types
        user_repo = factory.create_user_repository()
        product_repo = factory.create_product_repository()

        assert isinstance(user_repo, InMemoryUserRepository)
        assert isinstance(product_repo, InMemoryProductRepository)
