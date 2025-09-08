"""Unit tests for Firestore repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock, patch

if TYPE_CHECKING:
    from unittest.mock import MagicMock

import pytest

from src.infrastructure.persistence.repositories.firestore import FirestoreRepository
from src.shared.exceptions import ConnectionException


class TestEntity:
    """Test entity for Firestore operations."""

    def __init__(self, entity_id: str | None, name: str) -> None:
        """Initialize test entity."""
        self.id = entity_id
        self.name = name

    def to_dict(self) -> dict[str, str | None]:
        """Return dict representation."""
        return {"id": self.id, "name": self.name}


class MockFirestoreRepository(FirestoreRepository[TestEntity, str]):
    """Mock Firestore repository for testing."""

    def _entity_to_dict(self, entity: TestEntity) -> dict[str, str | None]:
        """Convert entity to dict."""
        return {"name": entity.name}

    def _dict_to_entity(self, data: dict[str, str | None]) -> TestEntity:
        """Convert dict to entity."""
        name = data.get("name")
        if name is None:
            name = ""
        return TestEntity(data.get("id"), name)

    def _get_entity_id(self, entity: TestEntity) -> str:
        """Get entity ID."""
        if entity.id is None:
            raise ValueError("Entity must have an ID")
        return entity.id


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestFirestoreRepositoryInitialisation:
    """Test Firestore repository initialisation and configuration."""

    def test_initialises_with_connection_and_collection_details(self) -> None:
        """Should initialise with connection URL and Firestore-specific configuration."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project",
            collection_name="test_entities",
            project_id="test-project",
            cache_ttl=600,
            max_retries=5,
            retry_delay=2.0,
        )

        assert repo.connection_url == "firestore://project"
        assert repo.collection_name == "test_entities"
        assert repo.project_id == "test-project"
        assert repo.cache_ttl == 600
        assert repo.max_retries == 5
        assert repo.retry_delay == 2.0
        assert repo._client is None
        assert repo._collection is None

    def test_initialises_with_default_project_when_not_specified(self) -> None:
        """Should initialise with default project configuration when project_id not specified."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        assert repo.project_id is None


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestFirestoreConnectionManagement:
    """Test Firestore connection establishment and management."""

    @patch("google.cloud.firestore.AsyncClient")
    async def test_establishes_firestore_connection_with_project_id(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should establish Firestore connection with specified project ID."""
        mock_client = AsyncMock()
        mock_collection = Mock()
        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project",
            collection_name="test_entities",
            project_id="test-project",
        )

        client = await repo._connect()

        assert client is mock_client
        mock_async_client.assert_called_once_with(project="test-project")
        mock_client.collection.assert_called_once_with("test_entities")

    @patch("google.cloud.firestore.AsyncClient")
    async def test_establishes_firestore_connection_with_default_project(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should establish Firestore connection with default project when project_id not specified."""
        mock_client = AsyncMock()
        mock_collection = Mock()
        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        client = await repo._connect()

        assert client is mock_client
        mock_async_client.assert_called_once_with()  # No project specified
        mock_client.collection.assert_called_once_with("test_entities")

    @patch("google.cloud.firestore.AsyncClient")
    async def test_handles_connection_failures_gracefully(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should handle Firestore connection failures gracefully."""
        mock_async_client.side_effect = Exception("Connection failed")

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        with pytest.raises(ConnectionException, match="Failed to connect to Firestore"):
            await repo._connect()

    async def test_disconnects_firestore_client_cleanly(self) -> None:
        """Should disconnect Firestore client cleanly."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = AsyncMock()
        repo._collection = AsyncMock()

        await repo._disconnect()

        assert repo._client is None
        assert repo._collection is None

    async def test_handles_disconnection_errors_gracefully(self) -> None:
        """Should handle disconnection errors gracefully."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        # Should not raise exception even with no client
        await repo._disconnect()


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestFirestoreTransactionManagement:
    """Test Firestore transaction handling and context management."""

    async def test_creates_transaction_context_with_auto_commit(self) -> None:
        """Should create transaction context with automatic commit on success."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        mock_client = AsyncMock()
        mock_transaction = AsyncMock()
        mock_transaction.commit = AsyncMock()
        mock_transaction.rollback = AsyncMock()
        mock_client.transaction = Mock(return_value=mock_transaction)
        repo._client = mock_client

        async with repo.transaction() as tx:
            assert tx is mock_transaction

        mock_transaction.commit.assert_called_once()

    async def test_connects_client_if_not_already_connected(self) -> None:
        """Should establish connection if client not already connected."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        with patch.object(repo, "_connect", new_callable=AsyncMock) as mock_connect:
            mock_client = AsyncMock()
            mock_transaction = AsyncMock()
            mock_transaction.commit = AsyncMock()
            mock_transaction.rollback = AsyncMock()
            mock_client.transaction = Mock(return_value=mock_transaction)

            # Set up the side effect to properly set the client
            async def connect_side_effect():
                repo._client = mock_client
                return mock_client

            mock_connect.side_effect = connect_side_effect

            async with repo.transaction():
                pass

            mock_connect.assert_called_once()

    async def test_rolls_back_transaction_on_exception(self) -> None:
        """Should rollback transaction when exception occurs."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        mock_client = AsyncMock()
        mock_transaction = AsyncMock()
        mock_transaction.commit = AsyncMock()
        mock_transaction.rollback = AsyncMock()
        mock_client.transaction = Mock(return_value=mock_transaction)
        repo._client = mock_client

        with pytest.raises(ValueError, match="Test error"):
            async with repo.transaction():
                raise ValueError("Test error")

        mock_transaction.rollback.assert_called_once()
        mock_transaction.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.resilience
class TestFirestoreCrudOperations:
    """Test Firestore CRUD operations with resilience and retry behavior."""

    async def test_creates_entity_with_generated_document_id(self) -> None:
        """Should create entity in Firestore with generated document ID."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        entity = TestEntity(None, "test_entity")
        mock_collection = AsyncMock()
        doc_ref = AsyncMock()
        doc_ref.id = "generated_id"
        mock_collection.add.return_value = (None, doc_ref)

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=None)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context
            repo._collection = mock_collection

            with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
                mock_retry.return_value = TestEntity("generated_id", "test_entity")

                result = await repo.create(entity)

                assert result.id == "generated_id"
                assert result.name == "test_entity"
                mock_retry.assert_called_once_with("create", repo._create_impl, entity)

    async def test_retrieves_entity_by_id_using_cache(self) -> None:
        """Should retrieve entity by ID using cache-first approach."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        cached_entity = TestEntity("cached_id", "cached_entity")
        repo._cache["cached_id"] = cached_entity

        result = await repo.get_by_id("cached_id")

        assert result is cached_entity

    async def test_retrieves_entity_from_firestore_on_cache_miss(self) -> None:
        """Should retrieve entity from Firestore when not in cache."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = TestEntity("test_id", "test_entity")

            result = await repo._get_by_id_from_db("test_id")

            assert result is not None
            assert result.id == "test_id"
            mock_retry.assert_called_once_with("get_by_id", repo._get_by_id_impl, "test_id")

    async def test_returns_none_when_document_not_found(self) -> None:
        """Should return None when Firestore document doesn't exist."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        mock_collection = AsyncMock()
        mock_doc_ref = AsyncMock()
        mock_doc = AsyncMock()
        mock_doc.exists = False
        mock_doc_ref.get = AsyncMock(return_value=mock_doc)
        mock_collection.document = Mock(return_value=mock_doc_ref)

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=None)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context
            repo._collection = mock_collection

            result = await repo._get_by_id_impl("nonexistent_id")

            assert result is None

    async def test_updates_entity_and_invalidates_cache(self) -> None:
        """Should update entity in Firestore and invalidate cache."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        entity = TestEntity("test_id", "updated_entity")
        repo._cache["test_id"] = TestEntity("test_id", "old_entity")

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = entity

            result = await repo.update(entity)

            assert result is entity
            assert "test_id" not in repo._cache
            mock_retry.assert_called_once_with("update", repo._update_impl, entity)

    async def test_deletes_entity_and_invalidates_cache(self) -> None:
        """Should delete entity from Firestore and invalidate cache."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._cache["test_id"] = TestEntity("test_id", "cached_entity")

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = True

            result = await repo.delete("test_id")

            assert result is True
            assert "test_id" not in repo._cache
            mock_retry.assert_called_once_with("delete", repo._delete_impl, "test_id")

    async def test_lists_entities_with_pagination_support(self) -> None:
        """Should list entities with proper pagination support."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        expected_entities = [TestEntity("1", "entity1"), TestEntity("2", "entity2")]

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = expected_entities

            result = await repo.list_all(limit=10, offset=5)

            assert result == expected_entities
            mock_retry.assert_called_once_with("list_all", repo._list_all_impl, 10, 5)


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.resilience
class TestFirestoreQueryOperations:
    """Test Firestore query operations and field-based filtering."""

    async def test_queries_entities_by_field_value(self) -> None:
        """Should query entities by field value with proper filtering."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        expected_entities = [TestEntity("1", "matching_entity")]

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = expected_entities

            result = await repo.query_by_field("name", "matching_entity", limit=5)

            assert result == expected_entities
            mock_retry.assert_called_once_with(
                "query_by_field", repo._query_by_field_impl, "name", "matching_entity", 5
            )

    async def test_applies_query_limit_when_specified(self) -> None:
        """Should apply query limit when specified."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        mock_collection = Mock()
        mock_query = Mock()
        mock_collection.where = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)

        mock_doc = Mock()
        mock_doc.to_dict = Mock(return_value={"name": "test"})
        mock_doc.id = "doc_id"

        # Mock async iterator for stream()
        class MockAsyncIterator:
            def __init__(self, items: list[Any]) -> None:
                self.items = items
                self.index = 0

            def __aiter__(self) -> MockAsyncIterator:
                return self

            async def __anext__(self) -> Any:
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        mock_query.stream = Mock(return_value=MockAsyncIterator([mock_doc]))

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=None)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context
            repo._collection = mock_collection

            await repo._query_by_field_impl("status", "active", limit=3)

            mock_query.limit.assert_called_once_with(3)


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.resilience
class TestFirestoreResilience:
    """Test Firestore repository resilience and error handling."""

    async def test_retries_failed_operations_with_exponential_backoff(self) -> None:
        """Should retry failed operations with proper backoff strategy."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project",
            collection_name="test_entities",
            max_retries=2,
            retry_delay=0.01,
        )
        entity = TestEntity("test_id", "test_entity")

        with patch.object(repo, "_create_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.side_effect = [Exception("Temporary failure"), entity]

            result = await repo.create(entity)

            assert result is entity
            assert mock_impl.call_count == 2

    async def test_fails_after_exhausting_all_retries(self) -> None:
        """Should fail operation after exhausting all retry attempts."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project",
            collection_name="test_entities",
            max_retries=1,
            retry_delay=0.01,
        )
        entity = TestEntity("test_id", "test_entity")

        with patch.object(repo, "_create_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.side_effect = Exception("Persistent failure")

            with pytest.raises(Exception, match="Persistent failure"):
                await repo.create(entity)

            assert mock_impl.call_count == 2  # Initial + 1 retry

    async def test_maintains_observability_during_errors(self) -> None:
        """Should maintain observability metrics and logging during error conditions."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        # Verify observability components are available during errors
        assert repo.logger is not None
        assert repo.metrics is not None

    async def test_handles_firestore_specific_exceptions(self) -> None:
        """Should handle Firestore-specific exceptions appropriately."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        with patch.object(repo, "_connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Permission denied")

            result = await repo.health_check()

            assert result is False


@pytest.mark.integration
@pytest.mark.behaviour
@pytest.mark.database
class TestFirestoreIntegration:
    """Test Firestore repository integration patterns."""

    def test_integrates_with_base_repository_interfaces(self) -> None:
        """Should integrate properly with base repository interfaces and protocols."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        # Verify it has all required repository methods
        assert hasattr(repo, "create")
        assert hasattr(repo, "get_by_id")
        assert hasattr(repo, "update")
        assert hasattr(repo, "delete")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "health_check")

    def test_provides_firestore_specific_functionality(self) -> None:
        """Should provide Firestore-specific functionality like queries and transactions."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        # Verify Firestore-specific methods
        assert hasattr(repo, "transaction")
        assert hasattr(repo, "query_by_field")
        assert hasattr(repo, "collection_name")
        assert hasattr(repo, "project_id")

    async def test_works_with_caching_layer(self) -> None:
        """Should work properly with inherited caching functionality."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        # Test that cache functionality is available
        assert hasattr(repo, "_cache")
        assert hasattr(repo, "_get_cache_key")
        assert hasattr(repo, "_invalidate_cache")

        # Test cache behavior
        cache_key = repo._get_cache_key("test_id")
        assert "test_id" in cache_key


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestFirestoreImplementationBehaviour:
    """Test Firestore repository implementation behaviour for core operations."""

    @patch("google.cloud.firestore.AsyncClient")
    async def test_establishes_connection_with_project_id(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should establish connection with specific project ID."""
        mock_client = AsyncMock()
        mock_collection = Mock()
        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project",
            collection_name="test_entities",
            project_id="test-project-123",
        )

        result = await repo._connect()

        assert result is mock_client
        mock_async_client.assert_called_once_with(project="test-project-123")
        mock_client.collection.assert_called_once_with("test_entities")
        assert repo._client is mock_client

    @patch("google.cloud.firestore.AsyncClient")
    async def test_establishes_connection_with_default_project(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should establish connection using default project."""
        mock_client = AsyncMock()
        mock_collection = Mock()
        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        result = await repo._connect()

        assert result is mock_client
        mock_async_client.assert_called_once_with()
        mock_client.collection.assert_called_once_with("test_entities")

    async def test_disconnects_client_cleanly(self) -> None:
        """Should disconnect client and clear references cleanly."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = Mock()
        repo._collection = Mock()

        await repo._disconnect()

        assert repo._client is None
        assert repo._collection is None

    @patch("google.cloud.firestore.AsyncClient")
    async def test_creates_entity_with_firestore_document(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should create entity using Firestore document operations."""
        entity = TestEntity(None, "test_name")

        mock_client = AsyncMock()
        mock_collection = AsyncMock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "generated_id"

        # Mock the add method to return a tuple (transaction_ref, doc_ref)
        mock_collection.add = AsyncMock(return_value=(None, mock_doc_ref))
        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = mock_client
        repo._collection = mock_collection

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=None)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._create_impl(entity)

            assert result.id == "generated_id"
            assert result.name == "test_name"
            mock_collection.add.assert_called_once_with({"name": "test_name"})

    @patch("google.cloud.firestore.AsyncClient")
    async def test_retrieves_existing_document_by_id(self, mock_async_client: MagicMock) -> None:
        """Should retrieve existing document by ID from Firestore."""
        mock_client = AsyncMock()
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc = Mock()

        # Mock existing document
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "test_entity"}
        mock_doc.id = "test_id"

        async def mock_get():
            return mock_doc

        mock_doc_ref.get = mock_get
        mock_collection.document.return_value = mock_doc_ref

        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = mock_client
        repo._collection = mock_collection

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=None)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._get_by_id_impl("test_id")

            assert result is not None
            assert result.id == "test_id"
            assert result.name == "test_entity"
            mock_collection.document.assert_called_once_with("test_id")

    @patch("google.cloud.firestore.AsyncClient")
    async def test_get_by_id_not_found_covers_missing_lines(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should cover get_by_id not found implementation lines."""
        mock_client = AsyncMock()
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc = Mock()

        # Mock non-existing document
        mock_doc.exists = False

        async def mock_get():
            return mock_doc

        mock_doc_ref.get = mock_get
        mock_collection.document.return_value = mock_doc_ref

        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = mock_client
        repo._collection = mock_collection

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=None)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._get_by_id_impl("nonexistent_id")

            assert result is None

    @patch("google.cloud.firestore.AsyncClient")
    async def test_update_implementation_covers_missing_lines(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should cover update implementation lines 211-221."""
        entity = TestEntity("test_id", "updated_name")

        mock_client = AsyncMock()
        mock_collection = Mock()
        mock_doc_ref = AsyncMock()
        mock_collection.document.return_value = mock_doc_ref

        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = mock_client
        repo._collection = mock_collection

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=None)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._update_impl(entity)

            assert result is entity
            mock_collection.document.assert_called_once_with("test_id")
            mock_doc_ref.update.assert_called_once_with({"name": "updated_name"})

    @patch("google.cloud.firestore.AsyncClient")
    async def test_delete_implementation_covers_missing_lines(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should cover delete implementation lines 241-259."""
        mock_client = AsyncMock()
        mock_collection = Mock()
        mock_doc_ref = AsyncMock()
        mock_doc = Mock()

        # Mock existing document
        mock_doc.exists = True

        async def mock_get():
            return mock_doc

        mock_doc_ref.get = mock_get
        mock_collection.document.return_value = mock_doc_ref

        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = mock_client
        repo._collection = mock_collection

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=None)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._delete_impl("test_id")

            assert result is True
            mock_collection.document.assert_called_once_with("test_id")
            mock_doc_ref.delete.assert_called_once()

    @patch("google.cloud.firestore.AsyncClient")
    async def test_delete_not_found_covers_missing_lines(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should cover delete not found implementation lines."""
        mock_client = AsyncMock()
        mock_collection = Mock()
        mock_doc_ref = AsyncMock()
        mock_doc = Mock()

        # Mock non-existing document
        mock_doc.exists = False

        async def mock_get():
            return mock_doc

        mock_doc_ref.get = mock_get
        mock_collection.document.return_value = mock_doc_ref

        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = mock_client
        repo._collection = mock_collection

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=None)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._delete_impl("nonexistent_id")

            assert result is False

    @patch("google.cloud.firestore.AsyncClient")
    async def test_list_all_implementation_covers_missing_lines(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should cover list_all implementation lines 275-300."""
        mock_client = AsyncMock()
        mock_collection = Mock()

        # Mock documents
        mock_doc1 = Mock()
        mock_doc1.to_dict.return_value = {"name": "entity1"}
        mock_doc1.id = "id1"

        mock_doc2 = Mock()
        mock_doc2.to_dict.return_value = {"name": "entity2"}
        mock_doc2.id = "id2"

        # Mock query operations
        mock_query = Mock()
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query

        class MockAsyncIterator:
            def __init__(self, items: list[Any]) -> None:
                self.items = items
                self.index = 0

            def __aiter__(self) -> MockAsyncIterator:
                return self

            async def __anext__(self) -> Any:
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        mock_query.stream = Mock(return_value=MockAsyncIterator([mock_doc1, mock_doc2]))
        mock_collection.offset.return_value = mock_query
        mock_collection.limit.return_value = mock_query

        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = mock_client
        repo._collection = mock_collection

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=None)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._list_all_impl(limit=10, offset=5)

            assert len(result) == 2
            assert result[0].id == "id1"
            assert result[0].name == "entity1"
            assert result[1].id == "id2"
            assert result[1].name == "entity2"

    async def test_converts_entity_to_dict_using_default_fallback(self) -> None:
        """Should convert entities to dict using default fallback when no override exists."""
        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )

        # Test with entity that has __dict__
        entity_with_dict = TestEntity("test_id", "test_name")
        result = repo._entity_to_dict(entity_with_dict)
        assert result == {"name": "test_name"}

        # Test default fallback for object without __dict__ attribute
        class SimpleEntity:
            __slots__ = ["name"]

            def __init__(self) -> None:
                self.name = "test"

        simple_entity: Any = SimpleEntity()

        # Override the method to test the default behavior
        class DefaultRepo(FirestoreRepository[SimpleEntity, str]):
            pass

        default_repo = DefaultRepo("url", "collection")
        result = default_repo._entity_to_dict(simple_entity)
        assert result == {"data": str(simple_entity)}

    async def test_returns_dict_as_entity_when_no_conversion_override(self) -> None:
        """Should return dict as entity when no conversion override is provided."""

        class DefaultRepo(FirestoreRepository[dict, str]):
            pass

        repo = DefaultRepo("url", "collection")
        test_dict = {"id": "test_id", "name": "test_name"}

        result = repo._dict_to_entity(test_dict)
        assert result is test_dict

    async def test_extracts_entity_id_from_id_attribute(self) -> None:
        """Should extract entity ID from id attribute or raise ValueError."""

        class DefaultRepo(FirestoreRepository[TestEntity, str]):
            pass

        repo = DefaultRepo("url", "collection")

        # Test with entity that has id
        entity_with_id = TestEntity("test_id", "test_name")
        result = repo._get_entity_id(entity_with_id)
        assert result == "test_id"

        # Test with entity without id
        class EntityWithoutId:
            def __init__(self, name: str) -> None:
                self.name = name

        class NoIdRepo(FirestoreRepository[EntityWithoutId, str]):
            pass

        no_id_repo = NoIdRepo("url", "collection")
        entity_without_id = EntityWithoutId("test_name")

        with pytest.raises(ValueError, match="Entity does not have an ID field"):
            no_id_repo._get_entity_id(entity_without_id)

    @patch("google.cloud.firestore.AsyncClient")
    async def test_query_by_field_implementation_covers_missing_lines(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should cover query_by_field implementation lines 371->374."""
        mock_client = AsyncMock()
        mock_collection = Mock()

        # Mock document
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {"name": "filtered_entity", "status": "active"}
        mock_doc.id = "filtered_id"

        # Mock query operations
        mock_query = Mock()
        mock_query.limit.return_value = mock_query

        class MockAsyncIterator:
            def __init__(self, items: list[Any]) -> None:
                self.items = items
                self.index = 0

            def __aiter__(self) -> MockAsyncIterator:
                return self

            async def __anext__(self) -> Any:
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        mock_query.stream = Mock(return_value=MockAsyncIterator([mock_doc]))
        mock_collection.where.return_value = mock_query

        mock_client.collection.return_value = mock_collection
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = mock_client
        repo._collection = mock_collection

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=None)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._query_by_field_impl("status", "active", limit=5)

            assert len(result) == 1
            assert result[0].id == "filtered_id"
            assert result[0].name == "filtered_entity"
            mock_collection.where.assert_called_once_with("status", "==", "active")
            mock_query.limit.assert_called_once_with(5)


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestFirestoreTransactionImplementation:
    """Test Firestore transaction context manager implementation."""

    @patch("google.cloud.firestore.AsyncClient")
    async def test_transaction_context_successful_commit(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should handle successful transaction with proper commit."""
        mock_client = Mock()
        mock_transaction = Mock()
        mock_transaction.commit = AsyncMock()
        mock_transaction.rollback = AsyncMock()
        mock_client.transaction = Mock(return_value=mock_transaction)
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = mock_client

        async with repo.transaction() as transaction:
            assert transaction is mock_transaction

        mock_client.transaction.assert_called_once()
        mock_transaction.commit.assert_called_once()

    @patch("google.cloud.firestore.AsyncClient")
    async def test_transaction_context_rollback_on_exception(
        self, mock_async_client: MagicMock
    ) -> None:
        """Should handle transaction rollback on exception."""
        mock_client = Mock()
        mock_transaction = Mock()
        mock_transaction.commit = AsyncMock()
        mock_transaction.rollback = AsyncMock()
        mock_client.transaction = Mock(return_value=mock_transaction)
        mock_async_client.return_value = mock_client

        repo = MockFirestoreRepository(
            connection_url="firestore://project", collection_name="test_entities"
        )
        repo._client = mock_client

        with pytest.raises(ValueError, match="Test error"):
            async with repo.transaction():
                raise ValueError("Test error")

        mock_transaction.rollback.assert_called_once()
        mock_transaction.commit.assert_not_called()
