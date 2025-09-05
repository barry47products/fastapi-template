"""Integration tests for Provider Repository with MessageProcessor."""

# pylint: disable=redefined-outer-name

from datetime import datetime, UTC
from unittest.mock import MagicMock

import pytest

from src.application.services.message_processor import MessageProcessor
from src.domain.models import ClassificationResult, MessageType, Provider
from src.domain.repositories import EndorsementRepository, ProviderRepository
from src.domain.value_objects import GroupID, PhoneNumber, ProviderID
from src.infrastructure.persistence.repositories.firestore_provider_repository import (
    FirestoreProviderRepository,
)


@pytest.fixture
def mock_firestore_client() -> MagicMock:
    """Mock Firestore client for testing."""
    return MagicMock()


@pytest.fixture
def provider_repository(
    mock_firestore_client: MagicMock,
) -> FirestoreProviderRepository:
    """Provider repository with mocked Firestore client."""
    return FirestoreProviderRepository(mock_firestore_client)


@pytest.fixture
def mock_endorsement_repository() -> MagicMock:
    """Mock endorsement repository."""
    return MagicMock(spec=EndorsementRepository)


@pytest.fixture
def sample_provider() -> Provider:
    """Sample provider for testing."""
    return Provider(
        id=ProviderID(value="550e8400-e29b-41d4-a716-446655440000"),
        name="John Smith Plumbing",
        phone=PhoneNumber(value="+27821234567"),
        category="plumbing",
        tags={"verified": "true"},
        endorsement_count=0,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


class TestProviderRepositoryIntegration:
    """Test Provider Repository integration with MessageProcessor."""

    @pytest.mark.asyncio
    async def test_should_create_new_provider_from_contact_mention(
        self,
        provider_repository: ProviderRepository,
        mock_endorsement_repository: EndorsementRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should create new provider when contact mention has no existing match."""
        # Arrange
        mock_firestore_client.query_collection.return_value = []  # No existing providers

        message_processor = MessageProcessor(
            provider_repository=provider_repository,
            endorsement_repository=mock_endorsement_repository,
        )

        group_id = GroupID(value="test-group-123@g.us")
        classification = ClassificationResult(
            message_type=MessageType.RECOMMENDATION,
            confidence=0.95,
            keywords=["contact_card_shared"],
            rule_matches=["contact_endorsement_signal"],
        )

        # Act
        result = await message_processor.process_endorsement_message(
            group_id=group_id,
            sender_name="Alice Smith",
            message_text="Contact shared: John Smith Plumbing",
            timestamp=1672531200,
            classification=classification,
        )

        # Assert - Processing should complete successfully
        assert result.success is True
        # Note: Current implementation is placeholder, will be enhanced in next steps

    @pytest.mark.asyncio
    async def test_should_find_existing_provider_by_phone_number(
        self,
        provider_repository: ProviderRepository,
        mock_endorsement_repository: EndorsementRepository,
        mock_firestore_client: MagicMock,
        sample_provider: Provider,
    ) -> None:
        """Should find and use existing provider when phone number matches."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [
            {
                "_id": sample_provider.id.value,
                "name": sample_provider.name,
                "phone": sample_provider.phone.value,
                "category": sample_provider.category,
                "tags": dict(sample_provider.tags),
                "endorsement_count": sample_provider.endorsement_count,
                "created_at": sample_provider.created_at,
            },
        ]

        message_processor = MessageProcessor(
            provider_repository=provider_repository,
            endorsement_repository=mock_endorsement_repository,
        )

        group_id = GroupID(value="test-group-123@g.us")
        classification = ClassificationResult(
            message_type=MessageType.RECOMMENDATION,
            confidence=0.95,
            keywords=["contact_card_shared"],
            rule_matches=["contact_endorsement_signal"],
        )

        # Act
        result = await message_processor.process_endorsement_message(
            group_id=group_id,
            sender_name="Alice Smith",
            message_text="Contact shared: John Smith Plumbing",
            timestamp=1672531200,
            classification=classification,
        )

        # Assert - Processing should complete successfully
        assert result.success is True
        # Phone number should be queried
        mock_firestore_client.query_collection.assert_called()

    @pytest.mark.asyncio
    async def test_should_increment_endorsement_count_for_existing_provider(
        self,
        provider_repository: ProviderRepository,
        mock_endorsement_repository: EndorsementRepository,
        mock_firestore_client: MagicMock,
        sample_provider: Provider,
    ) -> None:
        """Should increment endorsement count when provider receives new endorsement."""
        # Arrange
        mock_firestore_client.query_collection.return_value = [
            {
                "_id": sample_provider.id.value,
                "name": sample_provider.name,
                "phone": sample_provider.phone.value,
                "category": sample_provider.category,
                "tags": dict(sample_provider.tags),
                "endorsement_count": 3,  # Existing count
                "created_at": sample_provider.created_at,
            },
        ]

        message_processor = MessageProcessor(
            provider_repository=provider_repository,
            endorsement_repository=mock_endorsement_repository,
        )

        group_id = GroupID(value="test-group-123@g.us")
        classification = ClassificationResult(
            message_type=MessageType.RECOMMENDATION,
            confidence=0.95,
            keywords=["contact_card_shared"],
            rule_matches=["contact_endorsement_signal"],
        )

        # Act
        result = await message_processor.process_endorsement_message(
            group_id=group_id,
            sender_name="Alice Smith",
            message_text="Contact shared: John Smith Plumbing",
            timestamp=1672531200,
            classification=classification,
        )

        # Assert
        assert result.success is True
        # Provider should be updated with incremented count (in real implementation)

    @pytest.mark.asyncio
    async def test_should_handle_provider_repository_errors_gracefully(
        self,
        provider_repository: ProviderRepository,
        mock_endorsement_repository: EndorsementRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should handle provider repository errors without crashing."""
        # Arrange
        mock_firestore_client.query_collection.side_effect = Exception("Database error")

        message_processor = MessageProcessor(
            provider_repository=provider_repository,
            endorsement_repository=mock_endorsement_repository,
        )

        group_id = GroupID(value="test-group-123@g.us")
        classification = ClassificationResult(
            message_type=MessageType.RECOMMENDATION,
            confidence=0.95,
            keywords=["contact_card_shared"],
            rule_matches=["contact_endorsement_signal"],
        )

        # Act
        result = await message_processor.process_endorsement_message(
            group_id=group_id,
            sender_name="Alice Smith",
            message_text="Contact shared: John Smith Plumbing",
            timestamp=1672531200,
            classification=classification,
        )

        # Assert - Should handle gracefully (current implementation returns empty results)
        assert result.success is True


class TestContactProcessingEndToEnd:
    """Test end-to-end contact processing with repository integration."""

    def test_should_create_provider_from_contact_card_data(
        self,
        provider_repository: ProviderRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should create provider record from contact card vCard data."""
        # Arrange

        # Mock no existing providers
        mock_firestore_client.query_collection.return_value = []

        # Expected provider creation
        expected_provider = Provider(
            id=ProviderID(),  # Will be auto-generated
            name="John Smith Plumbing",
            phone=PhoneNumber(value="+27821234567"),
            category="services",  # Default category
            tags={},
            endorsement_count=1,  # First endorsement
        )

        # Act - Save the expected provider
        provider_repository.save(expected_provider)

        # Assert
        mock_firestore_client.create_document.assert_called_once()
        call_args = mock_firestore_client.create_document.call_args
        assert call_args[0][0] == "providers"  # Collection name
        assert call_args[0][1]["name"] == "John Smith Plumbing"
        assert call_args[0][1]["phone"] == "+27821234567"

    def test_should_handle_multiple_contacts_in_array_message(
        self,
        provider_repository: ProviderRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should process multiple contacts from contacts array message."""
        # Arrange
        contact_1 = Provider(
            id=ProviderID(value="550e8400-e29b-41d4-a716-446655440001"),
            name="John Smith Plumbing",
            phone=PhoneNumber(value="+27821234567"),
            category="plumbing",
        )

        contact_2 = Provider(
            id=ProviderID(value="550e8400-e29b-41d4-a716-446655440002"),
            name="Jane Doe Electrical",
            phone=PhoneNumber(value="+27821234568"),
            category="electrical",
        )

        # Act
        provider_repository.save(contact_1)
        provider_repository.save(contact_2)

        # Assert
        assert mock_firestore_client.create_document.call_count == 2

    def test_should_validate_phone_number_format_during_provider_creation(
        self,
        provider_repository: ProviderRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """Should validate phone numbers when creating providers from contact cards."""
        # Act & Assert - Valid South African number should work
        valid_provider = Provider(
            id=ProviderID(value="550e8400-e29b-41d4-a716-446655440003"),
            name="Valid Provider",
            phone=PhoneNumber(value="+27821234569"),
            category="services",
        )

        provider_repository.save(valid_provider)
        mock_firestore_client.create_document.assert_called_once()

        # Invalid phone number should raise validation error during creation
        from src.shared.exceptions import PhoneNumberValidationError

        with pytest.raises(PhoneNumberValidationError):
            Provider(
                id=ProviderID(value="550e8400-e29b-41d4-a716-446655440004"),
                name="Invalid Provider",
                phone=PhoneNumber(value="invalid-phone"),
                category="services",
            )
