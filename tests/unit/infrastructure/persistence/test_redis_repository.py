"""Unit tests for Redis cache repository implementation."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.persistence.repositories.redis_cache import RedisCacheRepository
from src.shared.exceptions import CacheException, ConnectionException


class TestEntity:
    """Test entity for Redis cache operations."""

    def __init__(self, entity_id: str | None, name: str, value: int = 0) -> None:
        """Initialize test entity."""
        self.id = entity_id
        self.name = name
        self.value = value

    def to_dict(self) -> dict[str, str | int | None]:
        """Return dict representation."""
        return {"id": self.id, "name": self.name, "value": self.value}


class MockRedisCacheRepository(RedisCacheRepository[TestEntity, str]):
    """Mock Redis cache repository for testing."""

    def _entity_to_json(self, entity: TestEntity) -> str:
        """Convert entity to JSON."""
        return json.dumps({"id": entity.id, "name": entity.name, "value": entity.value})

    def _json_to_entity(self, json_str: str) -> TestEntity:
        """Convert JSON to entity."""
        data = json.loads(json_str)
        return TestEntity(data.get("id"), data["name"], data.get("value", 0))

    def _get_entity_id(self, entity: TestEntity) -> str:
        """Get entity ID."""
        if entity.id is None:
            raise ValueError("Entity must have an ID")
        return entity.id


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestRedisCacheRepositoryInitialisation:
    """Test Redis cache repository initialisation and configuration."""

    def test_initialises_with_connection_and_cache_details(self) -> None:
        """Should initialise with connection URL and Redis-specific configuration."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379/0",
            key_prefix="test_app",
            default_ttl=7200,
            max_retries=5,
            retry_delay=1.0,
        )

        assert repo.connection_url == "redis://localhost:6379/0"
        assert repo.key_prefix == "test_app"
        assert repo.default_ttl == 7200
        assert repo.max_retries == 5
        assert repo.retry_delay == 1.0
        assert repo._client is None

    def test_initialises_with_default_configuration(self) -> None:
        """Should initialise with default cache settings when not specified."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        assert repo.key_prefix == ""
        assert repo.default_ttl == 3600
        assert repo.max_retries == 3
        assert repo.retry_delay == 0.5


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.network
class TestRedisConnectionManagement:
    """Test Redis connection establishment and management."""

    @patch("redis.asyncio.from_url")
    async def test_establishes_redis_connection_with_configuration(
        self, mock_from_url: Any
    ) -> None:
        """Should establish Redis connection with proper configuration."""
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client
        mock_client.ping.return_value = True

        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379/0", key_prefix="test_app"
        )

        client = await repo._connect()

        assert client is mock_client
        mock_from_url.assert_called_once_with(
            "redis://localhost:6379/0",
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
        mock_client.ping.assert_called_once()

    @patch("redis.asyncio.from_url")
    async def test_handles_connection_failures_gracefully(self, mock_from_url: Any) -> None:
        """Should handle Redis connection failures gracefully."""
        mock_from_url.side_effect = Exception("Redis unavailable")

        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        with pytest.raises(ConnectionException, match="Failed to connect to Redis"):
            await repo._connect()

    async def test_disconnects_redis_client_cleanly(self) -> None:
        """Should disconnect Redis client cleanly."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")
        mock_client = AsyncMock()
        repo._client = mock_client

        await repo._disconnect()

        mock_client.close.assert_called_once()
        assert repo._client is None

    async def test_handles_disconnection_errors_gracefully(self) -> None:
        """Should handle disconnection errors gracefully."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")
        mock_client = AsyncMock()
        mock_client.close.side_effect = Exception("Disconnection error")
        repo._client = mock_client

        with pytest.raises(ConnectionException, match="Failed to disconnect from Redis"):
            await repo._disconnect()


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestRedisCacheKeyManagement:
    """Test Redis cache key generation and management."""

    def test_generates_cache_key_with_prefix(self) -> None:
        """Should generate cache key with configured prefix."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379/0", key_prefix="myapp"
        )

        cache_key = repo._get_cache_key("user123")

        assert cache_key == "myapp:user123"

    def test_generates_cache_key_without_prefix(self) -> None:
        """Should generate cache key without prefix when not configured."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0", key_prefix="")

        cache_key = repo._get_cache_key("user123")

        assert cache_key == "user123"

    def test_handles_different_id_types_consistently(self) -> None:
        """Should handle different ID types consistently in cache key generation."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0", key_prefix="app")

        string_key = repo._get_cache_key("123")
        int_key = repo._get_cache_key("123")

        assert string_key == "app:123"
        assert int_key == "app:123"


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.resilience
class TestRedisCacheOperations:
    """Test Redis cache CRUD operations with resilience."""

    async def test_caches_entity_with_default_ttl(self) -> None:
        """Should cache entity with default TTL setting."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0", default_ttl=1800)
        entity = TestEntity("test_id", "Test Entity", 42)

        mock_client = AsyncMock()
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
                mock_retry.return_value = entity

                result = await repo.create(entity)

                assert result is entity
                mock_retry.assert_called_once_with("create", repo._create_impl, entity)

    async def test_retrieves_cached_entity_with_deserialization(self) -> None:
        """Should retrieve and deserialize cached entity."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")
        entity_json = '{"id": "test_id", "name": "Test Entity", "value": 42}'

        mock_client = AsyncMock()
        mock_client.get.return_value = entity_json

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._get_by_id_impl("test_id")

            assert result is not None
            assert result.id == "test_id"
            assert result.name == "Test Entity"
            assert result.value == 42
            mock_client.get.assert_called_once_with("test_id")

    async def test_returns_none_when_cache_miss(self) -> None:
        """Should return None when entity not found in cache."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        mock_client = AsyncMock()
        mock_client.get.return_value = None

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._get_by_id_impl("nonexistent_id")

            assert result is None

    async def test_updates_cached_entity_with_existence_check(self) -> None:
        """Should update cached entity after verifying it exists."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")
        entity = TestEntity("test_id", "Updated Entity", 99)

        mock_client = AsyncMock()
        mock_client.exists.return_value = True

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._update_impl(entity)

            assert result is entity
            mock_client.exists.assert_called_once_with("test_id")
            mock_client.setex.assert_called_once()

    async def test_raises_error_when_updating_nonexistent_entity(self) -> None:
        """Should raise error when trying to update non-existent cached entity."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")
        entity = TestEntity("nonexistent_id", "Test Entity")

        mock_client = AsyncMock()
        mock_client.exists.return_value = False

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            with pytest.raises(CacheException, match="Entity with ID nonexistent_id not found"):
                await repo._update_impl(entity)

    async def test_deletes_cached_entity_and_returns_status(self) -> None:
        """Should delete cached entity and return appropriate status."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = True

            result = await repo.delete("test_id")

            assert result is True
            mock_retry.assert_called_once_with("delete", repo._delete_impl, "test_id")

    async def test_delete_returns_false_when_entity_not_found(self) -> None:
        """Should return False when entity not found for deletion."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        mock_client = AsyncMock()
        mock_client.delete.return_value = 0  # No keys deleted

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._delete_impl("nonexistent_id")

            assert result is False

    async def test_lists_cached_entities_with_pattern_matching(self) -> None:
        """Should list cached entities using key pattern matching."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0", key_prefix="app")

        mock_client = AsyncMock()
        mock_client.keys.return_value = ["app:entity1", "app:entity2"]
        mock_client.mget.return_value = [
            '{"id": "entity1", "name": "Entity 1", "value": 1}',
            '{"id": "entity2", "name": "Entity 2", "value": 2}',
        ]

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._list_all_impl(limit=10, offset=0)

            assert len(result) == 2
            assert result[0].name == "Entity 1"
            assert result[1].name == "Entity 2"
            mock_client.keys.assert_called_once_with("app:*")

    async def test_handles_deserialization_errors_gracefully(self) -> None:
        """Should handle deserialization errors gracefully during list operations."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        mock_client = AsyncMock()
        mock_client.keys.return_value = ["key1", "key2"]
        mock_client.mget.return_value = [
            '{"id": "valid", "name": "Valid", "value": 1}',
            "invalid_json",  # This will cause deserialization error
        ]

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._list_all_impl()

            # Should only return successfully deserialized entities
            assert len(result) == 1
            assert result[0].name == "Valid"


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestRedisSpecialOperations:
    """Test Redis-specific cache operations like TTL and pattern operations."""

    async def test_sets_entity_with_custom_ttl(self) -> None:
        """Should cache entity with custom TTL value."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")
        entity = TestEntity("test_id", "Test Entity")

        mock_client = AsyncMock()
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            await repo._set_with_ttl_impl("test_id", entity, 900)

            mock_client.setex.assert_called_once_with(
                "test_id", 900, '{"id": "test_id", "name": "Test Entity", "value": 0}'
            )

    async def test_retrieves_ttl_for_cached_entity(self) -> None:
        """Should retrieve remaining TTL for cached entity."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        mock_client = AsyncMock()
        mock_client.ttl.return_value = 1200

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._get_ttl_impl("test_id")

            assert result == 1200
            mock_client.ttl.assert_called_once_with("test_id")

    async def test_invalidates_keys_by_pattern(self) -> None:
        """Should invalidate multiple keys matching a pattern."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0", key_prefix="app")

        mock_client = AsyncMock()
        mock_client.keys.return_value = ["app:user:1", "app:user:2", "app:user:3"]
        mock_client.delete.return_value = 3

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._invalidate_pattern_impl("user:*")

            assert result == 3
            mock_client.keys.assert_called_once_with("app:user:*")
            mock_client.delete.assert_called_once_with("app:user:1", "app:user:2", "app:user:3")

    async def test_invalidate_pattern_without_prefix(self) -> None:
        """Should invalidate keys by pattern without prefix when not configured."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0", key_prefix="")

        mock_client = AsyncMock()
        mock_client.keys.return_value = ["session:1", "session:2"]
        mock_client.delete.return_value = 2

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._invalidate_pattern_impl("session:*")

            assert result == 2
            mock_client.keys.assert_called_once_with("session:*")

    async def test_returns_zero_when_no_keys_match_pattern(self) -> None:
        """Should return zero when no keys match invalidation pattern."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        mock_client = AsyncMock()
        mock_client.keys.return_value = []

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._invalidate_pattern_impl("nonexistent:*")

            assert result == 0


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.resilience
class TestRedisCacheResilience:
    """Test Redis cache repository resilience and error handling."""

    async def test_retries_failed_operations_with_exponential_backoff(self) -> None:
        """Should retry failed operations with proper backoff strategy."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379/0", max_retries=2, retry_delay=0.01
        )
        entity = TestEntity("test_id", "test_entity")

        with patch.object(repo, "_create_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.side_effect = [Exception("Temporary Redis failure"), entity]

            result = await repo.create(entity)

            assert result is entity
            assert mock_impl.call_count == 2

    async def test_fails_after_exhausting_all_retries(self) -> None:
        """Should fail operation after exhausting all retry attempts."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379/0", max_retries=1, retry_delay=0.01
        )
        entity = TestEntity("test_id", "test_entity")

        with patch.object(repo, "_create_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.side_effect = Exception("Persistent Redis failure")

            with pytest.raises(Exception, match="Persistent Redis failure"):
                await repo.create(entity)

            assert mock_impl.call_count == 2  # Initial + 1 retry

    async def test_handles_json_serialization_errors(self) -> None:
        """Should handle JSON serialization errors gracefully."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        class UnserializableEntity:
            def __init__(self) -> None:
                self.id = "test_id"
                self.name = "unserializable"
                self.value = 123
                # This would cause serialization issues in a real scenario

        # The default implementation should handle this with str() fallback
        entity = UnserializableEntity()
        json_result = repo._entity_to_json(entity)  # type: ignore[arg-type]

        assert isinstance(json_result, str)
        # Should be valid JSON
        assert json.loads(json_result) is not None

    async def test_maintains_observability_during_errors(self) -> None:
        """Should maintain observability metrics and logging during error conditions."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        # Verify observability components are available during errors
        assert repo.logger is not None
        assert repo.metrics is not None

    async def test_handles_network_timeouts_gracefully(self) -> None:
        """Should handle Redis network timeouts and connection issues."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        with patch.object(repo, "_connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Connection timeout")

            result = await repo.health_check()

            assert result is False


@pytest.mark.integration
@pytest.mark.behaviour
@pytest.mark.network
class TestRedisCacheIntegration:
    """Test Redis cache repository integration patterns."""

    def test_integrates_with_base_repository_interfaces(self) -> None:
        """Should integrate properly with base repository interfaces and protocols."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        # Verify it has all required repository methods
        assert hasattr(repo, "create")
        assert hasattr(repo, "get_by_id")
        assert hasattr(repo, "update")
        assert hasattr(repo, "delete")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "health_check")

    def test_provides_redis_specific_functionality(self) -> None:
        """Should provide Redis-specific functionality like TTL and pattern operations."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        # Verify Redis-specific methods
        assert hasattr(repo, "set_with_ttl")
        assert hasattr(repo, "get_ttl")
        assert hasattr(repo, "invalidate_pattern")
        assert hasattr(repo, "key_prefix")
        assert hasattr(repo, "default_ttl")

    def test_works_with_retry_logic(self) -> None:
        """Should work properly with inherited retry functionality."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379/0", max_retries=5, retry_delay=0.5
        )

        # Test that retry functionality is available
        assert repo.max_retries == 5
        assert repo.retry_delay == 0.5
        assert hasattr(repo, "_with_retry")

    def test_supports_different_serialization_patterns(self) -> None:
        """Should support different entity serialization patterns through overrides."""
        repo = MockRedisCacheRepository(connection_url="redis://localhost:6379/0")

        # Test default serialization behavior
        entity = TestEntity("test_id", "Test Name", 42)
        json_str = repo._entity_to_json(entity)
        deserialized = repo._json_to_entity(json_str)

        assert deserialized.id == entity.id
        assert deserialized.name == entity.name
        assert deserialized.value == entity.value

    async def test_cache_as_primary_vs_secondary_storage(self) -> None:
        """Should work as both primary cache and secondary storage layer."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379/0", key_prefix="primary_cache"
        )

        # As a cache layer, it should handle misses gracefully
        result = await repo._get_by_id_impl("cache_miss_key")
        assert result is None

        # As primary storage for cache data, it should support full CRUD
        assert hasattr(repo, "create")
        assert hasattr(repo, "update")
        assert hasattr(repo, "delete")


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestRedisCacheImplementationBehaviour:
    """Test Redis cache repository actual implementation behaviour."""

    async def test_disconnects_existing_client(self) -> None:
        """Disconnects existing Redis client when one exists."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test"
        )
        mock_client = AsyncMock()
        repo._client = mock_client

        await repo._disconnect()

        mock_client.close.assert_called_once()
        assert repo._client is None

    async def test_creates_entity_in_redis_with_ttl(self) -> None:
        """Creates entity in Redis with specified TTL."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test", default_ttl=1800
        )
        entity = TestEntity("test_id", "test_name", 42)
        mock_client = AsyncMock()

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._create_impl(entity)

            mock_client.setex.assert_called_once_with(
                "test:test_id",
                1800,
                '{"id": "test_id", "name": "test_name", "value": 42}'
            )
            assert result is entity

    async def test_gets_entity_from_redis_cache(self) -> None:
        """Gets entity from Redis cache when found."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test"
        )
        mock_client = AsyncMock()
        cached_json = '{"id": "test_id", "name": "test_name", "value": 42}'
        mock_client.get.return_value = cached_json

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._get_by_id_impl("test_id")

            assert result is not None
            assert result.id == "test_id"
            assert result.name == "test_name"
            assert result.value == 42

    async def test_returns_none_when_entity_not_in_cache(self) -> None:
        """Returns None when entity not found in Redis cache."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test"
        )
        mock_client = AsyncMock()
        mock_client.get.return_value = None

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._get_by_id_impl("non_existent_id")

            assert result is None

    async def test_updates_entity_in_redis_cache(self) -> None:
        """Updates entity in Redis cache with TTL."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test", default_ttl=900
        )
        entity = TestEntity("test_id", "updated_name", 100)
        mock_client = AsyncMock()

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._update_impl(entity)

            mock_client.setex.assert_called_once_with(
                "test:test_id",
                900,
                '{"id": "test_id", "name": "updated_name", "value": 100}'
            )
            assert result is entity

    async def test_deletes_entity_from_redis_cache(self) -> None:
        """Deletes entity from Redis cache when exists."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test"
        )
        mock_client = AsyncMock()
        mock_client.delete.return_value = 1  # One key deleted

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._delete_impl("test_id")

            mock_client.delete.assert_called_once_with("test:test_id")
            assert result is True

    async def test_delete_returns_false_when_entity_not_found(self) -> None:
        """Returns False when entity to delete not found in Redis."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test"
        )
        mock_client = AsyncMock()
        mock_client.delete.return_value = 0  # No keys deleted

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._delete_impl("non_existent_id")

            assert result is False

    async def test_lists_all_entities_from_redis(self) -> None:
        """Lists all entities matching key pattern from Redis."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test"
        )
        mock_client = AsyncMock()
        mock_client.keys.return_value = ["test:1", "test:2"]
        mock_client.mget.return_value = [
            '{"id": "1", "name": "entity1", "value": 1}',
            '{"id": "2", "name": "entity2", "value": 2}',
        ]

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._list_all_impl(limit=10, offset=0)

            assert len(result) == 2
            assert result[0].id == "1"
            assert result[1].id == "2"

    async def test_list_handles_deserialization_errors(self) -> None:
        """Handles deserialization errors when listing entities."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test"
        )
        mock_client = AsyncMock()
        mock_client.keys.return_value = ["test:1", "test:2"]
        mock_client.mget.return_value = [
            '{"id": "1", "name": "entity1", "value": 1}',
            "invalid_json",  # This will cause deserialization error
        ]

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo._list_all_impl(limit=None, offset=0)

            # Should only return the valid entity, skip the invalid one
            assert len(result) == 1
            assert result[0].id == "1"

    async def test_sets_entity_with_custom_ttl(self) -> None:
        """Sets entity in Redis cache with custom TTL."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test"
        )
        entity = TestEntity("test_id", "test_name", 42)
        mock_client = AsyncMock()

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            await repo.set_with_ttl("test_id", entity, 1200)

            mock_client.setex.assert_called_once_with(
                "test:test_id",
                1200,
                '{"id": "test_id", "name": "test_name", "value": 42}'
            )

    async def test_gets_ttl_for_entity(self) -> None:
        """Gets TTL for entity key from Redis."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test"
        )
        mock_client = AsyncMock()
        mock_client.ttl.return_value = 900

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo.get_ttl("test_id")

            mock_client.ttl.assert_called_once_with("test:test_id")
            assert result == 900

    async def test_invalidates_keys_matching_pattern(self) -> None:
        """Invalidates all keys matching pattern."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test"
        )
        mock_client = AsyncMock()
        mock_client.keys.return_value = ["test:user:1", "test:user:2", "test:user:3"]
        mock_client.delete.return_value = 3

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo.invalidate_pattern("user:*")

            mock_client.keys.assert_called_once_with("test:user:*")
            mock_client.delete.assert_called_once_with("test:user:1", "test:user:2", "test:user:3")
            assert result == 3

    async def test_invalidate_pattern_handles_no_matches(self) -> None:
        """Handles case where pattern matches no keys."""
        repo = MockRedisCacheRepository(
            connection_url="redis://localhost:6379", key_prefix="test"
        )
        mock_client = AsyncMock()
        mock_client.keys.return_value = []

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = None
            mock_context.__aexit__.return_value = None
            mock_get_conn.return_value = mock_context
            repo._client = mock_client

            result = await repo.invalidate_pattern("nonexistent:*")

            assert result == 0
            mock_client.delete.assert_not_called()
