"""Application settings using Pydantic Settings."""  # noqa: I002

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

    host: str = Field(default="0.0.0.0", description="API server host")  # noqa: S104
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


class DatabaseType(str, Enum):
    """Supported database types."""

    FIRESTORE = "firestore"
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    IN_MEMORY = "in_memory"


class DatabaseSettings(BaseModel):
    """Multi-database configuration with feature flags."""

    # Primary database configuration
    primary_db: DatabaseType = Field(
        default=DatabaseType.IN_MEMORY,
        description="Primary database for persistent data storage",
    )
    database_url: str = Field(
        default="memory://localhost",
        description="Primary database connection URL",
    )

    # Cache database configuration
    cache_db: DatabaseType | None = Field(
        default=None,
        description="Optional cache database for performance optimization",
    )
    cache_url: str | None = Field(
        default=None,
        description="Cache database connection URL",
    )

    # Legacy settings for backward compatibility
    echo_queries: bool = Field(
        default=False,
        description="Echo database queries (development only)",
    )

    # Connection pooling configuration
    pool_size: int = Field(default=5, ge=1, le=50, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, le=100, description="Pool max overflow")
    pool_timeout: int = Field(default=30, ge=5, le=300, description="Pool timeout in seconds")
    pool_recycle: int = Field(
        default=3600, ge=300, le=86400, description="Pool recycle time in seconds"
    )

    # Retry configuration
    retry_attempts: int = Field(default=3, ge=1, le=10, description="Database retry attempts")
    retry_delay: float = Field(default=1.0, ge=0.1, le=10.0, description="Retry delay in seconds")
    connection_timeout: float = Field(
        default=30.0, ge=5.0, le=300.0, description="Connection timeout in seconds"
    )

    # Database feature flags
    enable_firestore: bool = Field(default=False, description="Enable Google Firestore support")
    enable_postgresql: bool = Field(default=False, description="Enable PostgreSQL support")
    enable_redis_cache: bool = Field(default=False, description="Enable Redis caching")
    enable_connection_pooling: bool = Field(default=True, description="Enable connection pooling")
    enable_retry_logic: bool = Field(default=True, description="Enable retry logic")
    enable_read_replicas: bool = Field(default=False, description="Enable read replica support")
    enable_migrations: bool = Field(default=False, description="Enable automatic migrations")

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a database feature is enabled.

        Args:
            feature: Feature flag name

        Returns:
            True if feature is enabled, False otherwise
        """
        return getattr(self, feature, False)

    def supports_transactions(self) -> bool:
        """Check if primary database supports transactions.

        Returns:
            True if transactions are supported
        """
        return self.primary_db in {DatabaseType.POSTGRESQL, DatabaseType.FIRESTORE}

    def supports_acid(self) -> bool:
        """Check if primary database supports ACID properties.

        Returns:
            True if ACID properties are supported
        """
        return self.primary_db == DatabaseType.POSTGRESQL

    def requires_schema_migrations(self) -> bool:
        """Check if database requires schema migrations.

        Returns:
            True if schema migrations are required
        """
        return self.primary_db == DatabaseType.POSTGRESQL

    def supports_full_text_search(self) -> bool:
        """Check if database supports full-text search.

        Returns:
            True if full-text search is supported
        """
        return self.primary_db in {DatabaseType.POSTGRESQL, DatabaseType.FIRESTORE}


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
            raise ConfigurationException("Debug mode cannot be enabled in production")  # noqa: EM101, TRY003

        if self.is_production() and "sample" in str(self.security.api_keys[0]).lower():
            raise ConfigurationException("Sample API keys cannot be used in production")  # noqa: EM101, TRY003

        # Database validation
        if self.database.enable_postgresql and not self.database.database_url.startswith(
            "postgresql"
        ):
            raise ConfigurationException("PostgreSQL enabled but database URL is not PostgreSQL")  # noqa: EM101, TRY003

        if self.database.enable_redis_cache and not self.database.cache_url:
            raise ConfigurationException("Redis cache enabled but no cache URL provided")  # noqa: EM101, TRY003

        if self.database.cache_db and not self.database.cache_url:
            raise ConfigurationException("Cache database specified but no cache URL provided")  # noqa: EM101, TRY003

        if self.is_production() and self.database.primary_db == DatabaseType.IN_MEMORY:
            raise ConfigurationException("In-memory database cannot be used in production")  # noqa: EM101, TRY003

        if (
            self.external_services.email_service_enabled
            and not self.external_services.email_service_api_key
        ):
            raise ConfigurationException("Email service API key required when email is enabled")  # noqa: EM101, TRY003

        if (
            self.external_services.sms_service_enabled
            and not self.external_services.sms_service_api_key
        ):
            raise ConfigurationException("SMS service API key required when SMS is enabled")  # noqa: EM101, TRY003


# Global settings instance (lowercase because it's mutable)
_settings: ApplicationSettings | None = None


def get_settings() -> ApplicationSettings:
    """
    Get application settings singleton.

    Returns:
        Application settings instance

    Raises:
        ConfigurationException: If configuration validation fails
    """
    global _settings  # pylint: disable=global-statement  # noqa: PLW0603

    if _settings is None:
        _settings = ApplicationSettings()
        _settings.validate_configuration()

    return _settings


def reset_settings() -> None:
    """Reset settings singleton (useful for testing)."""
    global _settings  # pylint: disable=global-statement  # noqa: PLW0603
    _settings = None
