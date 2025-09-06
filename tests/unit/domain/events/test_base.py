"""Unit tests for domain event base classes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError

from src.domain.events.base import DomainEvent, DomainEventPublisher


class TestDomainEvent:
    """Test domain event base class behavior."""

    def test_creates_event_with_default_values(self) -> None:
        """Creates event with default values."""

        class TestEvent(DomainEvent):
            data: str = "test_data"

        event = TestEvent(data="sample")  # type: ignore[call-arg]

        assert isinstance(event.event_id, UUID)
        assert isinstance(event.occurred_at, datetime)
        assert event.occurred_at.tzinfo == UTC
        assert event.event_type == "TestEvent"
        assert event.data == "sample"

    def test_creates_event_with_custom_values(self) -> None:
        """Creates event with custom values."""

        class CustomEvent(DomainEvent):
            message: str

        custom_time = datetime.now(UTC)
        custom_id = UUID("12345678-1234-5678-1234-567812345678")

        event = CustomEvent(  # type: ignore[call-arg]
            message="custom_message",
            event_id=custom_id,
            occurred_at=custom_time,
        )

        assert event.event_id == custom_id
        assert event.occurred_at == custom_time
        assert event.event_type == "CustomEvent"
        assert event.message == "custom_message"

    def test_event_is_frozen(self) -> None:
        """Event is frozen and immutable."""

        class ImmutableEvent(DomainEvent):
            value: int = 42

        event = ImmutableEvent()  # type: ignore[call-arg]

        with pytest.raises(ValidationError, match="Instance is frozen"):
            event.value = 100  # type: ignore[misc]

        with pytest.raises(ValidationError, match="Instance is frozen"):
            event.event_id = UUID("12345678-1234-5678-1234-567812345678")  # type: ignore[misc]

    def test_event_type_set_automatically(self) -> None:
        """Event type is set automatically from class name."""

        class OrderCreated(DomainEvent):
            order_id: str = "order_123"

        class UserRegistered(DomainEvent):
            user_id: str = "user_456"

        order_event = OrderCreated()  # type: ignore[call-arg]
        user_event = UserRegistered()  # type: ignore[call-arg]

        assert order_event.event_type == "OrderCreated"
        assert user_event.event_type == "UserRegistered"

    def test_aggregate_id_returns_empty_string_by_default(self) -> None:
        """Aggregate ID returns empty string by default."""

        class SimpleEvent(DomainEvent):
            pass

        event = SimpleEvent()  # type: ignore[call-arg]

        assert event.aggregate_id == ""

    def test_aggregate_id_can_be_overridden(self) -> None:
        """Aggregate ID can be overridden in subclasses."""

        class EntityEvent(DomainEvent):
            entity_id: str

            @property
            def aggregate_id(self) -> str:
                return self.entity_id

        event = EntityEvent(entity_id="entity_789")  # type: ignore[call-arg]

        assert event.aggregate_id == "entity_789"

    def test_to_dict_returns_serializable_dictionary(self) -> None:
        """To dict returns serializable dictionary."""

        class SerializableEvent(DomainEvent):
            name: str
            count: int
            active: bool

        event = SerializableEvent(name="test", count=5, active=True)  # type: ignore[call-arg]
        event_dict = event.to_dict()

        assert isinstance(event_dict, dict)
        assert "event_id" in event_dict
        assert "occurred_at" in event_dict
        assert "event_type" in event_dict
        assert event_dict["name"] == "test"
        assert event_dict["count"] == 5
        assert event_dict["active"] is True
        assert event_dict["event_type"] == "SerializableEvent"

    def test_to_dict_includes_all_fields(self) -> None:
        """To dict includes all event fields."""

        class ComplexEvent(DomainEvent):
            data: dict[str, str]
            items: list[int]

        event = ComplexEvent(  # type: ignore[call-arg]
            data={"key": "value"},
            items=[1, 2, 3],
        )
        event_dict = event.to_dict()

        assert len(event_dict) == 5  # event_id, occurred_at, event_type, data, items
        assert event_dict["data"] == {"key": "value"}
        assert event_dict["items"] == [1, 2, 3]

    def test_event_inherits_from_basemodel(self) -> None:
        """Event inherits from Pydantic BaseModel."""

        class InheritanceEvent(DomainEvent):
            pass

        event = InheritanceEvent()  # type: ignore[call-arg]

        assert isinstance(event, BaseModel)
        assert isinstance(event, DomainEvent)

    def test_event_validates_field_types(self) -> None:
        """Event validates field types using Pydantic."""

        class TypedEvent(DomainEvent):
            count: int
            name: str

        # Valid creation
        valid_event = TypedEvent(count=10, name="valid")  # type: ignore[call-arg]
        assert valid_event.count == 10
        assert valid_event.name == "valid"

        # Invalid types should raise validation error
        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            TypedEvent(count="not_a_number", name="test")  # type: ignore[call-arg,arg-type]

    def test_event_id_is_unique_across_instances(self) -> None:
        """Event ID is unique across different instances."""

        class UniqueEvent(DomainEvent):
            pass

        event1 = UniqueEvent()  # type: ignore[call-arg]
        event2 = UniqueEvent()  # type: ignore[call-arg]

        assert event1.event_id != event2.event_id
        assert isinstance(event1.event_id, UUID)
        assert isinstance(event2.event_id, UUID)

    def test_occurred_at_is_recent(self) -> None:
        """Occurred at timestamp is recent when created."""

        class TimestampEvent(DomainEvent):
            pass

        before_creation = datetime.now(UTC)
        event = TimestampEvent()  # type: ignore[call-arg]
        after_creation = datetime.now(UTC)

        assert before_creation <= event.occurred_at <= after_creation

    def test_multiple_inheritance_sets_correct_event_types(self) -> None:
        """Multiple inheritance sets correct event types."""

        class BaseBusinessEvent(DomainEvent):
            business_id: str = "default"

        class OrderPlaced(BaseBusinessEvent):
            order_id: str = "order_001"

        class PaymentProcessed(BaseBusinessEvent):
            payment_id: str = "payment_001"

        order_event = OrderPlaced()  # type: ignore[call-arg]
        payment_event = PaymentProcessed()  # type: ignore[call-arg]

        assert order_event.event_type == "OrderPlaced"
        assert payment_event.event_type == "PaymentProcessed"


class TestDomainEventPublisher:
    """Test domain event publisher interface."""

    def test_is_abstract_base_class(self) -> None:
        """Is abstract base class that cannot be instantiated."""

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            DomainEventPublisher()  # type: ignore[abstract]

    def test_requires_publish_implementation(self) -> None:
        """Requires publish method implementation."""

        class IncompletePublisher(DomainEventPublisher):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompletePublisher()  # type: ignore[abstract]

    def test_requires_publish_batch_implementation(self) -> None:
        """Requires publish batch method implementation."""

        class PartialPublisher(DomainEventPublisher):
            def publish(self, event: DomainEvent) -> None:
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            PartialPublisher()  # type: ignore[abstract]

    def test_allows_concrete_implementation(self) -> None:
        """Allows concrete implementation with all methods."""

        class ConcretePublisher(DomainEventPublisher):
            def __init__(self) -> None:
                self.published_events: list[DomainEvent] = []

            def publish(self, event: DomainEvent) -> None:
                self.published_events.append(event)

            def publish_batch(self, events: list[DomainEvent]) -> None:
                self.published_events.extend(events)

        publisher = ConcretePublisher()
        assert isinstance(publisher, DomainEventPublisher)
        assert hasattr(publisher, "publish")
        assert hasattr(publisher, "publish_batch")

    def test_concrete_implementation_works_correctly(self) -> None:
        """Concrete implementation works correctly."""

        class WorkingPublisher(DomainEventPublisher):
            def __init__(self) -> None:
                self.events: list[DomainEvent] = []

            def publish(self, event: DomainEvent) -> None:
                self.events.append(event)

            def publish_batch(self, events: list[DomainEvent]) -> None:
                self.events.extend(events)

        class TestEvent(DomainEvent):
            message: str

        publisher = WorkingPublisher()
        event1 = TestEvent(message="first")  # type: ignore[call-arg]
        event2 = TestEvent(message="second")  # type: ignore[call-arg]
        event3 = TestEvent(message="third")  # type: ignore[call-arg]

        # Test single publish
        publisher.publish(event1)
        assert len(publisher.events) == 1
        assert isinstance(publisher.events[0], TestEvent)
        assert publisher.events[0].message == "first"

        # Test batch publish
        publisher.publish_batch([event2, event3])
        assert len(publisher.events) == 3
        assert isinstance(publisher.events[1], TestEvent)
        assert isinstance(publisher.events[2], TestEvent)
        assert publisher.events[1].message == "second"
        assert publisher.events[2].message == "third"

    def test_supports_polymorphic_usage(self) -> None:
        """Supports polymorphic usage through interface."""

        class MockPublisher(DomainEventPublisher):
            def __init__(self) -> None:
                self.call_count = 0

            def publish(self, event: DomainEvent) -> None:
                self.call_count += 1

            def publish_batch(self, events: list[DomainEvent]) -> None:
                self.call_count += len(events)

        class SimpleEvent(DomainEvent):
            pass

        def use_publisher(publisher: DomainEventPublisher) -> None:
            event = SimpleEvent()  # type: ignore[call-arg]
            publisher.publish(event)
            publisher.publish_batch([event, event])

        mock_publisher = MockPublisher()
        use_publisher(mock_publisher)

        assert mock_publisher.call_count == 3  # 1 + 2 from batch
