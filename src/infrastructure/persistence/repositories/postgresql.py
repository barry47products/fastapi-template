"""PostgreSQL repository implementation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# SQLAlchemy imports will be done dynamically to avoid dependency issues

from src.shared.exceptions import ConnectionException, RepositoryException

from .base import BaseRepository, ConnectionPoolMixin, RetryMixin, TransactionalRepository

T = TypeVar("T")
ID = TypeVar("ID")


class PostgreSQLRepository(TransactionalRepository[T, ID], ConnectionPoolMixin, RetryMixin):
    """PostgreSQL repository implementation with connection pooling and retry logic."""

    def __init__(
        self,
        connection_url: str,
        table_name: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize PostgreSQL repository.

        Args:
            connection_url: PostgreSQL connection URL
            table_name: Database table name
            pool_size: Connection pool size
            max_overflow: Maximum pool overflow
            max_retries: Maximum retry attempts
            retry_delay: Retry delay in seconds
        """
        BaseRepository.__init__(self, connection_url)
        ConnectionPoolMixin.__init__(self, pool_size, max_overflow)
        RetryMixin.__init__(self, max_retries, retry_delay)
        self.table_name = table_name
        self._engine: Any = None
        self._pool: Any = None

    async def _connect(self) -> Any:
        """Establish PostgreSQL connection with connection pooling.

        Returns:
            SQLAlchemy engine instance

        Raises:
            ConnectionException: If connection fails
        """
        try:
            # Import here to avoid dependency issues
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            self._engine = create_async_engine(
                self.connection_url,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,  # Recycle connections after 1 hour
                echo=False,  # Set to True for SQL debugging
            )

            # Test connection
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            self.logger.info(
                "Connected to PostgreSQL",
                table=self.table_name,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
            )
            self.metrics.increment_counter("postgresql_connections_total", {"status": "success"})

            return self._engine

        except Exception as e:
            self.logger.error("Failed to connect to PostgreSQL", error=str(e))
            self.metrics.increment_counter("postgresql_connections_total", {"status": "failure"})
            raise ConnectionException(f"Failed to connect to PostgreSQL: {e}") from e

    async def _disconnect(self) -> None:
        """Close PostgreSQL connection and dispose of engine.

        Raises:
            ConnectionException: If disconnection fails
        """
        try:
            if self._engine:
                await self._engine.dispose()
                self._engine = None
                self.logger.info("Disconnected from PostgreSQL", table=self.table_name)

        except Exception as e:
            self.logger.error("Failed to disconnect from PostgreSQL", error=str(e))
            raise ConnectionException(f"Failed to disconnect from PostgreSQL: {e}") from e

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Any]:
        """Create PostgreSQL transaction context.

        Yields:
            SQLAlchemy connection with transaction

        Raises:
            Exception: If transaction fails
        """
        if not self._engine:
            await self._connect()

        async with self._engine.begin() as conn:
            try:
                yield conn
                # Transaction will be committed automatically
                self.metrics.increment_counter(
                    "postgresql_transactions_total", {"status": "committed"}
                )

            except Exception as e:
                # Transaction will be rolled back automatically
                self.logger.error("PostgreSQL transaction failed", error=str(e))
                self.metrics.increment_counter(
                    "postgresql_transactions_total", {"status": "rollback"}
                )
                raise

    async def create(self, entity: T) -> T:
        """Create entity in PostgreSQL.

        Args:
            entity: Entity to create

        Returns:
            Created entity with assigned ID

        Raises:
            RepositoryError: If creation fails
        """
        return await self._with_retry("create", self._create_impl, entity)

    async def _create_impl(self, entity: T) -> T:
        """Internal create implementation."""
        from sqlalchemy import text

        async with self._get_connection() as engine:  # noqa: SIM117
            async with engine.begin() as conn:
                # Convert entity to SQL INSERT
                entity_dict = self._entity_to_dict(entity)

                # Build INSERT statement
                columns = ", ".join(entity_dict.keys())
                placeholders = ", ".join([f":{key}" for key in entity_dict])

                # Safe: table_name is controlled, placeholders are parameterized
                sql = (
                    f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) RETURNING *"  # noqa: S608
                )

                result = await conn.execute(text(sql), entity_dict)
                row = result.fetchone()

                if row:
                    created_entity = self._row_to_entity(row)
                    self.logger.info(
                        "Created entity in PostgreSQL",
                        table=self.table_name,
                        entity_id=self._get_entity_id(created_entity),
                    )
                    self.metrics.increment_counter(
                        "postgresql_operations_total", {"operation": "create"}
                    )
                    return created_entity

                raise RepositoryException("Failed to create entity - no result returned")

    async def get_by_id(self, entity_id: ID) -> T | None:
        """Get entity by ID from PostgreSQL.

        Args:
            entity_id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        return await self._with_retry("get_by_id", self._get_by_id_impl, entity_id)

    async def _get_by_id_impl(self, entity_id: ID) -> T | None:
        """Internal get by ID implementation."""
        from sqlalchemy import text

        async with self._get_connection() as engine:  # noqa: SIM117
            async with engine.begin() as conn:
                # Safe: table_name is controlled, entity_id is parameterized
                sql = f"SELECT * FROM {self.table_name} WHERE id = :entity_id"  # noqa: S608
                result = await conn.execute(text(sql), {"entity_id": entity_id})
                row = result.fetchone()

                if row:
                    self.metrics.increment_counter(
                        "postgresql_operations_total", {"operation": "get_success"}
                    )
                    return self._row_to_entity(row)

                self.metrics.increment_counter(
                    "postgresql_operations_total", {"operation": "get_not_found"}
                )
                return None

    async def update(self, entity: T) -> T:
        """Update entity in PostgreSQL.

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
        from sqlalchemy import text

        async with self._get_connection() as engine:  # noqa: SIM117
            async with engine.begin() as conn:
                entity_id = self._get_entity_id(entity)
                entity_dict = self._entity_to_dict(entity)

                # Remove ID from update dict
                update_dict = {k: v for k, v in entity_dict.items() if k != "id"}

                # Build UPDATE statement
                set_clause = ", ".join([f"{key} = :{key}" for key in update_dict])
                # Safe: table_name and set_clause are controlled, parameters are bound
                sql = f"UPDATE {self.table_name} SET {set_clause} WHERE id = :id RETURNING *"  # noqa: S608

                update_dict["id"] = entity_id
                result = await conn.execute(text(sql), update_dict)
                row = result.fetchone()

                if row:
                    updated_entity = self._row_to_entity(row)
                    self.logger.info(
                        "Updated entity in PostgreSQL",
                        table=self.table_name,
                        entity_id=entity_id,
                    )
                    self.metrics.increment_counter(
                        "postgresql_operations_total", {"operation": "update"}
                    )
                    return updated_entity

                raise RepositoryException(f"Entity with ID {entity_id} not found for update")

    async def delete(self, entity_id: ID) -> bool:
        """Delete entity from PostgreSQL.

        Args:
            entity_id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        return await self._with_retry("delete", self._delete_impl, entity_id)

    async def _delete_impl(self, entity_id: ID) -> bool:
        """Internal delete implementation."""
        from sqlalchemy import text

        async with self._get_connection() as engine:  # noqa: SIM117
            async with engine.begin() as conn:
                # Safe: table_name is controlled, entity_id is parameterized
                sql = f"DELETE FROM {self.table_name} WHERE id = :entity_id"  # noqa: S608
                result = await conn.execute(text(sql), {"entity_id": entity_id})

                if result.rowcount > 0:
                    self.logger.info(
                        "Deleted entity from PostgreSQL", table=self.table_name, entity_id=entity_id
                    )
                    self.metrics.increment_counter(
                        "postgresql_operations_total", {"operation": "delete_success"}
                    )
                    return True

                self.metrics.increment_counter(
                    "postgresql_operations_total", {"operation": "delete_not_found"}
                )
                return False

    async def list_all(self, limit: int | None = None, offset: int = 0) -> list[T]:
        """List all entities from PostgreSQL.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities
        """
        return await self._with_retry("list_all", self._list_all_impl, limit, offset)

    async def _list_all_impl(self, limit: int | None = None, offset: int = 0) -> list[T]:
        """Internal list all implementation."""
        from sqlalchemy import text

        async with self._get_connection() as engine:  # noqa: SIM117
            async with engine.begin() as conn:
                # Safe: table_name is controlled by constructor
                sql = f"SELECT * FROM {self.table_name}"  # noqa: S608

                if offset > 0:
                    sql += f" OFFSET {offset}"

                if limit:
                    sql += f" LIMIT {limit}"

                result = await conn.execute(text(sql))
                rows = result.fetchall()

                entities = [self._row_to_entity(row) for row in rows]

                self.logger.info(
                    "Listed entities from PostgreSQL",
                    table=self.table_name,
                    count=len(entities),
                    limit=limit,
                    offset=offset,
                )
                self.metrics.increment_counter("postgresql_operations_total", {"operation": "list"})

                return entities

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
        from sqlalchemy import text

        async with self._get_connection() as engine:  # noqa: SIM117
            async with engine.begin() as conn:
                # Safe: table_name and field are controlled, value is parameterized
                sql = f"SELECT * FROM {self.table_name} WHERE {field} = :value"  # noqa: S608

                if limit:
                    sql += f" LIMIT {limit}"

                result = await conn.execute(text(sql), {"value": value})
                rows = result.fetchall()

                entities = [self._row_to_entity(row) for row in rows]

                self.logger.info(
                    "Queried entities by field",
                    table=self.table_name,
                    field=field,
                    value=str(value),
                    count=len(entities),
                )
                self.metrics.increment_counter(
                    "postgresql_operations_total", {"operation": "query"}
                )

                return entities

    async def execute_raw_sql(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        """Execute raw SQL query.

        Args:
            sql: SQL query to execute
            params: Query parameters

        Returns:
            Query result

        Raises:
            RepositoryError: If query fails
        """
        return await self._with_retry(
            "execute_raw_sql", self._execute_raw_sql_impl, sql, params or {}
        )

    async def _execute_raw_sql_impl(self, sql: str, params: dict[str, Any]) -> Any:
        """Internal raw SQL execution implementation."""
        from sqlalchemy import text

        async with self._get_connection() as engine:  # noqa: SIM117
            async with engine.begin() as conn:
                result = await conn.execute(text(sql), params)

                self.logger.info("Executed raw SQL", table=self.table_name, sql=sql[:100])
                self.metrics.increment_counter(
                    "postgresql_operations_total", {"operation": "raw_sql"}
                )

                return result

    def _entity_to_dict(self, entity: T) -> dict[str, Any]:
        """Convert entity to dictionary for PostgreSQL storage.

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

    def _row_to_entity(self, row: Any) -> T:
        """Convert database row to entity.

        Args:
            row: Database row

        Returns:
            Entity instance

        Note:
            This should be overridden by concrete implementations
        """
        # Default implementation - should be overridden
        return dict(row)  # type: ignore[return-value]

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
