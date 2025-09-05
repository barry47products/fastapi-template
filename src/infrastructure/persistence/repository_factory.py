"""Repository factory for dependency injection and clean architecture separation."""

from typing import Protocol

from config.settings import get_settings
from src.domain.repositories import EndorsementRepository, ProviderRepository
from src.infrastructure.observability import get_logger
from src.infrastructure.service_registry import get_service_registry

from .firestore_client import FirestoreClient
from .repositories import FirestoreEndorsementRepository, FirestoreProviderRepository


class RepositoryFactory(Protocol):
    """
    Factory interface for creating repository instances.

    Provides dependency injection for repository implementations while
    maintaining clean architecture boundaries. Enables easy testing
    with mock repositories and configuration-based implementation switching.
    """

    def create_provider_repository(self) -> ProviderRepository:
        """Create a provider repository instance."""

    def create_endorsement_repository(self) -> EndorsementRepository:
        """Create an endorsement repository instance."""


class FirestoreRepositoryFactory:
    """
    Firestore-based implementation of the repository factory.

    Creates repository instances configured with Firestore client
    and proper dependency injection. Handles all infrastructure
    concerns including logging, metrics, and service registry integration.
    """

    def __init__(self) -> None:
        """Initialize factory with dependencies."""
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self._firestore_client: FirestoreClient | None = None

    @property
    def firestore_client(self) -> FirestoreClient:
        """Get or create Firestore client instance."""
        if self._firestore_client is None:
            self._firestore_client = self._create_firestore_client()
        return self._firestore_client

    def _create_firestore_client(self) -> FirestoreClient:
        """Create and configure Firestore client."""
        try:
            # Get Firestore settings
            firestore_settings = self.settings.firestore

            # Try to get from service registry first (if available)
            try:
                service_registry = get_service_registry()
                if hasattr(service_registry, "get_firestore_client"):
                    try:
                        return service_registry.get_firestore_client()
                    except Exception:
                        # Fall back to creating new instance
                        pass
            except Exception:
                # Service registry not initialized, continue with direct creation
                pass

            # Create new client instance
            client = FirestoreClient(firestore_settings)

            # Register with service registry for reuse (if available)
            try:
                service_registry = get_service_registry()
                if hasattr(service_registry, "register_firestore_client"):
                    try:
                        service_registry.register_firestore_client(client)
                    except Exception:
                        # Service registry might not support this yet
                        pass
            except Exception:
                # Service registry not initialized, skip registration
                pass

            self.logger.info("Firestore client created successfully")
            return client

        except Exception as e:
            self.logger.error("Failed to create Firestore client", error=str(e))
            raise

    def create_provider_repository(self) -> ProviderRepository:
        """Create a provider repository instance with Firestore backend."""
        try:
            repository = FirestoreProviderRepository(self.firestore_client)
            self.logger.debug("Provider repository created successfully")
            return repository

        except Exception as e:
            self.logger.error("Failed to create provider repository", error=str(e))
            raise

    def create_endorsement_repository(self) -> EndorsementRepository:
        """Create an endorsement repository instance with Firestore backend."""
        try:
            repository = FirestoreEndorsementRepository(self.firestore_client)
            self.logger.debug("Endorsement repository created successfully")
            return repository

        except Exception as e:
            self.logger.error("Failed to create endorsement repository", error=str(e))
            raise

    def health_check(self) -> bool:
        """Perform health check on repository factory and dependencies."""
        try:
            # Test Firestore client health
            if not self.firestore_client.health_check():
                return False

            # Test repository creation
            provider_repo = self.create_provider_repository()
            endorsement_repo = self.create_endorsement_repository()

            # Verify repositories are properly configured
            if provider_repo is None or endorsement_repo is None:
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
            factory = FirestoreRepositoryFactory()

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
        factory: Factory instance to use, defaults to FirestoreRepositoryFactory
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
                    and hasattr(factory_instance, "create_provider_repository")
                    and hasattr(factory_instance, "create_endorsement_repository")
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
def get_provider_repository() -> ProviderRepository:
    """Get a provider repository instance."""
    factory = get_repository_factory()
    return factory.create_provider_repository()


def get_endorsement_repository() -> EndorsementRepository:
    """Get an endorsement repository instance."""
    factory = get_repository_factory()
    return factory.create_endorsement_repository()
