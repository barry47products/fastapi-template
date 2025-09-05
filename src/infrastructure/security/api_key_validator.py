"""API key validation system for webhook authentication."""

from typing import Optional

from fastapi import Header, HTTPException

from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import NeighbourApprovedError


class APIKeyValidationError(NeighbourApprovedError):
    """Exception raised when API key validation fails."""

    def __init__(self, message: str) -> None:
        """Initialize API key validation error.

        Args:
            message: Error message describing the validation failure
        """
        super().__init__(message)
        self.error_code = "API_KEY_INVALID"


class _APIKeyValidatorSingleton:
    """Singleton holder for the API key validator."""

    _instance: Optional["APIKeyValidator"] = None

    @classmethod
    def get_instance(cls) -> "APIKeyValidator":
        """Get the singleton API key validator instance.

        Returns:
            API key validator instance

        Raises:
            APIKeyValidationError: If validator not configured
        """
        if cls._instance is None:
            raise APIKeyValidationError("API key validator not configured")
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "APIKeyValidator") -> None:
        """Set the singleton API key validator instance.

        Args:
            instance: API key validator instance to set
        """
        cls._instance = instance


class APIKeyValidator:
    """API key validation system for webhook authentication."""

    def __init__(self, api_keys: list[str]) -> None:
        """Initialize API key validator.

        Args:
            api_keys: List of valid API keys for authentication
        """
        self.api_keys = set(api_keys)  # Use set for O(1) lookup

    def validate(self, api_key: str | None) -> bool:
        """Validate an API key.

        Args:
            api_key: API key to validate

        Returns:
            True if API key is valid, False otherwise
        """
        if not api_key:
            return False

        return api_key in self.api_keys


def configure_api_key_validator(api_keys: list[str]) -> None:
    """Configure the global API key validator.

    Args:
        api_keys: List of valid API keys for authentication
    """
    validator = APIKeyValidator(api_keys=api_keys)

    # Register with service registry (primary method)
    try:
        from src.infrastructure.service_registry import get_service_registry

        service_registry = get_service_registry()
        service_registry.register_api_key_validator(validator)
    except Exception:
        # Service registry might not be initialized yet
        pass

    # Also set in singleton for backward compatibility during transition
    _APIKeyValidatorSingleton.set_instance(validator)


def get_api_key_validator() -> APIKeyValidator:
    """Get the global API key validator instance via service registry.

    Returns:
        API key validator instance

    Raises:
        APIKeyValidationError: If validator not configured
    """
    # Try to get from service registry first (new DI pattern)
    try:
        from src.infrastructure.service_registry import get_service_registry

        service_registry = get_service_registry()
        if service_registry.has_api_key_validator():
            return service_registry.get_api_key_validator()
    except Exception:
        # Fall back to singleton pattern for backward compatibility
        pass

    # Fallback to singleton for backward compatibility during transition
    return _APIKeyValidatorSingleton.get_instance()


def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> str:
    """FastAPI dependency for API key verification.

    Supports both X-API-Key and Authorization header formats for GREEN-API compatibility.

    Args:
        x_api_key: API key from X-API-Key header
        authorization: API key from Authorization header (for GREEN-API webhook auth)

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is invalid (401 Unauthorized)
    """
    logger = get_logger(__name__)
    metrics = get_metrics_collector()

    # Get validator instance
    validator = get_api_key_validator()

    # Extract API key from either header
    api_key = None
    auth_method = None

    if x_api_key:
        api_key = x_api_key
        auth_method = "X-API-Key"
    elif authorization:
        # Handle different Authorization header formats
        if authorization.startswith("Bearer "):
            api_key = authorization[7:]  # Remove "Bearer " prefix
            auth_method = "Authorization Bearer"
        elif authorization.startswith("ApiKey "):
            api_key = authorization[7:]  # Remove "ApiKey " prefix
            auth_method = "Authorization ApiKey"
        else:
            # Treat entire authorization header as API key (GREEN-API format)
            api_key = authorization
            auth_method = "Authorization"

    # Validate API key
    if validator.validate(api_key):
        # Log successful authentication (with prefix for security)
        api_key_prefix = api_key[:8] + "..." if api_key else "None"
        logger.info(
            "API key validation successful",
            api_key_prefix=api_key_prefix,
            auth_method=auth_method,
        )

        # Record success metrics
        metrics.increment_counter("api_key_validations_total", {"status": "success"})

        return api_key  # type: ignore[return-value]

    # Log failed authentication attempt
    api_key_prefix = api_key[:8] + "..." if api_key else "None"
    logger.warning(
        "API key validation failed",
        api_key_prefix=api_key_prefix,
        auth_method=auth_method,
    )

    # Record failure metrics
    metrics.increment_counter("api_key_validations_total", {"status": "failure"})

    # Raise HTTP exception for failed validation
    raise HTTPException(
        status_code=401,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )
