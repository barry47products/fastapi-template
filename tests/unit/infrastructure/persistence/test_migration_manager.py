"""Unit tests for migration manager functionality."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from config.settings import DatabaseType
from src.infrastructure.persistence.migrations.base import BaseMigration, InMemoryMigrationRunner
from src.infrastructure.persistence.migrations.manager import (
    MigrationManager,
    get_migration_manager,
)
from src.shared.exceptions import MigrationException


class TestMigration(BaseMigration):
    """Test migration for testing purposes."""

    def __init__(
        self,
        version: str = "001",
        description: str = "Test migration",
        database_types: list[DatabaseType] | None = None,
    ) -> None:
        """Initialize test migration."""
        if database_types is None:
            database_types = [DatabaseType.IN_MEMORY, DatabaseType.POSTGRESQL]
        super().__init__(version, description, database_types)
        self.up_called = False
        self.down_called = False

    async def up(self, connection: Any) -> None:
        """Apply migration."""
        _ = connection  # Connection parameter not used in test
        self.up_called = True

    async def down(self, connection: Any) -> None:
        """Rollback migration."""
        _ = connection  # Connection parameter not used in test
        self.down_called = True


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestMigrationManagerBehaviour:
    """Test migration manager behavior and initialization."""

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    def test_initialises_with_database_settings_and_observability(
        self, mock_get_settings: Any
    ) -> None:
        """Should initialise with database settings and observability components."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.database_url = "memory://localhost"
        mock_db_settings.enable_migrations = True
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()

        assert manager.db_settings is mock_db_settings
        assert manager.logger is not None
        assert manager.metrics is not None
        assert manager._migrations == []
        assert manager._runner is None

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    def test_registers_compatible_migration_successfully(self, mock_get_settings: Any) -> None:
        """Should register migration when it supports current database type."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration = TestMigration("001", "Test migration", [DatabaseType.IN_MEMORY])

        manager.register_migration(migration)

        assert len(manager._migrations) == 1
        assert manager._migrations[0] is migration

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    def test_skips_incompatible_migration_with_warning(self, mock_get_settings: Any) -> None:
        """Should skip migration registration when database type not supported."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration = TestMigration("001", "PostgreSQL only", [DatabaseType.POSTGRESQL])

        manager.register_migration(migration)

        assert len(manager._migrations) == 0

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    @patch("src.infrastructure.persistence.migrations.manager.create_migration_runner")
    def test_creates_and_caches_migration_runner(
        self, mock_create_runner: Any, mock_get_settings: Any
    ) -> None:
        """Should create migration runner for database type and cache it."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.database_url = "memory://localhost"
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        mock_runner = Mock()
        mock_create_runner.return_value = mock_runner

        manager = MigrationManager()

        # First call should create runner
        result1 = manager.get_runner()
        # Second call should return cached runner
        result2 = manager.get_runner()

        assert result1 is mock_runner
        assert result2 is mock_runner
        mock_create_runner.assert_called_once_with(
            database_url="memory://localhost", db_type=DatabaseType.IN_MEMORY
        )

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_sets_up_migration_tracking_table(self, mock_get_settings: Any) -> None:
        """Should set up migration tracking table using runner."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.database_url = "memory://localhost"
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        mock_runner = AsyncMock()
        manager._runner = mock_runner

        await manager.setup_migration_tracking()

        mock_runner.create_migration_table.assert_called_once()

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_identifies_pending_migrations_correctly(self, mock_get_settings: Any) -> None:
        """Should identify pending migrations by comparing registered vs applied."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration1 = TestMigration("001")
        migration2 = TestMigration("002")
        migration3 = TestMigration("003")

        manager._migrations = [migration3, migration1, migration2]  # Unsorted order

        mock_runner = AsyncMock()
        mock_runner.get_applied_migrations.return_value = ["001"]  # Only 001 applied
        manager._runner = mock_runner

        pending = await manager.get_pending_migrations()

        assert len(pending) == 2
        # Should be sorted by version
        assert pending[0].version == "002"
        assert pending[1].version == "003"

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_skips_migrations_when_disabled(self, mock_get_settings: Any) -> None:
        """Should skip migration when migrations are disabled in settings."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.enable_migrations = False
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()

        result = await manager.migrate_up()

        assert result == 0

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_applies_no_migrations_when_none_pending(self, mock_get_settings: Any) -> None:
        """Should return zero when no pending migrations to apply."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.enable_migrations = True
        mock_db_settings.database_url = "memory://localhost"
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        manager._migrations = []

        mock_runner = AsyncMock()
        mock_runner.get_applied_migrations.return_value = []
        manager._runner = mock_runner

        result = await manager.migrate_up()

        assert result == 0

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_applies_pending_migrations_in_order(self, mock_get_settings: Any) -> None:
        """Should apply pending migrations in version order."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.enable_migrations = True
        mock_db_settings.database_url = "memory://localhost"
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration1 = TestMigration("001")
        migration2 = TestMigration("002")
        manager._migrations = [migration2, migration1]  # Reverse order

        mock_runner = AsyncMock()
        mock_runner.get_applied_migrations.return_value = []
        manager._runner = mock_runner

        result = await manager.migrate_up()

        assert result == 2
        # Should be applied in order
        assert mock_runner.apply_migration.call_args_list[0][0][0] is migration1
        assert mock_runner.apply_migration.call_args_list[1][0][0] is migration2
        assert migration1.applied_at is not None
        assert migration2.applied_at is not None

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_applies_migrations_up_to_target_version(self, mock_get_settings: Any) -> None:
        """Should apply migrations only up to specified target version."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.enable_migrations = True
        mock_db_settings.database_url = "memory://localhost"
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration1 = TestMigration("001")
        migration2 = TestMigration("002")
        migration3 = TestMigration("003")
        manager._migrations = [migration1, migration2, migration3]

        mock_runner = AsyncMock()
        mock_runner.get_applied_migrations.return_value = []
        manager._runner = mock_runner

        result = await manager.migrate_up(target_version="002")

        assert result == 2
        assert mock_runner.apply_migration.call_count == 2
        assert migration1.applied_at is not None
        assert migration2.applied_at is not None
        assert migration3.applied_at is None  # Should not be applied

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_handles_migration_application_failure(self, mock_get_settings: Any) -> None:
        """Should handle migration application failures with proper error handling."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.enable_migrations = True
        mock_db_settings.database_url = "memory://localhost"
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration = TestMigration("001")
        manager._migrations = [migration]

        mock_runner = AsyncMock()
        mock_runner.get_applied_migrations.return_value = []
        mock_runner.apply_migration.side_effect = MigrationException("Migration failed")
        manager._runner = mock_runner

        with pytest.raises(MigrationException):
            await manager.migrate_up()

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_skips_rollback_when_migrations_disabled(self, mock_get_settings: Any) -> None:
        """Should skip rollback when migrations are disabled."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.enable_migrations = False
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()

        result = await manager.migrate_down("001")

        assert result == 0

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_rolls_back_migrations_in_reverse_order(self, mock_get_settings: Any) -> None:
        """Should rollback migrations in reverse version order."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.enable_migrations = True
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration1 = TestMigration("001")
        migration2 = TestMigration("002")
        migration3 = TestMigration("003")
        manager._migrations = [migration1, migration2, migration3]

        mock_runner = AsyncMock()
        mock_runner.get_applied_migrations.return_value = ["001", "002", "003"]
        manager._runner = mock_runner

        result = await manager.migrate_down("001")

        assert result == 2  # Should rollback 003 and 002, keep 001
        # Should be rolled back in reverse order (newest first)
        assert mock_runner.rollback_migration.call_args_list[0][0][0] is migration3
        assert mock_runner.rollback_migration.call_args_list[1][0][0] is migration2

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_handles_rollback_failure(self, mock_get_settings: Any) -> None:
        """Should handle rollback failures with proper error handling."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.enable_migrations = True
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration = TestMigration("002")
        manager._migrations = [migration]

        mock_runner = AsyncMock()
        mock_runner.get_applied_migrations.return_value = ["002"]
        mock_runner.rollback_migration.side_effect = MigrationException("Rollback failed")
        manager._runner = mock_runner

        with pytest.raises(MigrationException):
            await manager.migrate_down("001")

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_returns_comprehensive_migration_status(self, mock_get_settings: Any) -> None:
        """Should return comprehensive migration status information."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.POSTGRESQL
        mock_db_settings.enable_migrations = True
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration1 = TestMigration("001")
        migration2 = TestMigration("002")
        migration3 = TestMigration("003")
        manager._migrations = [migration1, migration2, migration3]

        mock_runner = AsyncMock()
        mock_runner.get_applied_migrations.return_value = ["001", "002"]
        manager._runner = mock_runner

        status = await manager.get_migration_status()

        expected_status = {
            "database_type": "postgresql",
            "migrations_enabled": True,
            "total_registered": 3,
            "applied_count": 2,
            "pending_count": 1,
            "applied_versions": ["001", "002"],
            "pending_versions": ["003"],
        }
        assert status == expected_status

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_manages_database_connection_lifecycle(self, mock_get_settings: Any) -> None:
        """Should properly manage database connection lifecycle during operations."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.enable_migrations = True
        mock_db_settings.database_url = "memory://localhost"
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration = TestMigration("001")
        manager._migrations = [migration]

        mock_runner = AsyncMock()
        mock_runner.get_applied_migrations.return_value = []
        manager._runner = mock_runner

        await manager.migrate_up()

        # Verify connection was passed to migration operations
        assert mock_runner.apply_migration.called
        connection = mock_runner.apply_migration.call_args[0][1]
        assert connection["type"] == "mock"
        assert connection["database"] == "in_memory"


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestMigrationManagerResilience:
    """Test migration manager resilience and error handling."""

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_handles_no_migrations_to_rollback_gracefully(
        self, mock_get_settings: Any
    ) -> None:
        """Should handle case where no migrations need to be rolled back."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.enable_migrations = True
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration = TestMigration("001")
        manager._migrations = [migration]

        mock_runner = AsyncMock()
        mock_runner.get_applied_migrations.return_value = ["001"]
        manager._runner = mock_runner

        # Try to rollback to a version that would leave no migrations to rollback
        result = await manager.migrate_down("001")

        assert result == 0
        assert not mock_runner.rollback_migration.called

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_maintains_observability_during_errors(self, mock_get_settings: Any) -> None:
        """Should maintain observability metrics and logging during error conditions."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.enable_migrations = True
        mock_db_settings.database_url = "memory://localhost"
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration = TestMigration("001")
        manager._migrations = [migration]

        mock_runner = AsyncMock()
        mock_runner.get_applied_migrations.return_value = []
        mock_runner.apply_migration.side_effect = Exception("Unexpected error")
        manager._runner = mock_runner

        # Metrics and logging should still work during errors
        with pytest.raises(Exception, match="Unexpected error"):
            await manager.migrate_up()

        assert hasattr(manager, "logger")
        assert hasattr(manager, "metrics")


@pytest.mark.unit
@pytest.mark.behaviour
@pytest.mark.fast
class TestMigrationManagerSingleton:
    """Test migration manager global singleton behavior."""

    def test_returns_singleton_migration_manager_instance(self) -> None:
        """Should return the same migration manager instance on multiple calls."""
        # Reset global state
        import src.infrastructure.persistence.migrations.manager as manager_module

        manager_module._migration_manager = None

        manager1 = get_migration_manager()
        manager2 = get_migration_manager()

        assert manager1 is manager2
        assert isinstance(manager1, MigrationManager)

    def test_creates_new_instance_only_when_needed(self) -> None:
        """Should create new instance only when global instance is None."""
        # Reset global state
        import src.infrastructure.persistence.migrations.manager as manager_module

        manager_module._migration_manager = None

        with patch(
            "src.infrastructure.persistence.migrations.manager.MigrationManager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_manager.return_value = mock_instance

            # First call should create instance
            result1 = get_migration_manager()
            # Second call should return cached instance
            result2 = get_migration_manager()

            assert result1 is mock_instance
            assert result2 is mock_instance
            mock_manager.assert_called_once()


@pytest.mark.integration
@pytest.mark.behaviour
class TestMigrationManagerIntegration:
    """Test migration manager integration with database components."""

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_integrates_with_migration_runners_correctly(
        self, mock_get_settings: Any
    ) -> None:
        """Should integrate correctly with different migration runner types."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.database_url = "memory://localhost"
        mock_db_settings.enable_migrations = True
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()

        # Should work with actual runner implementation
        runner = manager.get_runner()
        assert isinstance(runner, InMemoryMigrationRunner)

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_handles_full_migration_lifecycle(self, mock_get_settings: Any) -> None:
        """Should handle complete migration lifecycle from registration to application."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.database_url = "memory://localhost"
        mock_db_settings.enable_migrations = True
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()
        migration = TestMigration("001")

        # Full lifecycle: register, setup, apply, check status
        manager.register_migration(migration)
        await manager.setup_migration_tracking()

        applied_count = await manager.migrate_up()
        assert applied_count == 1

        status = await manager.get_migration_status()
        assert status["applied_count"] == 1
        assert "001" in status["applied_versions"]

    @patch("src.infrastructure.persistence.migrations.manager.get_settings")
    async def test_migration_versioning_and_ordering_works_correctly(
        self, mock_get_settings: Any
    ) -> None:
        """Should handle migration versioning and ordering correctly."""
        mock_settings = Mock()
        mock_db_settings = Mock()
        mock_db_settings.primary_db = DatabaseType.IN_MEMORY
        mock_db_settings.database_url = "memory://localhost"
        mock_db_settings.enable_migrations = True
        mock_settings.database = mock_db_settings
        mock_get_settings.return_value = mock_settings

        manager = MigrationManager()

        # Register migrations in random order
        migration_003 = TestMigration("003")
        migration_001 = TestMigration("001")
        migration_002 = TestMigration("002")

        manager.register_migration(migration_003)
        manager.register_migration(migration_001)
        manager.register_migration(migration_002)

        # Should identify pending migrations in correct order
        pending = await manager.get_pending_migrations()
        assert len(pending) == 3
        assert pending[0].version == "001"
        assert pending[1].version == "002"
        assert pending[2].version == "003"
