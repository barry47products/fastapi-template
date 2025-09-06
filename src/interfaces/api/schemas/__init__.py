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
    "HealthResponse",
    "DetailedHealthResponse",
    "HealthCheckDetail",
    "ErrorResponse",
    "ValidationErrorResponse",
    "GenericWebhookPayload",
    "UserWebhookPayload",
    "OrderWebhookPayload",
    "PaymentWebhookPayload",
    "SystemWebhookPayload",
    "WebhookMetadata",
    "WebhookResponse",
    "AdminInfoResponse",
    "SafeConfigResponse",
    "ServiceStatusResponse",
]
