"""WhatsApp message processor for endorsement pipeline."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, NoReturn

from src.application.services.context_attribution import ContextAttributionService
from src.application.services.nlp import MentionExtractor, ProviderMatcher
from src.domain.models import ClassificationResult, Endorsement
from src.domain.repositories import EndorsementRepository, ProviderRepository
from src.domain.value_objects import GroupID
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import (
    ContextAttributionException,
    EndorsementPersistenceException,
    MentionExtractionException,
    MessageProcessingException,
    ProviderMatchingException,
)


@dataclass
class MessageProcessingResult:
    """Result of message processing operation."""

    success: bool
    endorsements_created: list[Endorsement]
    processing_notes: list[str]
    processing_duration_seconds: float


class MessageProcessor:
    """Async message processor for WhatsApp endorsement pipeline."""

    def __init__(
        self,
        mention_extractor: MentionExtractor | None = None,
        provider_matcher: ProviderMatcher | None = None,
        endorsement_repository: EndorsementRepository | None = None,
        provider_repository: ProviderRepository | None = None,
        context_attribution_service: ContextAttributionService | None = None,
    ) -> None:
        """
        Initialize MessageProcessor with dependencies.

        Args:
            mention_extractor: Service for extracting provider mentions
            provider_matcher: Service for matching mentions to providers
            endorsement_repository: Repository for persisting endorsements
            provider_repository: Repository for provider lookups
            context_attribution_service: Service for analysing request-response relationships
        """
        self.mention_extractor = mention_extractor or MentionExtractor()
        self.provider_matcher = provider_matcher or ProviderMatcher()
        self.endorsement_repository = endorsement_repository
        self.provider_repository = provider_repository
        self.context_attribution_service = context_attribution_service

        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()

    async def process_endorsement_message(
        self,
        group_id: GroupID,
        sender_name: str,
        message_text: str,
        timestamp: int,  # Currently unused in placeholder implementation
        classification: ClassificationResult,
    ) -> MessageProcessingResult:
        """
        Process a WhatsApp message for endorsements.

        Args:
            group_id: WhatsApp group identifier
            sender_name: Name of message sender
            message_text: Message content
            timestamp: Unix timestamp of message
            classification: Message classification result

        Returns:
            MessageProcessingResult with processing outcome

        Raises:
            MessageProcessingException: If processing fails
        """
        operation_start = datetime.now(UTC)
        processing_notes: list[str] = []
        endorsements_created: list[Endorsement] = []

        try:
            self._log_processing_start(group_id, sender_name, message_text, classification)

            # Step 2: Extract provider mentions
            extracted_mentions = self._extract_mentions(message_text, group_id)
            if not extracted_mentions:
                return self._create_no_mentions_result(processing_notes, operation_start)

            # Step 3: Match against known providers (placeholder implementation)
            provider_matches = await self._match_providers(extracted_mentions, group_id)
            if not provider_matches:
                return self._create_no_matches_result(processing_notes, operation_start)

            # Step 4: Store endorsements in repository
            endorsements_created = self._create_endorsements(
                provider_matches,
                group_id,
                message_text,
            )

            # Record success metrics
            self.metrics.increment_counter("message_processing_success_total", {})

            return self._create_result(
                success=True,
                endorsements_created=endorsements_created,
                processing_notes=processing_notes,
                operation_start=operation_start,
            )

        except MessageProcessingException:
            # Re-raise known processing exceptions
            raise

        except Exception as e:
            self._handle_unexpected_error(e, group_id)

    def _log_processing_start(
        self,
        group_id: GroupID,
        sender_name: str,
        message_text: str,
        classification: ClassificationResult,
    ) -> None:
        """Log the start of message processing."""
        self.logger.info(
            "Starting endorsement message processing",
            group_id=group_id.value,
            sender_name=sender_name,
            message_length=len(message_text),
            classification_confidence=classification.confidence,
        )

    def _extract_mentions(self, message_text: str, group_id: GroupID) -> list[Any]:
        """Extract provider mentions from message text."""
        try:
            extracted_mentions = self.mention_extractor.extract_mentions(message_text)

            if extracted_mentions:
                self.logger.info(
                    "Extracted provider mentions",
                    group_id=group_id.value,
                    mention_count=len(extracted_mentions),
                )

            return extracted_mentions

        except Exception as e:
            self.logger.error(
                "Failed to extract mentions",
                group_id=group_id.value,
                error=str(e),
            )
            self.metrics.increment_counter(
                "message_processing_errors_total",
                {"step": "mention_extraction"},
            )
            raise MentionExtractionException(f"Failed to extract mentions: {e}") from e

    async def _match_providers(self, extracted_mentions: list[Any], group_id: GroupID) -> list[Any]:
        """Match extracted mentions against known providers."""
        try:
            if not self.provider_repository:
                self.logger.warning(
                    "Provider repository not available - skipping provider matching",
                    group_id=group_id.value,
                )
                return []

            mention_groups = self._group_mentions_by_type(extracted_mentions)
            provider_matches = await self._process_name_mentions(
                mention_groups,
                group_id,
            )

            if provider_matches:
                self.logger.info(
                    "Matched providers",
                    group_id=group_id.value,
                    match_count=len(provider_matches),
                )

            return provider_matches

        except Exception as e:
            self.logger.error(
                "Failed to match providers",
                group_id=group_id.value,
                error=str(e),
            )
            self.metrics.increment_counter(
                "message_processing_errors_total",
                {"step": "provider_matching"},
            )
            raise ProviderMatchingException(f"Failed to match providers: {e}") from e

    def _group_mentions_by_type(self, extracted_mentions: list[Any]) -> dict[str, list[Any]]:
        """Group mentions by their extraction type for easier processing."""
        phone_mentions = [
            m for m in extracted_mentions if m.extraction_type == "contact_phone_number"
        ]
        contact_name_mentions = [
            m
            for m in extracted_mentions
            if m.extraction_type in ["contact_display_name", "contact_organization"]
        ]
        regular_name_mentions = [
            m for m in extracted_mentions if m.extraction_type == "name_pattern"
        ]

        return {
            "phone_mentions": phone_mentions,
            "all_name_mentions": contact_name_mentions + regular_name_mentions,
        }

    async def _process_name_mentions(
        self,
        mention_groups: dict[str, list[Any]],
        group_id: GroupID,
    ) -> list[Any]:
        """Process all name mentions to find or create providers."""
        await asyncio.sleep(0.01)
        provider_matches: list[Any] = []
        phone_mentions = mention_groups["phone_mentions"]
        all_name_mentions = mention_groups["all_name_mentions"]

        for name_mention in all_name_mentions:
            try:
                existing_providers = self._find_existing_providers(
                    name_mention,
                    phone_mentions,
                )

                if not existing_providers:
                    new_provider = self._create_new_provider(
                        name_mention,
                        phone_mentions,
                        group_id,
                    )
                    if new_provider:
                        provider_matches.append(new_provider)
                else:
                    provider_matches.extend(existing_providers)

            except Exception as mention_error:
                self.logger.error(
                    "Failed to process mention for provider matching",
                    group_id=group_id.value,
                    mention_text=getattr(name_mention, "text", "unknown"),
                    error=str(mention_error),
                )

        return provider_matches

    def _find_existing_providers(
        self,
        name_mention: Any,
        phone_mentions: list[Any],
    ) -> list[Any]:
        """Find existing providers by phone number or name pattern."""
        existing_providers = []

        # Try to find by phone number first
        existing_providers.extend(self._find_providers_by_phone(phone_mentions))

        # If no phone-based providers and this is a regular name mention, search by name
        if not existing_providers and name_mention.extraction_type == "name_pattern":
            existing_providers.extend(self._find_providers_by_name(name_mention.text))

        return existing_providers

    def _find_providers_by_phone(self, phone_mentions: list[Any]) -> list[Any]:
        """Find providers by phone number from mentions."""
        existing_providers: list[Any] = []

        if not self.provider_repository:
            return existing_providers

        for phone_mention in phone_mentions:
            try:
                from src.domain.value_objects import PhoneNumber

                phone = PhoneNumber(value=phone_mention.text)
                found_providers = self.provider_repository.find_by_phone(phone)
                existing_providers.extend(found_providers)
            except Exception as phone_error:
                self.logger.debug(
                    "Invalid phone number in mention",
                    phone=phone_mention.text,
                    error=str(phone_error),
                )

        return existing_providers

    def _find_providers_by_name(self, name_text: str) -> list[Any]:
        """Find providers by name pattern."""
        if not self.provider_repository:
            return []

        try:
            # provider_repository is guaranteed to be non-None after the check above
            if self.provider_repository:
                return self.provider_repository.find_by_name_pattern(name_text)
            return []
        except Exception as name_error:
            self.logger.debug(
                "Failed to search providers by name pattern",
                name=name_text,
                error=str(name_error),
            )
            return []

    def _create_new_provider(
        self,
        name_mention: Any,
        phone_mentions: list[Any],
        group_id: GroupID,
    ) -> Any:
        """Create a new provider from mention data."""
        phone_numbers = [pm.text for pm in phone_mentions] if phone_mentions else []
        return self._create_provider_from_contact_mentions(
            name_mention,
            phone_numbers,
            group_id,
        )

    def _create_provider_from_contact_mentions(
        self,
        name_mention: Any,
        phone_numbers: list[str],
        group_id: GroupID,
    ) -> Any:
        """Create a new provider from contact mentions (name + phone numbers)."""
        try:
            from src.domain.models import Provider
            from src.domain.value_objects import PhoneNumber, ProviderID

            # Extract provider name from mention
            provider_name = getattr(name_mention, "text", "Unknown Provider")

            # Validate phone numbers
            valid_phone = None
            for phone_str in phone_numbers:
                try:
                    valid_phone = PhoneNumber(value=phone_str)
                    break  # Use the first valid phone number
                except Exception as phone_error:
                    self.logger.debug(
                        "Invalid phone number in contact mentions",
                        phone=phone_str,
                        error=str(phone_error),
                    )

            # Only create provider if we have a valid phone number (required field)
            if not valid_phone:
                self.logger.debug(
                    "Skipping provider creation - no valid phone number",
                    provider_name=provider_name,
                    group_id=group_id.value,
                )
                return None

            # Determine provider category from mention context
            category = getattr(name_mention, "extraction_type", "services")
            if category in ["contact_display_name", "contact_organization"]:
                category = "services"  # Default for contact cards

            # Create new provider
            new_provider = Provider(
                id=ProviderID(),  # Auto-generate UUID
                name=provider_name,
                phone=valid_phone,
                category=category,
                tags={},
                endorsement_count=1,  # First endorsement
            )

            # Save to repository
            if self.provider_repository:
                self.provider_repository.save(new_provider)
                self.logger.info(
                    "Created new provider from contact mentions",
                    provider_id=new_provider.id.value,
                    provider_name=provider_name,
                    phone=valid_phone.value,
                    group_id=group_id.value,
                )

            return new_provider

        except Exception as e:
            self.logger.error(
                "Failed to create provider from contact mentions",
                mention_text=getattr(name_mention, "text", "unknown"),
                group_id=group_id.value,
                error=str(e),
            )
            return None

    def _create_endorsements(
        self,
        provider_matches: list[Any],
        group_id: GroupID,
        message_text: str,
    ) -> list[Endorsement]:
        """Create endorsements from provider matches."""
        endorsements_created: list[Endorsement] = []

        from src.domain.models import EndorsementType
        from src.domain.value_objects import EndorsementID

        try:
            if not self.endorsement_repository:
                self.logger.warning(
                    "Skipping endorsement creation - endorsement repository not available",
                    group_id=group_id.value,
                )
                return endorsements_created

            # Create endorsements for each matched provider

            for provider in provider_matches:
                try:
                    # Create endorsement (use provider phone as endorser placeholder)
                    endorsement = Endorsement(
                        id=EndorsementID(),  # Auto-generate UUID
                        provider_id=provider.id,
                        group_id=group_id,
                        endorser_phone=provider.phone,  # Use provider phone as endorser
                        endorsement_type=EndorsementType.MANUAL,  # Contact cards are manual
                        message_context=(
                            message_text[:200] if len(message_text) > 200 else message_text
                        ),
                        confidence_score=0.95,  # High confidence for contact cards
                    )

                    # Save endorsement
                    self.endorsement_repository.save(endorsement)
                    endorsements_created.append(endorsement)

                    # Update provider endorsement count
                    if self.provider_repository and hasattr(provider, "endorsement_count"):
                        updated_provider = provider.model_copy(
                            update={"endorsement_count": provider.endorsement_count + 1},
                        )
                        self.provider_repository.save(updated_provider)

                    self.logger.info(
                        "Created endorsement for provider",
                        endorsement_id=endorsement.id.value,
                        provider_id=provider.id.value,
                        group_id=group_id.value,
                    )

                except Exception as provider_error:
                    self.logger.error(
                        "Failed to create endorsement for provider",
                        provider_id=(
                            str(provider.id.value)
                            if hasattr(provider, "id") and hasattr(provider.id, "value")
                            else "unknown"
                        ),
                        group_id=group_id.value,
                        error=str(provider_error),
                    )

            self.logger.info(
                "Created endorsements",
                group_id=group_id.value,
                endorsement_count=len(endorsements_created),
            )

            return endorsements_created

        except Exception as e:
            self.logger.error(
                "Failed to persist endorsement",
                group_id=group_id.value,
                error=str(e),
            )
            self.metrics.increment_counter(
                "message_processing_errors_total",
                {"step": "persistence"},
            )
            raise EndorsementPersistenceException(f"Failed to persist endorsement: {e}") from e

    def _create_no_mentions_result(
        self,
        processing_notes: list[str],
        operation_start: datetime,
    ) -> MessageProcessingResult:
        """Create result when no mentions are found."""
        processing_notes.append("No provider mentions found")
        return self._create_result(
            success=True,
            endorsements_created=[],
            processing_notes=processing_notes,
            operation_start=operation_start,
        )

    def _create_no_matches_result(
        self,
        processing_notes: list[str],
        operation_start: datetime,
    ) -> MessageProcessingResult:
        """Create result when no provider matches are found."""
        processing_notes.append("No matching providers found")
        # Record success metrics even for no matches
        self.metrics.increment_counter("message_processing_success_total", {})
        return self._create_result(
            success=True,
            endorsements_created=[],
            processing_notes=processing_notes,
            operation_start=operation_start,
        )

    def _handle_unexpected_error(self, error: Exception, group_id: GroupID) -> NoReturn:
        """Handle unexpected errors during processing."""
        self.logger.error(
            "Unexpected error during message processing",
            group_id=group_id.value,
            error=str(error),
        )
        self.metrics.increment_counter(
            "message_processing_errors_total",
            {"step": "unexpected"},
        )
        raise MessageProcessingException(f"Unexpected processing error: {error}") from error

    def _create_result(
        self,
        success: bool,
        endorsements_created: list[Endorsement],
        processing_notes: list[str],
        operation_start: datetime,
    ) -> MessageProcessingResult:
        """Create processing result with metrics recording."""
        processing_duration = (datetime.now(UTC) - operation_start).total_seconds()

        self.metrics.record_histogram(
            "message_processing_duration_seconds",
            processing_duration,
            {},
        )

        return MessageProcessingResult(
            success=success,
            endorsements_created=endorsements_created,
            processing_notes=processing_notes,
            processing_duration_seconds=processing_duration,
        )

    async def process_structured_mentions(
        self,
        group_id: GroupID,
        sender_name: str,
        message_text: str,
        timestamp: int,
        classification: ClassificationResult,
        extracted_mentions: list[Any],
    ) -> MessageProcessingResult:
        """
        Process pre-extracted mentions for endorsements.

        This method is used when mentions have been extracted from structured data
        (like contact cards) rather than from message text parsing.

        Args:
            group_id: WhatsApp group identifier
            sender_name: Name of message sender
            message_text: Original message context
            timestamp: Unix timestamp of message
            classification: Message classification result
            extracted_mentions: Pre-extracted mentions from structured data

        Returns:
            MessageProcessingResult with processing outcome

        Raises:
            MessageProcessingException: If processing fails
        """
        operation_start = datetime.now(UTC)
        processing_notes: list[str] = []
        endorsements_created: list[Endorsement] = []

        try:
            self._log_processing_start(group_id, sender_name, message_text, classification)

            if not extracted_mentions:
                return self._create_no_mentions_result(processing_notes, operation_start)

            # Skip mention extraction step - use provided structured mentions
            self.logger.info(
                "Using pre-extracted structured mentions",
                group_id=group_id.value,
                mention_count=len(extracted_mentions),
            )

            # Step 3: Match against known providers
            provider_matches = await self._match_providers(extracted_mentions, group_id)
            if not provider_matches:
                return self._create_no_matches_result(processing_notes, operation_start)

            # Step 4: Store endorsements in repository
            endorsements_created = self._create_endorsements(
                provider_matches,
                group_id,
                message_text,
            )

            # Record success metrics
            self.metrics.increment_counter("message_processing_success_total", {})

            return self._create_result(
                success=True,
                endorsements_created=endorsements_created,
                processing_notes=processing_notes,
                operation_start=operation_start,
            )

        except MessageProcessingException:
            # Re-raise known processing exceptions
            raise

        except Exception as e:
            self._handle_unexpected_error(e, group_id)

    async def process_endorsement_message_with_context(
        self,
        group_id: GroupID,
        sender_name: str,
        message_text: str,
        timestamp: int,
        classification: ClassificationResult,
        webhook: Any,
    ) -> MessageProcessingResult:
        """
        Process endorsement message with context attribution analysis.

        Args:
            group_id: WhatsApp group identifier
            sender_name: Name of message sender
            message_text: Message content
            timestamp: Unix timestamp of message
            classification: Message classification result
            webhook: Webhook data for context analysis

        Returns:
            MessageProcessingResult with processing outcome including attribution

        Raises:
            MessageProcessingException: If processing fails
        """
        operation_start = datetime.now(UTC)
        processing_notes: list[str] = []
        endorsements_created: list[Endorsement] = []

        try:
            self._log_processing_start(group_id, sender_name, message_text, classification)

            # Step 1: Analyze context attribution
            attribution_result = self._analyze_context_attribution(
                webhook,
                group_id,
                timestamp,
            )

            # Step 2: Extract provider mentions
            extracted_mentions = self._extract_mentions(message_text, group_id)
            if not extracted_mentions:
                return self._create_no_mentions_result(processing_notes, operation_start)

            # Step 3: Match against known providers
            provider_matches = await self._match_providers(extracted_mentions, group_id)
            if not provider_matches:
                return self._create_no_matches_result(processing_notes, operation_start)

            # Step 4: Store endorsements with attribution data
            endorsements_created = self._create_endorsements_with_attribution(
                provider_matches,
                group_id,
                message_text,
                attribution_result,
            )

            # Record success metrics
            self.metrics.increment_counter("message_processing_success_total", {})

            return self._create_result(
                success=True,
                endorsements_created=endorsements_created,
                processing_notes=processing_notes,
                operation_start=operation_start,
            )

        except MessageProcessingException:
            # Re-raise known processing exceptions
            raise

        except Exception as e:
            self._handle_unexpected_error(e, group_id)

    def _analyze_context_attribution(
        self,
        webhook: Any,
        group_id: GroupID,
        timestamp: int,
    ) -> Any:
        """Analyze message context attribution using the context attribution service."""
        from src.application.services.context_attribution import AttributionResult

        if not self.context_attribution_service:
            # Return default attribution result if service not available
            return AttributionResult()

        try:
            return self.context_attribution_service.analyze_message_context(
                webhook=webhook,
                group_id=group_id,
                _timestamp=timestamp,
            )
        except ContextAttributionException as e:
            self.logger.warning(
                "Context attribution analysis failed, using default values",
                group_id=group_id.value,
                error=str(e),
            )
            return AttributionResult()

    def _create_endorsements_with_attribution(
        self,
        provider_matches: list[Any],
        group_id: GroupID,
        message_text: str,
        attribution_result: Any,
    ) -> list[Endorsement]:
        """Create endorsements with context attribution data."""
        endorsements_created: list[Endorsement] = []

        from src.domain.models import EndorsementType
        from src.domain.value_objects import EndorsementID

        try:
            if not self.endorsement_repository:
                self.logger.warning(
                    "Skipping endorsement creation - endorsement repository not available",
                    group_id=group_id.value,
                )
                return endorsements_created

            for provider in provider_matches:
                try:
                    # Create endorsement with attribution data
                    endorsement = Endorsement(
                        id=EndorsementID(),
                        provider_id=provider.id,
                        group_id=group_id,
                        endorser_phone=provider.phone,
                        endorsement_type=EndorsementType.MANUAL,
                        message_context=(
                            message_text[:200] if len(message_text) > 200 else message_text
                        ),
                        confidence_score=0.95,
                        request_message_id=attribution_result.request_message_id,
                        response_delay_seconds=attribution_result.response_delay_seconds,
                        attribution_confidence=attribution_result.attribution_confidence,
                    )

                    # Save endorsement
                    self.endorsement_repository.save(endorsement)
                    endorsements_created.append(endorsement)

                    # Update provider endorsement count
                    if self.provider_repository and hasattr(provider, "endorsement_count"):
                        updated_provider = provider.model_copy(
                            update={"endorsement_count": provider.endorsement_count + 1},
                        )
                        self.provider_repository.save(updated_provider)

                    self.logger.info(
                        "Created endorsement with context attribution",
                        endorsement_id=endorsement.id.value,
                        provider_id=provider.id.value,
                        group_id=group_id.value,
                        attribution_confidence=attribution_result.attribution_confidence,
                    )

                except Exception as provider_error:
                    self.logger.error(
                        "Failed to create endorsement for provider",
                        provider_id=(
                            str(provider.id.value)
                            if hasattr(provider, "id") and hasattr(provider.id, "value")
                            else "unknown"
                        ),
                        group_id=group_id.value,
                        error=str(provider_error),
                    )

            return endorsements_created

        except Exception as e:
            self.logger.error(
                "Failed to persist endorsement with attribution",
                group_id=group_id.value,
                error=str(e),
            )
            self.metrics.increment_counter(
                "message_processing_errors_total",
                {"step": "persistence"},
            )
            raise EndorsementPersistenceException(f"Failed to persist endorsement: {e}") from e
