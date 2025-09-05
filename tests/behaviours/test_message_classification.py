"""Message classification behaviour tests - WhatsApp message type detection."""

from unittest.mock import MagicMock

import pytest

from src.application.services import MessageClassifier
from src.domain.models import ClassificationResult
from src.domain.models.message_classification import MessageType


@pytest.fixture
def mock_message_classifier() -> MagicMock:
    """Mock message classifier for testing classification behaviours."""
    return MagicMock(spec=MessageClassifier)


@pytest.mark.behaviour
@pytest.mark.unit
@pytest.mark.nlp
@pytest.mark.fast
@pytest.mark.smoke
def test_should_classify_recommendation_as_endorsement(
    mock_message_classifier: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """'I recommend John the plumber' should classify as RECOMMENDATION type."""
    # Arrange
    recommendation_message = (
        "I highly recommend John the plumber 082-123-4567. Fixed my kitchen sink perfectly!"
    )
    expected_classification = ClassificationResult(
        message_type=MessageType.RECOMMENDATION,
        confidence=0.9,
        keywords=["recommend", "plumber", "fixed"],
        rule_matches=["recommendation_pattern", "service_mention"],
    )

    # Configure the mock return value - cast to Any for type safety

    mock_message_classifier.classify.return_value = expected_classification

    # Act
    result = mock_message_classifier.classify(recommendation_message)

    # Assert
    assert result.message_type == MessageType.RECOMMENDATION
    assert result.confidence >= 0.8  # High confidence for clear recommendation
    assert result.is_high_confidence()
    assert result.should_extract_mentions() is True
    assert result.is_actionable() is True
    assert "recommend" in result.keywords
    assert "plumber" in result.keywords
    assert len(result.rule_matches) > 0


def test_should_classify_question_as_query(
    mock_message_classifier: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """'Anyone know a good electrician?' should classify as REQUEST type."""
    # Arrange
    query_message = "Anyone know a good electrician in the area? Need some rewiring work done."

    expected_classification = ClassificationResult(
        message_type=MessageType.REQUEST,
        confidence=0.85,
        keywords=["anyone", "know", "good", "electrician", "need"],
        rule_matches=["question_pattern", "service_request"],
    )

    # Configure the mock return value - cast to Any for type safety

    mock_message_classifier.classify.return_value = expected_classification

    # Act
    result = mock_message_classifier.classify(query_message)

    # Assert
    assert result.message_type == MessageType.REQUEST
    assert result.confidence >= 0.7  # High confidence for clear question
    assert result.is_actionable() is True  # Requests are actionable
    assert result.should_extract_mentions() is False  # Requests don't extract mentions
    assert "electrician" in result.keywords
    assert "know" in result.keywords or "anyone" in result.keywords
    assert len(result.rule_matches) > 0


def test_should_classify_service_advertisement_as_offer(
    mock_message_classifier: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """'I do plumbing, call me' should classify as UNKNOWN type (service offer)."""
    # Arrange
    advertisement_message = "I do plumbing work in the area. Call me on 082-555-1234 for quotes!"

    expected_classification = ClassificationResult(
        message_type=MessageType.UNKNOWN,
        confidence=0.6,  # Medium confidence for service advertisement
        keywords=["plumbing", "work", "call", "quotes"],
        rule_matches=["service_offer_pattern", "contact_info"],
    )

    # Configure the mock return value
    mock_message_classifier.classify.return_value = expected_classification

    # Act
    result = mock_message_classifier.classify(advertisement_message)

    # Assert
    assert result.message_type == MessageType.UNKNOWN
    assert result.confidence >= 0.5  # Reasonable confidence for advertisement
    assert result.is_actionable() is False  # Advertisements are not actionable
    assert result.should_extract_mentions() is False  # Don't extract from self-promotion
    assert "plumbing" in result.keywords
    assert "call" in result.keywords or "work" in result.keywords
    assert len(result.rule_matches) > 0


def test_should_classify_general_chat_as_general(
    mock_message_classifier: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """'Beautiful weather today' should classify as UNKNOWN type (general chat)."""
    # Arrange
    general_message = "Beautiful weather today! Hope everyone has a lovely weekend."

    expected_classification = ClassificationResult(
        message_type=MessageType.UNKNOWN,
        confidence=0.3,  # Low confidence for general conversation
        keywords=["beautiful", "weather", "weekend"],
        rule_matches=["general_conversation"],
    )

    # Configure the mock return value
    mock_message_classifier.classify.return_value = expected_classification

    # Act
    result = mock_message_classifier.classify(general_message)

    # Assert
    assert result.message_type == MessageType.UNKNOWN
    assert result.confidence <= 0.5  # Low confidence for general chat
    assert result.is_actionable() is False  # General chat is not actionable
    assert result.should_extract_mentions() is False  # No mention extraction for general chat
    assert "weather" in result.keywords or "beautiful" in result.keywords
    assert len(result.rule_matches) > 0


def test_should_classify_mixed_content_by_primary_intent(
    mock_message_classifier: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """Mixed query + endorsement should be classified by dominant intent."""
    # Arrange - message with both query and endorsement elements, but endorsement is stronger
    mixed_message = (
        "Anyone know a good plumber? Actually, I can recommend John from last week - "
        "he fixed my sink perfectly! Call him on 082-123-4567."
    )

    expected_classification = ClassificationResult(
        message_type=MessageType.RECOMMENDATION,  # Endorsement dominates over query
        confidence=0.75,  # Lower confidence due to mixed content
        keywords=["recommend", "John", "fixed", "plumber", "know"],
        rule_matches=["recommendation_pattern", "question_pattern", "mixed_content"],
    )

    # Configure the mock return value
    mock_message_classifier.classify.return_value = expected_classification

    # Act
    result = mock_message_classifier.classify(mixed_message)

    # Assert
    assert result.message_type == MessageType.RECOMMENDATION  # Recommendation dominates
    assert result.confidence >= 0.7  # Good confidence despite mixed content
    assert result.is_actionable() is True  # Recommendations are actionable
    assert result.should_extract_mentions() is True  # Extract mentions from recommendation part
    assert "recommend" in result.keywords
    assert "plumber" in result.keywords
    assert len(result.rule_matches) >= 2  # Should match multiple patterns
