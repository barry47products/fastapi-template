"""Redis cache repository implementation."""

from __future__ import annotations

import json
from typing import Any, TypeVar

from .base import BaseRepository, RetryMixin
from src.shared.exceptions import CacheException, ConnectionException

T = TypeVar("T")
ID = TypeVar("ID")


class RedisCacheRepository(BaseRepository[T, ID], RetryMixin):
    """Redis cache repository implementation for high-performance caching."""

    def __init__(
        self,
        connection_url: str,
        key_prefix: str = "",
        default_ttl: int = 3600,
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ) -> None:
        """Initialize Redis cache repository.

        Args:
            connection_url: Redis connection URL
            key_prefix: Key prefix for namespacing
            default_ttl: Default time-to-live in seconds
            max_retries: Maximum retry attempts
            retry_delay: Retry delay in seconds
        """
        BaseRepository.__init__(self, connection_url)
        RetryMixin.__init__(self, max_retries, retry_delay)
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self._client: Any = None

    async def _connect(self) -> Any:
        """Establish Redis connection.

        Returns:
            Redis client instance

        Raises:
            ConnectionException: If connection fails
        """
        try:
            # Import here to avoid dependency issues
            import redis.asyncio as redis_async

            self._client = redis_async.from_url(
                self.connection_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30,
            )

            # Test connection
            await self._client.ping()

            self.logger.info(
                "Connected to Redis",
                key_prefix=self.key_prefix,
                default_ttl=self.default_ttl,
            )
            self.metrics.increment_counter("redis_connections_total", {"status": "success"})

            return self._client

        except Exception as e:
            self.logger.error("Failed to connect to Redis", error=str(e))
            self.metrics.increment_counter("redis_connections_total", {"status": "failure"})
            raise ConnectionException(f"Failed to connect to Redis: {e}") from e

    async def _disconnect(self) -> None:
        """Close Redis connection.

        Raises:
            ConnectionException: If disconnection fails
        """
        try:
            if self._client:
                await self._client.close()
                self._client = None
                self.logger.info("Disconnected from Redis", key_prefix=self.key_prefix)

        except Exception as e:
            self.logger.error("Failed to disconnect from Redis", error=str(e))
            raise ConnectionException(f"Failed to disconnect from Redis: {e}") from e

    def _get_cache_key(self, entity_id: ID) -> str:
        """Generate cache key for entity.

        Args:
            entity_id: Entity ID

        Returns:
            Cache key with prefix
        """
        if self.key_prefix:
            return f"{self.key_prefix}:{entity_id}"
        return str(entity_id)

    async def create(self, entity: T) -> T:
        """Create/cache entity in Redis.

        Args:
            entity: Entity to cache

        Returns:
            Cached entity

        Raises:
            RepositoryError: If caching fails
        """
        return await self._with_retry("create", self._create_impl, entity)

    async def _create_impl(self, entity: T) -> T:
        """Internal create implementation."""
        async with self._get_connection():
            entity_id = self._get_entity_id(entity)
            cache_key = self._get_cache_key(entity_id)

            # Serialize entity to JSON
            entity_json = self._entity_to_json(entity)

            # Store in Redis with TTL
            await self._client.setex(cache_key, self.default_ttl, entity_json)

            self.logger.info(
                "Cached entity in Redis",
                entity_id=entity_id,
                cache_key=cache_key,
                ttl=self.default_ttl,
            )
            self.metrics.increment_counter("redis_operations_total", {"operation": "create"})

            return entity

    async def get_by_id(self, entity_id: ID) -> T | None:
        """Get entity from Redis cache.

        Args:
            entity_id: Entity ID

        Returns:
            Cached entity if found, None otherwise
        """
        return await self._with_retry("get_by_id", self._get_by_id_impl, entity_id)

    async def _get_by_id_impl(self, entity_id: ID) -> T | None:
        """Internal get by ID implementation."""
        async with self._get_connection():
            cache_key = self._get_cache_key(entity_id)

            # Get from Redis
            entity_json = await self._client.get(cache_key)

            if entity_json:
                entity = self._json_to_entity(entity_json)
                self.logger.debug("Cache hit", entity_id=entity_id, cache_key=cache_key)
                self.metrics.increment_counter("redis_operations_total", {"operation": "get_hit"})
                return entity

            self.logger.debug("Cache miss", entity_id=entity_id, cache_key=cache_key)
            self.metrics.increment_counter("redis_operations_total", {"operation": "get_miss"})
            return None

    async def update(self, entity: T) -> T:
        """Update cached entity in Redis.

        Args:
            entity: Entity to update

        Returns:
            Updated entity

        Raises:
            RepositoryError: If update fails
        """
        return await self._with_retry("update", self._update_impl, entity)

    async def _update_impl(self, entity: T) -> T:
        """Internal update implementation."""
        async with self._get_connection():
            entity_id = self._get_entity_id(entity)
            cache_key = self._get_cache_key(entity_id)

            # Check if key exists
            exists = await self._client.exists(cache_key)
            if not exists:
                raise CacheException(f"Entity with ID {entity_id} not found in cache")

            # Update with new TTL
            entity_json = self._entity_to_json(entity)
            await self._client.setex(cache_key, self.default_ttl, entity_json)

            self.logger.info("Updated cached entity", entity_id=entity_id, cache_key=cache_key)
            self.metrics.increment_counter("redis_operations_total", {"operation": "update"})

            return entity

    async def delete(self, entity_id: ID) -> bool:
        """Delete entity from Redis cache.

        Args:
            entity_id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        return await self._with_retry("delete", self._delete_impl, entity_id)

    async def _delete_impl(self, entity_id: ID) -> bool:
        """Internal delete implementation."""
        async with self._get_connection():
            cache_key = self._get_cache_key(entity_id)

            # Delete from Redis
            deleted_count = await self._client.delete(cache_key)

            if deleted_count > 0:
                self.logger.info("Deleted cached entity", entity_id=entity_id, cache_key=cache_key)
                self.metrics.increment_counter(
                    "redis_operations_total", {"operation": "delete_success"}
                )
                return True

            self.metrics.increment_counter(
                "redis_operations_total", {"operation": "delete_not_found"}
            )
            return False

    async def list_all(self, limit: int | None = None, offset: int = 0) -> list[T]:
        """List all cached entities (expensive operation).

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of cached entities
        """
        return await self._with_retry("list_all", self._list_all_impl, limit, offset)

    async def _list_all_impl(self, limit: int | None = None, offset: int = 0) -> list[T]:
        """Internal list all implementation."""
        async with self._get_connection():
            # Get all keys matching pattern
            pattern = f"{self.key_prefix}:*" if self.key_prefix else "*"
            keys = await self._client.keys(pattern)

            # Apply offset and limit
            if offset > 0:
                keys = keys[offset:]
            if limit:
                keys = keys[:limit]

            # Get all values
            if not keys:
                return []

            values = await self._client.mget(keys)
            entities = []

            for value in values:
                if value:
                    try:
                        entity = self._json_to_entity(value)
                        entities.append(entity)
                    except Exception as e:
                        self.logger.warning("Failed to deserialize cached entity", error=str(e))

            self.logger.info(
                "Listed cached entities",
                count=len(entities),
                total_keys=len(keys),
                limit=limit,
                offset=offset,
            )
            self.metrics.increment_counter("redis_operations_total", {"operation": "list"})

            return entities

    async def set_with_ttl(self, entity_id: ID, entity: T, ttl: int) -> None:
        """Cache entity with specific TTL.

        Args:
            entity_id: Entity ID
            entity: Entity to cache
            ttl: Time-to-live in seconds
        """
        await self._with_retry("set_with_ttl", self._set_with_ttl_impl, entity_id, entity, ttl)

    async def _set_with_ttl_impl(self, entity_id: ID, entity: T, ttl: int) -> None:
        """Internal set with TTL implementation."""
        async with self._get_connection():
            cache_key = self._get_cache_key(entity_id)
            entity_json = self._entity_to_json(entity)

            await self._client.setex(cache_key, ttl, entity_json)

            self.logger.info(
                "Cached entity with custom TTL",
                entity_id=entity_id,
                cache_key=cache_key,
                ttl=ttl,
            )
            self.metrics.increment_counter("redis_operations_total", {"operation": "set_ttl"})

    async def get_ttl(self, entity_id: ID) -> int:
        """Get remaining TTL for cached entity.

        Args:
            entity_id: Entity ID

        Returns:
            Remaining TTL in seconds, -1 if no TTL, -2 if key doesn't exist
        """
        return await self._with_retry("get_ttl", self._get_ttl_impl, entity_id)

    async def _get_ttl_impl(self, entity_id: ID) -> int:
        """Internal get TTL implementation."""
        async with self._get_connection():
            cache_key = self._get_cache_key(entity_id)
            ttl = await self._client.ttl(cache_key)

            self.logger.debug("Retrieved TTL", entity_id=entity_id, ttl=ttl)
            self.metrics.increment_counter("redis_operations_total", {"operation": "get_ttl"})

            return ttl

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern.

        Args:
            pattern: Key pattern to match

        Returns:
            Number of keys deleted
        """
        return await self._with_retry("invalidate_pattern", self._invalidate_pattern_impl, pattern)

    async def _invalidate_pattern_impl(self, pattern: str) -> int:
        """Internal invalidate pattern implementation."""
        async with self._get_connection():
            # Add prefix to pattern if configured
            if self.key_prefix:
                full_pattern = f"{self.key_prefix}:{pattern}"
            else:
                full_pattern = pattern

            keys = await self._client.keys(full_pattern)

            if keys:
                deleted_count = await self._client.delete(*keys)
                self.logger.info(
                    "Invalidated keys by pattern",
                    pattern=full_pattern,
                    deleted_count=deleted_count,
                )
                self.metrics.increment_counter(
                    "redis_operations_total",
                    {"operation": "invalidate_pattern"},
                )
                return deleted_count

            return 0

    def _entity_to_json(self, entity: T) -> str:
        """Convert entity to JSON string for Redis storage.

        Args:
            entity: Entity to convert

        Returns:
            JSON string representation

        Note:
            This should be overridden by concrete implementations
        """
        if hasattr(entity, "__dict__"):
            return json.dumps(
                {k: v for k, v in entity.__dict__.items() if not k.startswith("_")},
                default=str,  # Handle non-serializable types
            )
        return json.dumps({"data": str(entity)})

    def _json_to_entity(self, json_str: str) -> T:
        """Convert JSON string to entity.

        Args:
            json_str: JSON string from Redis

        Returns:
            Entity instance

        Note:
            This should be overridden by concrete implementations
        """
        # Default implementation - should be overridden
        return json.loads(json_str)

    def _get_entity_id(self, entity: T) -> ID:
        """Get entity ID from entity.

        Args:
            entity: Entity

        Returns:
            Entity ID

        Note:
            This should be overridden by concrete implementations
        """
        if hasattr(entity, "id"):
            return entity.id
        raise ValueError("Entity does not have an ID field")
