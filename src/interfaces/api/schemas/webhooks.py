"""Generic webhook schemas using Pydantic V2."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WebhookMetadata(BaseModel):
    """Webhook metadata information."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(description="Webhook source identifier")
    event_type: str = Field(description="Type of event that triggered the webhook")
    version: str = Field(default="1.0", description="Webhook payload version")
    timestamp: datetime = Field(description="When the event occurred")
    request_id: str | None = Field(default=None, description="Unique request identifier")


class UserEventData(BaseModel):
    """User-related event data."""

    model_config = ConfigDict(frozen=True)

    user_id: str = Field(description="User identifier")
    action: str = Field(description="Action performed (created, updated, deleted)")
    previous_data: dict[str, Any] | None = Field(
        default=None,
        description="Previous data (for update events)",
    )
    current_data: dict[str, Any] = Field(description="Current user data")


class OrderEventData(BaseModel):
    """Order-related event data."""

    model_config = ConfigDict(frozen=True)

    order_id: str = Field(description="Order identifier")
    user_id: str = Field(description="User who owns the order")
    status: str = Field(description="Current order status")
    action: str = Field(description="Action performed (placed, updated, cancelled, shipped)")
    total_amount: float = Field(description="Order total amount")
    currency: str = Field(default="USD", description="Currency code")


class PaymentEventData(BaseModel):
    """Payment-related event data."""

    model_config = ConfigDict(frozen=True)

    payment_id: str = Field(description="Payment identifier")
    order_id: str = Field(description="Related order identifier")
    amount: float = Field(description="Payment amount")
    currency: str = Field(description="Currency code")
    status: str = Field(description="Payment status (pending, completed, failed)")
    payment_method: str = Field(description="Payment method used")
    provider: str = Field(description="Payment provider")


class SystemEventData(BaseModel):
    """System-related event data."""

    model_config = ConfigDict(frozen=True)

    component: str = Field(description="System component")
    event: str = Field(description="System event type")
    severity: str = Field(description="Event severity (info, warning, error)")
    message: str = Field(description="Event message")
    details: dict[str, Any] | None = Field(default=None, description="Additional details")


class GenericWebhookPayload(BaseModel):
    """Generic webhook payload structure."""

    model_config = ConfigDict(frozen=True)

    metadata: WebhookMetadata = Field(description="Webhook metadata")
    data: dict[str, Any] = Field(description="Event-specific data payload")


class UserWebhookPayload(BaseModel):
    """User event webhook payload."""

    model_config = ConfigDict(frozen=True)

    metadata: WebhookMetadata = Field(description="Webhook metadata")
    data: UserEventData = Field(description="User event data")


class OrderWebhookPayload(BaseModel):
    """Order event webhook payload."""

    model_config = ConfigDict(frozen=True)

    metadata: WebhookMetadata = Field(description="Webhook metadata")
    data: OrderEventData = Field(description="Order event data")


class PaymentWebhookPayload(BaseModel):
    """Payment event webhook payload."""

    model_config = ConfigDict(frozen=True)

    metadata: WebhookMetadata = Field(description="Webhook metadata")
    data: PaymentEventData = Field(description="Payment event data")


class SystemWebhookPayload(BaseModel):
    """System event webhook payload."""

    model_config = ConfigDict(frozen=True)

    metadata: WebhookMetadata = Field(description="Webhook metadata")
    data: SystemEventData = Field(description="System event data")


class WebhookResponse(BaseModel):
    """Standard webhook response."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(description="Processing status (success, error)")
    message: str = Field(description="Response message")
    request_id: str | None = Field(default=None, description="Request identifier")
    processed_at: datetime = Field(description="When the webhook was processed")
    errors: list[str] | None = Field(default=None, description="Any processing errors")
