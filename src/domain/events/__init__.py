"""
Domain events package for clean architecture separation.

This package contains sample domain events that demonstrate:
- Domain event patterns
- Event-driven architecture
- Clean separation of concerns
- Infrastructure-independent event publishing

Replace these with your actual domain events.
"""

from .base import DomainEvent, DomainEventPublisher
from .order_events import (
    OrderCancelled,
    OrderDelivered,
    OrderPlaced,
    OrderShipped,
    OrderStatusChanged,
    OrderUpdated,
)
from .registry import DomainEventRegistry
from .user_events import UserCreated, UserDeleted, UserEmailVerified, UserStatusChanged, UserUpdated

__all__ = [
    "DomainEvent",
    "DomainEventPublisher",
    "DomainEventRegistry",
    "OrderCancelled",
    "OrderDelivered",
    "OrderPlaced",
    "OrderShipped",
    "OrderStatusChanged",
    "OrderUpdated",
    "UserCreated",
    "UserDeleted",
    "UserEmailVerified",
    "UserStatusChanged",
    "UserUpdated",
]
