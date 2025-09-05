"""Tests for MessageProcessor context attribution integration."""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.application.services.context_attribution import (
    AttributionResult,
    ContextAttributionService,
    TemporalPattern,
)
from src.application.services.message_processor import MessageProcessor
from src.domain.models import ClassificationResult, MessageType
from src.domain.value_objects import GroupID, PhoneNumber, ProviderID
from src.interfaces.api.schemas.webhooks import GreenAPIMessageWebhook


class TestMessageProcessorContextAttribution:
    """Test MessageProcessor integration with Context Attribution System."""

    mention_extractor: Mock
    provider_matcher: Mock
    endorsement_repository: AsyncMock
    provider_repository: AsyncMock
    context_attribution_service: Mock
    processor: MessageProcessor

    def setup_method(self) -> None:
        """Set up test dependencies."""
        self.mention_extractor = Mock()
        self.provider_matcher = Mock()
        self.endorsement_repository = AsyncMock()
        self.provider_repository = AsyncMock()
        self.context_attribution_service = Mock(spec=ContextAttributionService)

        self.processor = MessageProcessor(
            mention_extractor=self.mention_extractor,
            provider_matcher=self.provider_matcher,
            endorsement_repository=self.endorsement_repository,
            provider_repository=self.provider_repository,
            context_attribution_service=self.context_attribution_service,
        )

    @patch.object(MessageProcessor, "_match_providers")
    async def test_should_analyze_context_attribution_for_endorsement_messages(
        self,
        mock_match_providers: AsyncMock,
    ) -> None:
        """Test that context attribution is analysed during message processing."""
        # This test should FAIL initially - MessageProcessor doesn't have context attribution

        # Setup mock webhook and attribution result
        mock_webhook = Mock(spec=GreenAPIMessageWebhook)
        mock_webhook.isQuotedMessage = True
        mock_webhook.quotedMessageId = "request_123"

        high_confidence_attribution = AttributionResult(
            attribution_confidence=0.95,
            request_message_id="request_123",
            response_delay_seconds=60,
            attribution_type="direct_quote",
            temporal_pattern=TemporalPattern.IMMEDIATE,
        )

        self.context_attribution_service.analyze_message_context.return_value = (
            high_confidence_attribution
        )

        # Setup message processing mocks
        mock_mention = Mock()
        mock_mention.text = "John's Plumbing"
        mock_mention.extraction_type = "name_pattern"

        self.mention_extractor.extract_mentions.return_value = [mock_mention]

        mock_provider = Mock()
        mock_provider.id = ProviderID()
        mock_provider.phone = PhoneNumber(value="+27123456789")
        mock_provider.endorsement_count = 5

        mock_match_providers.return_value = [mock_provider]

        # Process the message with webhook context
        group_id = GroupID(value="27123456789-group@g.us")
        classification = ClassificationResult(
            message_type=MessageType.RECOMMENDATION,
            confidence=0.9,
        )

        result = await self.processor.process_endorsement_message_with_context(
            group_id=group_id,
            sender_name="Helper User",
            message_text="Here's John's contact",
            timestamp=int(datetime.now(UTC).timestamp()),
            classification=classification,
            webhook=mock_webhook,
        )

        # Verify context attribution service was called
        self.context_attribution_service.analyze_message_context.assert_called_once_with(
            webhook=mock_webhook,
            group_id=group_id,
            _timestamp=pytest.approx(int(datetime.now(UTC).timestamp()), abs=10),
        )

        # Verify endorsement was created with attribution data
        assert result.success is True
        assert len(result.endorsements_created) == 1

        created_endorsement = result.endorsements_created[0]
        assert created_endorsement.request_message_id == "request_123"
        assert created_endorsement.response_delay_seconds == 60
        assert created_endorsement.attribution_confidence == 0.95

    @patch.object(MessageProcessor, "_match_providers")
    async def test_should_handle_low_confidence_attribution_gracefully(
        self,
        mock_match_providers: AsyncMock,
    ) -> None:
        """Test handling of low confidence attribution results."""
        # Setup mock webhook with low confidence attribution
        mock_webhook = Mock(spec=GreenAPIMessageWebhook)
        mock_webhook.isQuotedMessage = False

        low_confidence_attribution = AttributionResult(
            attribution_confidence=0.2,
            request_message_id=None,
            response_delay_seconds=None,
            attribution_type="standalone",
            temporal_pattern=TemporalPattern.NONE,
        )

        self.context_attribution_service.analyze_message_context.return_value = (
            low_confidence_attribution
        )

        # Setup basic processing mocks
        mock_mention = Mock()
        mock_mention.text = "Bob's Services"
        self.mention_extractor.extract_mentions.return_value = [mock_mention]

        mock_provider = Mock()
        mock_provider.id = ProviderID()
        mock_provider.phone = PhoneNumber(value="+27123456789")
        mock_provider.endorsement_count = 3

        mock_match_providers.return_value = [mock_provider]

        # Process message
        group_id = GroupID(value="27123456789-group@g.us")
        classification = ClassificationResult(
            message_type=MessageType.RECOMMENDATION,
            confidence=0.8,
        )

        result = await self.processor.process_endorsement_message_with_context(
            group_id=group_id,
            sender_name="Someone",
            message_text="Contact Bob for help",
            timestamp=int(datetime.now(UTC).timestamp()),
            classification=classification,
            webhook=mock_webhook,
        )

        # Should still succeed but with no attribution data
        assert result.success is True
        assert len(result.endorsements_created) == 1

        created_endorsement = result.endorsements_created[0]
        assert created_endorsement.request_message_id is None
        assert created_endorsement.response_delay_seconds is None
        assert created_endorsement.attribution_confidence == 0.2

    @patch.object(MessageProcessor, "_match_providers")
    async def test_should_fallback_gracefully_when_context_service_fails(
        self,
        mock_match_providers: AsyncMock,
    ) -> None:
        """Test graceful handling when context attribution service fails."""
        mock_webhook = Mock(spec=GreenAPIMessageWebhook)

        # Make context service raise an exception
        from src.shared.exceptions import ContextAttributionException

        self.context_attribution_service.analyze_message_context.side_effect = (
            ContextAttributionException("Context analysis failed")
        )

        # Setup basic processing mocks
        mock_mention = Mock()
        self.mention_extractor.extract_mentions.return_value = [mock_mention]

        mock_provider = Mock()
        mock_provider.id = ProviderID()
        mock_provider.phone = PhoneNumber(value="+27123456789")
        mock_provider.endorsement_count = 2

        mock_match_providers.return_value = [mock_provider]

        # Should not fail the entire processing pipeline
        group_id = GroupID(value="27123456789-group@g.us")
        classification = ClassificationResult(
            message_type=MessageType.RECOMMENDATION,
            confidence=0.9,
        )

        result = await self.processor.process_endorsement_message_with_context(
            group_id=group_id,
            sender_name="User",
            message_text="Some message",
            timestamp=int(datetime.now(UTC).timestamp()),
            classification=classification,
            webhook=mock_webhook,
        )

        # Should still process successfully with default attribution values
        assert result.success is True
        assert len(result.endorsements_created) == 1

        created_endorsement = result.endorsements_created[0]
        assert created_endorsement.request_message_id is None
        assert created_endorsement.attribution_confidence == 0.0
