"""Infrastructure event publisher for observability (logging and metrics)."""

from src.domain.events import (
    DomainEvent,
    DomainEventPublisher,
    OrderCancelled,
    OrderDelivered,
    OrderPlaced,
    OrderShipped,
    OrderStatusChanged,
    OrderUpdated,
    UserCreated,
    UserDeleted,
    UserEmailVerified,
    UserStatusChanged,
    UserUpdated,
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
        # User events
        if isinstance(event, UserCreated):
            self._logger.info(
                "User created",
                user_id=event.user_id,
                email=event.email,
            )
        elif isinstance(event, UserUpdated):
            self._logger.info(
                "User updated",
                user_id=event.user_id,
                changes=len(event.changes),
            )
        elif isinstance(event, UserStatusChanged):
            self._logger.info(
                "User status changed",
                user_id=event.user_id,
                old_status=event.old_status,
                new_status=event.new_status,
            )
        elif isinstance(event, UserEmailVerified):
            self._logger.info(
                "User email verified",
                user_id=event.user_id,
                email=event.email,
            )
        elif isinstance(event, UserDeleted):
            self._logger.info(
                "User deleted",
                user_id=event.user_id,
                reason=event.reason,
            )

        # Order events
        elif isinstance(event, OrderPlaced):
            self._logger.info(
                "Order placed",
                order_id=event.order_id,
                user_id=event.user_id,
                item_count=event.item_count,
                total_amount=float(event.total_amount.amount),
                currency=event.total_amount.currency,
            )
        elif isinstance(event, OrderUpdated):
            self._logger.info(
                "Order updated",
                order_id=event.order_id,
                changes=len(event.changes),
            )
        elif isinstance(event, OrderStatusChanged):
            self._logger.info(
                "Order status changed",
                order_id=event.order_id,
                old_status=event.old_status,
                new_status=event.new_status,
            )
        elif isinstance(event, OrderShipped):
            self._logger.info(
                "Order shipped",
                order_id=event.order_id,
                tracking_number=event.tracking_number,
                carrier=event.carrier,
                estimated_delivery=event.estimated_delivery_date.isoformat() if event.estimated_delivery_date else None,
            )
        elif isinstance(event, OrderDelivered):
            self._logger.info(
                "Order delivered",
                order_id=event.order_id,
                delivered_at=event.delivered_at.isoformat(),
            )
        elif isinstance(event, OrderCancelled):
            self._logger.info(
                "Order cancelled",
                order_id=event.order_id,
                reason=event.reason,
                refund_amount=float(event.refund_amount.amount) if event.refund_amount else None,
            )

        # Generic domain event logging
        else:
            self._logger.info(
                "Domain event published",
                event_type=event.event_type,
                occurred_at=event.occurred_at.isoformat(),
            )

    def _handle_metrics(self, event: DomainEvent) -> None:
        """Handle metrics collection for domain events."""
        # User metrics
        if isinstance(event, UserCreated):
            self._metrics.increment_counter("users_created_total", {})
        elif isinstance(event, UserUpdated):
            self._metrics.increment_counter("users_updated_total", {})
        elif isinstance(event, UserStatusChanged):
            self._metrics.increment_counter(
                "user_status_changes_total",
                {"old_status": event.old_status, "new_status": event.new_status},
            )
        elif isinstance(event, UserEmailVerified):
            self._metrics.increment_counter("user_email_verifications_total", {})
        elif isinstance(event, UserDeleted):
            self._metrics.increment_counter("users_deleted_total", {"reason": event.reason})

        # Order metrics
        elif isinstance(event, OrderPlaced):
            self._metrics.increment_counter("orders_placed_total", {})
            self._metrics.record_histogram(
                "order_total_amount",
                float(event.total_amount.amount),
                {"currency": event.total_amount.currency},
            )
        elif isinstance(event, OrderUpdated):
            self._metrics.increment_counter("orders_updated_total", {})
        elif isinstance(event, OrderStatusChanged):
            self._metrics.increment_counter(
                "order_status_changes_total",
                {"old_status": event.old_status, "new_status": event.new_status},
            )
        elif isinstance(event, OrderShipped):
            self._metrics.increment_counter("orders_shipped_total", {"carrier": event.carrier})
        elif isinstance(event, OrderDelivered):
            self._metrics.increment_counter("orders_delivered_total", {})
        elif isinstance(event, OrderCancelled):
            self._metrics.increment_counter("orders_cancelled_total", {"reason": event.reason})

        # Generic domain event metrics
        else:
            self._metrics.increment_counter(
                "domain_events_published_total",
                {"event_type": event.event_type},
            )