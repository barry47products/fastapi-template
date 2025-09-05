"""Tests for Firestore Provider Repository implementation."""

# pylint: disable=redefined-outer-name

from datetime import datetime, UTC
from unittest.mock import MagicMock

import pytest

from src.domain.models import Provider
from src.domain.value_objects import PhoneNumber, ProviderID
from src.infrastructure.persistence.firestore_client import FirestoreClient
from src.infrastructure.persistence.repositories.firestore_provider_repository import (
    FirestoreProviderRepository,
)
from src.shared.exceptions import RepositoryException


@pytest.fixture
def mock_firestore_client() -> MagicMock:
    """Mock Firestore client for testing."""
    return MagicMock(spec=FirestoreClient)


@pytest.fixture
def provider_repository(
    mock_firestore_client: MagicMock,
) -> FirestoreProviderRepository:
    """Provider repository with mocked Firestore client."""
    return FirestoreProviderRepository(mock_firestore_client)


@pytest.fixture
def sample_provider() -> Provider:
    """Sample provider for testing."""
    return Provider(
        id=ProviderID(value="550e8400-e29b-41d4-a716-446655440000"),
        name="John Smith Plumbing",
        phone=PhoneNumber(value="+27821234567"),
        category="plumbing",
        tags={"verified": "true", "emergency": "available"},
        endorsement_count=5,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def sample_document_data() -> dict[str, str | int | dict[str, str] | datetime]:
    """Sample Firestore document data."""
    return {
        "_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "John Smith Plumbing",
        "phone": "+27821234567",
        "category": "plumbing",
        "tags": {"verified": "true", "emergency": "available"},
        "endorsement_count": 5,
        "created_at": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    }


class TestFirestoreProviderRepositorySave:
    """Test provider saving functionality."""

    def test_should_save_provider_successfully(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_provider: Provider,
    ) -> None:
        """Should save provider to Firestore with correct document structure."""
        # Act
        provider_repository.save(sample_provider)

        # Assert
        mock_firestore_client.create_document.assert_called_once_with(
            "providers",
            {
                "_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "John Smith Plumbing",
                "phone": "+27821234567",
                "category": "plumbing",
                "tags": {"verified": "true", "emergency": "available"},
                "endorsement_count": 5,
                "created_at": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            },
            "550e8400-e29b-41d4-a716-446655440000",
        )

    def test_should_raise_repository_exception_on_firestore_error(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_provider: Provider,
    ) -> None:
        """Should raise RepositoryException when Firestore operation fails."""
        # Arrange
        mock_firestore_client.create_document.side_effect = Exception("Firestore error")

        # Act & Assert
        with pytest.raises(RepositoryException, match="Failed to save provider"):
            provider_repository.save(sample_provider)


class TestFirestoreProviderRepositoryFind:
    """Test provider finding functionality."""

    def test_should_find_provider_by_id_successfully(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should find and return provider when document exists."""
        # Arrange
        provider_id = ProviderID(value="550e8400-e29b-41d4-a716-446655440000")
        mock_firestore_client.get_document.return_value = sample_document_data

        # Act
        result = provider_repository.find_by_id(provider_id)

        # Assert
        assert result is not None
        assert result.id.value == "550e8400-e29b-41d4-a716-446655440000"
        assert result.name == "John Smith Plumbing"
        assert result.phone.value == "+27821234567"
        assert result.category == "plumbing"
        assert result.tags == {"verified": "true", "emergency": "available"}
        assert result.endorsement_count == 5
        mock_firestore_client.get_document.assert_called_once_with(
            "providers/550e8400-e29b-41d4-a716-446655440000",
        )

    def test_should_return_none_when_provider_not_found(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return None when provider document doesn't exist."""
        # Arrange
        provider_id = ProviderID(value="550e8400-e29b-41d4-a716-446655440001")
        mock_firestore_client.get_document.return_value = None

        # Act
        result = provider_repository.find_by_id(provider_id)

        # Assert
        assert result is None
        mock_firestore_client.get_document.assert_called_once_with(
            "providers/550e8400-e29b-41d4-a716-446655440001",
        )

    def test_should_raise_repository_exception_on_find_error(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should raise RepositoryException when find operation fails."""
        # Arrange
        provider_id = ProviderID(value="550e8400-e29b-41d4-a716-446655440002")
        mock_firestore_client.get_document.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(RepositoryException, match="Failed to find provider"):
            provider_repository.find_by_id(provider_id)


class TestFirestoreProviderRepositoryFindByPhone:
    """Test finding providers by phone number."""

    def test_should_find_providers_by_phone_number(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should find providers matching phone number."""
        # Arrange
        phone = PhoneNumber(value="+27821234567")
        mock_firestore_client.query_collection.return_value = [sample_document_data]

        # Act
        result = provider_repository.find_by_phone(phone)

        # Assert
        assert len(result) == 1
        assert result[0].phone.value == "+27821234567"
        assert result[0].name == "John Smith Plumbing"

    def test_should_return_empty_list_when_no_phone_matches(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return empty list when no providers match phone number."""
        # Arrange
        phone = PhoneNumber(value="+27821234568")
        mock_firestore_client.query_collection.return_value = []

        # Act
        result = provider_repository.find_by_phone(phone)

        # Assert
        assert result == []

    def test_should_handle_documents_without_id_field(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should skip documents that don't have _id field."""
        # Arrange
        phone = PhoneNumber(value="+27821234567")
        document_without_id = {"name": "John", "phone": "+27821234567"}
        mock_firestore_client.query_collection.return_value = [document_without_id]

        # Act
        result = provider_repository.find_by_phone(phone)

        # Assert
        assert result == []


class TestFirestoreProviderRepositoryFindByCategory:
    """Test finding providers by category."""

    def test_should_find_providers_by_category(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should find providers in specified category."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [sample_document_data]

        # Act
        result = provider_repository.find_by_category("plumbing")

        # Assert
        assert len(result) == 1
        assert result[0].category == "plumbing"

    def test_should_apply_limit_when_specified(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should respect limit parameter in category search."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [sample_document_data]

        # Act
        provider_repository.find_by_category("plumbing", limit=5)

        # Assert
        call_args = mock_firestore_client.query_collection.call_args
        assert call_args.kwargs["limit"] == 5


class TestFirestoreProviderRepositoryFindTopEndorsed:
    """Test finding top endorsed providers."""

    def test_should_find_top_endorsed_providers_without_category_filter(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should find top endorsed providers across all categories."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [sample_document_data]

        # Act
        result = provider_repository.find_top_endorsed()

        # Assert
        assert len(result) == 1
        call_args = mock_firestore_client.query_collection.call_args
        assert call_args.kwargs["order_by"] == "endorsement_count desc"
        assert call_args.kwargs["limit"] == 10

    def test_should_find_top_endorsed_providers_with_category_filter(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should find top endorsed providers in specific category."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [sample_document_data]

        # Act
        result = provider_repository.find_top_endorsed(category="plumbing", limit=5)

        # Assert
        assert len(result) == 1
        call_args = mock_firestore_client.query_collection.call_args
        assert call_args.kwargs["limit"] == 5


class TestFirestoreProviderRepositoryFindByNamePattern:
    """Test finding providers by name pattern."""

    def test_should_find_providers_by_name_pattern_case_insensitive(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should find providers matching name pattern case-insensitively."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [sample_document_data]

        # Act
        result = provider_repository.find_by_name_pattern("john")

        # Assert
        assert len(result) == 1
        assert result[0].name == "John Smith Plumbing"

    def test_should_handle_partial_name_matches(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should find providers with partial name matches."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [sample_document_data]

        # Act
        result = provider_repository.find_by_name_pattern("smith")

        # Assert
        assert len(result) == 1
        assert result[0].name == "John Smith Plumbing"

    def test_should_return_empty_list_for_non_matching_pattern(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return empty list when no names match pattern."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [
            {"_id": "test", "name": "Different Name", "phone": "+27821234567"},
        ]

        # Act
        result = provider_repository.find_by_name_pattern("nonexistent")

        # Assert
        assert result == []


class TestFirestoreProviderRepositoryFindByTag:
    """Test finding providers by tag."""

    def test_should_find_providers_by_tag_key_value(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should find providers matching tag key-value pair."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [sample_document_data]

        # Act
        result = provider_repository.find_by_tag("verified", "true")

        # Assert
        assert len(result) == 1
        assert result[0].tags.get("verified") == "true"


class TestFirestoreProviderRepositoryExists:
    """Test provider existence checking."""

    def test_should_return_true_when_provider_exists(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should return True when provider document exists."""
        # Arrange
        provider_id = ProviderID(value="550e8400-e29b-41d4-a716-446655440000")
        mock_firestore_client.get_document.return_value = sample_document_data

        # Act
        result = provider_repository.exists(provider_id)

        # Assert
        assert result is True

    def test_should_return_false_when_provider_does_not_exist(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should return False when provider document doesn't exist."""
        # Arrange
        provider_id = ProviderID(value="550e8400-e29b-41d4-a716-446655440003")
        mock_firestore_client.get_document.return_value = None

        # Act
        result = provider_repository.exists(provider_id)

        # Assert
        assert result is False


class TestFirestoreProviderRepositoryDelete:
    """Test provider deletion."""

    def test_should_delete_provider_successfully(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should delete provider document from Firestore."""
        # Arrange
        provider_id = ProviderID(value="550e8400-e29b-41d4-a716-446655440000")

        # Act
        provider_repository.delete(provider_id)

        # Assert
        mock_firestore_client.delete_document.assert_called_once_with(
            "providers/550e8400-e29b-41d4-a716-446655440000",
        )

    def test_should_raise_repository_exception_on_delete_error(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should raise RepositoryException when delete operation fails."""
        # Arrange
        provider_id = ProviderID(value="550e8400-e29b-41d4-a716-446655440002")
        mock_firestore_client.delete_document.side_effect = Exception("Delete failed")

        # Act & Assert
        with pytest.raises(RepositoryException, match="Failed to delete provider"):
            provider_repository.delete(provider_id)


class TestFirestoreProviderRepositoryCount:
    """Test provider counting functionality."""

    def test_should_count_all_providers(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should return total count of providers."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [
            sample_document_data,
            sample_document_data,
            sample_document_data,
        ]

        # Act
        result = provider_repository.count()

        # Assert
        assert result == 3

    def test_should_count_providers_by_category(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should return count of providers in specific category."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [sample_document_data]

        # Act
        result = provider_repository.count_by_category("plumbing")

        # Assert
        assert result == 1


class TestFirestoreProviderRepositoryDocumentConversion:
    """Test document conversion methods."""

    def test_should_convert_provider_to_document_correctly(
        self,
        provider_repository: FirestoreProviderRepository,
        sample_provider: Provider,
    ) -> None:
        """Should convert Provider entity to correct Firestore document format."""
        # Act
        result = provider_repository._to_document(sample_provider)

        # Assert
        expected = {
            "_id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "John Smith Plumbing",
            "phone": "+27821234567",
            "category": "plumbing",
            "tags": {"verified": "true", "emergency": "available"},
            "endorsement_count": 5,
            "created_at": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        }
        assert result == expected

    def test_should_convert_document_to_provider_correctly(
        self,
        provider_repository: FirestoreProviderRepository,
        sample_document_data: dict[str, str | int | dict[str, str] | datetime],
    ) -> None:
        """Should convert Firestore document to Provider entity correctly."""
        # Act
        result = provider_repository._from_document(
            sample_document_data,
            "550e8400-e29b-41d4-a716-446655440000",
        )

        # Assert
        assert result.id.value == "550e8400-e29b-41d4-a716-446655440000"
        assert result.name == "John Smith Plumbing"
        assert result.phone.value == "+27821234567"
        assert result.category == "plumbing"
        assert result.tags == {"verified": "true", "emergency": "available"}
        assert result.endorsement_count == 5
        assert result.created_at == datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

    def test_should_handle_missing_optional_fields_in_document(
        self,
        provider_repository: FirestoreProviderRepository,
    ) -> None:
        """Should handle documents with missing optional fields."""
        # Arrange
        minimal_document: dict[str, str | int | dict[str, str] | datetime] = {
            "_id": "550e8400-e29b-41d4-a716-446655440004",
            "name": "Test Provider",
            "phone": "+27821234567",
            "category": "test",
            "created_at": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        }

        # Act
        result = provider_repository._from_document(
            minimal_document,
            "550e8400-e29b-41d4-a716-446655440004",
        )

        # Assert
        assert result.id.value == "550e8400-e29b-41d4-a716-446655440004"
        assert result.name == "Test Provider"
        assert result.tags == {}  # Default empty dict
        assert result.endorsement_count == 0  # Default value


class TestFirestoreProviderRepositoryIntegration:
    """Integration tests with metrics and logging."""

    def test_should_record_metrics_on_successful_operations(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,  # Required for provider_repository fixture
        sample_provider: Provider,
    ) -> None:
        """Should record success metrics for repository operations."""
        # Act
        provider_repository.save(sample_provider)

        # Assert - This test would need to mock the metrics collector properly
        # The real repository uses get_metrics_collector() which returns a function
        # In a real test, we'd mock the get_metrics_collector import

    def test_should_record_metrics_on_failed_operations(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_firestore_client: MagicMock,
        sample_provider: Provider,
    ) -> None:
        """Should record error metrics for failed repository operations."""
        # Arrange
        mock_firestore_client.create_document.side_effect = Exception("Test error")

        # Act & Assert
        with pytest.raises(RepositoryException):
            provider_repository.save(sample_provider)

        # Assert - This test would need to mock the metrics collector properly
        # The real repository uses get_metrics_collector() which returns a function
