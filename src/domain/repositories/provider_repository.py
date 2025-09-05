"""Provider repository interface following Repository pattern."""

from abc import ABC, abstractmethod
from typing import Protocol

from src.domain.models import Provider
from src.domain.value_objects import PhoneNumber, ProviderID


class ProviderRepository(Protocol):
    """
    Repository interface for Provider aggregate persistence.

    Defines the contract for Provider data access following the Repository pattern.
    This interface lives in the domain layer and defines what operations the
    domain needs without coupling to any specific persistence technology.

    Implementation will be provided by infrastructure layer adapters.
    """

    def save(self, provider: Provider) -> None:
        """
        Save or update a provider.

        Args:
            provider: Provider entity to persist

        Raises:
            RepositoryException: If the save operation fails
        """

    def find_by_id(self, provider_id: ProviderID) -> Provider | None:
        """
        Find a provider by its unique identifier.

        Args:
            provider_id: Unique provider identifier

        Returns:
            Provider entity if found, None otherwise

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_by_phone(self, phone: PhoneNumber) -> list[Provider]:
        """
        Find providers by phone number.

        Args:
            phone: Phone number to search for

        Returns:
            List of providers with matching phone number

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_by_category(
        self,
        category: str,
        limit: int | None = None,
    ) -> list[Provider]:
        """
        Find providers by service category.

        Args:
            category: Service category to filter by
            limit: Maximum number of results to return

        Returns:
            List of providers in the specified category

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_top_endorsed(
        self,
        category: str | None = None,
        limit: int = 10,
    ) -> list[Provider]:
        """
        Find providers with highest endorsement counts.

        Args:
            category: Optional category filter
            limit: Maximum number of results to return

        Returns:
            List of providers ordered by endorsement count descending

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_by_name_pattern(self, name_pattern: str) -> list[Provider]:
        """
        Find providers by name pattern (case-insensitive partial match).

        Args:
            name_pattern: Name pattern to search for

        Returns:
            List of providers matching the name pattern

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_by_tag(self, tag_key: str, tag_value: str) -> list[Provider]:
        """
        Find providers by tag key-value pair.

        Args:
            tag_key: Tag key to search for
            tag_value: Tag value to match

        Returns:
            List of providers with matching tag

        Raises:
            RepositoryException: If the find operation fails
        """

    def exists(self, provider_id: ProviderID) -> bool:
        """
        Check if a provider exists.

        Args:
            provider_id: Provider identifier to check

        Returns:
            True if provider exists, False otherwise

        Raises:
            RepositoryException: If the existence check fails
        """

    def delete(self, provider_id: ProviderID) -> None:
        """
        Delete a provider by ID.

        Args:
            provider_id: Provider identifier to delete

        Raises:
            RepositoryException: If the delete operation fails
        """

    def count(self) -> int:
        """
        Get total number of providers.

        Returns:
            Total count of providers

        Raises:
            RepositoryException: If the count operation fails
        """

    def count_by_category(self, category: str) -> int:
        """
        Get number of providers in a specific category.

        Args:
            category: Category to count

        Returns:
            Count of providers in the category

        Raises:
            RepositoryException: If the count operation fails
        """


class AbstractProviderRepository(ABC):
    """
    Abstract base class for Provider repository implementations.

    Provides default implementations and common functionality that
    can be shared across different persistence backends while
    maintaining the Protocol interface contract.
    """

    @abstractmethod
    def save(self, provider: Provider) -> None:
        """Save or update a provider."""

    @abstractmethod
    def find_by_id(self, provider_id: ProviderID) -> Provider | None:
        """Find a provider by ID."""

    @abstractmethod
    def find_by_phone(self, phone: PhoneNumber) -> list[Provider]:
        """Find providers by phone number."""

    @abstractmethod
    def find_by_category(
        self,
        category: str,
        limit: int | None = None,
    ) -> list[Provider]:
        """Find providers by category."""

    @abstractmethod
    def find_top_endorsed(
        self,
        category: str | None = None,
        limit: int = 10,
    ) -> list[Provider]:
        """Find top endorsed providers."""

    @abstractmethod
    def find_by_name_pattern(self, name_pattern: str) -> list[Provider]:
        """Find providers by name pattern."""

    @abstractmethod
    def find_by_tag(self, tag_key: str, tag_value: str) -> list[Provider]:
        """Find providers by tag."""

    @abstractmethod
    def exists(self, provider_id: ProviderID) -> bool:
        """Check if provider exists."""

    @abstractmethod
    def delete(self, provider_id: ProviderID) -> None:
        """Delete a provider."""

    @abstractmethod
    def count(self) -> int:
        """Get total provider count."""

    @abstractmethod
    def count_by_category(self, category: str) -> int:
        """Get provider count by category."""

    def find_all(self) -> list[Provider]:
        """
        Find all providers (default implementation).

        Returns:
            List of all providers

        Note:
            This default implementation may not be efficient for large datasets.
            Override in concrete implementations for better performance.
        """
        # This is a default implementation that subclasses can override
        return []  # Placeholder - concrete implementations should override
