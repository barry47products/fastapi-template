"""Tests for context attribution service functionality."""

from datetime import datetime, timedelta, UTC

import pytest

from src.application.services.context_attribution import (
    AttributionResult,
    ContextAttributionService,
    TemporalPattern,
)
from src.domain.value_objects import GroupID
from src.interfaces.api.schemas.webhooks import GreenAPIMessageWebhook
from src.shared.exceptions import ContextAttributionException


class TestContextAttributionService:
    """Test context attribution service logic."""

    service: ContextAttributionService  # Type annotation for MyPy

    def setup_method(self) -> None:
        """Set up test dependencies."""
        self.service = ContextAttributionService()

    def test_should_identify_quoted_message_attribution(self) -> None:
        """Test direct quoted message attribution with high confidence."""
        quoted_webhook = self._create_quoted_message_webhook(
            quoted_message_id="original_request_123",
            quoted_participant="27123456789-user@c.us",
            reply_text="Here is the contact card",
        )

        result = self.service.analyze_message_context(
            webhook=quoted_webhook,
            group_id=GroupID(value="27123456789-group@g.us"),
            _timestamp=int(datetime.now(UTC).timestamp()),
        )

        assert result.attribution_confidence >= 0.9
        assert result.request_message_id == "original_request_123"
        assert result.attribution_type == "direct_quote"
        assert result.temporal_pattern == TemporalPattern.IMMEDIATE

    def test_should_calculate_temporal_proximity_with_stored_requests(self) -> None:
        """Test temporal proximity analysis when request messages are stored."""
        # Mock stored request message from 2 minutes ago
        request_timestamp = datetime.now(UTC) - timedelta(minutes=2)
        stored_requests = [
            {
                "message_id": "stored_request_456",
                "timestamp": int(request_timestamp.timestamp()),
                "sender": "27123456789-user@c.us",
                "content": "Need a plumber urgently",
                "message_type": "query",
            },
        ]

        contact_webhook = self._create_contact_message_webhook()
        current_timestamp = int(datetime.now(UTC).timestamp())

        result = self.service.analyze_temporal_proximity(
            webhook=contact_webhook,
            group_id=GroupID(value="27123456789-group@g.us"),
            timestamp=current_timestamp,
            recent_requests=stored_requests,
        )

        assert result.attribution_confidence >= 0.7
        assert result.request_message_id == "stored_request_456"
        assert result.response_delay_seconds == 120  # 2 minutes
        assert result.attribution_type == "temporal_proximity"
        assert result.temporal_pattern == TemporalPattern.NEAR_TERM

    def test_should_reject_attribution_beyond_time_window(self) -> None:
        """Test that messages outside time window get low confidence."""
        # Mock stored request message from 1 hour ago (beyond threshold)
        request_timestamp = datetime.now(UTC) - timedelta(hours=1)
        stored_requests = [
            {
                "message_id": "old_request_789",
                "timestamp": int(request_timestamp.timestamp()),
                "sender": "27123456789-user@c.us",
                "content": "Need a plumber",
                "message_type": "query",
            },
        ]

        contact_webhook = self._create_contact_message_webhook()
        current_timestamp = int(datetime.now(UTC).timestamp())

        result = self.service.analyze_temporal_proximity(
            webhook=contact_webhook,
            group_id=GroupID(value="27123456789-group@g.us"),
            timestamp=current_timestamp,
            recent_requests=stored_requests,
        )

        assert result.attribution_confidence < 0.3
        assert result.temporal_pattern == TemporalPattern.DISTANT

    def test_should_handle_multiple_candidate_requests(self) -> None:
        """Test selecting best match from multiple recent requests."""
        base_time = datetime.now(UTC)
        stored_requests = [
            # Most recent and relevant
            {
                "message_id": "best_match",
                "timestamp": int((base_time - timedelta(minutes=1)).timestamp()),
                "sender": "27123456789-user@c.us",
                "content": "Looking for plumber contact",
                "message_type": "query",
            },
            # Older request
            {
                "message_id": "older_request",
                "timestamp": int((base_time - timedelta(minutes=10)).timestamp()),
                "sender": "27987654321-user@c.us",
                "content": "Need electrician",
                "message_type": "query",
            },
        ]

        contact_webhook = self._create_contact_message_webhook()
        current_timestamp = int(base_time.timestamp())

        result = self.service.analyze_temporal_proximity(
            webhook=contact_webhook,
            group_id=GroupID(value="27123456789-group@g.us"),
            timestamp=current_timestamp,
            recent_requests=stored_requests,
        )

        assert result.request_message_id == "best_match"
        assert result.response_delay_seconds == 60  # 1 minute
        assert result.attribution_confidence >= 0.7

    def test_should_apply_sender_behaviour_patterns(self) -> None:
        """Test sender behaviour pattern recognition improves confidence."""
        # Same sender who made request now shares contact
        request_sender = "27123456789-user@c.us"
        stored_requests = [
            {
                "message_id": "sender_request",
                "timestamp": int((datetime.now(UTC) - timedelta(minutes=3)).timestamp()),
                "sender": request_sender,
                "content": "Does anyone know a good plumber?",
                "message_type": "query",
            },
        ]

        # Contact shared by different user (helpful community member)
        contact_webhook = self._create_contact_message_webhook(
            sender_id="27987654321-user@c.us",
            sender_name="Helpful Neighbour",
        )

        result = self.service.analyze_temporal_proximity(
            webhook=contact_webhook,
            group_id=GroupID(value="27123456789-group@g.us"),
            timestamp=int(datetime.now(UTC).timestamp()),
            recent_requests=stored_requests,
        )

        # Should have high confidence due to helpful response pattern
        assert result.attribution_confidence >= 0.7
        assert result.sender_pattern == "community_response"

    def test_should_handle_no_recent_requests(self) -> None:
        """Test behaviour when no recent requests are available."""
        contact_webhook = self._create_contact_message_webhook()

        result = self.service.analyze_temporal_proximity(
            webhook=contact_webhook,
            group_id=GroupID(value="27123456789-group@g.us"),
            timestamp=int(datetime.now(UTC).timestamp()),
            recent_requests=[],
        )

        assert result.attribution_confidence == 0.0
        assert result.request_message_id is None
        assert result.attribution_type == "standalone"
        assert result.temporal_pattern == TemporalPattern.NONE

    def test_should_validate_input_parameters(self) -> None:
        """Test input validation for context attribution."""
        with pytest.raises(ContextAttributionException) as exc_info:
            self.service.analyze_message_context(
                webhook=None,  # type: ignore
                group_id=GroupID(value="27123456789-group@g.us"),
                _timestamp=int(datetime.now(UTC).timestamp()),
            )

        assert "Webhook message is required" in str(exc_info.value)

    def test_should_handle_service_failures_gracefully(self) -> None:
        """Test graceful handling of internal service failures."""
        from unittest.mock import patch

        # Mock internal method to simulate failure
        service = ContextAttributionService()

        with patch.object(
            service,
            "_find_best_temporal_match",
            side_effect=Exception("Simulated failure"),
        ):
            stored_requests = [
                {
                    "message_id": "test_request",
                    "timestamp": int((datetime.now(UTC) - timedelta(minutes=1)).timestamp()),
                    "sender": "27123456789-user@c.us",
                    "content": "Need help",
                    "message_type": "query",
                },
            ]

            contact_webhook = self._create_contact_message_webhook()

            # Should not raise exception but return error fallback result
            result = service.analyze_temporal_proximity(
                webhook=contact_webhook,
                group_id=GroupID(value="27123456789-group@g.us"),
                timestamp=int(datetime.now(UTC).timestamp()),
                recent_requests=stored_requests,
            )

            # The error should be caught and handled gracefully
            assert result.attribution_confidence == 0.0
            assert result.attribution_type == "standalone"

    def _create_quoted_message_webhook(
        self,
        quoted_message_id: str,
        quoted_participant: str,
        reply_text: str,
    ) -> GreenAPIMessageWebhook:
        """Create a quoted message webhook for testing."""
        from src.interfaces.api.schemas.webhooks import (
            ExtendedTextMessageContent,
            InstanceData,
            MessageData,
            SenderData,
        )

        return GreenAPIMessageWebhook(
            typeWebhook="incomingMessageReceived",
            instanceData=InstanceData(
                idInstance=123,
                wid="27123456789@c.us",
                typeInstance="whatsapp",
            ),
            timestamp=int(datetime.now(UTC).timestamp()),
            idMessage="msg_quoted_123",
            senderData=SenderData(
                chatId="27123456789-group@g.us",
                sender="27987654321-user@c.us",
                chatName="Test Group",
                senderName="Test User",
            ),
            messageData=MessageData(
                typeMessage="quotedMessage",
                extendedTextMessageData=ExtendedTextMessageContent(
                    text=reply_text,
                    stanzaId=quoted_message_id,
                    participant=quoted_participant,
                ),
            ),
        )

    def _create_contact_message_webhook(
        self,
        sender_id: str = "27987654321-user@c.us",
        sender_name: str = "Contact Sharer",
    ) -> GreenAPIMessageWebhook:
        """Create a contact message webhook for testing."""
        from src.interfaces.api.schemas.webhooks import (
            ContactMessageContent,
            InstanceData,
            MessageData,
            SenderData,
        )

        return GreenAPIMessageWebhook(
            typeWebhook="incomingMessageReceived",
            instanceData=InstanceData(
                idInstance=123,
                wid="27123456789@c.us",
                typeInstance="whatsapp",
            ),
            timestamp=int(datetime.now(UTC).timestamp()),
            idMessage="msg_contact_456",
            senderData=SenderData(
                chatId="27123456789-group@g.us",
                sender=sender_id,
                chatName="Test Group",
                senderName=sender_name,
            ),
            messageData=MessageData(
                typeMessage="contactMessage",
                contactMessageData=ContactMessageContent(
                    displayName="John Plumber",
                    vcard=(
                        "BEGIN:VCARD\nVERSION:3.0\nFN:John Plumber\n" "TEL:+27123456789\nEND:VCARD"
                    ),
                ),
            ),
        )


