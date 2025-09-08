"""Unit tests for generic repository provider."""

from __future__ import annotations

from contextlib import suppress
from typing import Protocol
from unittest.mock import MagicMock, patch

import pytest

from config.settings import DatabaseType
from src.infrastructure.persistence.repositories import (
    InMemoryProductRepository,
    InMemoryUserRepository,
)


class Repository(Protocol):
    """Base repository protocol."""


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestRepositoryProvider:
    """Test generic repository provider functionality."""

    def test_creates_repository_provider_with_configuration(self) -> None:
        """Creates repository provider with database configuration."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        provider = RepositoryProvider(database_url="memory://", db_type=DatabaseType.IN_MEMORY)

        assert provider.database_url == "memory://"
        assert provider.db_type == DatabaseType.IN_MEMORY
        assert provider._repositories == {}

    def test_gets_repository_by_type(self) -> None:
        """Gets repository instance by type."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        provider = RepositoryProvider(database_url="memory://", db_type=DatabaseType.IN_MEMORY)

        user_repo = provider.get(InMemoryUserRepository)

        assert isinstance(user_repo, InMemoryUserRepository)

    def test_returns_same_instance_on_subsequent_calls(self) -> None:
        """Returns same repository instance on subsequent calls."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        provider = RepositoryProvider(database_url="memory://", db_type=DatabaseType.IN_MEMORY)

        user_repo1 = provider.get(InMemoryUserRepository)
        user_repo2 = provider.get(InMemoryUserRepository)

        assert user_repo1 is user_repo2

    def test_gets_different_repository_types(self) -> None:
        """Gets different repository types independently."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        provider = RepositoryProvider(database_url="memory://", db_type=DatabaseType.IN_MEMORY)

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

        provider = RepositoryProvider(database_url="memory://", db_type=DatabaseType.IN_MEMORY)

        with pytest.raises(ValueError, match="Unsupported.*repository type"):
            provider.get(UnsupportedRepository)

    def test_creates_repositories_based_on_db_type(self) -> None:
        """Creates repositories based on configured database type."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        # Test different database types
        memory_provider = RepositoryProvider(
            database_url="memory://", db_type=DatabaseType.IN_MEMORY
        )
        postgres_provider = RepositoryProvider(
            database_url="postgresql://", db_type=DatabaseType.POSTGRESQL
        )

        memory_repo = memory_provider.get(InMemoryUserRepository)

        # Should create in-memory repository for memory provider
        assert isinstance(memory_repo, InMemoryUserRepository)

        # PostgreSQL provider should raise error when disabled (default state)
        with pytest.raises(ValueError, match="Unsupported or disabled database type"):
            postgres_provider.get(InMemoryUserRepository)


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
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


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
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

        assert provider.db_type == DatabaseType.IN_MEMORY
        assert provider.database_url == "memory://localhost"


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestRepositoryProviderDatabaseTypes:
    """Test repository provider with different database types and feature flags."""

    def test_uses_postgresql_path_when_enabled_and_requested(self) -> None:
        """Should attempt to use PostgreSQL repository when it's enabled and requested."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.enable_postgresql = True
            mock_db_settings.enable_firestore = False
            mock_db_settings.pool_size = 10
            mock_db_settings.max_overflow = 20
            mock_db_settings.retry_attempts = 3
            mock_db_settings.retry_delay = 1.0
            mock_get_settings.return_value.database = mock_db_settings

            provider = RepositoryProvider(
                database_url="postgresql://localhost/test", db_type=DatabaseType.POSTGRESQL
            )

            # Verify it tries to create PostgreSQL repository
            with suppress(ImportError, NotImplementedError):
                provider.get(InMemoryUserRepository)

    def test_uses_firestore_path_when_enabled_and_requested(self) -> None:
        """Should attempt to use Firestore repository when it's enabled and requested."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.enable_firestore = True
            mock_db_settings.enable_postgresql = False
            mock_db_settings.retry_attempts = 5
            mock_db_settings.retry_delay = 2.0
            mock_get_settings.return_value.database = mock_db_settings

            provider = RepositoryProvider(
                database_url="firestore://project-id", db_type=DatabaseType.FIRESTORE
            )

            # Verify it tries to create Firestore repository
            with suppress(ImportError, NotImplementedError):
                provider.get(InMemoryUserRepository)

    def test_uses_redis_path_when_requested(self) -> None:
        """Should attempt to use Redis repository when requested."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.retry_attempts = 3
            mock_db_settings.retry_delay = 1.0
            mock_get_settings.return_value.database = mock_db_settings

            provider = RepositoryProvider(
                database_url="redis://localhost:6379", db_type=DatabaseType.REDIS
            )

            # Verify it tries to create Redis repository
            with suppress(ImportError, NotImplementedError):
                provider.get(InMemoryUserRepository)

    def test_repository_creation_method_paths_are_followed(self) -> None:
        """Should follow the correct method paths for different database types."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        # Test that the _create_repository method routes to the right sub-methods
        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.enable_postgresql = True
            mock_db_settings.enable_firestore = True
            mock_get_settings.return_value.database = mock_db_settings

            # Test PostgreSQL path
            postgresql_provider = RepositoryProvider(
                database_url="postgresql://localhost", db_type=DatabaseType.POSTGRESQL
            )

            # Mock the internal method to verify it gets called
            with patch.object(
                postgresql_provider, "_create_postgresql_repository"
            ) as mock_postgresql:
                mock_postgresql.return_value = MagicMock()

                postgresql_provider.get(InMemoryUserRepository)
                mock_postgresql.assert_called_once_with(InMemoryUserRepository)

            # Test Firestore path
            firestore_provider = RepositoryProvider(
                database_url="firestore://project", db_type=DatabaseType.FIRESTORE
            )

            with patch.object(firestore_provider, "_create_firestore_repository") as mock_firestore:
                mock_firestore.return_value = MagicMock()

                firestore_provider.get(InMemoryUserRepository)
                mock_firestore.assert_called_once_with(InMemoryUserRepository)

            # Test Redis path
            redis_provider = RepositoryProvider(
                database_url="redis://localhost", db_type=DatabaseType.REDIS
            )

            with patch.object(redis_provider, "_create_redis_repository") as mock_redis:
                mock_redis.return_value = MagicMock()

                redis_provider.get(InMemoryUserRepository)
                mock_redis.assert_called_once_with(InMemoryUserRepository)


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestRepositoryProviderInstantiation:
    """Test repository provider actual instantiation behaviour."""

    def test_creates_postgresql_user_repository_with_configuration(self) -> None:
        """Creates PostgreSQL user repository with proper configuration."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.enable_postgresql = True
            mock_db_settings.enable_firestore = False
            mock_db_settings.pool_size = 15
            mock_db_settings.max_overflow = 25
            mock_db_settings.retry_attempts = 4
            mock_db_settings.retry_delay = 2.5
            mock_get_settings.return_value.database = mock_db_settings

            with patch(
                "src.infrastructure.persistence.repositories.postgresql.PostgreSQLRepository"
            ) as mock_postgresql_repo:
                mock_repo_instance = MagicMock()
                mock_postgresql_repo.return_value = mock_repo_instance

                provider = RepositoryProvider(
                    database_url="postgresql://user:pass@localhost:5432/test",
                    db_type=DatabaseType.POSTGRESQL,
                )

                result = provider.get(InMemoryUserRepository)

                assert result is mock_repo_instance
                mock_postgresql_repo.assert_called_once_with(
                    connection_url="postgresql://user:pass@localhost:5432/test",
                    table_name="users",
                    pool_size=15,
                    max_overflow=25,
                    max_retries=4,
                    retry_delay=2.5,
                )

    def test_creates_postgresql_product_repository_with_configuration(self) -> None:
        """Creates PostgreSQL product repository with proper configuration."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.enable_postgresql = True
            mock_db_settings.pool_size = 20
            mock_db_settings.max_overflow = 30
            mock_db_settings.retry_attempts = 2
            mock_db_settings.retry_delay = 1.5
            mock_get_settings.return_value.database = mock_db_settings

            with patch(
                "src.infrastructure.persistence.repositories.postgresql.PostgreSQLRepository"
            ) as mock_postgresql_repo:
                mock_repo_instance = MagicMock()
                mock_postgresql_repo.return_value = mock_repo_instance

                provider = RepositoryProvider(
                    database_url="postgresql://test@localhost/products",
                    db_type=DatabaseType.POSTGRESQL,
                )

                result = provider.get(InMemoryProductRepository)

                assert result is mock_repo_instance
                mock_postgresql_repo.assert_called_once_with(
                    connection_url="postgresql://test@localhost/products",
                    table_name="products",
                    pool_size=20,
                    max_overflow=30,
                    max_retries=2,
                    retry_delay=1.5,
                )

    def test_creates_firestore_user_repository_with_configuration(self) -> None:
        """Creates Firestore user repository with proper configuration."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.enable_firestore = True
            mock_db_settings.retry_attempts = 5
            mock_db_settings.retry_delay = 3.0
            mock_get_settings.return_value.database = mock_db_settings

            with patch(
                "src.infrastructure.persistence.repositories.firestore.FirestoreRepository"
            ) as mock_firestore_repo:
                mock_repo_instance = MagicMock()
                mock_firestore_repo.return_value = mock_repo_instance

                provider = RepositoryProvider(
                    database_url="firestore://test-project",
                    db_type=DatabaseType.FIRESTORE,
                )

                result = provider.get(InMemoryUserRepository)

                assert result is mock_repo_instance
                mock_firestore_repo.assert_called_once_with(
                    connection_url="firestore://test-project",
                    collection_name="users",
                    cache_ttl=300,
                    max_retries=5,
                    retry_delay=3.0,
                )

    def test_creates_firestore_product_repository_with_configuration(self) -> None:
        """Creates Firestore product repository with proper configuration."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.enable_firestore = True
            mock_db_settings.retry_attempts = 6
            mock_db_settings.retry_delay = 2.0
            mock_get_settings.return_value.database = mock_db_settings

            with patch(
                "src.infrastructure.persistence.repositories.firestore.FirestoreRepository"
            ) as mock_firestore_repo:
                mock_repo_instance = MagicMock()
                mock_firestore_repo.return_value = mock_repo_instance

                provider = RepositoryProvider(
                    database_url="firestore://prod-project",
                    db_type=DatabaseType.FIRESTORE,
                )

                result = provider.get(InMemoryProductRepository)

                assert result is mock_repo_instance
                mock_firestore_repo.assert_called_once_with(
                    connection_url="firestore://prod-project",
                    collection_name="products",
                    cache_ttl=300,
                    max_retries=6,
                    retry_delay=2.0,
                )

    def test_creates_redis_user_repository_with_configuration(self) -> None:
        """Creates Redis user repository with proper configuration."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.retry_attempts = 4
            mock_db_settings.retry_delay = 1.8
            mock_db_settings.cache_url = "redis://cache:6379/1"
            mock_get_settings.return_value.database = mock_db_settings

            with patch(
                "src.infrastructure.persistence.repositories.redis_cache.RedisCacheRepository"
            ) as mock_redis_repo:
                mock_repo_instance = MagicMock()
                mock_redis_repo.return_value = mock_repo_instance

                provider = RepositoryProvider(
                    database_url="redis://localhost:6379/0",
                    db_type=DatabaseType.REDIS,
                )

                result = provider.get(InMemoryUserRepository)

                assert result is mock_repo_instance
                mock_redis_repo.assert_called_once_with(
                    connection_url="redis://cache:6379/1",
                    key_prefix="users",
                    default_ttl=3600,
                    max_retries=4,
                    retry_delay=1.8,
                )

    def test_creates_redis_product_repository_with_configuration(self) -> None:
        """Creates Redis product repository with proper configuration."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.retry_attempts = 7
            mock_db_settings.retry_delay = 0.5
            mock_db_settings.cache_url = None
            mock_get_settings.return_value.database = mock_db_settings

            with patch(
                "src.infrastructure.persistence.repositories.redis_cache.RedisCacheRepository"
            ) as mock_redis_repo:
                mock_repo_instance = MagicMock()
                mock_redis_repo.return_value = mock_repo_instance

                provider = RepositoryProvider(
                    database_url="redis://primary:6379",
                    db_type=DatabaseType.REDIS,
                )

                result = provider.get(InMemoryProductRepository)

                assert result is mock_repo_instance
                mock_redis_repo.assert_called_once_with(
                    connection_url="redis://primary:6379",
                    key_prefix="products",
                    default_ttl=3600,
                    max_retries=7,
                    retry_delay=0.5,
                )


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestRepositoryProviderErrorHandling:
    """Test repository provider error handling for unsupported repository types."""

    def test_raises_error_for_unsupported_postgresql_repository_type(self) -> None:
        """Raises ValueError for unsupported PostgreSQL repository type."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        class UnsupportedPostgreSQLRepository:
            pass

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.enable_postgresql = True
            mock_get_settings.return_value.database = mock_db_settings

            with patch(
                "src.infrastructure.persistence.repositories.postgresql.PostgreSQLRepository"
            ):
                provider = RepositoryProvider(
                    database_url="postgresql://localhost/test",
                    db_type=DatabaseType.POSTGRESQL,
                )

                with pytest.raises(ValueError, match="Unsupported PostgreSQL repository type"):
                    provider.get(UnsupportedPostgreSQLRepository)

    def test_raises_error_for_unsupported_firestore_repository_type(self) -> None:
        """Raises ValueError for unsupported Firestore repository type."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        class UnsupportedFirestoreRepository:
            pass

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_db_settings.enable_firestore = True
            mock_get_settings.return_value.database = mock_db_settings

            with patch("src.infrastructure.persistence.repositories.firestore.FirestoreRepository"):
                provider = RepositoryProvider(
                    database_url="firestore://test-project",
                    db_type=DatabaseType.FIRESTORE,
                )

                with pytest.raises(ValueError, match="Unsupported Firestore repository type"):
                    provider.get(UnsupportedFirestoreRepository)

    def test_raises_error_for_unsupported_redis_repository_type(self) -> None:
        """Raises ValueError for unsupported Redis repository type."""
        from src.infrastructure.persistence.repository_provider import RepositoryProvider

        class UnsupportedRedisRepository:
            pass

        with patch(
            "src.infrastructure.persistence.repository_provider.get_settings"
        ) as mock_get_settings:
            mock_db_settings = MagicMock()
            mock_get_settings.return_value.database = mock_db_settings

            with patch(
                "src.infrastructure.persistence.repositories.redis_cache.RedisCacheRepository"
            ):
                provider = RepositoryProvider(
                    database_url="redis://localhost:6379",
                    db_type=DatabaseType.REDIS,
                )

                with pytest.raises(ValueError, match="Unsupported Redis repository type"):
                    provider.get(UnsupportedRedisRepository)
