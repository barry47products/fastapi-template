"""API schemas package with Pydantic V2 models."""

from .admin import AdminInfoResponse, SafeConfigResponse, ServiceStatusResponse
from .errors import ErrorResponse, ValidationErrorResponse
from .health import DetailedHealthResponse, HealthCheckDetail, HealthResponse
from .webhooks import (
    GreenAPIGenericWebhook,
    GreenAPIMessageWebhook,
    GreenAPIStateWebhook,
    GreenAPIStatusWebhook,
    WebhookRequest,
    WebhookResponse,
)

__all__ = [
    "HealthResponse",
    "DetailedHealthResponse",
    "HealthCheckDetail",
    "ErrorResponse",
    "ValidationErrorResponse",
    "GreenAPIGenericWebhook",
    "GreenAPIMessageWebhook",
    "GreenAPIStateWebhook",
    "GreenAPIStatusWebhook",
    "WebhookRequest",
    "WebhookResponse",
    "AdminInfoResponse",
    "SafeConfigResponse",
    "ServiceStatusResponse",
]
