"""WhatsApp response generator for automated group summaries."""

import asyncio
from typing import Any, TypedDict

from config.settings import get_settings
from src.application.services.nlp import GroupSummaryGenerator
from src.application.services.nlp.mention_extractor import MentionExtractor
from src.domain.models import Endorsement, ExtractedMention, Provider
from src.domain.models.group_summary import GroupSummary, SummaryType
from src.domain.repositories import ProviderRepository
from src.domain.value_objects import GroupID
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.infrastructure.persistence.repository_factory import (
    get_endorsement_repository,
    get_provider_repository,
)
from src.shared.exceptions import WhatsAppException


class GroupData(TypedDict):
    """Type definition for group data dictionary."""

    providers: list[Provider]
    endorsements: list[Endorsement]
    mentions: list[ExtractedMention]


class WhatsAppResponseGenerator:
    """
    Generate WhatsApp-formatted responses for group summaries.

    Integrates with existing SummaryGenerator to create formatted messages
    suitable for WhatsApp group communication.
    """

    def __init__(self) -> None:
        """Initialize the WhatsApp response generator."""
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()
        self.settings = get_settings()
        self.summary_generator = GroupSummaryGenerator()

    async def generate_summary_response(self, group_id: GroupID) -> str:
        """
        Generate a WhatsApp-formatted summary response for a group.

        Args:
            group_id: WhatsApp group identifier

        Returns:
            Formatted WhatsApp message with group summary

        Raises:
            WhatsAppException: If summary generation fails
        """
        try:
            await asyncio.sleep(0.01)
            self.logger.info(
                "Generating WhatsApp summary response",
                group_id=group_id.value,
            )

            # Retrieve data from repositories
            data = self._retrieve_group_data(group_id)

            # Generate comprehensive summary using retrieved data
            group_summary = self.summary_generator.generate_summary(
                group_id=group_id,
                providers=data["providers"],
                endorsements=data["endorsements"],
                mentions=data["mentions"],
                summary_type=SummaryType.COMPREHENSIVE,
            )

            # Format the summary for WhatsApp
            whatsapp_message = self._format_group_summary_for_whatsapp(group_summary)

            self.logger.info(
                "WhatsApp summary response generated successfully",
                group_id=group_id.value,
                message_length=len(whatsapp_message),
            )

            self.metrics.increment_counter(
                "whatsapp_summary_responses_generated_total",
                {"summary_type": group_summary.summary_type.value},
            )

            return whatsapp_message

        except Exception as e:
            self.logger.error(
                "Failed to generate WhatsApp summary response",
                group_id=group_id.value,
                error=str(e),
            )
            self.metrics.increment_counter("whatsapp_summary_generation_errors_total", {})
            raise WhatsAppException(f"Failed to generate summary response: {e}") from e

    def _retrieve_group_data(
        self,
        group_id: GroupID,
    ) -> GroupData:
        """
        Retrieve providers, endorsements, and mentions for a group.

        Args:
            group_id: WhatsApp group identifier

        Returns:
            Dictionary containing providers, endorsements, and mentions
        """
        endorsement_repo = get_endorsement_repository()
        provider_repo = get_provider_repository()
        mention_extractor = MentionExtractor()

        # Get endorsements for this specific group
        endorsements = endorsement_repo.find_by_group(group_id)

        # Get providers from endorsements and additional categories
        providers = self._get_providers_for_group(endorsements, provider_repo)

        # Extract mentions from recent endorsement messages
        mentions = self._extract_mentions_from_endorsements(endorsements, mention_extractor)

        return {
            "providers": providers,
            "endorsements": endorsements,
            "mentions": mentions,
        }

    def _get_providers_for_group(
        self,
        endorsements: list[Endorsement],
        provider_repo: ProviderRepository,
    ) -> list[Provider]:
        """Get providers from endorsements and supplement with popular categories."""
        # Get providers from endorsements first
        providers = self._get_providers_from_endorsements(endorsements, provider_repo)

        # Supplement with popular categories if needed
        if len(providers) < 5:
            providers = self._supplement_with_popular_categories(providers, provider_repo)

        return providers

    def _get_providers_from_endorsements(
        self,
        endorsements: list[Endorsement],
        provider_repo: ProviderRepository,
    ) -> list[Provider]:
        """Extract providers from endorsement data."""
        provider_ids_from_endorsements = {e.provider_id for e in endorsements}
        providers = []

        for provider_id in provider_ids_from_endorsements:
            provider = provider_repo.find_by_id(provider_id)
            if provider:
                providers.append(provider)

        return providers

    def _supplement_with_popular_categories(
        self,
        existing_providers: list[Provider],
        provider_repo: ProviderRepository,
    ) -> list[Provider]:
        """Supplement existing providers with popular category providers."""
        providers = existing_providers.copy()
        popular_categories = ["Plumbing", "Electrical", "Cleaning", "Gardening", "Handyman"]

        for category in popular_categories:
            if self._should_stop_adding_providers(providers):
                break

            category_providers = provider_repo.find_by_category(category, limit=10)
            providers = self._add_unique_providers(providers, category_providers)

        return providers

    def _should_stop_adding_providers(self, providers: list[Provider]) -> bool:
        """Check if we should stop adding more providers."""
        return len(providers) >= 10

    def _add_unique_providers(
        self,
        existing_providers: list[Provider],
        new_providers: list[Provider],
    ) -> list[Provider]:
        """Add new providers that don't already exist."""
        providers = existing_providers.copy()

        for provider in new_providers:
            if provider not in providers:
                providers.append(provider)
                if len(providers) >= 10:
                    break

        return providers

    def _extract_mentions_from_endorsements(
        self,
        endorsements: list[Endorsement],
        mention_extractor: MentionExtractor,
    ) -> list[ExtractedMention]:
        """Extract mentions from recent endorsement messages."""
        mentions = []
        for endorsement in endorsements[-10:]:  # Last 10 endorsements
            if hasattr(endorsement, "message") and endorsement.message:
                try:
                    endorsement_mentions = mention_extractor.extract_mentions(
                        endorsement.message,
                    )
                    mentions.extend(endorsement_mentions)
                except Exception as e:
                    self.logger.warning(
                        "Failed to extract mentions from endorsement message",
                        endorsement_id=getattr(
                            endorsement,
                            "id",
                            "unknown",
                        ),
                        error=str(e),
                    )

        return mentions

    def generate_provider_endorsement_response(
        self,
        group_id: GroupID,
        provider_name: str,
    ) -> str:
        """
        Generate a response acknowledging a new provider endorsement.

        Args:
            group_id: WhatsApp group identifier
            provider_name: Name of the endorsed provider

        Returns:
            Formatted acknowledgment message
        """
        try:
            self.logger.info(
                "Generating provider endorsement response",
                group_id=group_id.value,
                provider_name=provider_name,
            )

            # Simple acknowledgment message
            message = (
                f"✅ Thanks for the endorsement!\n\n"
                f"I've recorded your recommendation for {provider_name}. "
                f"This helps other neighbours find great service providers.\n\n"
                f"💡 Type 'summary' anytime to see recent recommendations in this group."
            )

            self.metrics.increment_counter("whatsapp_endorsement_responses_generated_total", {})

            return message

        except Exception as e:
            self.logger.error(
                "Failed to generate endorsement response",
                group_id=group_id.value,
                provider_name=provider_name,
                error=str(e),
            )
            raise WhatsAppException(f"Failed to generate endorsement response: {e}") from e

    def _generate_placeholder_summary_response(
        self,
        _group_id: GroupID,
    ) -> str:
        """
        Generate a placeholder summary response.

        Args:
            _group_id: WhatsApp group identifier (unused in current implementation)

        Returns:
            Placeholder WhatsApp message string
        """
        return (
            "📋 *Neighbour Recommendations Summary*\n\n"
            "🚧 Summary feature coming soon!\n\n"
            "This feature will show recent provider recommendations from your group. "
            "Keep sharing your experiences with local service providers to help neighbours!\n\n"
            "💡 Type 'help' for available commands."
        )

    def _format_group_summary_for_whatsapp(self, group_summary: GroupSummary) -> str:
        """
        Format a GroupSummary for WhatsApp messaging.

        Args:
            group_summary: GroupSummary domain model

        Returns:
            WhatsApp-formatted message string
        """
        lines = self._format_header(group_summary)

        if not group_summary.provider_summaries:
            lines.extend(self._format_empty_summary())
        else:
            lines.extend(self._format_provider_summaries(group_summary.provider_summaries))
            lines.extend(self._format_footer(group_summary))

        return "\n".join(lines)

    def _format_header(self, group_summary: GroupSummary) -> list[str]:
        """Format the summary header."""
        return [
            "📋 *Neighbour Recommendations Summary*",
            f"📅 Generated: {group_summary.generation_timestamp.strftime('%Y-%m-%d %H:%M')}",
            "",
        ]

    def _format_empty_summary(self) -> list[str]:
        """Format empty summary message."""
        return [
            "No recommendations found in this group yet.",
            "",
            "💡 Share your experiences with local service providers to help neighbours!",
        ]

    def _format_provider_summaries(self, provider_summaries: list[Any]) -> list[str]:
        """Format the provider summaries section."""
        lines = [
            f"Found {len(provider_summaries)} recommended providers:",
            "",
        ]

        sorted_providers = sorted(
            provider_summaries,
            key=lambda p: p.endorsement_count,
            reverse=True,
        )

        for i, provider_summary in enumerate(sorted_providers, 1):
            lines.extend(self._format_single_provider(i, provider_summary))
            lines.append("")

        return lines

    def _format_single_provider(self, index: int, provider_summary: Any) -> list[str]:
        """Format a single provider entry."""
        provider = provider_summary.provider
        lines = [f"*{index}. {provider.name}*"]

        # Add contact info if available
        if hasattr(provider, "contact_info") and provider.contact_info:
            lines.append(f"📱 {provider.contact_info}")

        lines.append(f"⭐ {provider_summary.endorsement_count} recommendation(s)")

        # Add confidence rating
        if provider_summary.average_confidence:
            confidence_stars = self._confidence_to_stars(provider_summary.average_confidence)
            lines.append(f"🎯 Confidence: {confidence_stars}")

        # Add service categories
        if provider_summary.service_categories:
            categories = ", ".join(provider_summary.service_categories)
            lines.append(f"🔧 Services: {categories}")

        # Add recent mention context
        if provider_summary.recent_mentions:
            context = self._format_recent_mention(provider_summary.recent_mentions[0])
            if context:
                lines.append(context)

        return lines

    def _format_recent_mention(self, recent_mention: Any) -> str:
        """Format recent mention context."""
        if not hasattr(recent_mention, "content") or not recent_mention.content:
            return ""

        context = recent_mention.content[:100]
        if len(recent_mention.content) > 100:
            context += "..."
        return f'💬 "{context}"'

    def _format_footer(self, group_summary: GroupSummary) -> list[str]:
        """Format the summary footer."""
        return [
            "---",
            f"📊 Summary: {group_summary.summary_type.value.replace('_', ' ').title()}",
            "🤖 Generated by Neighbour Approved",
        ]

    def _confidence_to_stars(self, confidence: float) -> str:
        """
        Convert confidence score to star rating.

        Args:
            confidence: Confidence score (0.0 to 1.0)

        Returns:
            Star rating string
        """
        if confidence >= 0.9:
            return "⭐⭐⭐⭐⭐"
        if confidence >= 0.8:
            return "⭐⭐⭐⭐"
        if confidence >= 0.7:
            return "⭐⭐⭐"
        if confidence >= 0.6:
            return "⭐⭐"
        return "⭐"
