"""Repository factory for dependency injection and clean architecture separation."""

from typing import Protocol

from src.infrastructure.observability import get_logger
from src.infrastructure.service_registry import get_service_registry

from .repositories import InMemoryProductRepository, InMemoryUserRepository


class RepositoryFactory(Protocol):
    """
    Factory interface for creating repository instances.

    Provides dependency injection for repository implementations while
    maintaining clean architecture boundaries. Enables easy testing
    with mock repositories and configuration-based implementation switching.
    
    Replace these sample repositories with your actual domain repositories.
    """

    def create_user_repository(self) -> InMemoryUserRepository:
        """Create a user repository instance."""

    def create_product_repository(self) -> InMemoryProductRepository:
        """Create a product repository instance."""


class SampleRepositoryFactory:
    """
    Sample implementation of repository factory using in-memory storage.

    Demonstrates repository factory patterns without external dependencies.
    Replace this with your actual repository implementations (database-backed).
    """

    def __init__(self) -> None:
        """Initialize factory with dependencies."""
        self.logger = get_logger(__name__)
        self._user_repository: InMemoryUserRepository | None = None
        self._product_repository: InMemoryProductRepository | None = None

    def create_user_repository(self) -> InMemoryUserRepository:
        """Create a user repository instance."""
        try:
            if self._user_repository is None:
                self._user_repository = InMemoryUserRepository()

            self.logger.debug("User repository created successfully")
            return self._user_repository

        except Exception as e:
            self.logger.error("Failed to create user repository", error=str(e))
            raise

    def create_product_repository(self) -> InMemoryProductRepository:
        """Create a product repository instance."""
        try:
            if self._product_repository is None:
                self._product_repository = InMemoryProductRepository()

            self.logger.debug("Product repository created successfully")
            return self._product_repository

        except Exception as e:
            self.logger.error("Failed to create product repository", error=str(e))
            raise

    def health_check(self) -> bool:
        """Perform health check on repository factory and dependencies."""
        try:
            # Test repository creation
            user_repo = self.create_user_repository()
            product_repo = self.create_product_repository()

            # Verify repositories are properly configured
            if user_repo is None or product_repo is None:
                return False

            self.logger.debug("Repository factory health check passed")
            return True

        except Exception as e:
            self.logger.error("Repository factory health check failed", error=str(e))
            return False


# Factory singleton management
class RepositoryFactoryRegistry:
    """Registry for managing repository factory singleton."""

    _instance: RepositoryFactory | None = None

    @classmethod
    def configure(cls, factory: RepositoryFactory | None = None) -> None:
        """Configure the repository factory instance."""
        if factory is None:
            factory = SampleRepositoryFactory()

        cls._instance = factory

        # Register with service registry (if available)
        try:
            service_registry = get_service_registry()
            if hasattr(service_registry, "register_repository_factory"):
                service_registry.register_repository_factory(factory)
        except Exception:
            # Service registry not initialized or doesn't support this yet
            pass

    @classmethod
    def get_instance(cls) -> RepositoryFactory:
        """Get the configured repository factory instance."""
        if cls._instance is None:
            cls.configure()

        if cls._instance is None:
            raise RuntimeError("Repository factory not configured")

        return cls._instance


def configure_repository_factory(factory: RepositoryFactory | None = None) -> None:
    """
    Configure the global repository factory instance.

    Args:
        factory: Factory instance to use, defaults to SampleRepositoryFactory
    """
    RepositoryFactoryRegistry.configure(factory)


def get_repository_factory() -> RepositoryFactory:
    """
    Get the configured repository factory instance.

    Returns:
        Repository factory instance

    Raises:
        RuntimeError: If no factory has been configured
    """
    # Try to get from service registry first (if available)
    try:
        service_registry = get_service_registry()
        if hasattr(service_registry, "get_repository_factory"):
            try:
                factory_instance = service_registry.get_repository_factory()
                # Verify the factory implements the RepositoryFactory protocol
                if (
                    factory_instance is not None
                    and hasattr(factory_instance, "create_user_repository")
                    and hasattr(factory_instance, "create_product_repository")
                ):
                    return factory_instance
            except Exception:
                pass
    except Exception:
        # Service registry not initialized, continue with registry instance
        pass

    # Fall back to registry instance
    return RepositoryFactoryRegistry.get_instance()


# Convenience functions for direct repository access
def get_user_repository() -> InMemoryUserRepository:
    """Get a user repository instance."""
    factory = get_repository_factory()
    return factory.create_user_repository()


def get_product_repository() -> InMemoryProductRepository:
    """Get a product repository instance."""
    factory = get_repository_factory()
    return factory.create_product_repository()
