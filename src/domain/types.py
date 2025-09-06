"""
Domain types for strict typing throughout the application.

This module defines typed data structures to replace generic Any types
whilst maintaining template flexibility. These types provide better
type safety and IDE support.
"""

from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, Field, ConfigDict

# Union type for flexible metadata values
MetadataValue = str | int | float | bool | None
Metadata = dict[str, MetadataValue]

# Union type for flexible configuration values
ConfigValue = str | int | float | bool | list[str] | dict[str, str]
ConfigData = dict[str, ConfigValue]


class UserData(TypedDict):
    """Strongly typed user data structure."""

    id: str
    name: str
    email: str
    age: int
    created_at: datetime
    updated_at: datetime


class ProductData(TypedDict):
    """Strongly typed product data structure."""

    id: str
    name: str
    description: str
    price: float
    category: str
    created_at: datetime
    in_stock: bool


class HealthCheckResult(BaseModel):
    """Health check result with strict typing."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(description="Overall health status")
    timestamp: str = Field(description="When the check was performed")
    checks: dict[str, str] = Field(description="Individual component status")
    details: dict[str, str] = Field(description="Additional status details")
    version: str = Field(description="Application version")
    uptime_seconds: float = Field(description="Application uptime in seconds")


class ServiceInfo(BaseModel):
    """Service information with strict typing."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Service name")
    version: str = Field(description="Service version")
    environment: str = Field(description="Deployment environment")
    instance_id: str = Field(description="Unique instance identifier")
    started_at: datetime = Field(description="When the service started")


# Event change tracking types
ChangeValue = str | int | float | bool | datetime | None
ChangeData = dict[str, ChangeValue]

# Notification data types
NotificationData = dict[str, str | int | bool]


class MessageStatus(BaseModel):
    """Message delivery status with strict typing."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(description="Unique message identifier")
    status: str = Field(description="Delivery status")
    sent_at: datetime = Field(description="When message was sent")
    delivered_at: datetime | None = Field(None, description="When message was delivered")
    error_message: str | None = Field(None, description="Error details if failed")
    metadata: Metadata = Field(default_factory=dict, description="Additional metadata")
