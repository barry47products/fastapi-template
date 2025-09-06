"""Sample domain events for order-related operations."""

from datetime import datetime, UTC
from typing import Any

from .base import DomainEvent


class OrderPlaced(DomainEvent):
    """Domain event published when a new order is placed."""

    event_type: str = "order_placed"
    order_id: str
    user_id: str
    order_total: float
    currency: str = "USD"
    order_timestamp: datetime = datetime.now(UTC)


class OrderUpdated(DomainEvent):
    """Domain event published when order details are updated."""

    event_type: str = "order_updated"
    order_id: str
    user_id: str
    fields_updated: list[str]
    previous_values: dict[str, Any]
    new_values: dict[str, Any]


class OrderCancelled(DomainEvent):
    """Domain event published when an order is cancelled."""

    event_type: str = "order_cancelled"
    order_id: str
    user_id: str
    cancellation_reason: str
    cancelled_at: datetime = datetime.now(UTC)
    refund_amount: float = 0.0


class OrderShipped(DomainEvent):
    """Domain event published when an order is shipped."""

    event_type: str = "order_shipped"
    order_id: str
    user_id: str
    tracking_number: str
    carrier: str
    shipped_at: datetime = datetime.now(UTC)


class OrderDelivered(DomainEvent):
    """Domain event published when an order is delivered."""

    event_type: str = "order_delivered"
    order_id: str
    user_id: str
    delivered_at: datetime = datetime.now(UTC)
    delivery_location: str = ""


class OrderStatusChanged(DomainEvent):
    """Domain event published when order status changes."""

    event_type: str = "order_status_changed"
    order_id: str
    user_id: str
    previous_status: str
    new_status: str
    status_change_reason: str = "system_update"
