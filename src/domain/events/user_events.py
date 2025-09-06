"""Sample domain events for user-related operations."""

from datetime import datetime, UTC
from typing import Any

from .base import DomainEvent


class UserCreated(DomainEvent):
    """Domain event published when a new user is created."""

    event_type: str = "user_created"
    user_id: str
    user_email: str
    user_name: str
    registration_timestamp: datetime = datetime.now(UTC)


class UserUpdated(DomainEvent):
    """Domain event published when user information is updated."""

    event_type: str = "user_updated"
    user_id: str
    fields_updated: list[str]
    previous_values: dict[str, Any]
    new_values: dict[str, Any]


class UserDeleted(DomainEvent):
    """Domain event published when a user is deleted."""

    event_type: str = "user_deleted"
    user_id: str
    user_email: str
    deletion_timestamp: datetime = datetime.now(UTC)
    deletion_reason: str = "user_requested"


class UserEmailVerified(DomainEvent):
    """Domain event published when user email is verified."""

    event_type: str = "user_email_verified"
    user_id: str
    email: str
    verified_at: datetime = datetime.now(UTC)


class UserStatusChanged(DomainEvent):
    """Domain event published when user status changes."""

    event_type: str = "user_status_changed"
    user_id: str
    previous_status: str
    new_status: str
    status_change_reason: str = "system_update"
