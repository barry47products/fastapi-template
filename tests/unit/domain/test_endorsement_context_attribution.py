"""Tests for context attribution system functionality."""

from datetime import datetime, UTC

import pytest

from src.domain.models import Endorsement, EndorsementType
from src.domain.value_objects import EndorsementID, GroupID, PhoneNumber, ProviderID
from src.shared.exceptions import EndorsementValidationError


class TestEndorsementContextAttribution:
    """Test context attribution fields in Endorsement model."""

    def test_should_create_endorsement_with_request_context_fields(self) -> None:
        """Test creating endorsement with request-response correlation fields."""
        endorsement = Endorsement(
            id=EndorsementID(),
            provider_id=ProviderID(),
            group_id=GroupID(value="27123456789-group@g.us"),
            endorser_phone=PhoneNumber(value="+27123456789"),
            endorsement_type=EndorsementType.MANUAL,
            message_context="Contact card shared for plumber request",
            confidence_score=0.95,
            request_message_id="quoted_message_123",
            response_delay_seconds=120,
            attribution_confidence=0.9,
        )

        assert endorsement.request_message_id == "quoted_message_123"
        assert endorsement.response_delay_seconds == 120
        assert endorsement.attribution_confidence == 0.9

    def test_should_create_endorsement_without_context_fields(self) -> None:
        """Test creating endorsement without optional context fields."""
        endorsement = Endorsement(
            id=EndorsementID(),
            provider_id=ProviderID(),
            group_id=GroupID(value="27123456789-group@g.us"),
            endorser_phone=PhoneNumber(value="+27123456789"),
            endorsement_type=EndorsementType.MANUAL,
            message_context="Direct contact card share",
            confidence_score=0.8,
        )

        assert endorsement.request_message_id is None
        assert endorsement.response_delay_seconds is None
        assert endorsement.attribution_confidence == 0.0

    def test_should_validate_attribution_confidence_range(self) -> None:
        """Test attribution confidence must be between 0.0 and 1.0."""
        with pytest.raises(EndorsementValidationError) as exc_info:
            Endorsement(
                id=EndorsementID(),
                provider_id=ProviderID(),
                group_id=GroupID(value="27123456789-group@g.us"),
                endorser_phone=PhoneNumber(value="+27123456789"),
                endorsement_type=EndorsementType.MANUAL,
                message_context="Test message",
                attribution_confidence=1.5,
            )

        assert "Attribution confidence must be between 0.0 and 1.0" in str(exc_info.value)

    def test_should_validate_negative_attribution_confidence(self) -> None:
        """Test negative attribution confidence raises validation error."""
        with pytest.raises(EndorsementValidationError) as exc_info:
            Endorsement(
                id=EndorsementID(),
                provider_id=ProviderID(),
                group_id=GroupID(value="27123456789-group@g.us"),
                endorser_phone=PhoneNumber(value="+27123456789"),
                endorsement_type=EndorsementType.MANUAL,
                message_context="Test message",
                attribution_confidence=-0.1,
            )

        assert "Attribution confidence must be between 0.0 and 1.0" in str(exc_info.value)

    def test_should_validate_response_delay_is_positive(self) -> None:
        """Test response delay must be positive when provided."""
        with pytest.raises(EndorsementValidationError) as exc_info:
            Endorsement(
                id=EndorsementID(),
                provider_id=ProviderID(),
                group_id=GroupID(value="27123456789-group@g.us"),
                endorser_phone=PhoneNumber(value="+27123456789"),
                endorsement_type=EndorsementType.MANUAL,
                message_context="Test message",
                response_delay_seconds=-30,
            )

        assert "Response delay must be positive" in str(exc_info.value)

    def test_should_allow_zero_response_delay(self) -> None:
        """Test zero response delay is allowed (immediate response)."""
        endorsement = Endorsement(
            id=EndorsementID(),
            provider_id=ProviderID(),
            group_id=GroupID(value="27123456789-group@g.us"),
            endorser_phone=PhoneNumber(value="+27123456789"),
            endorsement_type=EndorsementType.MANUAL,
            message_context="Immediate contact share",
            response_delay_seconds=0,
        )

        assert endorsement.response_delay_seconds == 0

    def test_should_check_if_endorsement_has_context_attribution(self) -> None:
        """Test helper method to check if endorsement has context attribution."""
        # With context attribution
        with_context = Endorsement(
            id=EndorsementID(),
            provider_id=ProviderID(),
            group_id=GroupID(value="27123456789-group@g.us"),
            endorser_phone=PhoneNumber(value="+27123456789"),
            endorsement_type=EndorsementType.MANUAL,
            message_context="Response to request",
            request_message_id="msg_123",
            attribution_confidence=0.8,
        )

        # Without context attribution
        without_context = Endorsement(
            id=EndorsementID(),
            provider_id=ProviderID(),
            group_id=GroupID(value="27123456789-group@g.us"),
            endorser_phone=PhoneNumber(value="+27123456789"),
            endorsement_type=EndorsementType.MANUAL,
            message_context="Standalone share",
        )

        assert with_context.has_request_context() is True
        assert without_context.has_request_context() is False

    def test_should_check_if_endorsement_is_high_confidence_attribution(self) -> None:
        """Test helper method to check high confidence context attribution."""
        high_confidence = Endorsement(
            id=EndorsementID(),
            provider_id=ProviderID(),
            group_id=GroupID(value="27123456789-group@g.us"),
            endorser_phone=PhoneNumber(value="+27123456789"),
            endorsement_type=EndorsementType.MANUAL,
            message_context="Response to request",
            request_message_id="msg_123",
            attribution_confidence=0.9,
        )

        low_confidence = Endorsement(
            id=EndorsementID(),
            provider_id=ProviderID(),
            group_id=GroupID(value="27123456789-group@g.us"),
            endorser_phone=PhoneNumber(value="+27123456789"),
            endorsement_type=EndorsementType.MANUAL,
            message_context="Response to request",
            request_message_id="msg_123",
            attribution_confidence=0.4,
        )

        assert high_confidence.is_high_confidence_attribution() is True
        assert low_confidence.is_high_confidence_attribution() is False

    def test_should_include_context_fields_in_postgres_data(self) -> None:
        """Test context fields are included in PostgreSQL data conversion."""
        endorsement = Endorsement(
            id=EndorsementID(),
            provider_id=ProviderID(),
            group_id=GroupID(value="27123456789-group@g.us"),
            endorser_phone=PhoneNumber(value="+27123456789"),
            endorsement_type=EndorsementType.MANUAL,
            message_context="Context attribution test",
            request_message_id="req_456",
            response_delay_seconds=180,
            attribution_confidence=0.85,
        )

        postgres_data = endorsement.to_postgres_data()

        assert postgres_data["request_message_id"] == "req_456"
        assert postgres_data["response_delay_seconds"] == 180
        assert postgres_data["attribution_confidence"] == 0.85

    def test_should_create_endorsement_from_postgres_data_with_context(self) -> None:
        """Test creating endorsement from PostgreSQL data with context fields."""
        endorsement_id = EndorsementID()
        provider_id = ProviderID()

        data = {
            "id": str(endorsement_id),
            "provider_id": str(provider_id),
            "group_id": "27123456789-group@g.us",
            "endorser_phone": "+27123456789",
            "endorsement_type": "MANUAL",
            "message_context": "PostgreSQL context test",
            "confidence_score": 0.9,
            "status": "ACTIVE",
            "created_at": datetime.now(UTC),
            "request_message_id": "postgres_req_789",
            "response_delay_seconds": 240,
            "attribution_confidence": 0.75,
        }

        endorsement = Endorsement.from_postgres_data(data)

        assert endorsement.request_message_id == "postgres_req_789"
        assert endorsement.response_delay_seconds == 240
        assert endorsement.attribution_confidence == 0.75
