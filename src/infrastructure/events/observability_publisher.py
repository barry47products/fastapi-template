"""Infrastructure event publisher for observability (logging and metrics)."""

from src.domain.events import (
    DomainEvent,
    DomainEventPublisher,
    EndorsementConfidenceUpdated,
    EndorsementStatusChanged,
    PhoneNumberParseError,
    PhoneNumberValidated,
    PhoneNumberValidationError,
    ProviderEndorsementDecremented,
    ProviderEndorsementIncremented,
    ProviderTagAdded,
    ProviderTagRemoved,
)
from src.infrastructure.observability import get_logger, get_metrics_collector


class ObservabilityEventPublisher(DomainEventPublisher):
    """
    Infrastructure event publisher that handles observability concerns.

    Subscribes to domain events and translates them into logging and metrics
    operations, maintaining clean separation between domain and infrastructure.
    """

    def __init__(self) -> None:
        """Initialize with logger and metrics collector."""
        self._logger = get_logger(__name__)
        self._metrics = get_metrics_collector()

    def publish(self, event: DomainEvent) -> None:
        """
        Publish a single domain event to infrastructure concerns.

        Args:
            event: The domain event to publish
        """
        self._handle_logging(event)
        self._handle_metrics(event)

    def publish_batch(self, events: list[DomainEvent]) -> None:
        """
        Publish multiple domain events as a batch.

        Args:
            events: List of domain events to publish
        """
        for event in events:
            self.publish(event)

    def _handle_logging(self, event: DomainEvent) -> None:
        """Handle structured logging for domain events."""
        if isinstance(event, PhoneNumberValidated):
            self._logger.info(
                "Phone number validated successfully",
                extra={
                    "e164_format": event.normalized_number,
                    "region": event.region,
                    "original_value": event.phone_number,  # Already masked in domain
                },
            )
        elif isinstance(event, PhoneNumberValidationError):
            self._logger.warning(
                "Phone number validation failed: validation error",
                extra={
                    "raw_value": event.phone_number,  # Already masked in domain
                    "error_type": event.error_type,
                    "validation_error": event.error_message,
                },
            )
        elif isinstance(event, PhoneNumberParseError):
            self._logger.warning(
                "Phone number validation failed: parse error",
                extra={
                    "raw_value": event.phone_number,  # Already masked in domain
                    "parse_error": event.error_message,
                },
            )
        elif isinstance(event, ProviderEndorsementIncremented):
            self._logger.info(
                "Provider endorsement count incremented",
                extra={
                    "provider_id": event.provider_id,  # Already masked in domain
                    "provider_category": event.provider_category,
                    "new_count": event.new_endorsement_count,
                },
            )
        elif isinstance(event, ProviderEndorsementDecremented):
            self._logger.info(
                "Provider endorsement count decremented",
                extra={
                    "provider_id": event.provider_id,  # Already masked in domain
                    "provider_category": event.provider_category,
                    "new_count": event.new_endorsement_count,
                },
            )
        elif isinstance(event, ProviderTagAdded):
            self._logger.info(
                "Provider tag category added",
                extra={
                    "provider_id": event.provider_id,  # Already masked in domain
                    "category": event.tag_category,
                    "value_type": type(event.tag_value).__name__,
                },
            )
        elif isinstance(event, ProviderTagRemoved):
            self._logger.info(
                "Provider tag category removed",
                extra={
                    "provider_id": event.provider_id,  # Already masked in domain
                    "category": event.tag_category,
                },
            )
        elif isinstance(event, EndorsementStatusChanged):
            operation_msg = {
                "revoke": "Endorsement revoked",
                "restore": "Endorsement restored",
            }.get(event.operation, f"Endorsement status changed: {event.operation}")

            self._logger.info(
                operation_msg,
                extra={
                    "endorsement_id": event.endorsement_id,  # Already masked in domain
                    "provider_id": event.provider_id,  # Already masked in domain
                    "operation": event.operation,
                    "endorsement_type": event.endorsement_type,
                },
            )
        elif isinstance(event, EndorsementConfidenceUpdated):
            self._logger.info(
                "Endorsement confidence score updated",
                extra={
                    "endorsement_id": event.endorsement_id,  # Already masked in domain
                    "provider_id": event.provider_id,  # Already masked in domain
                    "old_score": event.old_score,
                    "new_score": event.new_score,
                },
            )

    def _handle_metrics(self, event: DomainEvent) -> None:
        """Handle metrics collection for domain events."""
        if isinstance(event, PhoneNumberValidated):
            self._metrics.increment_counter(
                "phone_number_validations_total",
                {"region": event.region},
            )
        elif isinstance(event, PhoneNumberValidationError | PhoneNumberParseError):
            error_type = (
                "validation_error"
                if isinstance(event, PhoneNumberValidationError)
                else "parse_error"
            )
            if isinstance(event, PhoneNumberValidationError):
                error_type = event.error_type
            self._metrics.increment_counter(
                "phone_number_validation_errors_total",
                {"error_type": error_type},
            )
        elif isinstance(event, ProviderEndorsementIncremented):
            self._metrics.increment_counter(
                "provider_endorsement_increments_total",
                {"provider_category": event.provider_category},
            )
        elif isinstance(event, ProviderEndorsementDecremented):
            self._metrics.increment_counter(
                "provider_endorsement_decrements_total",
                {"provider_category": event.provider_category},
            )
        elif isinstance(event, ProviderTagAdded):
            self._metrics.increment_counter(
                "provider_tag_operations_total",
                {"operation": "add", "category": event.tag_category},
            )
        elif isinstance(event, ProviderTagRemoved):
            self._metrics.increment_counter(
                "provider_tag_operations_total",
                {"operation": "remove", "category": event.tag_category},
            )
        elif isinstance(event, EndorsementStatusChanged):
            self._metrics.increment_counter(
                "endorsement_status_changes_total",
                {
                    "operation": event.operation,
                    "endorsement_type": event.endorsement_type,
                },
            )
