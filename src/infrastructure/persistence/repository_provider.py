"""Multi-database repository provider with feature flag support."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Protocol, TypeVar, cast

from config.settings import DatabaseType, get_settings
from src.infrastructure.observability import get_logger
from src.infrastructure.persistence.repositories import (
    InMemoryProductRepository,
    InMemoryUserRepository,
)

T = TypeVar("T", bound="Repository")


class Repository(Protocol):
    """Base repository protocol."""


class RepositoryProvider:
    """Multi-database repository provider with feature flag support."""

    def __init__(
        self, database_url: str | None = None, db_type: DatabaseType | None = None
    ) -> None:
        """Initialize repository provider with database configuration.

        Args:
            database_url: Database connection URL (uses settings if not provided)
            db_type: Type of database (uses settings if not provided)
        """
        settings = get_settings()

        self.database_url = database_url or settings.database.database_url
        self.db_type = db_type or settings.database.primary_db
        self.cache_url = settings.database.cache_url
        self.cache_db = settings.database.cache_db
        self.settings = settings.database
        self.logger = get_logger(__name__)
        self._repositories: dict[type[Any], Any] = {}
        self._cache_repositories: dict[type[Any], Any] = {}

    def get(self, repository_type: type[T]) -> T:
        """Get or create repository instance.

        Args:
            repository_type: Type of repository to get

        Returns:
            Repository instance

        Raises:
            ValueError: If repository type is not supported
        """
        if repository_type not in self._repositories:
            self._repositories[repository_type] = self._create_repository(repository_type)
        return self._repositories[repository_type]

    def _create_repository(self, repo_type: type[T]) -> T:
        """Factory method for creating repositories based on db_type.

        Args:
            repo_type: Repository type to create

        Returns:
            Repository instance

        Raises:
            ValueError: If repository type is not supported
            NotImplementedError: If database type is not implemented
        """
        if self.db_type == DatabaseType.IN_MEMORY:
            return self._create_in_memory_repository(repo_type)
        if self.db_type == DatabaseType.POSTGRESQL and self.settings.enable_postgresql:
            return self._create_postgresql_repository(repo_type)
        if self.db_type == DatabaseType.FIRESTORE and self.settings.enable_firestore:
            return self._create_firestore_repository(repo_type)
        if self.db_type == DatabaseType.REDIS:
            return self._create_redis_repository(repo_type)
        raise ValueError(f"Unsupported or disabled database type: {self.db_type}")

    def _create_in_memory_repository(self, repo_type: type[T]) -> T:
        """Create in-memory repository."""
        if repo_type == InMemoryUserRepository:
            return cast("T", InMemoryUserRepository())
        if repo_type == InMemoryProductRepository:
            return cast("T", InMemoryProductRepository())
        raise ValueError(f"Unsupported in-memory repository type: {repo_type}")

    def _create_postgresql_repository(self, repo_type: type[T]) -> T:
        """Create PostgreSQL repository."""
        try:
            from .repositories.postgresql import PostgreSQLRepository

            if repo_type == InMemoryUserRepository:
                # Map to PostgreSQL equivalent
                return cast(
                    "T",
                    PostgreSQLRepository(
                        connection_url=self.database_url,
                        table_name="users",
                        pool_size=self.settings.pool_size,
                        max_overflow=self.settings.max_overflow,
                        max_retries=self.settings.retry_attempts,
                        retry_delay=self.settings.retry_delay,
                    ),
                )
            if repo_type == InMemoryProductRepository:
                return cast(
                    "T",
                    PostgreSQLRepository(
                        connection_url=self.database_url,
                        table_name="products",
                        pool_size=self.settings.pool_size,
                        max_overflow=self.settings.max_overflow,
                        max_retries=self.settings.retry_attempts,
                        retry_delay=self.settings.retry_delay,
                    ),
                )
            raise ValueError(f"Unsupported PostgreSQL repository type: {repo_type}")
        except ImportError as e:
            self.logger.error("PostgreSQL dependencies not available", error=str(e))
            raise NotImplementedError(
                "PostgreSQL repositories require additional dependencies"
            ) from e

    def _create_firestore_repository(self, repo_type: type[T]) -> T:
        """Create Firestore repository."""
        try:
            from .repositories.firestore import FirestoreRepository

            if repo_type == InMemoryUserRepository:
                return cast(
                    "T",
                    FirestoreRepository(
                        connection_url=self.database_url,
                        collection_name="users",
                        cache_ttl=300,
                        max_retries=self.settings.retry_attempts,
                        retry_delay=self.settings.retry_delay,
                    ),
                )
            if repo_type == InMemoryProductRepository:
                return cast(
                    "T",
                    FirestoreRepository(
                        connection_url=self.database_url,
                        collection_name="products",
                        cache_ttl=300,
                        max_retries=self.settings.retry_attempts,
                        retry_delay=self.settings.retry_delay,
                    ),
                )
            raise ValueError(f"Unsupported Firestore repository type: {repo_type}")
        except ImportError as e:
            self.logger.error("Firestore dependencies not available", error=str(e))
            raise NotImplementedError(
                "Firestore repositories require additional dependencies"
            ) from e

    def _create_redis_repository(self, repo_type: type[T]) -> T:
        """Create Redis cache repository."""
        try:
            from .repositories.redis_cache import RedisCacheRepository

            if repo_type == InMemoryUserRepository:
                return cast(
                    "T",
                    RedisCacheRepository(
                        connection_url=self.cache_url or self.database_url,
                        key_prefix="users",
                        default_ttl=3600,
                        max_retries=self.settings.retry_attempts,
                        retry_delay=self.settings.retry_delay,
                    ),
                )
            if repo_type == InMemoryProductRepository:
                return cast(
                    "T",
                    RedisCacheRepository(
                        connection_url=self.cache_url or self.database_url,
                        key_prefix="products",
                        default_ttl=3600,
                        max_retries=self.settings.retry_attempts,
                        retry_delay=self.settings.retry_delay,
                    ),
                )
            raise ValueError(f"Unsupported Redis repository type: {repo_type}")
        except ImportError as e:
            self.logger.error("Redis dependencies not available", error=str(e))
            raise NotImplementedError("Redis repositories require additional dependencies") from e


# Global provider instance
_provider_instance: RepositoryProvider | None = None


@lru_cache
def get_repository_provider() -> RepositoryProvider:
    """Get the global repository provider instance.

    Returns:
        Repository provider instance
    """
    global _provider_instance
    if _provider_instance is None:
        # Use configuration from settings
        _provider_instance = RepositoryProvider()

    return _provider_instance


def configure_repository_provider(
    database_url: str | None = None,
    db_type: DatabaseType | None = None,
) -> None:
    """Configure the global repository provider instance.

    Args:
        database_url: Database connection URL
        db_type: Type of database
    """
    global _provider_instance

    _provider_instance = RepositoryProvider(database_url=database_url, db_type=db_type)

    # Clear the lru_cache to ensure new instance is returned
    get_repository_provider.cache_clear()


# Convenience functions for direct repository access
def get_user_repository() -> InMemoryUserRepository:
    """Get a user repository instance."""
    provider = get_repository_provider()
    return provider.get(InMemoryUserRepository)


def get_product_repository() -> InMemoryProductRepository:
    """Get a product repository instance."""
    provider = get_repository_provider()
    return provider.get(InMemoryProductRepository)
