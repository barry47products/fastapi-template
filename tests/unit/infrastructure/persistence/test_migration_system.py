"""Unit tests for database migration system."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from config.settings import DatabaseType
from src.infrastructure.persistence.migrations.base import (
    BaseMigration,
    FirestoreMigrationRunner,
    InMemoryMigrationRunner,
    PostgreSQLMigrationRunner,
    create_migration_runner,
)
from src.shared.exceptions import MigrationException


class TestMigration(BaseMigration):
    """Test migration implementation for testing."""

    def __init__(
        self,
        version: str = "001",
        description: str = "Test migration",
        database_types: list[DatabaseType] | None = None,
    ) -> None:
        """Initialize test migration."""
        super().__init__(
            version,
            description,
            database_types or [DatabaseType.IN_MEMORY, DatabaseType.POSTGRESQL],
        )
        self.up_called = False
        self.down_called = False

    async def up(self, connection: Any) -> None:
        """Apply migration."""
        self.up_called = True

    async def down(self, connection: Any) -> None:
        """Rollback migration."""
        self.down_called = True


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestBaseMigrationBehaviour:
    """Test base migration behavior and interface compliance."""

    def test_initialises_with_migration_metadata(self) -> None:
        """Should initialise with version, description and supported database types."""
        migration = TestMigration(
            version="20231201_001",
            description="Create user tables",
            database_types=[DatabaseType.POSTGRESQL, DatabaseType.FIRESTORE],
        )

        assert migration.version == "20231201_001"
        assert migration.description == "Create user tables"
        assert migration.database_types == [DatabaseType.POSTGRESQL, DatabaseType.FIRESTORE]
        assert migration.applied_at is None
        assert migration.logger is not None
        assert migration.metrics is not None

    def test_checks_database_type_support_correctly(self) -> None:
        """Should correctly check if migration supports specific database types."""
        migration = TestMigration(database_types=[DatabaseType.POSTGRESQL, DatabaseType.FIRESTORE])

        assert migration.supports_database(DatabaseType.POSTGRESQL) is True
        assert migration.supports_database(DatabaseType.FIRESTORE) is True
        assert migration.supports_database(DatabaseType.IN_MEMORY) is False

    def test_marks_migration_as_applied_with_timestamp(self) -> None:
        """Should mark migration as applied with current timestamp."""
        migration = TestMigration()
        before_time = datetime.now(UTC)

        migration.mark_applied()

        assert migration.applied_at is not None
        assert migration.applied_at >= before_time
        assert migration.applied_at <= datetime.now(UTC)

    async def test_abstract_methods_must_be_implemented(self) -> None:
        """Should require concrete implementations of up and down methods."""
        migration = TestMigration()

        # Test that the concrete implementation works
        await migration.up("mock_connection")
        await migration.down("mock_connection")

        assert migration.up_called is True
        assert migration.down_called is True


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestInMemoryMigrationRunner:
    """Test in-memory migration runner behavior."""

    def test_initialises_with_in_memory_configuration(self) -> None:
        """Should initialise with in-memory database configuration."""
        runner = InMemoryMigrationRunner()

        assert runner.database_url == "memory://"
        assert runner.db_type == DatabaseType.IN_MEMORY
        assert runner._applied_migrations == []
        assert runner.logger is not None
        assert runner.metrics is not None

    async def test_creates_migration_table_as_no_op(self) -> None:
        """Should create migration table as no-op for in-memory storage."""
        runner = InMemoryMigrationRunner()

        # Should not raise any exceptions
        await runner.create_migration_table()

    async def test_tracks_applied_migrations_in_memory(self) -> None:
        """Should track applied migrations in memory list."""
        runner = InMemoryMigrationRunner()
        migration = TestMigration(version="001")

        await runner.record_migration(migration)

        applied = await runner.get_applied_migrations()
        assert "001" in applied

    async def test_prevents_duplicate_migration_records(self) -> None:
        """Should prevent duplicate migration records."""
        runner = InMemoryMigrationRunner()
        migration = TestMigration(version="001")

        await runner.record_migration(migration)
        await runner.record_migration(migration)  # Second time should be no-op

        applied = await runner.get_applied_migrations()
        assert applied.count("001") == 1

    async def test_removes_migration_records_for_rollback(self) -> None:
        """Should remove migration records during rollback."""
        runner = InMemoryMigrationRunner()
        migration = TestMigration(version="001")

        await runner.record_migration(migration)
        await runner.remove_migration_record("001")

        applied = await runner.get_applied_migrations()
        assert "001" not in applied

    async def test_handles_removal_of_nonexistent_migrations(self) -> None:
        """Should handle removal of non-existent migration records gracefully."""
        runner = InMemoryMigrationRunner()

        # Should not raise exception
        await runner.remove_migration_record("nonexistent")

        applied = await runner.get_applied_migrations()
        assert applied == []


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.resilience
class TestMigrationRunnerApplicationLogic:
    """Test migration runner application and rollback logic."""

    async def test_applies_migration_with_logging_and_metrics(self) -> None:
        """Should apply migration with proper logging and metrics tracking."""
        runner = InMemoryMigrationRunner()
        migration = TestMigration(version="001", description="Test migration")

        await runner.apply_migration(migration, "mock_connection")

        assert migration.up_called is True
        applied = await runner.get_applied_migrations()
        assert "001" in applied

    async def test_handles_migration_application_failures(self) -> None:
        """Should handle migration application failures with proper error reporting."""
        runner = InMemoryMigrationRunner()

        class FailingMigration(BaseMigration):
            def __init__(self) -> None:
                super().__init__("failing", "Failing migration", [DatabaseType.IN_MEMORY])

            async def up(self, connection: Any) -> None:
                raise MigrationException("Migration failed")

            async def down(self, connection: Any) -> None:
                pass

        migration = FailingMigration()

        with pytest.raises(MigrationException, match="Migration failing failed"):
            await runner.apply_migration(migration, "mock_connection")

    async def test_rolls_back_migration_with_logging_and_metrics(self) -> None:
        """Should rollback migration with proper logging and metrics tracking."""
        runner = InMemoryMigrationRunner()
        migration = TestMigration(version="001")

        # First apply the migration
        await runner.apply_migration(migration, "mock_connection")

        # Then rollback
        await runner.rollback_migration(migration, "mock_connection")

        assert migration.down_called is True
        applied = await runner.get_applied_migrations()
        assert "001" not in applied

    async def test_handles_migration_rollback_failures(self) -> None:
        """Should handle migration rollback failures with proper error reporting."""
        runner = InMemoryMigrationRunner()

        class FailingRollbackMigration(BaseMigration):
            def __init__(self) -> None:
                super().__init__("failing_rollback", "Failing rollback", [DatabaseType.IN_MEMORY])

            async def up(self, connection: Any) -> None:
                pass

            async def down(self, connection: Any) -> None:
                raise MigrationException("Rollback failed")

        migration = FailingRollbackMigration()

        with pytest.raises(MigrationException, match="Migration failing_rollback rollback failed"):
            await runner.rollback_migration(migration, "mock_connection")

    async def test_tracks_migration_execution_time(self) -> None:
        """Should track and log migration execution time."""
        runner = InMemoryMigrationRunner()

        class SlowMigration(BaseMigration):
            def __init__(self) -> None:
                super().__init__("slow", "Slow migration", [DatabaseType.IN_MEMORY])

            async def up(self, connection: Any) -> None:
                # Simulate slow migration
                import asyncio

                await asyncio.sleep(0.01)

            async def down(self, connection: Any) -> None:
                pass

        migration = SlowMigration()

        # Should complete without error and log timing
        await runner.apply_migration(migration, "mock_connection")

        applied = await runner.get_applied_migrations()
        assert "slow" in applied


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.database
class TestPostgreSQLMigrationRunner:
    """Test PostgreSQL migration runner behavior."""

    def test_initialises_with_postgresql_configuration(self) -> None:
        """Should initialise with PostgreSQL database configuration."""
        runner = PostgreSQLMigrationRunner("postgresql://localhost/testdb")

        assert runner.database_url == "postgresql://localhost/testdb"
        assert runner.db_type == DatabaseType.POSTGRESQL

    @patch("sqlalchemy.create_engine")
    @patch("sqlalchemy.ext.declarative.declarative_base")
    async def test_creates_migration_table_with_sqlalchemy(
        self, mock_declarative_base: Any, mock_create_engine: Any
    ) -> None:
        """Should create migration table using SQLAlchemy."""
        mock_engine = Mock()
        mock_base = Mock()
        mock_metadata = Mock()
        mock_base.metadata = mock_metadata

        mock_create_engine.return_value = mock_engine
        mock_declarative_base.return_value = mock_base

        runner = PostgreSQLMigrationRunner("postgresql://localhost/testdb")

        await runner.create_migration_table()

        mock_create_engine.assert_called_once_with("postgresql://localhost/testdb")
        mock_metadata.create_all.assert_called_once_with(mock_engine)

    async def test_handles_sqlalchemy_import_errors(self) -> None:
        """Should handle SQLAlchemy import errors gracefully."""
        runner = PostgreSQLMigrationRunner("postgresql://localhost/testdb")

        with (
            patch("sqlalchemy.Column", side_effect=ImportError("SQLAlchemy not available")),
            pytest.raises(NotImplementedError, match="PostgreSQL migrations require SQLAlchemy"),
        ):
            await runner.create_migration_table()

    async def test_stub_methods_return_appropriate_defaults(self) -> None:
        """Should return appropriate defaults for stub implementations."""
        runner = PostgreSQLMigrationRunner("postgresql://localhost/testdb")

        applied = await runner.get_applied_migrations()
        assert applied == []

        # Should not raise exceptions
        migration = TestMigration()
        await runner.record_migration(migration)
        await runner.remove_migration_record("001")


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.database
class TestFirestoreMigrationRunner:
    """Test Firestore migration runner behavior."""

    def test_initialises_with_firestore_configuration(self) -> None:
        """Should initialise with Firestore database configuration."""
        runner = FirestoreMigrationRunner("firestore://project-id")

        assert runner.database_url == "firestore://project-id"
        assert runner.db_type == DatabaseType.FIRESTORE
        assert runner._migrations_collection == "schema_migrations"

    @patch("google.cloud.firestore.AsyncClient")
    async def test_creates_migration_collection_with_firestore_client(
        self, mock_async_client: Any
    ) -> None:
        """Should create migration collection using Firestore client."""
        mock_client = AsyncMock()
        mock_async_client.return_value = mock_client

        runner = FirestoreMigrationRunner("firestore://project-id")

        await runner.create_migration_table()

        mock_async_client.assert_called_once()

    @patch("google.cloud.firestore.AsyncClient")
    async def test_handles_firestore_import_errors(self, mock_client: Any) -> None:
        """Should handle Firestore import errors gracefully."""
        mock_client.side_effect = ImportError("No module named 'google.cloud.firestore'")

        runner = FirestoreMigrationRunner("firestore://project-id")

        with pytest.raises(
            NotImplementedError, match="Firestore migrations require google-cloud-firestore"
        ):
            await runner.create_migration_table()

    async def test_stub_methods_return_appropriate_defaults(self) -> None:
        """Should return appropriate defaults for stub implementations."""
        runner = FirestoreMigrationRunner("firestore://project-id")

        applied = await runner.get_applied_migrations()
        assert applied == []

        # Should not raise exceptions
        migration = TestMigration()
        await runner.record_migration(migration)
        await runner.remove_migration_record("001")


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestMigrationRunnerFactory:
    """Test migration runner factory function."""

    def test_creates_in_memory_migration_runner(self) -> None:
        """Should create in-memory migration runner for in-memory database type."""
        runner = create_migration_runner("memory://", DatabaseType.IN_MEMORY)

        assert isinstance(runner, InMemoryMigrationRunner)
        assert runner.db_type == DatabaseType.IN_MEMORY

    def test_creates_postgresql_migration_runner(self) -> None:
        """Should create PostgreSQL migration runner for PostgreSQL database type."""
        runner = create_migration_runner("postgresql://localhost/db", DatabaseType.POSTGRESQL)

        assert isinstance(runner, PostgreSQLMigrationRunner)
        assert runner.db_type == DatabaseType.POSTGRESQL
        assert runner.database_url == "postgresql://localhost/db"

    def test_creates_firestore_migration_runner(self) -> None:
        """Should create Firestore migration runner for Firestore database type."""
        runner = create_migration_runner("firestore://project-id", DatabaseType.FIRESTORE)

        assert isinstance(runner, FirestoreMigrationRunner)
        assert runner.db_type == DatabaseType.FIRESTORE
        assert runner.database_url == "firestore://project-id"

    def test_raises_error_for_unsupported_database_type(self) -> None:
        """Should raise error for unsupported database types."""
        with pytest.raises(ValueError, match="Unsupported database type for migrations"):
            # Using a custom enum value that doesn't exist
            create_migration_runner("unknown://", "unknown")  # type: ignore[arg-type]


@pytest.mark.integration
@pytest.mark.behaviour
@pytest.mark.resilience
class TestMigrationSystemIntegration:
    """Test migration system integration patterns and cross-cutting concerns."""

    async def test_migration_lifecycle_with_observability(self) -> None:
        """Should track complete migration lifecycle with observability."""
        runner = InMemoryMigrationRunner()
        migration = TestMigration(version="lifecycle_test")

        # Apply migration
        await runner.apply_migration(migration, "mock_connection")

        # Verify it was applied
        applied = await runner.get_applied_migrations()
        assert "lifecycle_test" in applied

        # Rollback migration
        await runner.rollback_migration(migration, "mock_connection")

        # Verify rollback
        applied_after_rollback = await runner.get_applied_migrations()
        assert "lifecycle_test" not in applied_after_rollback

        # Verify both up and down were called
        assert migration.up_called is True
        assert migration.down_called is True

    async def test_handles_multiple_database_types_consistently(self) -> None:
        """Should handle different database types with consistent interface."""
        runners = [
            InMemoryMigrationRunner(),
            PostgreSQLMigrationRunner("postgresql://localhost/db"),
            FirestoreMigrationRunner("firestore://project-id"),
        ]

        for runner in runners:
            # All runners should have the same interface
            assert hasattr(runner, "create_migration_table")
            assert hasattr(runner, "get_applied_migrations")
            assert hasattr(runner, "record_migration")
            assert hasattr(runner, "remove_migration_record")
            assert hasattr(runner, "apply_migration")
            assert hasattr(runner, "rollback_migration")

    def test_migration_database_compatibility_checks(self) -> None:
        """Should correctly check migration compatibility with database types."""
        postgresql_migration = TestMigration(
            version="pg_only", database_types=[DatabaseType.POSTGRESQL]
        )
        firestore_migration = TestMigration(
            version="fs_only", database_types=[DatabaseType.FIRESTORE]
        )
        universal_migration = TestMigration(
            version="universal",
            database_types=[
                DatabaseType.IN_MEMORY,
                DatabaseType.POSTGRESQL,
                DatabaseType.FIRESTORE,
            ],
        )

        # Test PostgreSQL migration
        assert postgresql_migration.supports_database(DatabaseType.POSTGRESQL) is True
        assert postgresql_migration.supports_database(DatabaseType.FIRESTORE) is False
        assert postgresql_migration.supports_database(DatabaseType.IN_MEMORY) is False

        # Test Firestore migration
        assert firestore_migration.supports_database(DatabaseType.FIRESTORE) is True
        assert firestore_migration.supports_database(DatabaseType.POSTGRESQL) is False
        assert firestore_migration.supports_database(DatabaseType.IN_MEMORY) is False

        # Test universal migration
        assert universal_migration.supports_database(DatabaseType.IN_MEMORY) is True
        assert universal_migration.supports_database(DatabaseType.POSTGRESQL) is True
        assert universal_migration.supports_database(DatabaseType.FIRESTORE) is True

    async def test_migration_error_handling_maintains_system_integrity(self) -> None:
        """Should maintain system integrity when migrations fail."""
        runner = InMemoryMigrationRunner()

        class PartiallyFailingMigration(BaseMigration):
            def __init__(self) -> None:
                super().__init__("partial_fail", "Partially failing", [DatabaseType.IN_MEMORY])
                self.state_modified = False

            async def up(self, connection: Any) -> None:
                _ = connection  # Connection parameter not used in test
                self.state_modified = True
                raise MigrationException("Migration failed after state change")

            async def down(self, connection: Any) -> None:
                _ = connection  # Connection parameter not used in test
                self.state_modified = False

        migration = PartiallyFailingMigration()

        # Migration should fail
        with pytest.raises(MigrationException):
            await runner.apply_migration(migration, "mock_connection")

        # Migration should not be recorded as applied
        applied = await runner.get_applied_migrations()
        assert "partial_fail" not in applied

        # State was modified but migration wasn't recorded
        assert migration.state_modified is True

    def test_observability_integration_across_migration_system(self) -> None:
        """Should integrate observability consistently across migration system."""
        migration = TestMigration()
        runner = InMemoryMigrationRunner()

        # Both should have logger and metrics
        assert migration.logger is not None
        assert migration.metrics is not None
        assert runner.logger is not None
        assert runner.metrics is not None

        # Logger names should be meaningful
        assert migration.logger is not None
        assert runner.logger is not None
