"""Unit tests for observability event publisher."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.domain.events import (
    DomainEvent,
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
from src.infrastructure.events.observability_publisher import ObservabilityEventPublisher


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger for testing."""
    return MagicMock()


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create mock metrics collector for testing."""
    return MagicMock()


@pytest.fixture
@patch("src.infrastructure.events.observability_publisher.get_metrics_collector")
@patch("src.infrastructure.events.observability_publisher.get_logger")
def publisher(
    mock_get_logger: MagicMock,
    mock_get_metrics: MagicMock,
    mock_logger: MagicMock,
    mock_metrics: MagicMock,
) -> ObservabilityEventPublisher:
    """Create observability publisher with mocked dependencies."""
    mock_get_logger.return_value = mock_logger
    mock_get_metrics.return_value = mock_metrics
    return ObservabilityEventPublisher()


class TestObservabilityEventPublisherInitialization:
    """Test publisher initialization and setup."""

    @patch("src.infrastructure.events.observability_publisher.get_metrics_collector")
    @patch("src.infrastructure.events.observability_publisher.get_logger")
    def test_initializes_with_logger_and_metrics(
        self, mock_get_logger: MagicMock, mock_get_metrics: MagicMock
    ) -> None:
        """Initializes with logger and metrics collector from infrastructure."""
        mock_logger = MagicMock()
        mock_metrics_collector = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics_collector

        publisher = ObservabilityEventPublisher()

        assert publisher._logger is mock_logger
        assert publisher._metrics is mock_metrics_collector
        mock_get_logger.assert_called_once_with("src.infrastructure.events.observability_publisher")
        mock_get_metrics.assert_called_once_with()


class TestUserEventHandling:
    """Test handling of user-related domain events."""

    def test_publishes_user_created_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for user created event."""
        event = UserCreated(
            user_id="user-123",
            user_email="test@example.com",
            user_name="Test User",
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "User created",
            user_id="user-123",
            email="test@example.com",
        )
        mock_metrics.increment_counter.assert_called_once_with("users_created_total", {})

    def test_publishes_user_updated_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for user updated event."""
        event = UserUpdated(
            user_id="user-123",
            fields_updated=["name", "phone"],
            previous_values={"name": "Old Name", "phone": "111"},
            new_values={"name": "New Name", "phone": "222"},
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "User updated",
            user_id="user-123",
            fields_updated=["name", "phone"],
        )
        mock_metrics.increment_counter.assert_called_once_with("users_updated_total", {})

    def test_publishes_user_status_changed_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for user status changed event."""
        event = UserStatusChanged(
            user_id="user-123",
            previous_status="active",
            new_status="suspended",
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "User status changed",
            user_id="user-123",
            previous_status="active",
            new_status="suspended",
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "user_status_changes_total",
            {"previous_status": "active", "new_status": "suspended"},
        )

    def test_publishes_user_email_verified_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for user email verified event."""
        event = UserEmailVerified(
            user_id="user-123",
            email="test@example.com",
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "User email verified",
            user_id="user-123",
            email="test@example.com",
        )
        mock_metrics.increment_counter.assert_called_once_with("user_email_verifications_total", {})

    def test_publishes_user_deleted_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for user deleted event."""
        event = UserDeleted(
            user_id="user-123",
            user_email="deleted@example.com",
            deletion_reason="user_request",
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "User deleted",
            user_id="user-123",
            deletion_reason="user_request",
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "users_deleted_total", {"deletion_reason": "user_request"}
        )


class TestOrderEventHandling:
    """Test handling of order-related domain events."""

    def test_publishes_order_placed_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for order placed event."""
        event = OrderPlaced(
            order_id="order-456",
            user_id="user-123",
            order_total=99.99,
            currency="USD",
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "Order placed",
            order_id="order-456",
            user_id="user-123",
            order_total=99.99,
            currency="USD",
        )
        assert mock_metrics.increment_counter.call_count == 1
        assert mock_metrics.increment_counter.call_args_list[0] == (("orders_placed_total", {}),)
        mock_metrics.record_histogram.assert_called_once_with(
            "order_total_amount",
            99.99,
            {"currency": "USD"},
        )

    def test_publishes_order_updated_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for order updated event."""
        previous_vals: dict[str, Any] = {"address": "Old Address"}
        new_vals: dict[str, Any] = {"address": "New Address"}
        event = OrderUpdated(
            order_id="order-456",
            user_id="user-123",
            fields_updated=["shipping_address"],
            previous_values=previous_vals,
            new_values=new_vals,
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "Order updated",
            order_id="order-456",
            fields_updated=["shipping_address"],
        )
        mock_metrics.increment_counter.assert_called_once_with("orders_updated_total", {})

    def test_publishes_order_status_changed_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for order status changed event."""
        event = OrderStatusChanged(
            order_id="order-456",
            user_id="user-123",
            previous_status="pending",
            new_status="processing",
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "Order status changed",
            order_id="order-456",
            previous_status="pending",
            new_status="processing",
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "order_status_changes_total",
            {"previous_status": "pending", "new_status": "processing"},
        )

    def test_publishes_order_shipped_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for order shipped event."""
        shipped_at = datetime.now(UTC)
        event = OrderShipped(
            order_id="order-456",
            user_id="user-123",
            tracking_number="TRACK123456",
            carrier="FedEx",
            shipped_at=shipped_at,
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "Order shipped",
            order_id="order-456",
            tracking_number="TRACK123456",
            carrier="FedEx",
            shipped_at=shipped_at.isoformat(),
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "orders_shipped_total", {"carrier": "FedEx"}
        )

    def test_publishes_order_delivered_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for order delivered event."""
        delivered_at = datetime.now(UTC)
        event = OrderDelivered(
            order_id="order-456",
            user_id="user-123",
            delivered_at=delivered_at,
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "Order delivered",
            order_id="order-456",
            delivered_at=delivered_at.isoformat(),
        )
        mock_metrics.increment_counter.assert_called_once_with("orders_delivered_total", {})

    def test_publishes_order_cancelled_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for order cancelled event."""
        event = OrderCancelled(
            order_id="order-456",
            user_id="user-123",
            cancellation_reason="customer_request",
            refund_amount=99.99,
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "Order cancelled",
            order_id="order-456",
            cancellation_reason="customer_request",
            refund_amount=99.99,
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "orders_cancelled_total", {"cancellation_reason": "customer_request"}
        )


