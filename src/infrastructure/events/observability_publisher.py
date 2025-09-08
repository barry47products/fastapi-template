"""Infrastructure event publisher for observability (logging and metrics)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.infrastructure.observability import get_logger, get_metrics_collector

if TYPE_CHECKING:
    from src.domain.events import DomainEvent


class ObservabilityEventPublisher:
    """
    Simple event publisher for observability concerns.

    Handles domain events by logging them and recording metrics,
    maintaining clean separation between domain and infrastructure.
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
        self._log_event(event)
        self._record_metrics(event)

    def publish_batch(self, events: list[DomainEvent]) -> None:
        """
        Publish multiple domain events as a batch.

        Args:
            events: List of domain events to publish
        """
        for event in events:
            self.publish(event)

    def _log_event(self, event: DomainEvent) -> None:
        """Log domain event with structured data."""
        event_data = event.to_dict()

        self._logger.info(
            "Domain event: %s",
            event.event_type,
            event_type=event.event_type,
            event_id=str(event.event_id),
            occurred_at=event.occurred_at.isoformat(),
            aggregate_id=event.aggregate_id,
            **{
                k: v
                for k, v in event_data.items()
                if k not in {"event_id", "occurred_at", "event_type"}
            },
        )

    def _record_metrics(self, event: DomainEvent) -> None:
        """Record metrics for domain event."""
        self._metrics.increment_counter("domain_events_total", {"event_type": event.event_type})
