"""Base repository interfaces and shared functionality."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar

from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import ConnectionException

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

T = TypeVar("T")  # Entity type
ID = TypeVar("ID")  # ID type - contravariance removed for simplicity


class Repository(Protocol[T, ID]):  # type: ignore[misc]
    """Base repository protocol for CRUD operations."""

    async def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity with assigned ID

        Raises:
            RepositoryError: If creation fails
        """
        ...

    async def get_by_id(self, entity_id: ID) -> T | None:
        """Get entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity if found, None otherwise

        Raises:
            RepositoryError: If retrieval fails
        """
        ...

    async def update(self, entity: T) -> T:
        """Update existing entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity

        Raises:
            RepositoryError: If update fails or entity not found
        """
        ...

    async def delete(self, entity_id: ID) -> bool:
        """Delete entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        ...

    async def list_all(self, limit: int | None = None, offset: int = 0) -> list[T]:
        """List all entities.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities

        Raises:
            RepositoryError: If listing fails
        """
        ...


class BaseRepository(ABC, Generic[T, ID]):  # noqa: UP046
    """Abstract base repository with observability and common functionality."""

    def __init__(self, connection_url: str) -> None:
        """Initialize repository with connection details.

        Args:
            connection_url: Database connection URL
        """
        self.connection_url = connection_url
        self.logger = get_logger(self.__class__.__name__)
        self.metrics = get_metrics_collector()
        self._connection: Any = None

    @abstractmethod
    async def _connect(self) -> Any:
        """Establish database connection.

        Returns:
            Database connection instance

        Raises:
            ConnectionException: If connection fails
        """

    @abstractmethod
    async def _disconnect(self) -> None:
        """Close database connection.

        Raises:
            ConnectionException: If disconnection fails
        """

    @asynccontextmanager
    async def _get_connection(self) -> AsyncGenerator[Any]:
        """Get database connection with automatic cleanup.

        Yields:
            Database connection

        Raises:
            ConnectionException: If connection fails
        """
        if self._connection is None:
            self._connection = await self._connect()

        try:
            yield self._connection
        except Exception:
            # Log error and re-raise
            self.logger.error("Database operation failed", connection_url=self.connection_url)
            self.metrics.increment_counter("database_errors_total", {"operation": "connection"})
            raise

    async def health_check(self) -> bool:
        """Check if repository is healthy and can connect to database.

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with self._get_connection():
                self.metrics.increment_counter(
                    "database_health_checks_total", {"status": "success"}
                )
                return True
        except Exception as e:
            self.logger.warning("Database health check failed", error=str(e))
            self.metrics.increment_counter("database_health_checks_total", {"status": "failure"})
            return False


class TransactionalRepository(BaseRepository[T, ID], Repository[T, ID]):
    """Base repository with transaction support."""

    @abstractmethod
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Any]:
        """Create database transaction context.

        Yields:
            Transaction context

        Raises:
            TransactionError: If transaction fails
        """
        yield  # Placeholder for abstract method

    async def create_with_transaction(self, entity: T) -> T:
        """Create entity within transaction.

        Args:
            entity: Entity to create

        Returns:
            Created entity

        Raises:
            RepositoryError: If creation fails
        """
        async with self.transaction():
            # Concrete implementation must handle transaction-based creation
            _ = entity  # Suppress unused parameter warning
            raise NotImplementedError("Concrete implementation must override this method")

    async def update_with_transaction(self, entity: T) -> T:
        """Update entity within transaction.

        Args:
            entity: Entity to update

        Returns:
            Updated entity

        Raises:
            RepositoryError: If update fails
        """
        async with self.transaction():
            # Concrete implementation must handle transaction-based update
            _ = entity  # Suppress unused parameter warning
            raise NotImplementedError("Concrete implementation must override this method")


class CacheableRepository(BaseRepository[T, ID]):
    """Base repository with caching support."""

    def __init__(self, connection_url: str, cache_ttl: int = 300) -> None:
        """Initialize cacheable repository.

        Args:
            connection_url: Database connection URL
            cache_ttl: Cache time-to-live in seconds
        """
        super().__init__(connection_url)
        self.cache_ttl = cache_ttl
        self._cache: dict[ID, T] = {}

    def _get_cache_key(self, entity_id: ID) -> str:
        """Generate cache key for entity.

        Args:
            entity_id: Entity ID

        Returns:
            Cache key
        """
        return f"{self.__class__.__name__}:{entity_id}"

    async def get_by_id(self, entity_id: ID) -> T | None:
        """Get entity by ID with caching.

        Args:
            entity_id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        # Check cache first
        cache_key = self._get_cache_key(entity_id)
        if entity_id in self._cache:
            self.metrics.increment_counter("repository_cache_hits_total", {})
            self.logger.debug("Cache hit", entity_id=entity_id, cache_key=cache_key)
            return self._cache[entity_id]

        # Fetch from database
        self.metrics.increment_counter("repository_cache_misses_total", {})
        entity = await self._get_by_id_from_db(entity_id)

        # Cache the result
        if entity is not None:
            self._cache[entity_id] = entity
            self.logger.debug("Cached entity", entity_id=entity_id, cache_key=cache_key)

        return entity

    @abstractmethod
    async def _get_by_id_from_db(self, entity_id: ID) -> T | None:
        """Get entity by ID from database (bypass cache).

        Args:
            entity_id: Entity ID

        Returns:
            Entity if found, None otherwise
        """

    def _invalidate_cache(self, entity_id: ID) -> None:
        """Invalidate cache entry for entity.

        Args:
            entity_id: Entity ID to invalidate
        """
        if entity_id in self._cache:
            del self._cache[entity_id]
            self.logger.debug("Invalidated cache", entity_id=entity_id)


class ConnectionPoolMixin:
    """Mixin for repositories with connection pooling support."""

    def __init__(self, pool_size: int = 10, max_overflow: int = 20) -> None:
        """Initialize connection pool settings.

        Args:
            pool_size: Base connection pool size
            max_overflow: Maximum additional connections
        """
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._pool: Any = None

    @contextmanager
    def _get_pooled_connection(self) -> Generator[Any]:
        """Get connection from pool.

        Yields:
            Database connection from pool

        Raises:
            ConnectionException: If pool is exhausted
        """
        if self._pool is None:
            raise ConnectionException("Connection pool not initialized")

        connection = None
        try:
            connection = self._pool.get_connection()
            yield connection
        finally:
            if connection:
                self._pool.return_connection(connection)


class RetryMixin:
    """Mixin for repositories with retry logic."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """Initialize retry settings.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = get_logger(self.__class__.__name__)
        self.metrics = get_metrics_collector()

    async def _with_retry(self, operation: str, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute function with retry logic.

        Args:
            operation: Operation name for logging
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries fail
        """
        import asyncio

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries:
                    self.logger.error(
                        "Operation failed after all retries",
                        operation=operation,
                        attempts=attempt + 1,
                        error=str(e),
                    )
                    self.metrics.increment_counter(
                        "repository_operation_failures_total",
                        {"operation": operation, "final_attempt": "true"},
                    )
                    raise

                self.logger.warning(
                    "Operation failed, retrying",
                    operation=operation,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e),
                )
                self.metrics.increment_counter(
                    "repository_operation_retries_total",
                    {"operation": operation, "attempt": str(attempt + 1)},
                )

                await asyncio.sleep(self.retry_delay * (2**attempt))  # Exponential backoff

        return None  # Should never reach here, but satisfies type checker
