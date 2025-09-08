"""Google Firestore repository implementation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, TypeVar

from .base import CacheableRepository, RetryMixin
from src.shared.exceptions import ConnectionException

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

T = TypeVar("T")
ID = TypeVar("ID")


class FirestoreRepository(CacheableRepository[T, ID], RetryMixin):
    """Google Firestore repository implementation."""

    def __init__(
        self,
        connection_url: str,
        collection_name: str,
        project_id: str | None = None,
        cache_ttl: int = 300,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize Firestore repository.

        Args:
            connection_url: Firestore connection URL
            collection_name: Firestore collection name
            project_id: GCP project ID (optional, will use default)
            cache_ttl: Cache time-to-live in seconds
            max_retries: Maximum retry attempts
            retry_delay: Retry delay in seconds
        """
        CacheableRepository.__init__(self, connection_url, cache_ttl)
        RetryMixin.__init__(self, max_retries, retry_delay)
        self.collection_name = collection_name
        self.project_id = project_id
        self._client: Any = None
        self._collection: Any = None

    async def _connect(self) -> Any:
        """Establish Firestore connection.

        Returns:
            Firestore client instance

        Raises:
            ConnectionException: If connection fails
        """
        try:
            # Import here to avoid dependency issues
            from google.cloud import firestore

            if self.project_id:
                self._client = firestore.AsyncClient(project=self.project_id)
            else:
                self._client = firestore.AsyncClient()

            self._collection = self._client.collection(self.collection_name)

            self.logger.info(
                "Connected to Firestore",
                collection=self.collection_name,
                project_id=self.project_id,
            )
            self.metrics.increment_counter("firestore_connections_total", {"status": "success"})

            return self._client

        except Exception as e:
            self.logger.error("Failed to connect to Firestore", error=str(e))
            self.metrics.increment_counter("firestore_connections_total", {"status": "failure"})
            raise ConnectionException(f"Failed to connect to Firestore: {e}") from e

    async def _disconnect(self) -> None:
        """Close Firestore connection.

        Raises:
            ConnectionException: If disconnection fails
        """
        try:
            if self._client:
                # Firestore client doesn't require explicit disconnection
                self._client = None
                self._collection = None
                self.logger.info("Disconnected from Firestore", collection=self.collection_name)

        except Exception as e:
            self.logger.error("Failed to disconnect from Firestore", error=str(e))
            raise ConnectionException(f"Failed to disconnect from Firestore: {e}") from e

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Any]:
        """Create Firestore transaction context.

        Yields:
            Firestore transaction

        Raises:
            Exception: If transaction fails
        """
        if not self._client:
            await self._connect()

        transaction = self._client.transaction()
        try:
            yield transaction
            await transaction.commit()
            self.metrics.increment_counter("firestore_transactions_total", {"status": "committed"})

        except Exception as e:
            await transaction.rollback()
            self.logger.error("Firestore transaction failed", error=str(e))
            self.metrics.increment_counter("firestore_transactions_total", {"status": "rollback"})
            raise

    async def create(self, entity: T) -> T:
        """Create entity in Firestore.

        Args:
            entity: Entity to create

        Returns:
            Created entity with document ID

        Raises:
            RepositoryError: If creation fails
        """
        return await self._with_retry("create", self._create_impl, entity)

    async def _create_impl(self, entity: T) -> T:
        """Internal create implementation."""
        async with self._get_connection():
            # Convert entity to dictionary for Firestore
            entity_dict = self._entity_to_dict(entity)

            # Add document to collection
            doc_ref = await self._collection.add(entity_dict)

            # Update entity with generated ID
            updated_entity = self._dict_to_entity({**entity_dict, "id": doc_ref[1].id})

            self.logger.info("Created entity in Firestore", entity_id=doc_ref[1].id)
            self.metrics.increment_counter("firestore_operations_total", {"operation": "create"})

            return updated_entity

    async def get_by_id(self, entity_id: ID) -> T | None:
        """Get entity by ID from Firestore with caching.

        Args:
            entity_id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        return await super().get_by_id(entity_id)

    async def _get_by_id_from_db(self, entity_id: ID) -> T | None:
        """Get entity by ID from Firestore (bypass cache)."""
        return await self._with_retry("get_by_id", self._get_by_id_impl, entity_id)

    async def _get_by_id_impl(self, entity_id: ID) -> T | None:
        """Internal get by ID implementation."""
        async with self._get_connection():
            doc_ref = self._collection.document(str(entity_id))
            doc = await doc_ref.get()

            if not doc.exists:
                self.metrics.increment_counter(
                    "firestore_operations_total", {"operation": "get_not_found"}
                )
                return None

            entity_dict = doc.to_dict()
            entity_dict["id"] = doc.id

            self.metrics.increment_counter(
                "firestore_operations_total", {"operation": "get_success"}
            )
            return self._dict_to_entity(entity_dict)

    async def update(self, entity: T) -> T:
        """Update entity in Firestore.

        Args:
            entity: Entity to update

        Returns:
            Updated entity

        Raises:
            RepositoryError: If update fails
        """
        result = await self._with_retry("update", self._update_impl, entity)

        # Invalidate cache
        entity_id = self._get_entity_id(entity)
        self._invalidate_cache(entity_id)

        return result

    async def _update_impl(self, entity: T) -> T:
        """Internal update implementation."""
        async with self._get_connection():
            entity_id = self._get_entity_id(entity)
            entity_dict = self._entity_to_dict(entity)

            doc_ref = self._collection.document(str(entity_id))
            await doc_ref.update(entity_dict)

            self.logger.info("Updated entity in Firestore", entity_id=entity_id)
            self.metrics.increment_counter("firestore_operations_total", {"operation": "update"})

            return entity

    async def delete(self, entity_id: ID) -> bool:
        """Delete entity from Firestore.

        Args:
            entity_id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        result = await self._with_retry("delete", self._delete_impl, entity_id)

        # Invalidate cache
        self._invalidate_cache(entity_id)

        return result

    async def _delete_impl(self, entity_id: ID) -> bool:
        """Internal delete implementation."""
        async with self._get_connection():
            doc_ref = self._collection.document(str(entity_id))

            # Check if document exists
            doc = await doc_ref.get()
            if not doc.exists:
                self.metrics.increment_counter(
                    "firestore_operations_total", {"operation": "delete_not_found"}
                )
                return False

            await doc_ref.delete()

            self.logger.info("Deleted entity from Firestore", entity_id=entity_id)
            self.metrics.increment_counter(
                "firestore_operations_total", {"operation": "delete_success"}
            )

            return True

    async def list_all(self, limit: int | None = None, offset: int = 0) -> list[T]:
        """List all entities from Firestore.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities
        """
        return await self._with_retry("list_all", self._list_all_impl, limit, offset)

    async def _list_all_impl(self, limit: int | None = None, offset: int = 0) -> list[T]:
        """Internal list all implementation."""
        async with self._get_connection():
            query = self._collection

            if offset > 0:
                query = query.offset(offset)

            if limit:
                query = query.limit(limit)

            docs = [doc async for doc in query.stream()]
            entities = []

            for doc in docs:
                entity_dict = doc.to_dict()
                entity_dict["id"] = doc.id
                entities.append(self._dict_to_entity(entity_dict))

            self.logger.info(
                "Listed entities from Firestore",
                count=len(entities),
                limit=limit,
                offset=offset,
            )
            self.metrics.increment_counter("firestore_operations_total", {"operation": "list"})

            return entities

    def _entity_to_dict(self, entity: T) -> dict[str, Any]:
        """Convert entity to dictionary for Firestore storage.

        Args:
            entity: Entity to convert

        Returns:
            Dictionary representation

        Note:
            This should be overridden by concrete implementations
        """
        if hasattr(entity, "__dict__"):
            return {k: v for k, v in entity.__dict__.items() if not k.startswith("_")}
        return {"data": str(entity)}

    def _dict_to_entity(self, data: dict[str, Any]) -> T:
        """Convert dictionary to entity.

        Args:
            data: Dictionary data from Firestore

        Returns:
            Entity instance

        Note:
            This should be overridden by concrete implementations
        """
        # Default implementation - should be overridden
        return data  # type: ignore[return-value]

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

    async def query_by_field(self, field: str, value: Any, limit: int | None = None) -> list[T]:
        """Query entities by field value.

        Args:
            field: Field name to query
            value: Field value to match
            limit: Maximum number of results

        Returns:
            List of matching entities
        """
        return await self._with_retry(
            "query_by_field", self._query_by_field_impl, field, value, limit
        )

    async def _query_by_field_impl(
        self, field: str, value: Any, limit: int | None = None
    ) -> list[T]:
        """Internal query by field implementation."""
        async with self._get_connection():
            query = self._collection.where(field, "==", value)

            if limit:
                query = query.limit(limit)

            docs = [doc async for doc in query.stream()]
            entities = []

            for doc in docs:
                entity_dict = doc.to_dict()
                entity_dict["id"] = doc.id
                entities.append(self._dict_to_entity(entity_dict))

            self.logger.info(
                "Queried entities by field",
                field=field,
                value=str(value),
                count=len(entities),
            )
            self.metrics.increment_counter("firestore_operations_total", {"operation": "query"})

            return entities
