"""Application exception hierarchy for FastAPI template."""


class ApplicationError(Exception):
    """Base exception for all application-specific errors."""

    error_code: str = "APPLICATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# Validation exceptions
class ValidationException(ApplicationError):
    """Exception for validation errors."""

    error_code: str = "VALIDATION_ERROR"

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


# Business logic exceptions
class EntityNotFoundException(ApplicationError):
    """Exception when an entity is not found."""

    error_code: str = "ENTITY_NOT_FOUND"


class UserNotFoundException(EntityNotFoundException):
    """Exception when a user is not found."""

    error_code: str = "USER_NOT_FOUND"


class ProductNotFoundException(EntityNotFoundException):
    """Exception when a product is not found."""

    error_code: str = "PRODUCT_NOT_FOUND"


class OrderNotFoundException(EntityNotFoundException):
    """Exception when an order is not found."""

    error_code: str = "ORDER_NOT_FOUND"


class RateLimitExceededException(ApplicationError):
    """Exception when rate limits are exceeded."""

    error_code: str = "RATE_LIMIT_EXCEEDED"


class ServiceNotConfiguredException(ApplicationError):
    """Exception when a required service is not configured in the service registry."""

    error_code: str = "SERVICE_NOT_CONFIGURED"


# Configuration exceptions
class ConfigurationException(ApplicationError):
    """Exception for configuration-related errors."""

    error_code: str = "CONFIGURATION_ERROR"


class MissingEnvironmentVariableException(ConfigurationException):
    """Exception for missing environment variables."""

    error_code: str = "MISSING_ENVIRONMENT_VARIABLE"

    def __init__(self, message: str, variable: str) -> None:
        super().__init__(message)
        self.variable = variable


# Infrastructure exceptions
class DatabaseException(ApplicationError):
    """Exception for database-related errors."""

    error_code: str = "DATABASE_ERROR"


class ExternalAPIException(ApplicationError):
    """Exception for external API errors."""

    error_code: str = "EXTERNAL_API_ERROR"


class MessageDeliveryException(ApplicationError):
    """Exception for message delivery failures."""

    error_code: str = "MESSAGE_DELIVERY_ERROR"


# Domain-specific validation exceptions
class EmailValidationError(ValidationException):
    """Exception for email validation errors."""

    error_code: str = "EMAIL_VALIDATION_ERROR"


class PhoneNumberValidationError(ValidationException):
    """Exception for phone number validation errors."""

    error_code: str = "PHONE_NUMBER_VALIDATION_ERROR"


class MoneyValidationError(ValidationException):
    """Exception for money/currency validation errors."""

    error_code: str = "MONEY_VALIDATION_ERROR"


class UserValidationError(ValidationException):
    """Exception for user model validation errors."""

    error_code: str = "USER_VALIDATION_ERROR"


class ProductValidationError(ValidationException):
    """Exception for product model validation errors."""

    error_code: str = "PRODUCT_VALIDATION_ERROR"


class OrderValidationError(ValidationException):
    """Exception for order model validation errors."""

    error_code: str = "ORDER_VALIDATION_ERROR"


# Persistence exceptions
class PersistenceException(ApplicationError):
    """Exception for persistence layer errors."""

    error_code: str = "PERSISTENCE_ERROR"


class RepositoryException(PersistenceException):
    """Exception for repository layer errors."""

    error_code: str = "REPOSITORY_ERROR"


class ConnectionException(PersistenceException):
    """Exception for database/cache connection errors."""

    error_code: str = "CONNECTION_ERROR"


class TransactionException(PersistenceException):
    """Exception for database transaction errors."""

    error_code: str = "TRANSACTION_ERROR"


class MigrationException(PersistenceException):
    """Exception for database migration errors."""

    error_code: str = "MIGRATION_ERROR"


class CacheException(PersistenceException):
    """Exception for cache-related errors."""

    error_code: str = "CACHE_ERROR"


# Authentication and authorization exceptions
class AuthenticationException(ApplicationError):
    """Exception for authentication failures."""

    error_code: str = "AUTHENTICATION_ERROR"


class AuthorizationException(ApplicationError):
    """Exception for authorization failures."""

    error_code: str = "AUTHORIZATION_ERROR"


class InvalidAPIKeyException(AuthenticationException):
    """Exception for invalid API key errors."""

    error_code: str = "INVALID_API_KEY"


# Business rule exceptions
class BusinessRuleViolationException(ApplicationError):
    """Exception for business rule violations."""

    error_code: str = "BUSINESS_RULE_VIOLATION"


class InsufficientInventoryException(BusinessRuleViolationException):
    """Exception when there's insufficient inventory for an operation."""

    error_code: str = "INSUFFICIENT_INVENTORY"


class DuplicateEntityException(BusinessRuleViolationException):
    """Exception when trying to create a duplicate entity."""

    error_code: str = "DUPLICATE_ENTITY"


class InvalidOperationException(BusinessRuleViolationException):
    """Exception for invalid business operations."""

    error_code: str = "INVALID_OPERATION"
