"""Endorsement repository interface following Repository pattern."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol

from src.domain.models import Endorsement
from src.domain.models.endorsement import EndorsementStatus, EndorsementType
from src.domain.value_objects import EndorsementID, GroupID, PhoneNumber, ProviderID


class EndorsementRepository(Protocol):
    """
    Repository interface for Endorsement aggregate persistence.

    Defines the contract for Endorsement data access following the Repository pattern.
    This interface lives in the domain layer and defines what operations the
    domain needs without coupling to any specific persistence technology.

    Implementation will be provided by infrastructure layer adapters.
    """

    def save(self, endorsement: Endorsement) -> None:
        """
        Save or update an endorsement.

        Args:
            endorsement: Endorsement entity to persist

        Raises:
            RepositoryException: If the save operation fails
        """

    def find_by_id(self, endorsement_id: EndorsementID) -> Endorsement | None:
        """
        Find an endorsement by its unique identifier.

        Args:
            endorsement_id: Unique endorsement identifier

        Returns:
            Endorsement entity if found, None otherwise

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_by_provider(
        self,
        provider_id: ProviderID,
        status: EndorsementStatus | None = None,
    ) -> list[Endorsement]:
        """
        Find endorsements for a specific provider.

        Args:
            provider_id: Provider identifier
            status: Optional status filter

        Returns:
            List of endorsements for the provider

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_by_group(
        self,
        group_id: GroupID,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """
        Find endorsements within a specific group.

        Args:
            group_id: Group identifier
            limit: Maximum number of results to return

        Returns:
            List of endorsements in the group

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_by_endorser(
        self,
        endorser_phone: PhoneNumber,
        status: EndorsementStatus | None = None,
    ) -> list[Endorsement]:
        """
        Find endorsements created by a specific endorser.

        Args:
            endorser_phone: Phone number of the endorser
            status: Optional status filter

        Returns:
            List of endorsements by the endorser

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_by_type(
        self,
        endorsement_type: EndorsementType,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """
        Find endorsements by type.

        Args:
            endorsement_type: Type of endorsement (AUTOMATIC, MANUAL)
            limit: Maximum number of results to return

        Returns:
            List of endorsements of the specified type

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_recent(
        self,
        days: int = 30,
        status: EndorsementStatus | None = None,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """
        Find recent endorsements within specified time period.

        Args:
            days: Number of days to look back
            status: Optional status filter
            limit: Maximum number of results to return

        Returns:
            List of recent endorsements ordered by creation time desc

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_by_confidence_range(
        self,
        min_confidence: float,
        max_confidence: float,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """
        Find endorsements within confidence score range.

        Args:
            min_confidence: Minimum confidence score (0.0-1.0)
            max_confidence: Maximum confidence score (0.0-1.0)
            limit: Maximum number of results to return

        Returns:
            List of endorsements within confidence range

        Raises:
            RepositoryException: If the find operation fails
        """

    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        status: EndorsementStatus | None = None,
    ) -> list[Endorsement]:
        """
        Find endorsements within date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            status: Optional status filter

        Returns:
            List of endorsements within date range

        Raises:
            RepositoryException: If the find operation fails
        """

    def exists(self, endorsement_id: EndorsementID) -> bool:
        """
        Check if an endorsement exists.

        Args:
            endorsement_id: Endorsement identifier to check

        Returns:
            True if endorsement exists, False otherwise

        Raises:
            RepositoryException: If the existence check fails
        """

    def delete(self, endorsement_id: EndorsementID) -> None:
        """
        Delete an endorsement by ID.

        Args:
            endorsement_id: Endorsement identifier to delete

        Raises:
            RepositoryException: If the delete operation fails
        """

    def count(self) -> int:
        """
        Get total number of endorsements.

        Returns:
            Total count of endorsements

        Raises:
            RepositoryException: If the count operation fails
        """

    def count_by_provider(
        self,
        provider_id: ProviderID,
        status: EndorsementStatus | None = None,
    ) -> int:
        """
        Get number of endorsements for a provider.

        Args:
            provider_id: Provider identifier
            status: Optional status filter

        Returns:
            Count of endorsements for the provider

        Raises:
            RepositoryException: If the count operation fails
        """

    def count_by_group(self, group_id: GroupID) -> int:
        """
        Get number of endorsements in a group.

        Args:
            group_id: Group identifier

        Returns:
            Count of endorsements in the group

        Raises:
            RepositoryException: If the count operation fails
        """

    def count_by_type(self, endorsement_type: EndorsementType) -> int:
        """
        Get number of endorsements by type.

        Args:
            endorsement_type: Type of endorsement

        Returns:
            Count of endorsements of the specified type

        Raises:
            RepositoryException: If the count operation fails
        """


class AbstractEndorsementRepository(ABC):
    """
    Abstract base class for Endorsement repository implementations.

    Provides default implementations and common functionality that
    can be shared across different persistence backends while
    maintaining the Protocol interface contract.
    """

    @abstractmethod
    def save(self, endorsement: Endorsement) -> None:
        """Save or update an endorsement."""

    @abstractmethod
    def find_by_id(self, endorsement_id: EndorsementID) -> Endorsement | None:
        """Find an endorsement by ID."""

    @abstractmethod
    def find_by_provider(
        self,
        provider_id: ProviderID,
        status: EndorsementStatus | None = None,
    ) -> list[Endorsement]:
        """Find endorsements by provider."""

    @abstractmethod
    def find_by_group(
        self,
        group_id: GroupID,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """Find endorsements by group."""

    @abstractmethod
    def find_by_endorser(
        self,
        endorser_phone: PhoneNumber,
        status: EndorsementStatus | None = None,
    ) -> list[Endorsement]:
        """Find endorsements by endorser."""

    @abstractmethod
    def find_by_type(
        self,
        endorsement_type: EndorsementType,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """Find endorsements by type."""

    @abstractmethod
    def find_recent(
        self,
        days: int = 30,
        status: EndorsementStatus | None = None,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """Find recent endorsements."""

    @abstractmethod
    def find_by_confidence_range(
        self,
        min_confidence: float,
        max_confidence: float,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """Find endorsements by confidence range."""

    @abstractmethod
    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        status: EndorsementStatus | None = None,
    ) -> list[Endorsement]:
        """Find endorsements by date range."""

    @abstractmethod
    def exists(self, endorsement_id: EndorsementID) -> bool:
        """Check if endorsement exists."""

    @abstractmethod
    def delete(self, endorsement_id: EndorsementID) -> None:
        """Delete an endorsement."""

    @abstractmethod
    def count(self) -> int:
        """Get total endorsement count."""

    @abstractmethod
    def count_by_provider(
        self,
        provider_id: ProviderID,
        status: EndorsementStatus | None = None,
    ) -> int:
        """Get endorsement count by provider."""

    @abstractmethod
    def count_by_group(self, group_id: GroupID) -> int:
        """Get endorsement count by group."""

    @abstractmethod
    def count_by_type(self, endorsement_type: EndorsementType) -> int:
        """Get endorsement count by type."""

    def find_all(self) -> list[Endorsement]:
        """
        Find all endorsements (default implementation).

        Returns:
            List of all endorsements

        Note:
            This default implementation may not be efficient for large datasets.
            Override in concrete implementations for better performance.
        """
        # This is a default implementation that subclasses can override
        return []  # Placeholder - concrete implementations should override
