"""Unit tests for simplified observability event publisher."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from src.domain.events import DomainEvent

from src.domain.events import DomainEvent, UserCreated
from src.infrastructure.events import ObservabilityEventPublisher


class TestObservabilityEventPublisher:
    """Test simplified observability event publisher."""

    @patch("src.infrastructure.events.observability_publisher.get_logger")
    @patch("src.infrastructure.events.observability_publisher.get_metrics_collector")
    def test_initializes_with_logger_and_metrics(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Initializes with logger and metrics collector."""
        publisher = ObservabilityEventPublisher()

        mock_get_logger.assert_called_once()
        mock_get_metrics.assert_called_once()
        assert publisher._logger == mock_get_logger.return_value
        assert publisher._metrics == mock_get_metrics.return_value

    @patch("src.infrastructure.events.observability_publisher.get_logger")
    @patch("src.infrastructure.events.observability_publisher.get_metrics_collector")
    def test_publishes_domain_event_with_generic_logging(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Publishes domain event with generic logging and metrics."""
        mock_logger = mock_get_logger.return_value
        mock_metrics = mock_get_metrics.return_value

        publisher = ObservabilityEventPublisher()

        event = UserCreated(
            user_id="user-123",
            user_email="test@example.com",
            user_name="Test User",
            occurred_at=datetime.now(UTC),
        )

        publisher.publish(event)

        # Verify generic logging was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "Domain event: %s"
        assert call_args[0][1] == "user_created"
        assert call_args[1]["event_type"] == "user_created"
        assert call_args[1]["user_id"] == "user-123"
        assert call_args[1]["user_email"] == "test@example.com"

        # Verify generic metrics were recorded
        mock_metrics.increment_counter.assert_called_once_with(
            "domain_events_total", {"event_type": "user_created"}
        )

    @patch("src.infrastructure.events.observability_publisher.get_logger")
    @patch("src.infrastructure.events.observability_publisher.get_metrics_collector")
    def test_publishes_batch_of_events(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Publishes batch of events by calling publish for each."""
        mock_logger = mock_get_logger.return_value
        mock_metrics = mock_get_metrics.return_value

        publisher = ObservabilityEventPublisher()

        events: list[DomainEvent] = [
            UserCreated(
                user_id="user-1",
                user_email="test1@example.com",
                user_name="User 1",
            ),
            UserCreated(
                user_id="user-2",
                user_email="test2@example.com",
                user_name="User 2",
            ),
        ]

        publisher.publish_batch(events)

        # Should have called logger and metrics for each event
        assert mock_logger.info.call_count == 2
        assert mock_metrics.increment_counter.call_count == 2

        # Verify each call had correct event type
        for call in mock_metrics.increment_counter.call_args_list:
            assert call[0] == ("domain_events_total", {"event_type": "user_created"})

    @patch("src.infrastructure.events.observability_publisher.get_logger")
    @patch("src.infrastructure.events.observability_publisher.get_metrics_collector")
    def test_handles_empty_batch(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Handles empty batch without errors."""
        mock_logger = mock_get_logger.return_value
        mock_metrics = mock_get_metrics.return_value

        publisher = ObservabilityEventPublisher()

        publisher.publish_batch([])

        mock_logger.info.assert_not_called()
        mock_metrics.increment_counter.assert_not_called()

    @patch("src.infrastructure.events.observability_publisher.get_logger")
    @patch("src.infrastructure.events.observability_publisher.get_metrics_collector")
    def test_includes_all_event_data_in_logs(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Includes all event data in log context."""
        mock_logger = mock_get_logger.return_value

        class CustomEvent(DomainEvent):
            name: str
            count: int
            active: bool

        publisher = ObservabilityEventPublisher()

        event = CustomEvent(name="test", count=42, active=True)  # type: ignore[call-arg]

        publisher.publish(event)

        call_args = mock_logger.info.call_args
        assert call_args[1]["name"] == "test"
        assert call_args[1]["count"] == 42
        assert call_args[1]["active"] is True
        assert call_args[1]["event_type"] == "CustomEvent"

    @patch("src.infrastructure.events.observability_publisher.get_logger")
    @patch("src.infrastructure.events.observability_publisher.get_metrics_collector")
    def test_formats_datetime_as_iso_string(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock
    ) -> None:
        """Formats datetime fields as ISO strings in logs."""
        mock_logger = mock_get_logger.return_value

        publisher = ObservabilityEventPublisher()

        event = UserCreated(
            user_id="user-123",
            user_email="test@example.com",
            user_name="Test User",
        )

        publisher.publish(event)

        call_args = mock_logger.info.call_args
        # occurred_at should be formatted as ISO string
        assert isinstance(call_args[1]["occurred_at"], str)
        assert "T" in call_args[1]["occurred_at"]  # ISO format indicator
        assert "+00:00" in call_args[1]["occurred_at"]  # UTC timezone
