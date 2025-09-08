"""Unit tests for generic repository provider."""

from __future__ import annotations

from typing import Protocol
from unittest.mock import patch

import pytest

from src.infrastructure.persistence.repositories import (
    InMemoryProductRepository,
    InMemoryUserRepository,
)


class Repository(Protocol):
    """Base repository protocol."""


class TestRepositoryProvider:
    """Test generic repository provider functionality."""

    def test_creates_repository_provider_with_configuration(self) -> None:
        """Creates repository provider with database configuration."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        provider = RepositoryProvider(database_url="memory://", db_type="in_memory")

        assert provider.database_url == "memory://"
        assert provider.db_type == "in_memory"
        assert provider._repositories == {}

    def test_gets_repository_by_type(self) -> None:
        """Gets repository instance by type."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        provider = RepositoryProvider(database_url="memory://", db_type="in_memory")

        user_repo = provider.get(InMemoryUserRepository)

        assert isinstance(user_repo, InMemoryUserRepository)

    def test_returns_same_instance_on_subsequent_calls(self) -> None:
        """Returns same repository instance on subsequent calls."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        provider = RepositoryProvider(database_url="memory://", db_type="in_memory")

        user_repo1 = provider.get(InMemoryUserRepository)
        user_repo2 = provider.get(InMemoryUserRepository)

        assert user_repo1 is user_repo2

    def test_gets_different_repository_types(self) -> None:
        """Gets different repository types independently."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        provider = RepositoryProvider(database_url="memory://", db_type="in_memory")

        user_repo = provider.get(InMemoryUserRepository)
        product_repo = provider.get(InMemoryProductRepository)

        assert isinstance(user_repo, InMemoryUserRepository)
        assert isinstance(product_repo, InMemoryProductRepository)
        # Repositories should be different instances
        assert id(user_repo) != id(product_repo)

    def test_raises_error_for_unsupported_repository_type(self) -> None:
        """Raises error for unsupported repository type."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        class UnsupportedRepository:
            pass

        provider = RepositoryProvider(database_url="memory://", db_type="in_memory")

        with pytest.raises(ValueError, match="Unsupported repository type"):
            provider.get(UnsupportedRepository)

    def test_creates_repositories_based_on_db_type(self) -> None:
        """Creates repositories based on configured database type."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        # Test different database types
        memory_provider = RepositoryProvider(database_url="memory://", db_type="in_memory")
        postgres_provider = RepositoryProvider(database_url="postgresql://", db_type="postgresql")

        memory_repo = memory_provider.get(InMemoryUserRepository)

        # Should create in-memory repository for memory provider
        assert isinstance(memory_repo, InMemoryUserRepository)

        # PostgreSQL provider should work when implemented
        # For now, it should raise NotImplementedError
        with pytest.raises(NotImplementedError, match="PostgreSQL repositories not implemented"):
            postgres_provider.get(InMemoryUserRepository)


class TestRepositoryProviderDependencyInjection:
    """Test repository provider as dependency injection replacement."""

    def test_integrates_with_dependency_injection_pattern(self) -> None:
        """Integrates with FastAPI dependency injection pattern."""
        from src.infrastructure.persistence.repository_provider import get_repository_provider

        provider = get_repository_provider()

        assert provider is not None
        # Should be cached/singleton
        provider2 = get_repository_provider()
        assert provider is provider2

    def test_provides_convenient_repository_getters(self) -> None:
        """Provides convenient repository getter functions."""
        from src.infrastructure.persistence.repository_provider import (
            get_product_repository,
            get_user_repository,
        )

        user_repo = get_user_repository()
        product_repo = get_product_repository()

        assert isinstance(user_repo, InMemoryUserRepository)
        assert isinstance(product_repo, InMemoryProductRepository)

    def test_repository_getters_return_same_instances(self) -> None:
        """Repository getter functions return same instances when called multiple times."""
        from src.infrastructure.persistence.repository_provider import (
            get_product_repository,
            get_user_repository,
        )

        user_repo1 = get_user_repository()
        user_repo2 = get_user_repository()
        product_repo1 = get_product_repository()
        product_repo2 = get_product_repository()

        assert user_repo1 is user_repo2
        assert product_repo1 is product_repo2


class TestRepositoryProviderConfiguration:
    """Test repository provider configuration and setup."""

    def test_configures_provider_with_environment_settings(self) -> None:
        """Configures provider with environment-based settings."""
        from src.infrastructure.persistence.repository_provider import configure_repository_provider

        # Should use environment variables or default settings
        configure_repository_provider()

        # Should not raise any errors and set up provider
        from src.infrastructure.persistence.repository_provider import get_repository_provider

        provider = get_repository_provider()
        assert provider is not None

    @patch.dict("os.environ", {"DATABASE_TYPE": "in_memory", "DATABASE_URL": "memory://"})
    def test_respects_environment_configuration(self) -> None:
        """Respects environment configuration for database setup."""
        from src.infrastructure.persistence.repository_provider import configure_repository_provider

        configure_repository_provider()

        from src.infrastructure.persistence.repository_provider import get_repository_provider

        provider = get_repository_provider()

        assert provider.db_type == "in_memory"
        assert provider.database_url == "memory://"
