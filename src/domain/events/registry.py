"""Domain event registry for dependency-free event publishing."""

from .base import DomainEvent, DomainEventPublisher


class DomainEventRegistry:
    """
    Registry for domain event publishers using dependency injection.

    This allows domain models to publish events without direct dependencies
    on infrastructure layers. The application layer registers publishers
    and the domain layer publishes events through this registry.
    """

    _publisher: DomainEventPublisher | None = None

    @classmethod
    def register_publisher(cls, publisher: DomainEventPublisher) -> None:
        """
        Register a domain event publisher.

        Args:
            publisher: The publisher to register
        """
        cls._publisher = publisher

    @classmethod
    def publish(cls, event: DomainEvent) -> None:
        """
        Publish a domain event if a publisher is registered.

        Args:
            event: The domain event to publish
        """
        if cls._publisher is not None:
            cls._publisher.publish(event)

    @classmethod
    def publish_batch(cls, events: list[DomainEvent]) -> None:
        """
        Publish multiple domain events if a publisher is registered.

        Args:
            events: List of domain events to publish
        """
        if cls._publisher is not None:
            cls._publisher.publish_batch(events)

    @classmethod
    def clear_publisher(cls) -> None:
        """Clear the registered publisher (useful for testing)."""
        cls._publisher = None

    @classmethod
    def has_publisher(cls) -> bool:
        """Check if a publisher is registered."""
        return cls._publisher is not None
