"""FastAPI dependency injection providers replacing ServiceRegistry pattern."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.infrastructure.feature_flags.manager import FeatureFlagManager
    from src.infrastructure.messaging.sample_notification_service import SampleNotificationService
    from src.infrastructure.observability.health_checker import HealthChecker
    from src.infrastructure.observability.metrics import MetricsCollector
    from src.infrastructure.persistence.repositories import (
        InMemoryProductRepository,
        InMemoryUserRepository,
    )
    from src.infrastructure.persistence.repository_provider import RepositoryProvider
    from src.infrastructure.security.api_key_validator import APIKeyValidator
    from src.infrastructure.security.rate_limiter import RateLimiter
    from src.infrastructure.security.webhook_verifier import WebhookVerifier


@lru_cache
def get_metrics_collector() -> MetricsCollector:
    """Get singleton metrics collector via FastAPI DI."""
    from src.infrastructure.observability.metrics import MetricsCollector

    return MetricsCollector()


@lru_cache
def get_health_checker() -> HealthChecker:
    """Get singleton health checker via FastAPI DI."""
    from src.infrastructure.observability.health_checker import HealthChecker

    return HealthChecker(timeout=30)


@lru_cache
def get_api_key_validator() -> APIKeyValidator:
    """Get singleton API key validator via FastAPI DI."""
    from config.settings import get_settings
    from src.infrastructure.security.api_key_validator import APIKeyValidator

    settings = get_settings()
    return APIKeyValidator(api_keys=settings.security.api_keys)


@lru_cache
def get_rate_limiter() -> RateLimiter:
    """Get singleton rate limiter via FastAPI DI."""
    from config.settings import get_settings
    from src.infrastructure.security.rate_limiter import RateLimiter

    settings = get_settings()
    return RateLimiter(
        limit=settings.security.rate_limit_requests_per_minute,
        window_seconds=60,
    )


@lru_cache
def get_webhook_verifier() -> WebhookVerifier:
    """Get singleton webhook verifier via FastAPI DI."""
    from config.settings import get_settings
    from src.infrastructure.security.webhook_verifier import WebhookVerifier

    settings = get_settings()
    return WebhookVerifier(secret_key=settings.security.webhook_secret)


@lru_cache
def get_feature_flag_manager() -> FeatureFlagManager:
    """Get singleton feature flag manager via FastAPI DI."""
    from src.infrastructure.feature_flags.manager import FeatureFlagManager

    return FeatureFlagManager()


@lru_cache
def get_repository_provider() -> RepositoryProvider:
    """Get singleton repository provider via FastAPI DI."""
    from config.settings import DatabaseType
    from src.infrastructure.persistence.repository_provider import RepositoryProvider

    return RepositoryProvider(database_url="memory://", db_type=DatabaseType.IN_MEMORY)


def get_user_repository() -> InMemoryUserRepository:
    """Get user repository via dependency injection."""
    from src.infrastructure.persistence.repositories import InMemoryUserRepository

    provider = get_repository_provider()
    return provider.get(InMemoryUserRepository)


def get_product_repository() -> InMemoryProductRepository:
    """Get product repository via dependency injection."""
    from src.infrastructure.persistence.repositories import InMemoryProductRepository

    provider = get_repository_provider()
    return provider.get(InMemoryProductRepository)


@lru_cache
def get_notification_service() -> SampleNotificationService:
    """Get singleton notification service via FastAPI DI."""
    from src.infrastructure.messaging.sample_notification_service import SampleNotificationService

    return SampleNotificationService()
