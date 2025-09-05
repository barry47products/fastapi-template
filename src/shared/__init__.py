"""Shared utilities and exceptions for Neighbour Approved."""

from .exceptions import (
    ConfigurationException,
    DatabaseException,
    EndorsementNotFoundException,
    ExternalAPIException,
    MissingEnvironmentVariableException,
    NeighbourApprovedError,
    ProviderNotFoundException,
    RateLimitExceededException,
    ValidationException,
    WhatsAppDeliveryException,
    WhatsAppException,
)

__all__ = [
    "ConfigurationException",
    "DatabaseException",
    "EndorsementNotFoundException",
    "ExternalAPIException",
    "MissingEnvironmentVariableException",
    "NeighbourApprovedError",
    "ProviderNotFoundException",
    "RateLimitExceededException",
    "ValidationException",
    "WhatsAppDeliveryException",
    "WhatsAppException",
]
