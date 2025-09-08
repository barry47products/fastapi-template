"""Migration manager for coordinating database migrations."""

from __future__ import annotations

from typing import Any

from config.settings import get_settings
from src.infrastructure.observability import get_logger, get_metrics_collector

from .base import Migration, MigrationRunner, create_migration_runner


class MigrationManager:
    """Migration manager for coordinating database migrations across different database types."""

    def __init__(self) -> None:
        """Initialize migration manager with application settings."""
        settings = get_settings()
        self.db_settings = settings.database
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()
        self._migrations: list[Migration] = []
        self._runner: MigrationRunner | None = None

    def register_migration(self, migration: Migration) -> None:
        """Register a migration.

        Args:
            migration: Migration to register
        """
        if not migration.supports_database(self.db_settings.primary_db):
            self.logger.warning(
                "Migration does not support current database type",
                version=migration.version,
                database=self.db_settings.primary_db.value,
                supported_types=[db.value for db in migration.database_types],
            )
            return

        self._migrations.append(migration)
        self.logger.info(
            "Registered migration",
            version=migration.version,
            description=migration.description,
        )

    def get_runner(self) -> MigrationRunner:
        """Get migration runner for current database type.

        Returns:
            Migration runner instance
        """
        if self._runner is None:
            self._runner = create_migration_runner(
                database_url=self.db_settings.database_url,
                db_type=self.db_settings.primary_db,
            )
        return self._runner

    async def setup_migration_tracking(self) -> None:
        """Set up migration tracking table/collection."""
        runner = self.get_runner()
        await runner.create_migration_table()
        self.logger.info("Migration tracking setup complete")

    async def get_pending_migrations(self) -> list[Migration]:
        """Get list of pending migrations.

        Returns:
            List of migrations that haven't been applied
        """
        runner = self.get_runner()
        applied_versions = await runner.get_applied_migrations()

        pending = [
            migration for migration in self._migrations if migration.version not in applied_versions
        ]

        # Sort by version
        pending.sort(key=lambda m: m.version)

        self.logger.info(
            "Found pending migrations",
            count=len(pending),
            total_registered=len(self._migrations),
            applied_count=len(applied_versions),
        )

        return pending

    async def migrate_up(self, target_version: str | None = None) -> int:
        """Apply migrations up to target version.

        Args:
            target_version: Target migration version (None for all pending)

        Returns:
            Number of migrations applied

        Raises:
            RuntimeError: If migration fails
        """
        if not self.db_settings.enable_migrations:
            self.logger.info("Migrations are disabled, skipping")
            return 0

        await self.setup_migration_tracking()
        pending = await self.get_pending_migrations()

        if target_version:
            # Filter to only migrations up to target version
            pending = [m for m in pending if m.version <= target_version]

        if not pending:
            self.logger.info("No pending migrations to apply")
            return 0

        runner = self.get_runner()
        applied_count = 0

        # Apply migrations with database connection
        connection = await self._get_database_connection()

        try:
            for migration in pending:
                await runner.apply_migration(migration, connection)
                migration.mark_applied()
                applied_count += 1

                if target_version and migration.version == target_version:
                    break

            self.logger.info(
                "Migration batch completed",
                applied_count=applied_count,
                target_version=target_version,
            )
            self.metrics.increment_counter(
                "database_migration_batches_total",
                {"database": self.db_settings.primary_db.value, "status": "success"},
            )

        except Exception as e:
            self.logger.error("Migration batch failed", applied_count=applied_count, error=str(e))
            self.metrics.increment_counter(
                "database_migration_batches_total",
                {"database": self.db_settings.primary_db.value, "status": "failure"},
            )
            raise
        finally:
            await self._close_database_connection(connection)

        return applied_count

    async def migrate_down(self, target_version: str) -> int:
        """Rollback migrations down to target version.

        Args:
            target_version: Target version to rollback to

        Returns:
            Number of migrations rolled back

        Raises:
            RuntimeError: If rollback fails
        """
        if not self.db_settings.enable_migrations:
            self.logger.info("Migrations are disabled, skipping")
            return 0

        runner = self.get_runner()
        applied_versions = await runner.get_applied_migrations()

        # Find migrations to rollback (in reverse order)
        to_rollback = [
            migration
            for migration in reversed(self._migrations)
            if migration.version in applied_versions and migration.version > target_version
        ]

        if not to_rollback:
            self.logger.info("No migrations to rollback")
            return 0

        rollback_count = 0
        connection = await self._get_database_connection()

        try:
            for migration in to_rollback:
                await runner.rollback_migration(migration, connection)
                rollback_count += 1

            self.logger.info(
                "Rollback completed",
                rollback_count=rollback_count,
                target_version=target_version,
            )
            self.metrics.increment_counter(
                "database_rollback_batches_total",
                {"database": self.db_settings.primary_db.value, "status": "success"},
            )

        except Exception as e:
            self.logger.error("Rollback failed", rollback_count=rollback_count, error=str(e))
            self.metrics.increment_counter(
                "database_rollback_batches_total",
                {"database": self.db_settings.primary_db.value, "status": "failure"},
            )
            raise
        finally:
            await self._close_database_connection(connection)

        return rollback_count

    async def get_migration_status(self) -> dict[str, Any]:
        """Get migration status information.

        Returns:
            Dictionary with migration status information
        """
        runner = self.get_runner()
        applied_versions = await runner.get_applied_migrations()
        pending = await self.get_pending_migrations()

        return {
            "database_type": self.db_settings.primary_db.value,
            "migrations_enabled": self.db_settings.enable_migrations,
            "total_registered": len(self._migrations),
            "applied_count": len(applied_versions),
            "pending_count": len(pending),
            "applied_versions": applied_versions,
            "pending_versions": [m.version for m in pending],
        }

    async def _get_database_connection(self) -> Any:
        """Get database connection for migrations.

        Returns:
            Database connection

        Note:
            This is a placeholder - actual implementation would depend on database type
        """
        # For the template, return a mock connection
        # Real implementation would create actual database connections
        self.logger.debug("Getting database connection for migrations")
        return {"type": "mock", "database": self.db_settings.primary_db.value}

    async def _close_database_connection(self, connection: Any) -> None:
        """Close database connection.

        Args:
            connection: Database connection to close
        """
        # For the template, this is a no-op
        # Real implementation would properly close database connections
        self.logger.debug("Closing database connection", connection_type=connection.get("type"))


# Global migration manager instance
_migration_manager: MigrationManager | None = None


def get_migration_manager() -> MigrationManager:
    """Get the global migration manager instance.

    Returns:
        Migration manager instance
    """
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = MigrationManager()
    return _migration_manager
