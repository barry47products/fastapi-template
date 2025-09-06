"""Unit tests for domain event registry."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.domain.events.base import DomainEvent, DomainEventPublisher
from src.domain.events.registry import DomainEventRegistry


class TestDomainEventRegistry:
    """Test domain event registry behavior."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        DomainEventRegistry.clear_publisher()

    def teardown_method(self) -> None:
        """Clear registry after each test."""
        DomainEventRegistry.clear_publisher()

    def test_starts_with_no_publisher(self) -> None:
        """Starts with no publisher registered."""
        assert DomainEventRegistry.has_publisher() is False
        assert DomainEventRegistry._publisher is None

    def test_registers_publisher_successfully(self) -> None:
        """Registers publisher successfully."""
        mock_publisher = MagicMock(spec=DomainEventPublisher)

        DomainEventRegistry.register_publisher(mock_publisher)

        assert DomainEventRegistry.has_publisher() is True
        assert DomainEventRegistry._publisher is mock_publisher

    def test_replaces_existing_publisher(self) -> None:
        """Replaces existing publisher when new one is registered."""
        first_publisher = MagicMock(spec=DomainEventPublisher)
        second_publisher = MagicMock(spec=DomainEventPublisher)

        DomainEventRegistry.register_publisher(first_publisher)
        DomainEventRegistry.register_publisher(second_publisher)

        assert DomainEventRegistry.has_publisher() is True
        assert DomainEventRegistry._publisher is second_publisher
        assert DomainEventRegistry._publisher is not first_publisher

    def test_clears_publisher_successfully(self) -> None:
        """Clears publisher successfully."""
        mock_publisher = MagicMock(spec=DomainEventPublisher)

        DomainEventRegistry.register_publisher(mock_publisher)
        assert DomainEventRegistry.has_publisher() is True

        DomainEventRegistry.clear_publisher()
        assert DomainEventRegistry.has_publisher() is False
        assert DomainEventRegistry._publisher is None

    def test_publish_calls_registered_publisher(self) -> None:
        """Publish calls registered publisher."""
        mock_publisher = MagicMock(spec=DomainEventPublisher)
        DomainEventRegistry.register_publisher(mock_publisher)

        class TestEvent(DomainEvent):
            message: str = "test"

        event = TestEvent()  # type: ignore[call-arg]
        DomainEventRegistry.publish(event)

        mock_publisher.publish.assert_called_once_with(event)

    def test_publish_does_nothing_when_no_publisher(self) -> None:
        """Publish does nothing when no publisher is registered."""

        class TestEvent(DomainEvent):
            message: str = "test"

        event = TestEvent()  # type: ignore[call-arg]

        # Should not raise exception
        DomainEventRegistry.publish(event)

        # Verify no publisher was called (since none was registered)
        assert DomainEventRegistry.has_publisher() is False

    def test_publish_batch_calls_registered_publisher(self) -> None:
        """Publish batch calls registered publisher."""
        mock_publisher = MagicMock(spec=DomainEventPublisher)
        DomainEventRegistry.register_publisher(mock_publisher)

        class TestEvent(DomainEvent):
            message: str

        events: list[DomainEvent] = [TestEvent(message="first"), TestEvent(message="second")]  # type: ignore[call-arg]
        DomainEventRegistry.publish_batch(events)

        mock_publisher.publish_batch.assert_called_once_with(events)

    def test_publish_batch_does_nothing_when_no_publisher(self) -> None:
        """Publish batch does nothing when no publisher is registered."""

        class TestEvent(DomainEvent):
            message: str

        events: list[DomainEvent] = [TestEvent(message="first"), TestEvent(message="second")]  # type: ignore[call-arg]

        # Should not raise exception
        DomainEventRegistry.publish_batch(events)

        # Verify no publisher was called
        assert DomainEventRegistry.has_publisher() is False

    def test_publish_handles_multiple_different_events(self) -> None:
        """Publish handles multiple different event types."""
        mock_publisher = MagicMock(spec=DomainEventPublisher)
        DomainEventRegistry.register_publisher(mock_publisher)

        class FirstEvent(DomainEvent):
            data: str = "first_data"

        class SecondEvent(DomainEvent):
            count: int = 42

        event1 = FirstEvent()  # type: ignore[call-arg]
        event2 = SecondEvent()  # type: ignore[call-arg]

        DomainEventRegistry.publish(event1)
        DomainEventRegistry.publish(event2)

        assert mock_publisher.publish.call_count == 2
        mock_publisher.publish.assert_any_call(event1)
        mock_publisher.publish.assert_any_call(event2)

    def test_publish_batch_handles_empty_list(self) -> None:
        """Publish batch handles empty event list."""
        mock_publisher = MagicMock(spec=DomainEventPublisher)
        DomainEventRegistry.register_publisher(mock_publisher)

        empty_events: list[DomainEvent] = []
        DomainEventRegistry.publish_batch(empty_events)

        mock_publisher.publish_batch.assert_called_once_with(empty_events)

    def test_publish_batch_handles_mixed_event_types(self) -> None:
        """Publish batch handles mixed event types."""
        mock_publisher = MagicMock(spec=DomainEventPublisher)
        DomainEventRegistry.register_publisher(mock_publisher)

        class OrderEvent(DomainEvent):
            order_id: str = "order_123"

        class PaymentEvent(DomainEvent):
            payment_id: str = "payment_456"

        class UserEvent(DomainEvent):
            user_id: str = "user_789"

        events: list[DomainEvent] = [OrderEvent(), PaymentEvent(), UserEvent()]  # type: ignore[call-arg]
        DomainEventRegistry.publish_batch(events)

        mock_publisher.publish_batch.assert_called_once_with(events)
        call_args = mock_publisher.publish_batch.call_args[0][0]
        assert len(call_args) == 3
        assert isinstance(call_args[0], OrderEvent)
        assert isinstance(call_args[1], PaymentEvent)
        assert isinstance(call_args[2], UserEvent)

    def test_registry_is_singleton_like(self) -> None:
        """Registry maintains state across calls (singleton-like behavior)."""
        mock_publisher = MagicMock(spec=DomainEventPublisher)

        # Register in one call
        DomainEventRegistry.register_publisher(mock_publisher)

        # Verify in another call
        assert DomainEventRegistry.has_publisher() is True

        # Clear in third call
        DomainEventRegistry.clear_publisher()

        # Verify cleared in fourth call
        assert DomainEventRegistry.has_publisher() is False

    def test_supports_concrete_publisher_implementation(self) -> None:
        """Supports concrete publisher implementation."""

        class ConcretePublisher(DomainEventPublisher):
            def __init__(self) -> None:
                self.published_events: list[DomainEvent] = []
                self.batch_calls: int = 0

            def publish(self, event: DomainEvent) -> None:
                self.published_events.append(event)

            def publish_batch(self, events: list[DomainEvent]) -> None:
                self.published_events.extend(events)
                self.batch_calls += 1

        publisher = ConcretePublisher()
        DomainEventRegistry.register_publisher(publisher)

        class SampleEvent(DomainEvent):
            value: int

        event1 = SampleEvent(value=1)  # type: ignore[call-arg]
        event2 = SampleEvent(value=2)  # type: ignore[call-arg]
        event3 = SampleEvent(value=3)  # type: ignore[call-arg]

        # Test individual publish
        DomainEventRegistry.publish(event1)
        assert len(publisher.published_events) == 1
        assert isinstance(publisher.published_events[0], SampleEvent)
        assert publisher.published_events[0].value == 1

        # Test batch publish
        batch_events: list[DomainEvent] = [event2, event3]
        DomainEventRegistry.publish_batch(batch_events)
        assert len(publisher.published_events) == 3
        assert publisher.batch_calls == 1
        assert isinstance(publisher.published_events[1], SampleEvent)
        assert isinstance(publisher.published_events[2], SampleEvent)
        assert publisher.published_events[1].value == 2
        assert publisher.published_events[2].value == 3

    def test_registry_methods_are_class_methods(self) -> None:
        """Registry methods are class methods (no instance needed)."""
        # Can call without instantiating registry
        assert DomainEventRegistry.has_publisher() is False

        mock_publisher = MagicMock(spec=DomainEventPublisher)
        DomainEventRegistry.register_publisher(mock_publisher)

        assert DomainEventRegistry.has_publisher() is True

        # Class method calls should work
        class TestEvent(DomainEvent):
            pass

        event = TestEvent()  # type: ignore[call-arg]
        DomainEventRegistry.publish(event)
        DomainEventRegistry.publish_batch([event])

        assert mock_publisher.publish.called
        assert mock_publisher.publish_batch.called

    def test_publisher_exception_propagates(self) -> None:
        """Publisher exceptions propagate through registry."""

        class FailingPublisher(DomainEventPublisher):
            def publish(self, event: DomainEvent) -> None:
                raise ValueError("Publisher failed")

            def publish_batch(self, events: list[DomainEvent]) -> None:
                raise RuntimeError("Batch publish failed")

        publisher = FailingPublisher()
        DomainEventRegistry.register_publisher(publisher)

        class TestEvent(DomainEvent):
            pass

        event = TestEvent()  # type: ignore[call-arg]

        # Test single publish exception
        with pytest.raises(ValueError, match="Publisher failed"):
            DomainEventRegistry.publish(event)

        # Test batch publish exception
        events: list[DomainEvent] = [event]
        with pytest.raises(RuntimeError, match="Batch publish failed"):
            DomainEventRegistry.publish_batch(events)
