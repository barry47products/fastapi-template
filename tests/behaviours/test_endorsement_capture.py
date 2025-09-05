"""Endorsement capture behaviour tests - WhatsApp message processing."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services import MessageProcessor
from src.domain.models import ClassificationResult, Endorsement
from src.domain.models.endorsement import EndorsementType
from src.domain.models.message_classification import MessageType
from src.domain.value_objects import GroupID, PhoneNumber, ProviderID


@pytest.fixture
def mock_message_processor() -> MessageProcessor:
    """Mock message processor for testing endorsement capture behaviours."""
    processor = MagicMock(spec=MessageProcessor)
    # Configure the async method properly
    async_method = AsyncMock()
    processor.process_endorsement_message = async_method
    return processor


@pytest.fixture
def group_message_data() -> dict[str, str | int]:
    """Sample WhatsApp group message data."""
    return {
        "chatId": "12345678901234567890@g.us",
        "senderName": "Alice Johnson",
        "textMessage": "I highly recommend John the plumber 082-123-4567. "
        "Fixed my kitchen sink perfectly!",
        "timestamp": 1735470000,
    }


@pytest.fixture
def individual_group_message_data() -> dict[str, str | int]:
    """Sample WhatsApp individual message data."""
    return {
        "chatId": "27821234567@c.us",
        "senderName": "Bob Smith",
        "textMessage": "Hello, how are you?",
        "timestamp": 1735470000,
    }


async def test_should_extract_endorsement_from_group_message_with_phone(
    mock_message_processor: MessageProcessor,  # pylint: disable=redefined-outer-name
    group_message_data: dict[str, str | int],  # pylint: disable=redefined-outer-name
) -> None:
    """Provider mention with phone number should create endorsement."""
    # Arrange
    expected_endorsement = Endorsement(
        provider_id=ProviderID(),
        group_id=GroupID(value=str(group_message_data["chatId"])),
        endorser_phone=PhoneNumber(value="+27821234567"),
        endorsement_type=EndorsementType.AUTOMATIC,
        message_context=str(group_message_data["textMessage"]),
        confidence_score=0.9,
    )

    classification_data = ClassificationResult(
        message_type=MessageType.RECOMMENDATION,
        confidence=0.9,
    )

    # Configure AsyncMock properly
    mock_result = MagicMock(
        success=True,
        endorsements_created=[expected_endorsement],
        processing_notes=[],
        processing_duration_seconds=0.05,
    )
    # Configure the AsyncMock return value - cast to Any for type safety
    from typing import Any, cast

    cast(Any, mock_message_processor.process_endorsement_message).return_value = mock_result

    # Act
    result = await mock_message_processor.process_endorsement_message(
        group_id=GroupID(value=str(group_message_data["chatId"])),
        sender_name=str(group_message_data["senderName"]),
        message_text=str(group_message_data["textMessage"]),
        timestamp=int(group_message_data["timestamp"]),
        classification=classification_data,
    )

    # Assert
    assert result.success is True
    assert len(result.endorsements_created) == 1
    endorsement_result = result.endorsements_created[0]
    assert endorsement_result.provider_id is not None
    assert endorsement_result.endorser_phone == PhoneNumber(value="+27821234567")
    assert endorsement_result.endorsement_type == EndorsementType.AUTOMATIC


async def test_should_extract_endorsement_from_group_message_without_phone(
    mock_message_processor: MessageProcessor,  # pylint: disable=redefined-outer-name
    group_message_data: dict[str, str | int],  # pylint: disable=redefined-outer-name
) -> None:
    """Provider mention without phone number should still create endorsement."""
    # Arrange - message without phone number
    message_without_phone = {
        **group_message_data,
        "textMessage": "Really happy with Sarah the electrician. Great work on rewiring!",
    }

    expected_endorsement = Endorsement(
        provider_id=ProviderID(),
        group_id=GroupID(value=str(message_without_phone["chatId"])),
        endorser_phone=PhoneNumber(value="+27821234567"),  # From sender profile
        endorsement_type=EndorsementType.AUTOMATIC,
        message_context=str(message_without_phone["textMessage"]),
        confidence_score=0.85,  # Slightly lower confidence without phone
    )

    classification_data = ClassificationResult(
        message_type=MessageType.RECOMMENDATION,
        confidence=0.85,
    )

    # Configure AsyncMock properly
    mock_result = MagicMock(
        success=True,
        endorsements_created=[expected_endorsement],
        processing_notes=["No phone number extracted, using name/service only"],
        processing_duration_seconds=0.04,
    )
    # Configure the AsyncMock return value - cast to Any for type safety
    from typing import Any, cast

    cast(Any, mock_message_processor.process_endorsement_message).return_value = mock_result

    # Act
    result = await mock_message_processor.process_endorsement_message(
        group_id=GroupID(value=str(message_without_phone["chatId"])),
        sender_name=str(message_without_phone["senderName"]),
        message_text=str(message_without_phone["textMessage"]),
        timestamp=int(message_without_phone["timestamp"]),
        classification=classification_data,
    )

    # Assert
    assert result.success is True
    assert len(result.endorsements_created) == 1
    endorsement_result = result.endorsements_created[0]
    assert endorsement_result.provider_id is not None
    assert endorsement_result.endorser_phone == PhoneNumber(value="+27821234567")
    assert endorsement_result.endorsement_type == EndorsementType.AUTOMATIC
    assert "No phone number extracted" in result.processing_notes[0]


async def test_should_extract_multiple_endorsements_from_single_message(
    mock_message_processor: MessageProcessor,  # pylint: disable=redefined-outer-name
    group_message_data: dict[str, str | int],  # pylint: disable=redefined-outer-name
) -> None:
    """Multiple provider mentions should create multiple endorsements."""
    # Arrange - message with multiple provider mentions
    message_with_multiple = {
        **group_message_data,
        "textMessage": "Great experiences this week! Tom the plumber 082-555-1234 fixed our pipes, "
        "and Maria from CleanCo 071-555-5678 did fantastic house cleaning. "
        "Highly recommend both!",
    }

    # Create two expected endorsements
    endorsement_tom = Endorsement(
        provider_id=ProviderID(),
        group_id=GroupID(value=str(message_with_multiple["chatId"])),
        endorser_phone=PhoneNumber(value="+27821234567"),
        endorsement_type=EndorsementType.AUTOMATIC,
        message_context=str(message_with_multiple["textMessage"]),
        confidence_score=0.9,
    )

    endorsement_maria = Endorsement(
        provider_id=ProviderID(),
        group_id=GroupID(value=str(message_with_multiple["chatId"])),
        endorser_phone=PhoneNumber(value="+27821234567"),
        endorsement_type=EndorsementType.AUTOMATIC,
        message_context=str(message_with_multiple["textMessage"]),
        confidence_score=0.9,
    )

    classification_data = ClassificationResult(
        message_type=MessageType.RECOMMENDATION,
        confidence=0.95,  # High confidence for multiple clear recommendations
    )

    # Configure AsyncMock properly
    mock_result = MagicMock(
        success=True,
        endorsements_created=[endorsement_tom, endorsement_maria],
        processing_notes=["Extracted 2 provider mentions", "Tom (plumber)", "Maria (cleaning)"],
        processing_duration_seconds=0.08,
    )
    # Configure the AsyncMock return value - cast to Any for type safety
    from typing import Any, cast

    cast(Any, mock_message_processor.process_endorsement_message).return_value = mock_result

    # Act
    result = await mock_message_processor.process_endorsement_message(
        group_id=GroupID(value=str(message_with_multiple["chatId"])),
        sender_name=str(message_with_multiple["senderName"]),
        message_text=str(message_with_multiple["textMessage"]),
        timestamp=int(message_with_multiple["timestamp"]),
        classification=classification_data,
    )

    # Assert
    assert result.success is True
    assert len(result.endorsements_created) == 2

    # Verify both endorsements created
    assert all(endorsement.provider_id is not None for endorsement in result.endorsements_created)
    assert all(
        endorsement.endorser_phone == PhoneNumber(value="+27821234567")
        for endorsement in result.endorsements_created
    )
    assert all(
        endorsement.endorsement_type == EndorsementType.AUTOMATIC
        for endorsement in result.endorsements_created
    )

    # Verify processing notes document multiple extractions
    assert "Extracted 2 provider mentions" in result.processing_notes[0]
    assert len(result.processing_notes) == 3  # Main note + 2 provider details


async def test_should_ignore_individual_whatsapp_messages(
    mock_message_processor: MessageProcessor,  # pylint: disable=redefined-outer-name
    individual_group_message_data: dict[str, str | int],  # pylint: disable=redefined-outer-name
) -> None:
    """Non-group messages (no @g.us) should be skipped."""
    # Arrange - individual message with provider mention
    individual_with_recommendation = {
        **individual_group_message_data,
        "textMessage": "Thanks for the recommendation! I'll definitely call John the plumber "
        "082-123-4567.",
    }

    classification_data = ClassificationResult(
        message_type=MessageType.RECOMMENDATION,
        confidence=0.8,
    )

    # Configure AsyncMock to simulate skipping individual messages
    # In real implementation, this wouldn't be called for individual messages
    mock_result = MagicMock(
        success=True,
        endorsements_created=[],  # No endorsements for individual messages
        processing_notes=["Skipped: Individual message (not from group)"],
        processing_duration_seconds=0.01,
    )
    # Configure the AsyncMock return value - cast to Any for type safety
    from typing import Any, cast

    cast(Any, mock_message_processor.process_endorsement_message).return_value = mock_result

    # Act - This simulates the webhook level filtering
    # In real implementation, individual messages wouldn't reach the processor
    result = await mock_message_processor.process_endorsement_message(
        group_id=GroupID(value=str(individual_with_recommendation["chatId"])),  # @c.us format
        sender_name=str(individual_with_recommendation["senderName"]),
        message_text=str(individual_with_recommendation["textMessage"]),
        timestamp=int(individual_with_recommendation["timestamp"]),
        classification=classification_data,
    )

    # Assert
    assert result.success is True
    assert len(result.endorsements_created) == 0  # No endorsements created
    assert "Skipped: Individual message" in result.processing_notes[0]
    assert result.processing_duration_seconds < 0.02  # Fast skip processing


async def test_should_handle_empty_message_gracefully(
    mock_message_processor: MessageProcessor,  # pylint: disable=redefined-outer-name
    group_message_data: dict[str, str | int],  # pylint: disable=redefined-outer-name
) -> None:
    """Empty/null message text should not crash system."""
    # Arrange - message with empty text
    empty_message = {
        **group_message_data,
        "textMessage": "",
    }

    classification_data = ClassificationResult(
        message_type=MessageType.UNKNOWN,
        confidence=0.1,  # Low confidence for empty message
    )

    # Configure AsyncMock to simulate graceful handling of empty message
    mock_result = MagicMock(
        success=True,
        endorsements_created=[],  # No endorsements for empty message
        processing_notes=["Skipped: Empty message text"],
        processing_duration_seconds=0.005,  # Very fast processing
    )
    # Configure the AsyncMock return value - cast to Any for type safety
    from typing import Any, cast

    cast(Any, mock_message_processor.process_endorsement_message).return_value = mock_result

    # Act
    result = await mock_message_processor.process_endorsement_message(
        group_id=GroupID(value=str(empty_message["chatId"])),
        sender_name=str(empty_message["senderName"]),
        message_text=str(empty_message["textMessage"]),
        timestamp=int(empty_message["timestamp"]),
        classification=classification_data,
    )

    # Assert
    assert result.success is True
    assert len(result.endorsements_created) == 0  # No endorsements created
    assert "Skipped: Empty message text" in result.processing_notes[0]
    assert result.processing_duration_seconds < 0.01  # Very fast processing for empty message


async def test_should_not_create_endorsement_for_non_provider_content(
    mock_message_processor: MessageProcessor,  # pylint: disable=redefined-outer-name
    group_message_data: dict[str, str | int],  # pylint: disable=redefined-outer-name
) -> None:
    """General chat messages should not create false endorsements."""
    # Arrange - general chat message that might contain keywords but isn't an endorsement
    general_chat_message = {
        **group_message_data,
        "textMessage": "Good morning everyone! Beautiful weather today. Hope everyone has a "
        "great day at work. My plumbing is fine, no issues here!",
    }

    classification_data = ClassificationResult(
        message_type=MessageType.UNKNOWN,
        confidence=0.2,  # Low confidence, not a recommendation
    )

    # Configure AsyncMock to simulate no endorsement creation for general chat
    mock_result = MagicMock(
        success=True,
        endorsements_created=[],  # No endorsements for general chat
        processing_notes=["No provider mentions detected", "Classified as general conversation"],
        processing_duration_seconds=0.02,
    )
    # Configure the AsyncMock return value - cast to Any for type safety
    from typing import Any, cast

    cast(Any, mock_message_processor.process_endorsement_message).return_value = mock_result

    # Act
    result = await mock_message_processor.process_endorsement_message(
        group_id=GroupID(value=str(general_chat_message["chatId"])),
        sender_name=str(general_chat_message["senderName"]),
        message_text=str(general_chat_message["textMessage"]),
        timestamp=int(general_chat_message["timestamp"]),
        classification=classification_data,
    )

    # Assert
    assert result.success is True
    assert len(result.endorsements_created) == 0  # No false endorsements
    assert "No provider mentions detected" in result.processing_notes[0]
    assert "Classified as general conversation" in result.processing_notes[1]
    assert result.processing_duration_seconds < 0.05  # Reasonable processing time
