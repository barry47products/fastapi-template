"""Base migration interfaces and utilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Protocol

from config.settings import DatabaseType
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import MigrationException


class Migration(Protocol):
    """Protocol for database migrations."""

    version: str
    description: str
    database_types: list[DatabaseType]

    async def up(self, connection: Any) -> None:
        """Apply migration.

        Args:
            connection: Database connection
        """
        ...

    async def down(self, connection: Any) -> None:
        """Rollback migration.

        Args:
            connection: Database connection
        """
        ...

    def supports_database(self, db_type: DatabaseType) -> bool:
        """Check if migration supports database type.

        Args:
            db_type: Database type to check

        Returns:
            True if supported
        """
        ...

    def mark_applied(self) -> None:
        """Mark migration as applied."""
        ...


class BaseMigration(ABC):
    """Base migration implementation with common functionality."""

    def __init__(self, version: str, description: str, database_types: list[DatabaseType]) -> None:
        """Initialize migration.

        Args:
            version: Migration version (e.g., "001", "20231201_001")
            description: Human-readable description
            database_types: Supported database types
        """
        self.version = version
        self.description = description
        self.database_types = database_types
        self.logger = get_logger(f"migration_{version}")
        self.metrics = get_metrics_collector()
        self.applied_at: datetime | None = None

    @abstractmethod
    async def up(self, connection: Any) -> None:
        """Apply migration."""

    @abstractmethod
    async def down(self, connection: Any) -> None:
        """Rollback migration."""

    def supports_database(self, db_type: DatabaseType) -> bool:
        """Check if migration supports database type.

        Args:
            db_type: Database type to check

        Returns:
            True if supported
        """
        return db_type in self.database_types

    def mark_applied(self) -> None:
        """Mark migration as applied."""
        self.applied_at = datetime.now(UTC)


class MigrationRunner(ABC):
    """Abstract migration runner for specific database types."""

    def __init__(self, database_url: str, db_type: DatabaseType) -> None:
        """Initialize migration runner.

        Args:
            database_url: Database connection URL
            db_type: Database type
        """
        self.database_url = database_url
        self.db_type = db_type
        self.logger = get_logger(f"migration_runner_{db_type.value}")
        self.metrics = get_metrics_collector()

    @abstractmethod
    async def create_migration_table(self) -> None:
        """Create migration tracking table."""

    @abstractmethod
    async def get_applied_migrations(self) -> list[str]:
        """Get list of applied migration versions.

        Returns:
            List of applied migration versions
        """

    @abstractmethod
    async def record_migration(self, migration: Migration) -> None:
        """Record migration as applied.

        Args:
            migration: Migration that was applied
        """

    @abstractmethod
    async def remove_migration_record(self, version: str) -> None:
        """Remove migration record (for rollback).

        Args:
            version: Migration version to remove
        """

    async def apply_migration(self, migration: Migration, connection: Any) -> None:
        """Apply a migration with logging and metrics.

        Args:
            migration: Migration to apply
            connection: Database connection

        Raises:
            MigrationException: If migration fails
        """
        try:
            self.logger.info(
                "Applying migration",
                version=migration.version,
                description=migration.description,
            )

            start_time = datetime.now(UTC)
            await migration.up(connection)
            duration = (datetime.now(UTC) - start_time).total_seconds()

            await self.record_migration(migration)

            self.logger.info(
                "Migration applied successfully",
                version=migration.version,
                duration_seconds=duration,
            )
            self.metrics.increment_counter(
                "database_migrations_total",
                {"database": self.db_type.value, "operation": "apply", "status": "success"},
            )

        except Exception as e:
            self.logger.error(
                "Migration failed",
                version=migration.version,
                error=str(e),
            )
            self.metrics.increment_counter(
                "database_migrations_total",
                {"database": self.db_type.value, "operation": "apply", "status": "failure"},
            )
            raise MigrationException(f"Migration {migration.version} failed: {e}") from e

    async def rollback_migration(self, migration: Migration, connection: Any) -> None:
        """Rollback a migration with logging and metrics.

        Args:
            migration: Migration to rollback
            connection: Database connection

        Raises:
            MigrationException: If rollback fails
        """
        try:
            self.logger.info(
                "Rolling back migration",
                version=migration.version,
                description=migration.description,
            )

            start_time = datetime.now(UTC)
            await migration.down(connection)
            duration = (datetime.now(UTC) - start_time).total_seconds()

            await self.remove_migration_record(migration.version)

            self.logger.info(
                "Migration rolled back successfully",
                version=migration.version,
                duration_seconds=duration,
            )
            self.metrics.increment_counter(
                "database_migrations_total",
                {"database": self.db_type.value, "operation": "rollback", "status": "success"},
            )

        except Exception as e:
            self.logger.error(
                "Migration rollback failed",
                version=migration.version,
                error=str(e),
            )
            self.metrics.increment_counter(
                "database_migrations_total",
                {"database": self.db_type.value, "operation": "rollback", "status": "failure"},
            )
            raise MigrationException(f"Migration {migration.version} rollback failed: {e}") from e


class InMemoryMigrationRunner(MigrationRunner):
    """In-memory migration runner (no-op for testing)."""

    def __init__(self) -> None:
        """Initialize in-memory migration runner."""
        super().__init__("memory://", DatabaseType.IN_MEMORY)
        self._applied_migrations: list[str] = []

    async def create_migration_table(self) -> None:
        """Create migration tracking (no-op for in-memory)."""
        self.logger.debug("In-memory migration table created")

    async def get_applied_migrations(self) -> list[str]:
        """Get applied migrations from memory."""
        return self._applied_migrations.copy()

    async def record_migration(self, migration: Migration) -> None:
        """Record migration in memory."""
        if migration.version not in self._applied_migrations:
            self._applied_migrations.append(migration.version)
            self.logger.debug("Recorded migration", version=migration.version)

    async def remove_migration_record(self, version: str) -> None:
        """Remove migration record from memory."""
        if version in self._applied_migrations:
            self._applied_migrations.remove(version)
            self.logger.debug("Removed migration record", version=version)


class PostgreSQLMigrationRunner(MigrationRunner):
    """PostgreSQL migration runner."""

    def __init__(self, database_url: str) -> None:
        """Initialize PostgreSQL migration runner."""
        super().__init__(database_url, DatabaseType.POSTGRESQL)

    async def create_migration_table(self) -> None:
        """Create migration tracking table in PostgreSQL."""
        try:
            from sqlalchemy import (  # type: ignore[import-not-found]
                Column,
                DateTime,
                String,
                create_engine,
            )
            from sqlalchemy.ext.declarative import (  # type: ignore[import-not-found]
                declarative_base,
            )

            base = declarative_base()

            class MigrationRecord(base):  # type: ignore[misc,valid-type]
                __tablename__ = "schema_migrations"
                version = Column(String(255), primary_key=True)
                description = Column(String(500))
                applied_at = Column(DateTime, nullable=False)

            engine = create_engine(self.database_url)
            base.metadata.create_all(engine)

            self.logger.info("Created PostgreSQL migration table")

        except ImportError as e:
            self.logger.error("SQLAlchemy not available for PostgreSQL migrations", error=str(e))
            raise NotImplementedError("PostgreSQL migrations require SQLAlchemy") from e

    async def get_applied_migrations(self) -> list[str]:
        """Get applied migrations from PostgreSQL."""
        # Implementation would query the schema_migrations table
        # This is a stub for the template
        return []

    async def record_migration(self, migration: Migration) -> None:
        """Record migration in PostgreSQL."""
        # Implementation would insert into schema_migrations table
        self.logger.debug("Recorded PostgreSQL migration", version=migration.version)

    async def remove_migration_record(self, version: str) -> None:
        """Remove migration record from PostgreSQL."""
        # Implementation would delete from schema_migrations table
        self.logger.debug("Removed PostgreSQL migration record", version=version)


class FirestoreMigrationRunner(MigrationRunner):
    """Firestore migration runner."""

    def __init__(self, database_url: str) -> None:
        """Initialize Firestore migration runner."""
        super().__init__(database_url, DatabaseType.FIRESTORE)
        self._migrations_collection = "schema_migrations"

    async def create_migration_table(self) -> None:
        """Create migration tracking collection in Firestore."""
        try:
            from google.cloud import firestore

            _ = firestore.AsyncClient()  # Create client to verify availability
            # Firestore creates collections automatically when first document is added
            self.logger.info("Firestore migration tracking initialized")

        except ImportError as e:
            self.logger.error("Firestore client not available", error=str(e))
            raise NotImplementedError("Firestore migrations require google-cloud-firestore") from e

    async def get_applied_migrations(self) -> list[str]:
        """Get applied migrations from Firestore."""
        # Implementation would query the schema_migrations collection
        return []

    async def record_migration(self, migration: Migration) -> None:
        """Record migration in Firestore."""
        self.logger.debug("Recorded Firestore migration", version=migration.version)

    async def remove_migration_record(self, version: str) -> None:
        """Remove migration record from Firestore."""
        self.logger.debug("Removed Firestore migration record", version=version)


def create_migration_runner(database_url: str, db_type: DatabaseType) -> MigrationRunner:
    """Factory function to create appropriate migration runner.

    Args:
        database_url: Database connection URL
        db_type: Database type

    Returns:
        Migration runner instance

    Raises:
        ValueError: If database type is not supported
    """
    if db_type == DatabaseType.IN_MEMORY:
        return InMemoryMigrationRunner()
    if db_type == DatabaseType.POSTGRESQL:
        return PostgreSQLMigrationRunner(database_url)
    if db_type == DatabaseType.FIRESTORE:
        return FirestoreMigrationRunner(database_url)
    raise ValueError(f"Unsupported database type for migrations: {db_type}")
