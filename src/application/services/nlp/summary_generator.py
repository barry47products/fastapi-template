"""Group Summary Generator for creating provider summaries."""

from datetime import datetime, UTC

from config.settings import Settings, SummaryGenerationSettings
from src.domain.models import (
    Endorsement,
    ExtractedMention,
    GroupSummary,
    Provider,
    ProviderSummary,
    SummaryType,
)
from src.domain.value_objects import GroupID
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import SummaryGenerationError


class GroupSummaryGenerator:
    """
    Generates comprehensive summaries of endorsed providers for WhatsApp groups.

    Creates structured summaries of provider recommendations and endorsements
    with configurable filtering, confidence scoring, and categorization.
    Integrates with full infrastructure (logging, metrics, health monitoring).
    """

    def __init__(self, settings: SummaryGenerationSettings | None = None) -> None:
        """Initialize summary generator with infrastructure integration."""
        self._logger = get_logger(__name__)
        self._metrics = get_metrics_collector()

        if settings is None:
            from config.settings import get_settings

            app_settings: Settings = get_settings()
            self.settings = app_settings.summary_generation
        else:
            self.settings = settings

        self._logger.info(
            "Summary generator initialized",
            generator_class="GroupSummaryGenerator",
        )

    def generate_summary(
        self,
        group_id: GroupID,
        providers: list[Provider],
        endorsements: list[Endorsement],
        mentions: list[ExtractedMention],
        summary_type: SummaryType = SummaryType.COMPREHENSIVE,
    ) -> GroupSummary:
        """
        Generate group summary with full infrastructure integration.

        Args:
            group_id: WhatsApp group identifier
            providers: List of available providers
            endorsements: List of provider endorsements
            mentions: List of extracted mentions
            summary_type: Type of summary to generate

        Returns:
            GroupSummary: Complete summary with provider details

        Raises:
            SummaryGenerationError: If summary generation fails
        """
        start_time = datetime.now(UTC)

        try:
            self._logger.info(
                "Starting summary generation",
                summary_type=summary_type.value,
                provider_count=len(providers),
                endorsement_count=len(endorsements),
                mention_count=len(mentions),
            )

            # Create provider summaries
            provider_summaries = []
            for provider in providers:
                provider_endorsements = [e for e in endorsements if e.provider_id == provider.id]
                provider_mentions = self._match_mentions_to_provider(provider, mentions)
                provider_summary = self._create_provider_summary(
                    provider,
                    provider_endorsements,
                    provider_mentions,
                )
                provider_summaries.append(provider_summary)

            # Apply summary type filtering
            filtered_summaries = self._filter_by_summary_type(
                provider_summaries,
                summary_type,
            )

            # Calculate overall metrics
            total_endorsements = sum(ps.endorsement_count for ps in filtered_summaries)
            confidence_score = self._calculate_confidence_score(mentions, endorsements)

            # Create final summary
            summary = GroupSummary(
                group_id=group_id,
                generation_timestamp=start_time,
                provider_summaries=filtered_summaries,
                total_providers=len(filtered_summaries),
                total_endorsements=total_endorsements,
                summary_type=summary_type,
                confidence_score=confidence_score,
            )

            # Record metrics
            duration = (datetime.now(UTC) - start_time).total_seconds()
            self._metrics.increment_counter(
                "summary_generated_total",
                {"type": summary_type.value},
            )
            self._metrics.record_histogram(
                "summary_generation_duration_seconds",
                duration,
                {},
            )
            self._metrics.record_gauge(
                "summary_provider_count",
                len(filtered_summaries),
                {},
            )

            self._logger.info(
                "Summary generation completed",
                summary_type=summary_type.value,
                total_providers=len(filtered_summaries),
                total_endorsements=total_endorsements,
                confidence_score=confidence_score,
                duration_seconds=duration,
            )

            return summary

        except Exception as e:
            self._metrics.increment_counter(
                "summary_generation_errors_total",
                {"error_type": type(e).__name__},
            )
            self._logger.error(
                "Summary generation failed",
                error_message=str(e),
                error_type=type(e).__name__,
                summary_type=summary_type.value,
            )
            raise SummaryGenerationError(f"Failed to generate summary: {e}") from e

    def _create_provider_summary(
        self,
        provider: Provider,
        endorsements: list[Endorsement],
        mentions: list[ExtractedMention],
    ) -> ProviderSummary:
        """Create individual provider summary."""
        # Calculate average confidence from mentions
        avg_confidence = sum(m.confidence for m in mentions) / len(mentions) if mentions else 0.0

        # Determine service categories (simplified for Phase 2)
        service_categories = {provider.category}

        # Get most recent mention or creation timestamp
        last_mentioned = (
            max(endorsement.created_at for endorsement in endorsements)
            if endorsements
            else provider.created_at
        )

        return ProviderSummary(
            provider=provider,
            endorsement_count=len(endorsements),
            recent_mentions=mentions,
            average_confidence=avg_confidence,
            service_categories=service_categories,
            last_mentioned=last_mentioned,
        )

    def _match_mentions_to_provider(
        self,
        provider: Provider,
        mentions: list[ExtractedMention],
    ) -> list[ExtractedMention]:
        """Match mentions to provider (simplified for Phase 2)."""
        # Simple name matching for Phase 2
        matched_mentions = []
        for mention in mentions:
            if provider.name.lower() in mention.text.lower():
                matched_mentions.append(mention)
        return matched_mentions

    def _filter_by_summary_type(
        self,
        provider_summaries: list[ProviderSummary],
        summary_type: SummaryType,
    ) -> list[ProviderSummary]:
        """Filter provider summaries based on summary type."""
        if summary_type == SummaryType.COMPREHENSIVE:
            return provider_summaries
        elif summary_type == SummaryType.TOP_RATED:
            # Filter for highly endorsed providers using configuration
            return [
                ps
                for ps in provider_summaries
                if ps.endorsement_count >= self.settings.top_rated_min_endorsements
                and ps.average_confidence >= (self.settings.top_rated_confidence_threshold)
            ]
        elif summary_type == SummaryType.RECENT_ACTIVITY:
            # Filter for recent activity using configuration
            return [
                ps
                for ps in provider_summaries
                if ps.has_recent_activity(days=self.settings.recent_activity_days)
            ]
        elif summary_type == SummaryType.CATEGORY_FOCUSED:
            # Group by category (simplified - return all for Phase 2)
            return provider_summaries
        else:
            return provider_summaries

    def _calculate_confidence_score(
        self,
        mentions: list[ExtractedMention],
        endorsements: list[Endorsement],
    ) -> float:
        """Calculate overall summary confidence score."""
        if not mentions and not endorsements:
            return 0.0

        # Simple confidence calculation for Phase 2
        mention_confidence = (
            sum(m.confidence for m in mentions) / len(mentions) if mentions else 0.0
        )

        # Weight endorsements as high confidence
        endorsement_confidence = min(len(endorsements) * 0.2, 1.0)

        # Combine mention and endorsement confidence
        combined_confidence = (mention_confidence * 0.7) + (endorsement_confidence * 0.3)

        return min(combined_confidence, 1.0)

    def _health_check(self) -> bool:
        """Test summary generation with minimal data for health monitoring."""
        try:
            test_group_id = GroupID(value="447911123456-1234567890@g.us")
            test_summary = self.generate_summary(
                group_id=test_group_id,
                providers=[],
                endorsements=[],
                mentions=[],
                summary_type=SummaryType.COMPREHENSIVE,
            )
            return test_summary.total_providers == 0
        except Exception:
            return False