class TestAttributionResult:
    """Test AttributionResult model functionality."""

    def test_should_create_attribution_result_with_required_fields(self) -> None:
        """Test creating attribution result with all required fields."""
        result = AttributionResult(
            attribution_confidence=0.85,
            request_message_id="msg_123",
            response_delay_seconds=180,
            attribution_type="temporal_proximity",
            temporal_pattern=TemporalPattern.NEAR_TERM,
            sender_pattern="community_response",
        )

        assert result.attribution_confidence == 0.85
        assert result.request_message_id == "msg_123"
        assert result.response_delay_seconds == 180
        assert result.attribution_type == "temporal_proximity"
        assert result.temporal_pattern == TemporalPattern.NEAR_TERM
        assert result.sender_pattern == "community_response"

    def test_should_create_attribution_result_with_defaults(self) -> None:
        """Test creating attribution result with default values."""
        result = AttributionResult()

        assert result.attribution_confidence == 0.0
        assert result.request_message_id is None
        assert result.response_delay_seconds is None
        assert result.attribution_type == "standalone"
        assert result.temporal_pattern == TemporalPattern.NONE
        assert result.sender_pattern is None

    def test_should_validate_confidence_score_range(self) -> None:
        """Test attribution confidence validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            AttributionResult(attribution_confidence=1.5)

        assert "less than or equal to 1" in str(exc_info.value)

    def test_should_check_if_result_has_strong_attribution(self) -> None:
        """Test helper method for strong attribution detection."""
        strong_result = AttributionResult(attribution_confidence=0.9)
        weak_result = AttributionResult(attribution_confidence=0.4)

        assert strong_result.is_strong_attribution() is True
        assert weak_result.is_strong_attribution() is False


class TestTemporalPattern:
    """Test temporal pattern enumeration."""

    def test_should_have_expected_temporal_patterns(self) -> None:
        """Test temporal pattern enum values."""
        assert TemporalPattern.IMMEDIATE.value == "immediate"
        assert TemporalPattern.NEAR_TERM.value == "near_term"
        assert TemporalPattern.DISTANT.value == "distant"
        assert TemporalPattern.NONE.value == "none"

    def test_should_convert_temporal_pattern_to_string(self) -> None:
        """Test string conversion of temporal patterns."""
        assert str(TemporalPattern.IMMEDIATE) == "immediate"
        assert str(TemporalPattern.NEAR_TERM) == "near_term"
        assert str(TemporalPattern.DISTANT) == "distant"
        assert str(TemporalPattern.NONE) == "none"
