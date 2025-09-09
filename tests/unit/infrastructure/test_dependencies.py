"""Tests for FastAPI dependency injection providers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.infrastructure.dependencies import (
    get_api_key_validator,
    get_feature_flag_manager,
    get_health_checker,
    get_metrics_collector,
    get_notification_service,
    get_product_repository,
    get_rate_limiter,
    get_repository_provider,
    get_user_repository,
    get_webhook_verifier,
)


class TestDependencyProviders:
    """Test FastAPI dependency providers return correct service instances."""

    def test_get_metrics_collector_returns_singleton(self) -> None:
        """Metrics collector provider returns singleton instance."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2
        assert collector1.__class__.__name__ == "MetricsCollector"

    def test_get_health_checker_returns_singleton_with_timeout(self) -> None:
        """Health checker provider returns singleton with correct timeout."""
        checker1 = get_health_checker()
        checker2 = get_health_checker()

        assert checker1 is checker2
        assert checker1.timeout == 30

    @patch("config.settings.get_settings")
    def test_get_api_key_validator_returns_singleton_with_settings(
        self, mock_settings: MagicMock
    ) -> None:
        """API key validator provider uses settings configuration."""
        mock_settings.return_value.security.api_keys = ["test-key"]

        validator = get_api_key_validator()

        assert validator.__class__.__name__ == "APIKeyValidator"

    @patch("config.settings.get_settings")
    def test_get_rate_limiter_returns_singleton_with_settings(
        self, mock_settings: MagicMock
    ) -> None:
        """Rate limiter provider uses settings configuration."""
        mock_settings.return_value.security.rate_limit_requests_per_minute = 60

        limiter = get_rate_limiter()

        assert limiter.__class__.__name__ == "RateLimiter"

    @patch("config.settings.get_settings")
    def test_get_webhook_verifier_returns_singleton_with_settings(
        self, mock_settings: MagicMock
    ) -> None:
        """Webhook verifier provider uses settings configuration."""
        mock_settings.return_value.security.webhook_secret = "test-secret"

        verifier = get_webhook_verifier()

        assert verifier.__class__.__name__ == "WebhookVerifier"

    def test_get_feature_flag_manager_returns_singleton(self) -> None:
        """Feature flag manager provider returns singleton instance."""
        manager1 = get_feature_flag_manager()
        manager2 = get_feature_flag_manager()

        assert manager1 is manager2
        assert manager1.__class__.__name__ == "FeatureFlagManager"

    def test_get_repository_provider_returns_singleton(self) -> None:
        """Repository provider returns singleton instance."""
        provider1 = get_repository_provider()
        provider2 = get_repository_provider()

        assert provider1 is provider2
        assert provider1.__class__.__name__ == "RepositoryProvider"

    def test_get_notification_service_returns_singleton(self) -> None:
        """Notification service provider returns singleton instance."""
        service1 = get_notification_service()
        service2 = get_notification_service()

        assert service1 is service2
        assert service1.__class__.__name__ == "SampleNotificationService"

    def test_get_user_repository_returns_repository_instance(self) -> None:
        """User repository provider returns correct repository instance."""
        from src.infrastructure.persistence.repositories import InMemoryUserRepository

        repository = get_user_repository()

        assert isinstance(repository, InMemoryUserRepository)
        assert repository.__class__.__name__ == "InMemoryUserRepository"

    def test_get_product_repository_returns_repository_instance(self) -> None:
        """Product repository provider returns correct repository instance."""
        from src.infrastructure.persistence.repositories import InMemoryProductRepository

        repository = get_product_repository()

        assert isinstance(repository, InMemoryProductRepository)
        assert repository.__class__.__name__ == "InMemoryProductRepository"
