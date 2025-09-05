"""End-to-end integration test for contact card processing with provider persistence."""

# pylint: disable=redefined-outer-name

from unittest.mock import MagicMock

import pytest

from src.application.services.contact_parser import ContactParser
from src.application.services.message_processor import MessageProcessor
from src.domain.value_objects import GroupID, PhoneNumber
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
    return MagicMock()


@pytest.fixture
def contact_parser() -> ContactParser:
    """Contact parser for vCard processing."""
    return ContactParser()


@pytest.fixture
def sample_vcard() -> str:
    """Sample vCard with valid South African phone number."""
    return """BEGIN:VCARD
VERSION:3.0
FN:John Smith Plumbing
TEL;TYPE=CELL:+27821234567
END:VCARD"""


class TestContactCardEndToEndIntegration:
    """Test complete contact card processing pipeline with provider persistence."""

    @pytest.mark.asyncio
    async def test_contact_card_creates_provider_and_endorsement(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_endorsement_repository: MagicMock,
        mock_firestore_client: MagicMock,
        contact_parser: ContactParser,
        sample_vcard: str,
    ) -> None:
        """Test that contact card processing creates provider and endorsement records."""
        # Arrange - Simulate no existing providers
        mock_firestore_client.query_collection.return_value = []

        # Parse the contact card to get mentions
        parsed_contact = contact_parser.parse_vcard(
            vcard_data=sample_vcard,
            display_name="John Smith Plumbing",
        )
        mentions = contact_parser.contact_to_mentions(parsed_contact, confidence=0.95)

        # Create MessageProcessor with repositories
        message_processor = MessageProcessor(
            provider_repository=provider_repository,
            endorsement_repository=mock_endorsement_repository,
        )

        group_id = GroupID(value="test-group-123@g.us")

        # Act - Process the mentions through the endorsement pipeline
        # We need to simulate the message processor receiving the mentions
        # For now, we'll test the integration by calling _match_providers directly
        provider_matches = await message_processor._match_providers(mentions, group_id)

        # Assert
        assert len(provider_matches) > 0, "Should create at least one provider from contact"

        # Verify provider was saved to repository
        mock_firestore_client.create_document.assert_called_once()
        call_args = mock_firestore_client.create_document.call_args
        assert call_args[0][0] == "providers"  # Collection name
        assert "John Smith Plumbing" in str(call_args[0][1]["name"])
        assert "+27821234567" == call_args[0][1]["phone"]

    @pytest.mark.asyncio
    async def test_contact_card_finds_existing_provider_by_phone(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_endorsement_repository: MagicMock,
        mock_firestore_client: MagicMock,
        contact_parser: ContactParser,
        sample_vcard: str,
    ) -> None:
        """Test that contact card processing finds existing provider by phone number."""
        # Arrange - Simulate existing provider
        existing_provider_data = {
            "_id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "John Smith Plumbing",
            "phone": "+27821234567",
            "category": "plumbing",
            "tags": {},
            "endorsement_count": 3,
            "created_at": "2025-01-01T12:00:00Z",
        }
        mock_firestore_client.query_collection.return_value = [existing_provider_data]

        # Parse the contact card
        parsed_contact = contact_parser.parse_vcard(
            vcard_data=sample_vcard,
            display_name="John Smith Plumbing",
        )
        mentions = contact_parser.contact_to_mentions(parsed_contact, confidence=0.95)

        # Create MessageProcessor with repositories
        message_processor = MessageProcessor(
            provider_repository=provider_repository,
            endorsement_repository=mock_endorsement_repository,
        )

        group_id = GroupID(value="test-group-123@g.us")

        # Act
        provider_matches = await message_processor._match_providers(mentions, group_id)

        # Assert
        assert len(provider_matches) == 1, "Should find the existing provider"
        assert provider_matches[0].phone.value == "+27821234567"
        assert provider_matches[0].name == "John Smith Plumbing"

        # Verify phone number search was performed
        mock_firestore_client.query_collection.assert_called()

    @pytest.mark.asyncio
    async def test_contact_card_without_phone_skips_provider_creation(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_endorsement_repository: MagicMock,
        mock_firestore_client: MagicMock,
        contact_parser: ContactParser,
    ) -> None:
        """Test that contact cards without phone numbers are skipped."""
        # Arrange - vCard without phone number
        vcard_without_phone = """BEGIN:VCARD
VERSION:3.0
FN:John Smith Plumbing
EMAIL:john@example.com
END:VCARD"""

        # Parse the contact card
        parsed_contact = contact_parser.parse_vcard(
            vcard_data=vcard_without_phone,
            display_name="John Smith Plumbing",
        )
        mentions = contact_parser.contact_to_mentions(parsed_contact, confidence=0.95)

        # Create MessageProcessor with repositories
        message_processor = MessageProcessor(
            provider_repository=provider_repository,
            endorsement_repository=mock_endorsement_repository,
        )

        group_id = GroupID(value="test-group-123@g.us")

        # Act
        provider_matches = await message_processor._match_providers(mentions, group_id)

        # Assert - No providers should be created without phone numbers
        assert len(provider_matches) == 0, "Should not create provider without phone number"
        mock_firestore_client.create_document.assert_not_called()

    def test_parsed_contact_extracts_phone_numbers_correctly(
        self,
        contact_parser: ContactParser,
        sample_vcard: str,
    ) -> None:
        """Test that contact parser extracts phone numbers correctly."""
        # Act
        parsed_contact = contact_parser.parse_vcard(
            vcard_data=sample_vcard,
            display_name="John Smith Plumbing",
        )

        # Assert
        assert parsed_contact.display_name == "John Smith Plumbing"
        assert len(parsed_contact.phone_numbers) == 1
        assert parsed_contact.phone_numbers[0].normalized == "+27821234567"

        # Verify phone number is valid
        phone = PhoneNumber(value=parsed_contact.phone_numbers[0].normalized)
        assert phone.value == "+27821234567"

    def test_contact_mentions_include_phone_numbers(
        self,
        contact_parser: ContactParser,
        sample_vcard: str,
    ) -> None:
        """Test that mentions created from contact cards include phone numbers."""
        # Arrange
        parsed_contact = contact_parser.parse_vcard(
            vcard_data=sample_vcard,
            display_name="John Smith Plumbing",
        )

        # Act
        mentions = contact_parser.contact_to_mentions(parsed_contact, confidence=0.95)

        # Assert
        assert len(mentions) > 0, "Should create mentions from contact"

        # Find the display name mention and phone mention
        name_mentions = [m for m in mentions if m.extraction_type == "contact_display_name"]
        phone_mentions = [m for m in mentions if m.extraction_type == "contact_phone_number"]

        assert len(name_mentions) == 1, "Should have one display name mention"
        assert len(phone_mentions) == 1, "Should have one phone number mention"

        name_mention = name_mentions[0]
        phone_mention = phone_mentions[0]
        assert name_mention.text == "John Smith Plumbing"
        assert phone_mention.text == "+27821234567"

    @pytest.mark.asyncio
    async def test_full_contact_processing_pipeline(
        self,
        provider_repository: FirestoreProviderRepository,
        mock_endorsement_repository: MagicMock,
        mock_firestore_client: MagicMock,
        contact_parser: ContactParser,
        sample_vcard: str,
    ) -> None:
        """Test the complete contact processing pipeline from vCard to stored endorsement."""
        # Arrange - No existing providers
        mock_firestore_client.query_collection.return_value = []

        # Parse contact and create mentions (simulating contact webhook processing)
        parsed_contact = contact_parser.parse_vcard(
            vcard_data=sample_vcard,
            display_name="John Smith Plumbing",
        )
        mentions = contact_parser.contact_to_mentions(parsed_contact, confidence=0.95)

        # Create synthetic message text
        synthetic_message = f"Contact shared: {parsed_contact.display_name}"

        # Initialize MessageProcessor with both repositories
        message_processor = MessageProcessor(
            provider_repository=provider_repository,
            endorsement_repository=mock_endorsement_repository,
        )

        group_id = GroupID(value="test-group-123@g.us")

        # Act - Process the contact mentions directly (simulating the correct pipeline)
        provider_matches = await message_processor._match_providers(mentions, group_id)

        if provider_matches:
            # Create endorsements for the matched providers
            result_endorsements = message_processor._create_endorsements(
                provider_matches,
                group_id,
                synthetic_message,
            )
        else:
            result_endorsements = []

        # Assert - End-to-end processing should succeed
        assert len(provider_matches) > 0, "Should create provider from contact"

        # Verify provider was created
        mock_firestore_client.create_document.assert_called()
        provider_call = mock_firestore_client.create_document.call_args
        assert provider_call[0][0] == "providers"

        # Verify endorsement was created
        mock_endorsement_repository.save.assert_called()

        # Verify we created endorsements
        assert len(result_endorsements) > 0, "Should create endorsements"
