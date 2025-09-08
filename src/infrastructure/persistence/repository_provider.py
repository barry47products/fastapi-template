"""Generic repository provider for dependency injection and clean architecture separation."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Protocol, TypeVar, cast

from src.infrastructure.observability import get_logger
from src.infrastructure.persistence.repositories import (
    InMemoryProductRepository,
    InMemoryUserRepository,
)

T = TypeVar("T", bound="Repository")


class Repository(Protocol):
    """Base repository protocol."""


class RepositoryProvider:
    """Simple, extensible repository provider."""

    def __init__(self, database_url: str, db_type: str) -> None:
        """Initialize repository provider with database configuration.

        Args:
            database_url: Database connection URL
            db_type: Type of database (in_memory, postgresql, etc.)
        """
        self.database_url = database_url
        self.db_type = db_type
        self.logger = get_logger(__name__)
        self._repositories: dict[type[Any], Any] = {}

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
        if self.db_type == "in_memory":
            # Handle in-memory repositories
            if repo_type == InMemoryUserRepository:
                return cast(T, InMemoryUserRepository())
            if repo_type == InMemoryProductRepository:
                return cast(T, InMemoryProductRepository())
            raise ValueError(f"Unsupported repository type: {repo_type}")
        if self.db_type == "postgresql":
            raise NotImplementedError("PostgreSQL repositories not implemented")
        raise ValueError(f"Unsupported database type: {self.db_type}")


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
        # Use default configuration if not configured
        database_url = os.getenv("DATABASE_URL", "memory://")
        db_type = os.getenv("DATABASE_TYPE", "in_memory")
        _provider_instance = RepositoryProvider(database_url=database_url, db_type=db_type)

    return _provider_instance


def configure_repository_provider(
    database_url: str | None = None,
    db_type: str | None = None,
) -> None:
    """Configure the global repository provider instance.

    Args:
        database_url: Database connection URL
        db_type: Type of database
    """
    global _provider_instance

    # Use environment variables as defaults
    final_database_url = (
        database_url if database_url is not None else os.getenv("DATABASE_URL", "memory://")
    )
    final_db_type = db_type if db_type is not None else os.getenv("DATABASE_TYPE", "in_memory")

    _provider_instance = RepositoryProvider(database_url=final_database_url, db_type=final_db_type)

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