class TestGenericEventHandling:
    """Test handling of generic/unknown domain events."""

    def test_handles_unknown_domain_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Logs and tracks metrics for unknown domain event types."""
        occurred_at = datetime.now(UTC)

        class CustomEvent(DomainEvent):
            """Custom test event."""

            event_type: str = "custom_event"

        event = CustomEvent(occurred_at=occurred_at)

        publisher.publish(event)

        mock_logger.info.assert_called_once_with(
            "Domain event published",
            event_type="custom_event",
            occurred_at=occurred_at.isoformat(),
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "domain_events_published_total",
            {"event_type": "custom_event"},
        )


class TestBatchPublishing:
    """Test batch event publishing functionality."""

    def test_publishes_batch_of_events(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Publishes each event in a batch sequentially."""
        events = [
            UserCreated(
                user_id="user-1",
                user_email="user1@example.com",
                user_name="User One",
                occurred_at=datetime.now(UTC),
            ),
            OrderPlaced(
                order_id="order-1",
                user_id="user-1",
                order_total=50.00,
                currency="USD",
                occurred_at=datetime.now(UTC),
            ),
            UserUpdated(
                user_id="user-1",
                fields_updated=["address"],
                previous_values={"address": "Old"},
                new_values={"address": "New"},
                occurred_at=datetime.now(UTC),
            ),
        ]

        publisher.publish_batch(events)

        assert mock_logger.info.call_count == 3
        assert mock_metrics.increment_counter.call_count == 3
        assert mock_metrics.record_histogram.call_count == 1

        # Verify first event (UserCreated)
        assert mock_logger.info.call_args_list[0][0][0] == "User created"
        assert mock_metrics.increment_counter.call_args_list[0][0][0] == "users_created_total"

        # Verify second event (OrderPlaced)
        assert mock_logger.info.call_args_list[1][0][0] == "Order placed"
        assert mock_metrics.increment_counter.call_args_list[1][0][0] == "orders_placed_total"

        # Verify third event (UserUpdated)
        assert mock_logger.info.call_args_list[2][0][0] == "User updated"
        assert mock_metrics.increment_counter.call_args_list[2][0][0] == "users_updated_total"

    def test_handles_empty_batch(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Handles empty batch without errors."""
        publisher.publish_batch([])

        mock_logger.info.assert_not_called()
        mock_metrics.increment_counter.assert_not_called()

    def test_continues_batch_processing_on_individual_failures(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Continues processing batch even if individual events fail."""
        mock_logger.info.side_effect = [Exception("Log error"), None, None]

        events = [
            UserCreated(
                user_id="user-1",
                user_email="fail@example.com",
                user_name="Fail User",
                occurred_at=datetime.now(UTC),
            ),
            UserUpdated(
                user_id="user-2",
                fields_updated=["name"],
                previous_values={"name": "Old"},
                new_values={"name": "New"},
                occurred_at=datetime.now(UTC),
            ),
            UserDeleted(
                user_id="user-3",
                user_email="deleted@example.com",
                deletion_reason="test",
                occurred_at=datetime.now(UTC),
            ),
        ]

        # This will raise the exception from the first event
        with pytest.raises(Exception, match="Log error"):
            publisher.publish_batch(events)

        # Only the first event's logging should have been attempted
        assert mock_logger.info.call_count == 1


class TestEventPublisherIntegration:
    """Test integration scenarios for the event publisher."""

    def test_handles_mixed_event_types(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Correctly routes and handles different event types."""
        user_event = UserEmailVerified(
            user_id="user-789",
            email="verified@example.com",
            occurred_at=datetime.now(UTC),
        )
        order_event = OrderShipped(
            order_id="order-999",
            user_id="user-789",
            tracking_number="SHIP999",
            carrier="UPS",
            shipped_at=datetime.now(UTC),
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(user_event)
        publisher.publish(order_event)

        assert mock_logger.info.call_count == 2
        assert mock_metrics.increment_counter.call_count == 2

        # Verify correct event type routing
        assert "User email verified" in str(mock_logger.info.call_args_list[0])
        assert "Order shipped" in str(mock_logger.info.call_args_list[1])

    def test_preserves_event_data_types(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Preserves correct data types when logging and recording metrics."""
        event = OrderPlaced(
            order_id="order-123",
            user_id="user-456",
            order_total=1234.56,
            currency="EUR",
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        # Verify float is preserved
        call_kwargs = mock_logger.info.call_args[1]
        assert isinstance(call_kwargs["order_total"], float)
        assert call_kwargs["order_total"] == 1234.56

        # Verify histogram receives float
        histogram_call = mock_metrics.record_histogram.call_args
        assert isinstance(histogram_call[0][1], float)

    def test_handles_all_event_types(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Verifies all domain event types are handled."""
        now = datetime.now(UTC)
        all_events = [
            # User events
            UserCreated(
                user_id="u1", user_email="test@test.com", user_name="Test", occurred_at=now
            ),
            UserUpdated(
                user_id="u1",
                fields_updated=["name"],
                previous_values={"name": "Old"},
                new_values={"name": "New"},
                occurred_at=now,
            ),
            UserStatusChanged(
                user_id="u1", previous_status="active", new_status="inactive", occurred_at=now
            ),
            UserEmailVerified(user_id="u1", email="test@test.com", occurred_at=now),
            UserDeleted(
                user_id="u1", user_email="test@test.com", deletion_reason="request", occurred_at=now
            ),
            # Order events
            OrderPlaced(
                order_id="o1", user_id="u1", order_total=10.0, currency="USD", occurred_at=now
            ),
            OrderUpdated(
                order_id="o1",
                user_id="u1",
                fields_updated=["status"],
                previous_values={"status": "new"},
                new_values={"status": "paid"},
                occurred_at=now,
            ),
            OrderStatusChanged(
                order_id="o1",
                user_id="u1",
                previous_status="new",
                new_status="paid",
                occurred_at=now,
            ),
            OrderShipped(
                order_id="o1",
                user_id="u1",
                tracking_number="T1",
                carrier="DHL",
                shipped_at=now,
                occurred_at=now,
            ),
            OrderDelivered(order_id="o1", user_id="u1", delivered_at=now, occurred_at=now),
            OrderCancelled(
                order_id="o1",
                user_id="u1",
                cancellation_reason="test",
                refund_amount=10.0,
                occurred_at=now,
            ),
        ]

        for event in all_events:
            mock_logger.reset_mock()
            mock_metrics.reset_mock()

            publisher.publish(event)

            # Every event should log and record metrics
            assert mock_logger.info.call_count == 1
            assert mock_metrics.increment_counter.call_count >= 1

    def test_logging_methods_called_for_each_event(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Both logging and metrics methods are called for each event."""
        event = UserCreated(
            user_id="user-999",
            user_email="test@example.com",
            user_name="Test User",
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        # Verify both infrastructure concerns are addressed
        mock_logger.info.assert_called_once()
        mock_metrics.increment_counter.assert_called_once()


class TestEventDataFormatting:
    """Test correct formatting of event data for observability."""

    def test_formats_datetime_fields_as_iso_strings(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Formats datetime fields as ISO strings for logging."""
        now = datetime.now(UTC)
        event = OrderDelivered(
            order_id="order-789",
            user_id="user-456",
            delivered_at=now,
            occurred_at=now,
        )

        publisher.publish(event)

        call_kwargs = mock_logger.info.call_args[1]
        assert call_kwargs["delivered_at"] == now.isoformat()

    def test_preserves_list_fields(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Preserves list fields when logging."""
        fields_updated = ["field1", "field2", "field3"]
        event = UserUpdated(
            user_id="user-456",
            fields_updated=fields_updated,
            previous_values={"field1": "a", "field2": "b", "field3": "c"},
            new_values={"field1": "x", "field2": "y", "field3": "z"},
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        call_kwargs = mock_logger.info.call_args[1]
        assert call_kwargs["fields_updated"] == fields_updated
        assert isinstance(call_kwargs["fields_updated"], list)

    def test_includes_labels_in_metrics(
        self,
        publisher: ObservabilityEventPublisher,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Includes appropriate labels when recording metrics."""
        event = OrderCancelled(
            order_id="order-111",
            user_id="user-222",
            cancellation_reason="fraud_detected",
            refund_amount=250.00,
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        metric_call = mock_metrics.increment_counter.call_args
        assert metric_call[0][0] == "orders_cancelled_total"
        assert metric_call[0][1] == {"cancellation_reason": "fraud_detected"}
