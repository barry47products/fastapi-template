"""Application settings using Pydantic Settings."""

import os
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.shared.exceptions import ConfigurationException


def _get_env_files() -> list[str]:
    """Get environment files based on ENV_FILE environment variable."""
    env_file = os.getenv("ENV_FILE")
    if env_file:
        return [env_file, ".env"]  # Specified file first, then fallback to .env
    return [".env.local", ".env.test", ".env"]  # Local dev, test, then default


class Environment(str, Enum):
    """Valid application environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    TESTING = "testing"
    PRODUCTION = "production"


class APISettings(BaseModel):
    """API server configuration."""

    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, ge=1000, le=65535, description="API server port")
    title: str = Field(default="FastAPI Template", description="API title")
    description: str = Field(
        default="A clean architecture FastAPI template",
        description="API description",
    )
    version: str = Field(default="1.0.0", description="API version")
    docs_url: str | None = Field(default="/docs", description="Swagger UI URL")
    redoc_url: str | None = Field(default="/redoc", description="ReDoc URL")
    openapi_url: str | None = Field(default="/openapi.json", description="OpenAPI JSON URL")


class DatabaseSettings(BaseModel):
    """Database configuration."""

    # For template purposes, we use simple settings
    # Replace with actual database settings (PostgreSQL, MySQL, etc.)
    database_url: str = Field(
        default="sqlite:///./template.db",
        description="Database connection URL",
    )
    echo_queries: bool = Field(
        default=False,
        description="Echo database queries (development only)",
    )
    pool_size: int = Field(default=5, ge=1, le=50, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, le=100, description="Pool max overflow")


class SecuritySettings(BaseModel):
    """Security and authentication configuration."""

    api_keys: list[str] = Field(
        default_factory=lambda: ["sample-api-key-replace-in-production"],
        description="Valid API keys for authentication",
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        description="CORS allowed origins",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests",
    )
    cors_allow_methods: list[str] = Field(
        default_factory=lambda: ["*"],
        description="CORS allowed methods",
    )
    cors_allow_headers: list[str] = Field(
        default_factory=lambda: ["*"],
        description="CORS allowed headers",
    )
    rate_limit_requests_per_minute: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Rate limit requests per minute",
    )
    webhook_secret: str = Field(
        default="sample-webhook-secret-replace-in-production",
        description="Webhook verification secret",
    )


class ObservabilitySettings(BaseModel):
    """Observability configuration (logging, metrics, health checks)."""

    # Logging settings
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    log_format: str = Field(
        default="structured",
        description="Log format (structured, simple)",
    )
    log_file: str | None = Field(
        default=None,
        description="Log file path (None for stdout only)",
    )

    # Metrics settings
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(
        default=9090,
        ge=1000,
        le=65535,
        description="Metrics server port",
    )
    metrics_path: str = Field(default="/metrics", description="Metrics endpoint path")

    # Health check settings
    health_check_enabled: bool = Field(default=True, description="Enable health checks")
    health_check_timeout: float = Field(
        default=5.0,
        ge=0.1,
        le=30.0,
        description="Health check timeout in seconds",
    )


class FeatureFlagSettings(BaseModel):
    """Feature flag configuration."""

    # Sample feature flags - replace with your actual features
    new_user_onboarding_enabled: bool = Field(
        default=True,
        description="Enable new user onboarding flow",
    )
    advanced_search_enabled: bool = Field(
        default=False,
        description="Enable advanced search functionality",
    )
    email_notifications_enabled: bool = Field(
        default=True,
        description="Enable email notifications",
    )
    sms_notifications_enabled: bool = Field(
        default=False,
        description="Enable SMS notifications",
    )
    push_notifications_enabled: bool = Field(
        default=False,
        description="Enable push notifications",
    )


class ExternalServicesSettings(BaseModel):
    """External service integrations."""

    # Email service settings
    email_service_enabled: bool = Field(default=False, description="Enable email service")
    email_service_api_key: str = Field(default="", description="Email service API key")
    email_from_address: str = Field(
        default="noreply@example.com",
        description="Default from email address",
    )

    # SMS service settings
    sms_service_enabled: bool = Field(default=False, description="Enable SMS service")
    sms_service_api_key: str = Field(default="", description="SMS service API key")

    # Analytics settings
    analytics_enabled: bool = Field(default=False, description="Enable analytics")
    analytics_api_key: str = Field(default="", description="Analytics API key")


class ApplicationSettings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=_get_env_files(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Core application settings
    app_name: str = Field(default="fastapi-template", description="Application name")
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    timezone: str = Field(default="UTC", description="Application timezone")

    # Component settings
    api: APISettings = Field(default_factory=APISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    feature_flags: FeatureFlagSettings = Field(default_factory=FeatureFlagSettings)
    external_services: ExternalServicesSettings = Field(
        default_factory=ExternalServicesSettings,
    )

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING

    def validate_configuration(self) -> None:
        """Validate configuration for common issues."""
        if self.is_production() and self.debug:
            raise ConfigurationException("Debug mode cannot be enabled in production")

        if self.is_production() and "sample" in str(self.security.api_keys[0]).lower():
            raise ConfigurationException("Sample API keys cannot be used in production")

        if (
            self.external_services.email_service_enabled
            and not self.external_services.email_service_api_key
        ):
            raise ConfigurationException("Email service API key required when email is enabled")

        if (
            self.external_services.sms_service_enabled
            and not self.external_services.sms_service_api_key
        ):
            raise ConfigurationException("SMS service API key required when SMS is enabled")


# Global settings instance
_SETTINGS: ApplicationSettings | None = None


def get_settings() -> ApplicationSettings:
    """
    Get application settings singleton.

    Returns:
        Application settings instance

    Raises:
        ConfigurationException: If configuration validation fails
    """
    global _SETTINGS  # pylint: disable=global-statement

    if _SETTINGS is None:
        _SETTINGS = ApplicationSettings()
        _SETTINGS.validate_configuration()

    return _SETTINGS


def reset_settings() -> None:
    """Reset settings singleton (useful for testing)."""
    global _SETTINGS  # pylint: disable=global-statement
    _SETTINGS = None