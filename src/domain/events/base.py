"""Base domain event classes for clean architecture separation."""

# pylint: disable=E1136,W0107
# E1136: Pylint doesn't understand Pydantic's dynamic model_fields access
# W0107: Abstract method pass statements are intentional for interface definition

from datetime import datetime, UTC
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """
    Base class for all domain events.

    Domain events represent business operations that have occurred in the domain
    and need to be communicated to infrastructure layers for cross-cutting concerns
    like logging, metrics, and external system notifications.
    """

    model_config = {"frozen": True}

    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str = Field(init=False)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Set event_type based on class name."""
        super().__init_subclass__(**kwargs)
        # pylint: disable=unsubscriptable-object
        cls.model_fields["event_type"].default = cls.__name__
        # pylint: enable=unsubscriptable-object

    @property
    def aggregate_id(self) -> str:
        """Override in subclasses to provide the aggregate identifier."""
        return ""

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return self.model_dump()


@runtime_checkable
class DomainEventPublisher(Protocol):
    """
    Protocol for domain event publishers.

    Infrastructure layers implement this interface to receive domain events
    and handle cross-cutting concerns without coupling the domain to infrastructure.
    """

    def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event.

        Args:
            event: The domain event to publish
        """

    def publish_batch(self, events: list[DomainEvent]) -> None:
        """
        Publish multiple domain events as a batch.

        Args:
            events: List of domain events to publish
        """
