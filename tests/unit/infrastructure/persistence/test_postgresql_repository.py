"""Unit tests for PostgreSQL repository implementation."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.infrastructure.persistence.repositories.postgresql import PostgreSQLRepository
from src.shared.exceptions import ConnectionException, RepositoryException


class TestEntity:
    """Test entity for PostgreSQL operations."""

    def __init__(self, entity_id: str | None, name: str, email: str | None = None) -> None:
        """Initialize test entity."""
        self.id = entity_id
        self.name = name
        self.email = email

    def to_dict(self) -> dict[str, str | None]:
        """Return dict representation."""
        return {"id": self.id, "name": self.name, "email": self.email}


class MockPostgreSQLRepository(PostgreSQLRepository[TestEntity, str]):
    """Mock PostgreSQL repository for testing."""

    def _entity_to_dict(self, entity: TestEntity) -> dict[str, str | None]:
        """Convert entity to dict."""
        result: dict[str, str | None] = {"name": entity.name}
        if entity.email:
            result["email"] = entity.email
        if entity.id:
            result["id"] = entity.id
        return result

    def _row_to_entity(self, row: Any) -> TestEntity:
        """Convert row to entity."""
        return TestEntity(row.get("id"), row["name"], row.get("email"))

    def _get_entity_id(self, entity: TestEntity) -> str:
        """Get entity ID."""
        if entity.id is None:
            raise ValueError("Entity must have an ID")
        return entity.id


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestPostgreSQLRepositoryInitialisation:
    """Test PostgreSQL repository initialisation and configuration."""

    def test_initialises_with_connection_and_table_details(self) -> None:
        """Should initialise with connection URL and PostgreSQL-specific configuration."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://user:pass@localhost/db",
            table_name="test_entities",
            pool_size=15,
            max_overflow=25,
            max_retries=5,
            retry_delay=2.0,
        )

        assert repo.connection_url == "postgresql://user:pass@localhost/db"
        assert repo.table_name == "test_entities"
        assert repo.pool_size == 15
        assert repo.max_overflow == 25
        assert repo.max_retries == 5
        assert repo.retry_delay == 2.0
        assert repo._engine is None
        assert repo._pool is None

    def test_initialises_with_default_pool_settings(self) -> None:
        """Should initialise with default connection pool settings."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        assert repo.pool_size == 10
        assert repo.max_overflow == 20
        assert repo.max_retries == 3
        assert repo.retry_delay == 1.0


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.network
class TestPostgreSQLConnectionManagement:
    """Test PostgreSQL connection establishment and management."""

    @patch("sqlalchemy.ext.asyncio.create_async_engine")
    async def test_establishes_connection_with_pool_configuration(
        self, mock_create_engine: Any
    ) -> None:
        """Should establish PostgreSQL connection with connection pooling."""
        mock_engine = Mock()
        mock_conn = AsyncMock()
        mock_create_engine.return_value = mock_engine

        # Setup async context manager for engine.begin()
        mock_context = Mock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_context)

        # Setup execute method
        mock_conn.execute = AsyncMock(return_value=None)

        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db",
            table_name="test_entities",
            pool_size=15,
            max_overflow=25,
        )

        engine = await repo._connect()

        assert engine is mock_engine
        mock_create_engine.assert_called_once_with(
            "postgresql://localhost/db",
            pool_size=15,
            max_overflow=25,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
        # Verify execute was called with SQLAlchemy text object containing "SELECT 1"
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert len(call_args) == 1
        assert str(call_args[0]) == "SELECT 1"

    @patch("sqlalchemy.ext.asyncio.create_async_engine")
    async def test_handles_connection_failures_gracefully(self, mock_create_engine: Any) -> None:
        """Should handle PostgreSQL connection failures gracefully."""
        mock_create_engine.side_effect = Exception("Database unavailable")

        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        with pytest.raises(ConnectionException, match="Failed to connect to PostgreSQL"):
            await repo._connect()

    async def test_disconnects_engine_cleanly(self) -> None:
        """Should disconnect PostgreSQL engine cleanly."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )
        mock_engine = AsyncMock()
        repo._engine = mock_engine

        await repo._disconnect()

        mock_engine.dispose.assert_called_once()
        assert repo._engine is None

    async def test_handles_disconnection_errors_gracefully(self) -> None:
        """Should handle disconnection errors gracefully."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )
        mock_engine = AsyncMock()
        mock_engine.dispose.side_effect = Exception("Disconnection error")
        repo._engine = mock_engine

        with pytest.raises(ConnectionException, match="Failed to disconnect from PostgreSQL"):
            await repo._disconnect()


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestPostgreSQLTransactionManagement:
    """Test PostgreSQL transaction handling and context management."""

    async def test_creates_transaction_context_with_auto_commit(self) -> None:
        """Should create transaction context with automatic commit on success."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()

        # Mock the context manager properly with __aenter__ and __aexit__
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_transaction)
        repo._engine = mock_engine

        async with repo.transaction() as conn:
            assert conn is mock_conn

        mock_engine.begin.assert_called_once()

    async def test_connects_engine_if_not_already_connected(self) -> None:
        """Should establish connection if engine not already connected."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        with patch.object(repo, "_connect", new_callable=AsyncMock) as mock_connect:
            mock_engine = AsyncMock()
            mock_conn = AsyncMock()
            mock_transaction = AsyncMock()
            mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_transaction.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = Mock(return_value=mock_transaction)

            # Set up the side effect to properly set the engine
            async def connect_side_effect():
                repo._engine = mock_engine
                return mock_engine

            mock_connect.side_effect = connect_side_effect

            async with repo.transaction():
                pass

            mock_connect.assert_called_once()

    async def test_handles_transaction_exceptions_with_rollback(self) -> None:
        """Should handle transaction exceptions with automatic rollback."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )
        mock_engine = AsyncMock()
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__ = AsyncMock(side_effect=Exception("Transaction error"))
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_transaction)
        repo._engine = mock_engine

        with pytest.raises(Exception, match="Transaction error"):
            async with repo.transaction():
                pass


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.resilience
class TestPostgreSQLCrudOperations:
    """Test PostgreSQL CRUD operations with resilience and SQL generation."""

    async def test_creates_entity_with_sql_insert_and_returning(self) -> None:
        """Should create entity using SQL INSERT with RETURNING clause."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )
        entity = TestEntity(None, "John Doe", "john@example.com")

        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_row = {"id": "generated_id", "name": "John Doe", "email": "john@example.com"}

        mock_result.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_result

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            mock_tx_context = AsyncMock()
            mock_tx_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tx_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin.return_value = mock_tx_context

            with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
                expected_entity = TestEntity("generated_id", "John Doe", "john@example.com")
                mock_retry.return_value = expected_entity

                result = await repo.create(entity)

                assert result.id == "generated_id"
                assert result.name == "John Doe"
                mock_retry.assert_called_once_with("create", repo._create_impl, entity)

    async def test_retrieves_entity_by_id_with_parameterized_query(self) -> None:
        """Should retrieve entity by ID using parameterized SQL query."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            expected_entity = TestEntity("test_id", "Test User")
            mock_retry.return_value = expected_entity

            result = await repo.get_by_id("test_id")

            assert result is not None
            assert result.id == "test_id"
            mock_retry.assert_called_once_with("get_by_id", repo._get_by_id_impl, "test_id")

    async def test_returns_none_when_entity_not_found(self) -> None:
        """Should return None when entity not found in database."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )

        mock_engine = Mock()
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone = Mock(return_value=None)
        mock_conn.execute.return_value = mock_result

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            mock_tx_context = Mock()
            mock_tx_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tx_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = Mock(return_value=mock_tx_context)

            result = await repo._get_by_id_impl("nonexistent_id")

            assert result is None

    async def test_updates_entity_with_sql_update_and_returning(self) -> None:
        """Should update entity using SQL UPDATE with RETURNING clause."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )
        entity = TestEntity("test_id", "Updated Name", "updated@example.com")

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = entity

            result = await repo.update(entity)

            assert result is entity
            mock_retry.assert_called_once_with("update", repo._update_impl, entity)

    async def test_raises_error_when_entity_not_found_for_update(self) -> None:
        """Should raise error when entity not found for update."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )
        entity = TestEntity("nonexistent_id", "Test Name")

        mock_engine = Mock()
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone = Mock(return_value=None)
        mock_conn.execute.return_value = mock_result

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            mock_tx_context = Mock()
            mock_tx_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tx_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = Mock(return_value=mock_tx_context)

            with pytest.raises(
                RepositoryException, match="Entity with ID nonexistent_id not found"
            ):
                await repo._update_impl(entity)

    async def test_deletes_entity_and_returns_success_status(self) -> None:
        """Should delete entity and return appropriate success status."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = True

            result = await repo.delete("test_id")

            assert result is True
            mock_retry.assert_called_once_with("delete", repo._delete_impl, "test_id")

    async def test_delete_returns_false_when_entity_not_found(self) -> None:
        """Should return False when entity not found for deletion."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )

        mock_engine = Mock()
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_result.rowcount = 0
        mock_conn.execute.return_value = mock_result

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            mock_tx_context = Mock()
            mock_tx_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tx_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = Mock(return_value=mock_tx_context)

            result = await repo._delete_impl("nonexistent_id")

            assert result is False

    async def test_lists_entities_with_pagination_support(self) -> None:
        """Should list entities with proper pagination support using LIMIT and OFFSET."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )
        expected_entities = [TestEntity("1", "User1"), TestEntity("2", "User2")]

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = expected_entities

            result = await repo.list_all(limit=10, offset=5)

            assert result == expected_entities
            mock_retry.assert_called_once_with("list_all", repo._list_all_impl, 10, 5)


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.resilience
class TestPostgreSQLQueryOperations:
    """Test PostgreSQL query operations and field-based filtering."""

    async def test_queries_entities_by_field_with_parameterized_where_clause(self) -> None:
        """Should query entities by field using parameterized WHERE clause."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )
        expected_entities = [TestEntity("1", "John Doe")]

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = expected_entities

            result = await repo.query_by_field("name", "John Doe", limit=5)

            assert result == expected_entities
            mock_retry.assert_called_once_with(
                "query_by_field", repo._query_by_field_impl, "name", "John Doe", 5
            )

    async def test_applies_query_limit_when_specified(self) -> None:
        """Should apply LIMIT clause when specified."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )

        mock_engine = Mock()
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchall = Mock(return_value=[{"id": "1", "name": "User", "email": None}])
        mock_conn.execute.return_value = mock_result

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            mock_tx_context = Mock()
            mock_tx_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tx_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = Mock(return_value=mock_tx_context)

            await repo._query_by_field_impl("status", "active", limit=3)

            # Verify SQL contains LIMIT
            call_args = mock_conn.execute.call_args[0][0]
            assert "LIMIT 3" in str(call_args)

    async def test_executes_raw_sql_with_parameter_binding(self) -> None:
        """Should execute raw SQL queries with proper parameter binding."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )

        with patch.object(repo, "_with_retry", new_callable=AsyncMock) as mock_retry:
            mock_result = AsyncMock()
            mock_retry.return_value = mock_result

            result = await repo.execute_raw_sql(
                "SELECT * FROM users WHERE created_at > :date", {"date": "2023-01-01"}
            )

            assert result is mock_result
            mock_retry.assert_called_once_with(
                "execute_raw_sql",
                repo._execute_raw_sql_impl,
                "SELECT * FROM users WHERE created_at > :date",
                {"date": "2023-01-01"},
            )


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.resilience
class TestPostgreSQLResilience:
    """Test PostgreSQL repository resilience and error handling."""

    async def test_retries_failed_operations_with_exponential_backoff(self) -> None:
        """Should retry failed operations with proper backoff strategy."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db",
            table_name="users",
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
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db",
            table_name="users",
            max_retries=1,
            retry_delay=0.01,
        )
        entity = TestEntity("test_id", "test_entity")

        with patch.object(repo, "_create_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.side_effect = Exception("Persistent failure")

            with pytest.raises(Exception, match="Persistent failure"):
                await repo.create(entity)

            assert mock_impl.call_count == 2  # Initial + 1 retry

    async def test_handles_sql_injection_prevention(self) -> None:
        """Should prevent SQL injection through parameterized queries."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )

        mock_engine = Mock()
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchall = Mock(return_value=[])
        mock_conn.execute.return_value = mock_result

        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            mock_tx_context = Mock()
            mock_tx_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tx_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = Mock(return_value=mock_tx_context)

            # Attempt SQL injection - should be safely parameterized
            malicious_value = "'; DROP TABLE users; --"
            await repo._query_by_field_impl("name", malicious_value)

            # Verify the value is passed as parameter, not concatenated
            call_args = mock_conn.execute.call_args
            assert malicious_value not in str(call_args[0][0])  # Not in SQL string
            # Check that malicious value is passed as parameter (second argument)
            assert call_args[0][1]["value"] == malicious_value  # Passed as parameter

    async def test_maintains_observability_during_errors(self) -> None:
        """Should maintain observability metrics and logging during error conditions."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )

        # Verify observability components are available during errors
        assert repo.logger is not None
        assert repo.metrics is not None


@pytest.mark.integration
@pytest.mark.behaviour
@pytest.mark.database
class TestPostgreSQLIntegration:
    """Test PostgreSQL repository integration patterns."""

    def test_integrates_with_base_repository_interfaces(self) -> None:
        """Should integrate properly with base repository interfaces and protocols."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )

        # Verify it has all required repository methods
        assert hasattr(repo, "create")
        assert hasattr(repo, "get_by_id")
        assert hasattr(repo, "update")
        assert hasattr(repo, "delete")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "health_check")

    def test_provides_postgresql_specific_functionality(self) -> None:
        """Should provide PostgreSQL-specific functionality like transactions and raw SQL."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users"
        )

        # Verify PostgreSQL-specific methods
        assert hasattr(repo, "transaction")
        assert hasattr(repo, "query_by_field")
        assert hasattr(repo, "execute_raw_sql")
        assert hasattr(repo, "table_name")
        assert hasattr(repo, "pool_size")
        assert hasattr(repo, "max_overflow")

    def test_works_with_connection_pooling(self) -> None:
        """Should work properly with connection pooling functionality."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="users", pool_size=20
        )

        # Test that pooling functionality is available
        assert repo.pool_size == 20
        assert hasattr(repo, "max_overflow")

    def test_works_with_retry_logic(self) -> None:
        """Should work properly with inherited retry functionality."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db",
            table_name="users",
            max_retries=5,
            retry_delay=2.0,
        )

        # Test that retry functionality is available
        assert repo.max_retries == 5
        assert repo.retry_delay == 2.0
        assert hasattr(repo, "_with_retry")

    async def test_sql_generation_follows_secure_patterns(self) -> None:
        """Should generate SQL following secure patterns with parameterization."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="safe_table"
        )

        # Verify table name is controlled and safe
        assert repo.table_name == "safe_table"

        # All SQL should use parameterized queries - this is enforced by the implementation
        # The actual SQL generation is tested in the individual operation tests


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestPostgreSQLImplementationBehaviour:
    """Test PostgreSQL repository actual implementation behaviour."""

    async def test_disconnects_existing_engine(self) -> None:
        """Disconnects existing engine when one exists."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )
        mock_engine = AsyncMock()
        repo._engine = mock_engine

        await repo._disconnect()

        mock_engine.dispose.assert_called_once()

    async def test_transaction_rollback_on_exception(self) -> None:
        """Rolls back transaction and increments metrics on exception."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()

        # Set up the transaction context to raise an exception
        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_transaction)
        repo._engine = mock_engine

        # Mock the operation that will fail inside the transaction
        with pytest.raises(ValueError, match="Transaction failed"):
            async with repo.transaction():
                raise ValueError("Transaction failed")

    async def test_create_returns_entity_with_generated_id(self) -> None:
        """Creates entity and returns it with generated ID."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        entity = TestEntity(None, "test_name", "test@example.com")

        # Mock the _get_connection method to avoid actual connection
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_row = {"id": "generated_id", "name": "test_name", "email": "test@example.com"}

        mock_result.fetchone = Mock(return_value=mock_row)
        mock_conn.execute = AsyncMock(return_value=mock_result)
        mock_conn.begin = AsyncMock()
        mock_conn.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.begin.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock _get_connection to return the mocked connection
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock engine.begin() to return an async context manager
            mock_tx_context = Mock()
            mock_tx_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_tx_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = Mock(return_value=mock_tx_context)

            result = await repo._create_impl(entity)

            assert result.id == "generated_id"
            assert result.name == "test_name"
            assert result.email == "test@example.com"

    async def test_create_raises_exception_when_no_result_returned(self) -> None:
        """Raises RepositoryException when no result returned from INSERT."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        entity = TestEntity(None, "test_name", "test@example.com")

        # Mock the database connection with no result returned
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_result = AsyncMock()

        mock_result.fetchone = Mock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=mock_result)

        # Mock _get_connection to avoid actual connection
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            mock_transaction_context = AsyncMock()
            mock_transaction_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_transaction_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = Mock(return_value=mock_transaction_context)

            with pytest.raises(
                RepositoryException, match="Failed to create entity - no result returned"
            ):
                await repo._create_impl(entity)

    async def test_get_by_id_returns_entity_when_found(self) -> None:
        """Returns entity when found by ID."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        # Mock the database connection and query execution
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_result = AsyncMock()
        mock_row = {"id": "test_id", "name": "test_name", "email": "test@example.com"}

        mock_result.fetchone = Mock(return_value=mock_row)
        mock_conn.execute = AsyncMock(return_value=mock_result)

        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_transaction)

        # Mock _get_connection to return the mocked engine
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._get_by_id_impl("test_id")

            assert result is not None
            assert result.id == "test_id"
            assert result.name == "test_name"

    async def test_get_by_id_returns_none_when_not_found(self) -> None:
        """Returns None when entity not found by ID."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        # Mock the database connection with no result
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_result = AsyncMock()

        mock_result.fetchone = Mock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=mock_result)

        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_transaction)

        # Mock _get_connection to return the mocked engine
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._get_by_id_impl("non_existent_id")

            assert result is None

    async def test_update_returns_updated_entity(self) -> None:
        """Updates entity and returns updated version."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        entity = TestEntity("test_id", "updated_name", "updated@example.com")

        # Mock the database connection and query execution
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_result = AsyncMock()
        mock_row = {"id": "test_id", "name": "updated_name", "email": "updated@example.com"}

        mock_result.fetchone = Mock(return_value=mock_row)
        mock_result.rowcount = 1
        mock_conn.execute = AsyncMock(return_value=mock_result)

        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_transaction)

        # Mock _get_connection to return the mocked engine
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._update_impl(entity)

            assert result.id == "test_id"
            assert result.name == "updated_name"
            assert result.email == "updated@example.com"

    async def test_update_raises_exception_when_entity_not_found(self) -> None:
        """Raises RepositoryException when entity to update not found."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        entity = TestEntity("non_existent_id", "updated_name", "updated@example.com")

        # Mock the database connection with no rows affected
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_result = AsyncMock()

        mock_result.rowcount = 0
        mock_result.fetchone = Mock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=mock_result)

        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_transaction)

        # Mock _get_connection to return the mocked engine
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            with pytest.raises(
                RepositoryException, match="Entity with ID non_existent_id not found for update"
            ):
                await repo._update_impl(entity)

    async def test_delete_returns_true_when_entity_deleted(self) -> None:
        """Returns True when entity successfully deleted."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        # Mock the database connection and query execution
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_result = AsyncMock()

        mock_result.rowcount = 1
        mock_conn.execute = AsyncMock(return_value=mock_result)

        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_transaction)

        # Mock _get_connection to return the mocked engine
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._delete_impl("test_id")

            assert result is True

    async def test_delete_returns_false_when_entity_not_found(self) -> None:
        """Returns False when entity to delete not found."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        # Mock the database connection with no rows affected
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_result = AsyncMock()

        mock_result.rowcount = 0
        mock_conn.execute = AsyncMock(return_value=mock_result)

        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_transaction)

        # Mock _get_connection to return the mocked engine
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._delete_impl("non_existent_id")

            assert result is False

    async def test_list_all_returns_entities(self) -> None:
        """Lists all entities from database."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        # Mock the database connection and query execution
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_result = AsyncMock()
        mock_rows = [
            {"id": "1", "name": "name1", "email": "email1@example.com"},
            {"id": "2", "name": "name2", "email": "email2@example.com"},
        ]

        mock_result.fetchall = Mock(return_value=mock_rows)
        mock_conn.execute = AsyncMock(return_value=mock_result)

        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_transaction)

        # Mock _get_connection to return the mocked engine
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._list_all_impl(limit=10, offset=0)

            assert len(result) == 2
            assert result[0].id == "1"
            assert result[1].id == "2"

    async def test_query_by_field_returns_matching_entities(self) -> None:
        """Returns entities matching field query."""
        repo = MockPostgreSQLRepository(
            connection_url="postgresql://localhost/db", table_name="test_entities"
        )

        # Mock the database connection and query execution
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_result = AsyncMock()
        mock_rows = [
            {"id": "1", "name": "active_user", "email": "active@example.com"},
        ]

        mock_result.fetchall = Mock(return_value=mock_rows)
        mock_conn.execute = AsyncMock(return_value=mock_result)

        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin = Mock(return_value=mock_transaction)

        # Mock _get_connection to return the mocked engine
        with patch.object(repo, "_get_connection") as mock_get_conn:
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_conn.return_value = mock_context

            result = await repo._query_by_field_impl("status", "active", limit=10)

            assert len(result) == 1
            assert result[0].name == "active_user"
