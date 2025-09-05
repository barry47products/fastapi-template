"""Application exception hierarchy for Neighbour Approved."""


class NeighbourApprovedError(Exception):
    """Base exception for all application-specific errors."""

    error_code: str = "NEIGHBOUR_APPROVED_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# WhatsApp-related exceptions
class WhatsAppException(NeighbourApprovedError):
    """Base exception for WhatsApp-related errors."""

    error_code: str = "WHATSAPP_ERROR"


class WhatsAppDeliveryException(WhatsAppException):
    """Exception for WhatsApp message delivery failures."""

    error_code: str = "WHATSAPP_DELIVERY_ERROR"


class MessageProcessingException(WhatsAppException):
    """Base exception for message processing pipeline failures."""

    error_code: str = "MESSAGE_PROCESSING_ERROR"


class MentionExtractionException(MessageProcessingException):
    """Exception for mention extraction failures."""

    error_code: str = "MENTION_EXTRACTION_FAILED"


class ProviderMatchingException(MessageProcessingException):
    """Exception for provider matching failures."""

    error_code: str = "PROVIDER_MATCHING_FAILED"


class EndorsementPersistenceException(MessageProcessingException):
    """Exception for endorsement persistence failures."""

    error_code: str = "ENDORSEMENT_PERSISTENCE_FAILED"


class ContactParsingException(MessageProcessingException):
    """Exception for contact card parsing failures."""

    error_code: str = "CONTACT_PARSING_FAILED"


# Validation exceptions
class ValidationException(NeighbourApprovedError):
    """Exception for validation errors."""

    error_code: str = "VALIDATION_ERROR"

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


# Business logic exceptions
class ProviderNotFoundException(NeighbourApprovedError):
    """Exception when a service provider is not found."""

    error_code: str = "PROVIDER_NOT_FOUND"


class EndorsementNotFoundException(NeighbourApprovedError):
    """Exception when an endorsement is not found."""

    error_code: str = "ENDORSEMENT_NOT_FOUND"


class RateLimitExceededException(NeighbourApprovedError):
    """Exception when rate limits are exceeded."""

    error_code: str = "RATE_LIMIT_EXCEEDED"


class ServiceNotConfiguredException(NeighbourApprovedError):
    """Exception when a required service is not configured in the service registry."""

    error_code: str = "SERVICE_NOT_CONFIGURED"


# Configuration exceptions
class ConfigurationException(NeighbourApprovedError):
    """Exception for configuration-related errors."""

    error_code: str = "CONFIGURATION_ERROR"


class MissingEnvironmentVariableException(ConfigurationException):
    """Exception for missing environment variables."""

    error_code: str = "MISSING_ENVIRONMENT_VARIABLE"

    def __init__(self, message: str, variable: str) -> None:
        super().__init__(message)
        self.variable = variable


# Infrastructure exceptions
class DatabaseException(NeighbourApprovedError):
    """Exception for database-related errors."""

    error_code: str = "DATABASE_ERROR"


class ExternalAPIException(NeighbourApprovedError):
    """Exception for external API errors."""

    error_code: str = "EXTERNAL_API_ERROR"


# Domain-specific validation exceptions
class PhoneNumberValidationError(ValidationException):
    """Exception for phone number validation errors."""

    error_code: str = "PHONE_NUMBER_VALIDATION_ERROR"


class ProviderValidationError(ValidationException):
    """Exception for provider model validation errors."""

    error_code: str = "PROVIDER_VALIDATION_ERROR"


class EndorsementValidationError(ValidationException):
    """Exception for endorsement model validation errors."""

    error_code: str = "ENDORSEMENT_VALIDATION_ERROR"


class GroupIDValidationError(ValidationException):
    """Exception for group ID validation errors."""

    error_code: str = "GROUP_ID_VALIDATION_ERROR"


class ProviderIDValidationError(ValidationException):
    """Exception for provider ID validation errors."""

    error_code: str = "PROVIDER_ID_VALIDATION_ERROR"


class MessageClassificationError(ValidationException):
    """Exception for message classification errors."""

    error_code: str = "MESSAGE_CLASSIFICATION_ERROR"


class MentionExtractionError(ValidationException):
    """Exception for mention extraction errors."""

    error_code: str = "MENTION_EXTRACTION_ERROR"


class SummaryGenerationError(ValidationException):
    """Exception for summary generation errors."""

    error_code: str = "SUMMARY_GENERATION_ERROR"


class InsufficientDataError(SummaryGenerationError):
    """Exception when insufficient data exists for summary generation."""

    error_code: str = "INSUFFICIENT_DATA_ERROR"


class PersistenceException(NeighbourApprovedError):
    """Exception for persistence layer errors."""

    error_code: str = "PERSISTENCE_ERROR"


class RepositoryException(PersistenceException):
    """Exception for repository layer errors."""

    error_code: str = "REPOSITORY_ERROR"


class EndorsementIDValidationError(ValidationException):
    """Exception for endorsement ID validation errors."""

    error_code: str = "ENDORSEMENT_ID_VALIDATION_ERROR"


class GreenAPIErrorException(ExternalAPIException):
    """Exception for GREEN-API specific errors."""

    error_code: str = "GREEN_API_ERROR"


class ContextAttributionException(MessageProcessingException):
    """Exception for context attribution failures."""

    error_code: str = "CONTEXT_ATTRIBUTION_ERROR"
