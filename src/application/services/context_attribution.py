"""Context attribution service for request-response correlation analysis."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.domain.value_objects import GroupID
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.interfaces.api.schemas.webhooks import GreenAPIMessageWebhook
from src.shared.exceptions import ContextAttributionException


class TemporalPattern(str, Enum):
    """Temporal proximity patterns for request-response correlation."""

    IMMEDIATE = "immediate"  # 0-30 seconds
    NEAR_TERM = "near_term"  # 30 seconds - 15 minutes
    DISTANT = "distant"  # 15 minutes - 1 hour
    NONE = "none"  # No temporal correlation

    def __str__(self) -> str:
        """Return the enum value as string."""
        return self.value


class AttributionResult(BaseModel):
    """Result of context attribution analysis."""

    model_config = {"frozen": True}

    attribution_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for request-response correlation",
    )
    request_message_id: str | None = Field(
        default=None,
        description="ID of the correlated request message",
    )
    response_delay_seconds: int | None = Field(
        default=None,
        description="Time delay between request and response",
    )
    attribution_type: str = Field(
        default="standalone",
        description="Type of attribution detected",
    )
    temporal_pattern: TemporalPattern = Field(
        default=TemporalPattern.NONE,
        description="Temporal proximity pattern",
    )
    sender_pattern: str | None = Field(
        default=None,
        description="Sender behaviour pattern detected",
    )

    @field_validator("attribution_confidence")
    @classmethod
    def validate_attribution_confidence(cls, value: float) -> float:
        """Validate attribution confidence is within range."""
        if not 0.0 <= value <= 1.0:
            raise ValueError("Attribution confidence must be between 0.0 and 1.0")
        return value

    def is_strong_attribution(self) -> bool:
        """Check if this result represents strong attribution confidence."""
        return self.attribution_confidence >= 0.7


class ContextAttributionService:
    """Service for analysing request-response context attribution."""

    # Temporal thresholds for attribution analysis
    IMMEDIATE_THRESHOLD_SECONDS = 30
    NEAR_TERM_THRESHOLD_SECONDS = 900  # 15 minutes
    DISTANT_THRESHOLD_SECONDS = 3600  # 1 hour

    def __init__(self) -> None:
        """Initialize context attribution service."""
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()

    def analyze_message_context(
        self,
        webhook: GreenAPIMessageWebhook,
        group_id: GroupID,
        _timestamp: int,
    ) -> AttributionResult:
        """
        Analyze message context to determine request-response correlation.

        Args:
            webhook: WhatsApp webhook message
            group_id: Group where message was sent
            _timestamp: Unix timestamp of message (unused in current implementation)

        Returns:
            AttributionResult with correlation analysis

        Raises:
            ContextAttributionException: If analysis fails
        """
        if webhook is None:
            raise ContextAttributionException("Webhook message is required")

        try:
            self.logger.info(
                "Starting context attribution analysis",
                group_id=group_id.value,
                message_type=webhook.messageData.typeMessage,
            )

            # Check for direct quote attribution first
            if webhook.isQuotedMessage:
                return self._analyze_quoted_message(webhook, group_id)

            # For contact messages, analyze as potential response without direct quote
            if webhook.isAnyContactMessage:
                return self._analyze_contact_response(webhook, group_id)

            # Default case - standalone message
            return AttributionResult()

        except Exception as e:
            self.logger.error(
                "Context attribution analysis failed",
                group_id=group_id.value,
                error=str(e),
            )
            self.metrics.increment_counter(
                "context_attribution_errors_total",
                {"error_type": "analysis_failure"},
            )

            # Return error fallback result instead of raising
            return AttributionResult(attribution_type="error_fallback")

    def analyze_temporal_proximity(
        self,
        webhook: GreenAPIMessageWebhook,
        group_id: GroupID,
        timestamp: int,
        recent_requests: list[dict[str, Any]],
    ) -> AttributionResult:
        """
        Analyze temporal proximity to recent request messages.

        Args:
            webhook: WhatsApp webhook message
            group_id: Group where message was sent
            timestamp: Unix timestamp of message
            recent_requests: List of recent request messages

        Returns:
            AttributionResult with temporal correlation analysis
        """
        try:
            if not recent_requests:
                return AttributionResult(
                    attribution_type="standalone",
                    temporal_pattern=TemporalPattern.NONE,
                )

            self.logger.info(
                "Analysing temporal proximity",
                group_id=group_id.value,
                candidate_requests=len(recent_requests),
            )

            # Find best matching request within time window
            best_match = self._find_best_temporal_match(
                timestamp,
                recent_requests,
            )

            if not best_match:
                return AttributionResult(
                    attribution_type="standalone",
                    temporal_pattern=TemporalPattern.DISTANT,
                    attribution_confidence=0.0,
                )

            # Calculate attribution confidence based on temporal and contextual factors
            attribution_confidence = self._calculate_attribution_confidence(
                webhook,
                best_match,
                timestamp,
            )

            response_delay = timestamp - best_match["timestamp"]
            temporal_pattern = self._classify_temporal_pattern(response_delay)
            sender_pattern = self._analyze_sender_pattern(webhook, best_match)

            return AttributionResult(
                attribution_confidence=attribution_confidence,
                request_message_id=best_match["message_id"],
                response_delay_seconds=response_delay,
                attribution_type="temporal_proximity",
                temporal_pattern=temporal_pattern,
                sender_pattern=sender_pattern,
            )

        except Exception as e:
            self.logger.error(
                "Temporal proximity analysis failed",
                group_id=group_id.value,
                error=str(e),
            )
            self.metrics.increment_counter(
                "context_attribution_errors_total",
                {"error_type": "temporal_analysis_failure"},
            )

            # Return error fallback result
            return AttributionResult(
                attribution_confidence=0.0,
                attribution_type="standalone",
                temporal_pattern=TemporalPattern.NONE,
            )

    def _analyze_quoted_message(
        self,
        webhook: GreenAPIMessageWebhook,
        group_id: GroupID,
    ) -> AttributionResult:
        """Analyze direct quoted message for attribution."""
        quoted_message_id = webhook.quotedMessageId
        if not quoted_message_id:
            return AttributionResult()

        self.logger.info(
            "Detected direct quote attribution",
            group_id=group_id.value,
            quoted_message_id=quoted_message_id,
        )

        self.metrics.increment_counter(
            "context_attribution_total",
            {"attribution_type": "direct_quote"},
        )

        return AttributionResult(
            attribution_confidence=0.95,  # High confidence for direct quotes
            request_message_id=quoted_message_id,
            response_delay_seconds=None,  # Unknown without request timestamp
            attribution_type="direct_quote",
            temporal_pattern=TemporalPattern.IMMEDIATE,
        )

    def _analyze_contact_response(
        self,
        webhook: GreenAPIMessageWebhook,
        group_id: GroupID,
    ) -> AttributionResult:
        """Analyze contact message as potential response."""
        # This is a placeholder for when we have stored request history
        # For now, return low confidence standalone result
        self.logger.debug(
            "Contact message without direct quote",
            group_id=group_id.value,
            message_type=webhook.messageData.typeMessage,
        )

        return AttributionResult(
            attribution_confidence=0.2,  # Low confidence without context
            attribution_type="potential_response",
            temporal_pattern=TemporalPattern.NONE,
        )

    def _find_best_temporal_match(
        self,
        timestamp: int,
        recent_requests: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Find the best matching request within time window."""
        valid_candidates = []

        for request in recent_requests:
            time_diff = timestamp - request["timestamp"]

            # Only consider requests within the distant threshold
            if 0 <= time_diff <= self.DISTANT_THRESHOLD_SECONDS:
                valid_candidates.append(
                    {
                        **request,
                        "time_diff": time_diff,
                    },
                )

        if not valid_candidates:
            return None

        # Sort by time proximity (most recent first)
        valid_candidates.sort(key=lambda x: x["time_diff"])
        return valid_candidates[0]

    def _calculate_attribution_confidence(
        self,
        webhook: GreenAPIMessageWebhook,
        request: dict[str, Any],
        timestamp: int,
    ) -> float:
        """Calculate attribution confidence based on multiple factors."""
        confidence = 0.0
        time_diff = timestamp - request["timestamp"]

        # Temporal proximity scoring - much stricter for distant messages
        if time_diff <= self.IMMEDIATE_THRESHOLD_SECONDS:
            confidence += 0.6
        elif time_diff <= self.NEAR_TERM_THRESHOLD_SECONDS:
            confidence += 0.4
        elif time_diff <= self.DISTANT_THRESHOLD_SECONDS:
            # Very low confidence for distant messages
            confidence += 0.05
        else:
            # No temporal confidence for messages beyond threshold
            confidence += 0.0

        # Apply much stronger penalty for distant messages
        time_penalty_factor = 1.0
        if time_diff > self.DISTANT_THRESHOLD_SECONDS:
            time_penalty_factor = 0.1  # Heavy penalty for messages beyond time window
        elif time_diff > self.NEAR_TERM_THRESHOLD_SECONDS:
            time_penalty_factor = 0.5  # Moderate penalty for distant messages

        # Message type relevance
        if request.get("message_type") == "query":
            confidence += 0.15 * time_penalty_factor

        # Sender behaviour pattern
        if webhook.senderId != request.get("sender"):
            # Different sender sharing contact (helpful community response)
            confidence += 0.1 * time_penalty_factor
        else:
            # Same sender (self-answer pattern - less common but possible)
            confidence += 0.05 * time_penalty_factor

        # Content relevance (placeholder - could analyze keywords)
        confidence += 0.05 * time_penalty_factor

        return min(confidence, 1.0)  # Cap at 1.0

    def _classify_temporal_pattern(self, time_diff_seconds: int) -> TemporalPattern:
        """Classify temporal pattern based on time difference."""
        if time_diff_seconds <= self.IMMEDIATE_THRESHOLD_SECONDS:
            return TemporalPattern.IMMEDIATE
        if time_diff_seconds <= self.NEAR_TERM_THRESHOLD_SECONDS:
            return TemporalPattern.NEAR_TERM
        if time_diff_seconds <= self.DISTANT_THRESHOLD_SECONDS:
            return TemporalPattern.DISTANT

        return TemporalPattern.NONE

    def _analyze_sender_pattern(
        self,
        webhook: GreenAPIMessageWebhook,
        request: dict[str, Any],
    ) -> str | None:
        """Analyze sender behaviour patterns."""
        if webhook.senderId != request.get("sender"):
            return "community_response"

        return "self_response"
