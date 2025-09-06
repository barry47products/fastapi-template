"""
Service registry for dependency injection pattern replacing singleton anti-patterns.
"""

from typing import TYPE_CHECKING

from src.shared.exceptions import ServiceNotConfiguredException

if TYPE_CHECKING:
    from src.infrastructure.feature_flags.manager import FeatureFlagManager
    from src.infrastructure.messaging.sample_notification_service import SampleNotificationService
    from src.infrastructure.observability.health_checker import HealthChecker
    from src.infrastructure.observability.metrics import MetricsCollector
    from src.infrastructure.persistence.repository_factory import RepositoryFactory
    from src.infrastructure.security.api_key_validator import APIKeyValidator
    from src.infrastructure.security.rate_limiter import RateLimiter
    from src.infrastructure.security.webhook_verifier import WebhookVerifier


class ServiceRegistry:
    """
    Central service registry for dependency injection pattern.

    Replaces singleton anti-patterns with proper dependency injection,
    enabling better testing, clearer dependencies, and improved modularity.
    """

    def __init__(self) -> None:
        """Initialize empty service registry."""
        self._metrics_collector: MetricsCollector | None = None
        self._health_checker: HealthChecker | None = None
        self._api_key_validator: APIKeyValidator | None = None
        self._rate_limiter: RateLimiter | None = None
        self._webhook_verifier: WebhookVerifier | None = None
        self._feature_flag_manager: FeatureFlagManager | None = None
        self._repository_factory: RepositoryFactory | None = None
        self._notification_service: SampleNotificationService | None = None

    # Metrics Collector Service
    def register_metrics_collector(self, collector: "MetricsCollector") -> None:
        """Register metrics collector service."""
        self._metrics_collector = collector

    def get_metrics_collector(self) -> "MetricsCollector":
        """Get registered metrics collector service."""
        if self._metrics_collector is None:
            raise ServiceNotConfiguredException("MetricsCollector not registered")
        return self._metrics_collector

    def has_metrics_collector(self) -> bool:
        """Check if metrics collector is registered."""
        return self._metrics_collector is not None

    # Health Checker Service
    def register_health_checker(self, checker: "HealthChecker") -> None:
        """Register health checker service."""
        self._health_checker = checker

    def get_health_checker(self) -> "HealthChecker":
        """Get registered health checker service."""
        if self._health_checker is None:
            raise ServiceNotConfiguredException("HealthChecker not registered")
        return self._health_checker

    def has_health_checker(self) -> bool:
        """Check if health checker is registered."""
        return self._health_checker is not None

    # API Key Validator Service
    def register_api_key_validator(self, validator: "APIKeyValidator") -> None:
        """Register API key validator service."""
        self._api_key_validator = validator

    def get_api_key_validator(self) -> "APIKeyValidator":
        """Get registered API key validator service."""
        if self._api_key_validator is None:
            raise ServiceNotConfiguredException("APIKeyValidator not registered")
        return self._api_key_validator

    def has_api_key_validator(self) -> bool:
        """Check if API key validator is registered."""
        return self._api_key_validator is not None

    # Rate Limiter Service
    def register_rate_limiter(self, limiter: "RateLimiter") -> None:
        """Register rate limiter service."""
        self._rate_limiter = limiter

    def get_rate_limiter(self) -> "RateLimiter":
        """Get registered rate limiter service."""
        if self._rate_limiter is None:
            raise ServiceNotConfiguredException("RateLimiter not registered")
        return self._rate_limiter

    def has_rate_limiter(self) -> bool:
        """Check if rate limiter is registered."""
        return self._rate_limiter is not None

    # Webhook Verifier Service
    def register_webhook_verifier(self, verifier: "WebhookVerifier") -> None:
        """Register webhook verifier service."""
        self._webhook_verifier = verifier

    def get_webhook_verifier(self) -> "WebhookVerifier":
        """Get registered webhook verifier service."""
        if self._webhook_verifier is None:
            raise ServiceNotConfiguredException("WebhookVerifier not registered")
        return self._webhook_verifier

    def has_webhook_verifier(self) -> bool:
        """Check if webhook verifier is registered."""
        return self._webhook_verifier is not None

    # Feature Flag Manager Service
    def register_feature_flag_manager(self, manager: "FeatureFlagManager") -> None:
        """Register feature flag manager service."""
        self._feature_flag_manager = manager

    def get_feature_flag_manager(self) -> "FeatureFlagManager":
        """Get registered feature flag manager service."""
        if self._feature_flag_manager is None:
            raise ServiceNotConfiguredException("FeatureFlagManager not registered")
        return self._feature_flag_manager

    def has_feature_flag_manager(self) -> bool:
        """Check if feature flag manager is registered."""
        return self._feature_flag_manager is not None

    # Notification Service
    def register_notification_service(self, service: "SampleNotificationService") -> None:
        """Register notification service."""
        self._notification_service = service

    def get_notification_service(self) -> "SampleNotificationService":
        """Get registered notification service."""
        if self._notification_service is None:
            raise ServiceNotConfiguredException("SampleNotificationService not registered")
        return self._notification_service

    def has_notification_service(self) -> bool:
        """Check if notification service is registered."""
        return self._notification_service is not None

    # Repository Factory Service
    def register_repository_factory(self, factory: "RepositoryFactory") -> None:
        """Register repository factory service."""
        self._repository_factory = factory

    def get_repository_factory(self) -> "RepositoryFactory":
        """Get registered repository factory service."""
        if self._repository_factory is None:
            raise ServiceNotConfiguredException("RepositoryFactory not registered")
        return self._repository_factory

    def has_repository_factory(self) -> bool:
        """Check if repository factory is registered."""
        return self._repository_factory is not None

    def clear_all_services(self) -> None:
        """Clear all registered services (useful for testing)."""
        self._metrics_collector = None
        self._health_checker = None
        self._api_key_validator = None
        self._rate_limiter = None
        self._webhook_verifier = None
        self._feature_flag_manager = None
        self._repository_factory = None
        self._notification_service = None


# Global service registry instance
_SERVICE_REGISTRY: ServiceRegistry | None = None


def get_service_registry() -> ServiceRegistry:
    """
    Get the global service registry instance.

    Returns:
        Global service registry instance

    Raises:
        ServiceNotConfiguredException: If service registry not initialized
    """
    if _SERVICE_REGISTRY is None:
        raise ServiceNotConfiguredException("Service registry not initialized")
    return _SERVICE_REGISTRY


def initialize_service_registry() -> ServiceRegistry:
    """
    Initialize the global service registry.

    Returns:
        Initialized service registry instance
    """
    global _SERVICE_REGISTRY  # pylint: disable=global-statement
    _SERVICE_REGISTRY = ServiceRegistry()
    return _SERVICE_REGISTRY


def clear_service_registry() -> None:
    """Clear the global service registry (useful for testing)."""
    global _SERVICE_REGISTRY  # pylint: disable=global-statement
    if _SERVICE_REGISTRY is not None:
        _SERVICE_REGISTRY.clear_all_services()
    _SERVICE_REGISTRY = None
