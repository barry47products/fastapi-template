"""Sample in-memory implementation of User repository for template demonstration."""

from datetime import datetime, UTC
from typing import Any

from src.domain.models import User
from src.domain.value_objects import Email
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import RepositoryException


class InMemoryUserRepository:
    """
    In-memory implementation of User repository for template demonstration.

    This implementation demonstrates repository patterns without external
    dependencies like databases. In production, replace this with your
    actual persistence implementation (SQLAlchemy, MongoDB, etc.).
    """

    def __init__(self) -> None:
        """Initialize repository with in-memory storage."""
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()
        self._storage: dict[str, dict[str, Any]] = {}

    def save(self, user: User) -> None:
        """Save or update a user."""
        try:
            user_data = self._to_document(user)
            self._storage[user.id.value] = user_data

            self.metrics.increment_counter("user_saves_total", {})
            self.logger.info("User saved successfully", user_id=user.id.value)

        except Exception as e:
            self.metrics.increment_counter("user_save_errors_total", {})
            self.logger.error(
                "Failed to save user",
                user_id=user.id.value,
                error=str(e),
            )
            raise RepositoryException(f"Failed to save user: {e}") from e

    def find_by_id(self, user_id: str) -> User | None:
        """Find a user by ID."""
        try:
            user_data = self._storage.get(user_id)
            if user_data is None:
                self.logger.debug("User not found", user_id=user_id)
                return None

            user = self._from_document(user_data)
            self.metrics.increment_counter("user_finds_total", {})
            return user

        except Exception as e:
            self.metrics.increment_counter("user_find_errors_total", {})
            self.logger.error(
                "Failed to find user by ID",
                user_id=user_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find user: {e}") from e

    def find_by_email(self, email: Email) -> User | None:
        """Find a user by email address."""
        try:
            for user_data in self._storage.values():
                if user_data.get("email") == email.value:
                    user = self._from_document(user_data)
                    self.metrics.increment_counter("user_email_searches_total", {})
                    return user

            self.logger.debug("User not found by email", email=email.value)
            return None

        except Exception as e:
            self.metrics.increment_counter("user_email_search_errors_total", {})
            self.logger.error(
                "Failed to find user by email",
                email=email.value,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find user by email: {e}") from e

    def find_by_status(self, status: str) -> list[User]:
        """Find users by status."""
        try:
            users = []
            for user_data in self._storage.values():
                if user_data.get("status") == status:
                    user = self._from_document(user_data)
                    users.append(user)

            self.metrics.increment_counter("user_status_searches_total", {})
            self.logger.debug("Found users by status", status=status, count=len(users))
            return users

        except Exception as e:
            self.metrics.increment_counter("user_status_search_errors_total", {})
            self.logger.error(
                "Failed to find users by status",
                status=status,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find users by status: {e}") from e

    def find_created_after(self, date: datetime) -> list[User]:
        """Find users created after specified date."""
        try:
            users = []
            for user_data in self._storage.values():
                if user_data.get("created_at", datetime.min) > date:
                    user = self._from_document(user_data)
                    users.append(user)

            self.metrics.increment_counter("user_date_searches_total", {})
            self.logger.debug(
                "Found users by creation date",
                date=date.isoformat(),
                count=len(users),
            )
            return users

        except Exception as e:
            self.metrics.increment_counter("user_date_search_errors_total", {})
            self.logger.error(
                "Failed to find users by creation date",
                date=date.isoformat(),
                error=str(e),
            )
            raise RepositoryException(f"Failed to find users by date: {e}") from e

    def exists(self, user_id: str) -> bool:
        """Check if a user exists."""
        try:
            exists = user_id in self._storage
            self.metrics.increment_counter("user_exists_checks_total", {})
            return exists

        except Exception as e:
            self.metrics.increment_counter("user_exists_check_errors_total", {})
            self.logger.error(
                "Failed to check user existence",
                user_id=user_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to check user existence: {e}") from e

    def delete(self, user_id: str) -> None:
        """Delete a user by ID."""
        try:
            if user_id in self._storage:
                del self._storage[user_id]
                self.metrics.increment_counter("user_deletes_total", {})
                self.logger.info("User deleted successfully", user_id=user_id)
            else:
                raise RepositoryException(f"User not found: {user_id}")

        except Exception as e:
            self.metrics.increment_counter("user_delete_errors_total", {})
            self.logger.error(
                "Failed to delete user",
                user_id=user_id,
                error=str(e),
            )
            raise RepositoryException(f"Failed to delete user: {e}") from e

    def count(self) -> int:
        """Get total number of users."""
        try:
            count = len(self._storage)
            self.metrics.increment_counter("user_counts_total", {})
            self.logger.debug("User count retrieved", count=count)
            return count

        except Exception as e:
            self.metrics.increment_counter("user_count_errors_total", {})
            self.logger.error("Failed to count users", error=str(e))
            raise RepositoryException(f"Failed to count users: {e}") from e

    def list_all(self, limit: int | None = None) -> list[User]:
        """List all users with optional limit."""
        try:
            all_data = list(self._storage.values())
            if limit:
                all_data = all_data[:limit]

            users = [self._from_document(data) for data in all_data]
            self.metrics.increment_counter("user_list_all_total", {})
            self.logger.debug("Listed all users", count=len(users))
            return users

        except Exception as e:
            self.metrics.increment_counter("user_list_errors_total", {})
            self.logger.error("Failed to list users", error=str(e))
            raise RepositoryException(f"Failed to list users: {e}") from e

    def _to_document(self, user: User) -> dict[str, Any]:
        """Convert User entity to storage document."""
        return {
            "id": user.id.value,
            "name": user.name,
            "email": user.email.value,
            "age": user.age,
            "status": user.status,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    def _from_document(self, doc_data: dict[str, Any]) -> User:
        """Convert storage document to User entity."""
        return User(
            id=doc_data["id"],
            name=doc_data["name"],
            email=doc_data["email"],
            age=doc_data["age"],
            status=doc_data["status"],
            created_at=doc_data["created_at"],
            updated_at=doc_data["updated_at"],
        )