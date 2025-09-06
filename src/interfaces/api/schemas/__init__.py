"""API schemas package with Pydantic V2 models."""

from .admin import AdminInfoResponse, SafeConfigResponse, ServiceStatusResponse
from .errors import ErrorResponse, ValidationErrorResponse
from .health import DetailedHealthResponse, HealthCheckDetail, HealthResponse
from .webhooks import (
    GenericWebhookPayload,
    OrderWebhookPayload,
    PaymentWebhookPayload,
    SystemWebhookPayload,
    UserWebhookPayload,
    WebhookMetadata,
    WebhookResponse,
)

__all__ = [
    "AdminInfoResponse",
    "DetailedHealthResponse",
    "ErrorResponse",
    "GenericWebhookPayload",
    "HealthCheckDetail",
    "HealthResponse",
    "OrderWebhookPayload",
    "PaymentWebhookPayload",
    "SafeConfigResponse",
    "ServiceStatusResponse",
    "SystemWebhookPayload",
    "UserWebhookPayload",
    "ValidationErrorResponse",
    "WebhookMetadata",
    "WebhookResponse",
]
