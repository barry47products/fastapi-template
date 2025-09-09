"""Unit tests for application settings configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from config.settings import (
    APISettings,
    ApplicationSettings,
    DatabaseSettings,
    DatabaseType,
    Environment,
    ExternalServicesSettings,
    FeatureFlagSettings,
    ObservabilitySettings,
    SecuritySettings,
    _get_env_files,
    get_settings,
    reset_settings,
)
from src.shared.exceptions import ConfigurationException


class TestGetEnvFiles:
    """Tests for _get_env_files function."""

    def test_returns_specified_env_file_when_set(self) -> None:
        """Returns specified env file and .env when ENV_FILE is set."""
        with patch.dict(os.environ, {"ENV_FILE": ".env.production"}):
            result = _get_env_files()
            assert result == [".env.production", ".env"]

    def test_returns_default_files_when_not_set(self) -> None:
        """Returns default files when ENV_FILE is not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = _get_env_files()
            assert result == [".env.local", ".env.test", ".env"]

    def test_handles_empty_env_file_variable(self) -> None:
        """Handles empty ENV_FILE variable correctly."""
        with patch.dict(os.environ, {"ENV_FILE": ""}):
            result = _get_env_files()
            assert result == [".env.local", ".env.test", ".env"]


class TestEnvironmentEnum:
    """Tests for Environment enum."""

    def test_has_all_required_environments(self) -> None:
        """Has all required environment values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.TESTING.value == "testing"
        assert Environment.PRODUCTION.value == "production"

    def test_can_compare_environments(self) -> None:
        """Can compare environment values."""
        env = Environment.DEVELOPMENT
        assert env.value == "development"
        assert env != Environment.PRODUCTION


class TestAPISettings:
    """Tests for APISettings configuration."""

    def test_creates_with_default_values(self) -> None:
        """Creates API settings with default values."""
        settings = APISettings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.title == "FastAPI Template"
        assert settings.docs_url == "/docs"
        assert settings.redoc_url == "/redoc"
        assert settings.openapi_url == "/openapi.json"

    def test_creates_with_custom_values(self) -> None:
        """Creates API settings with custom values."""
        settings = APISettings(
            host="127.0.0.1",
            port=3000,
            title="Custom API",
            docs_url=None,
        )
        assert settings.host == "127.0.0.1"
        assert settings.port == 3000
        assert settings.title == "Custom API"
        assert settings.docs_url is None

    def test_validates_port_range(self) -> None:
        """Validates port is within valid range."""
        with pytest.raises(ValidationError) as exc_info:
            APISettings(port=999)
        assert "greater than or equal to 1000" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            APISettings(port=70000)
        assert "less than or equal to 65535" in str(exc_info.value)


class TestDatabaseType:
    """Tests for DatabaseType enum."""

    def test_has_all_database_types(self) -> None:
        """Has all supported database types."""
        assert DatabaseType.FIRESTORE.value == "firestore"
        assert DatabaseType.POSTGRESQL.value == "postgresql"
        assert DatabaseType.REDIS.value == "redis"
        assert DatabaseType.IN_MEMORY.value == "in_memory"


class TestDatabaseSettings:
    """Tests for DatabaseSettings configuration."""

    def test_creates_with_default_values(self) -> None:
        """Creates database settings with default values."""
        settings = DatabaseSettings()
        assert settings.primary_db == DatabaseType.IN_MEMORY
        assert settings.database_url == "memory://localhost"
        assert settings.cache_db is None
        assert settings.pool_size == 5
        assert settings.retry_attempts == 3

    def test_creates_with_custom_values(self) -> None:
        """Creates database settings with custom values."""
        settings = DatabaseSettings(
            primary_db=DatabaseType.POSTGRESQL,
            database_url="postgresql://localhost/db",
            cache_db=DatabaseType.REDIS,
            cache_url="redis://localhost",
            pool_size=10,
        )
        assert settings.primary_db == DatabaseType.POSTGRESQL
        assert settings.database_url == "postgresql://localhost/db"
        assert settings.cache_db == DatabaseType.REDIS
        assert settings.cache_url == "redis://localhost"
        assert settings.pool_size == 10

    def test_is_feature_enabled_method(self) -> None:
        """Tests is_feature_enabled method."""
        settings = DatabaseSettings(
            enable_postgresql=True,
            enable_redis_cache=False,
        )
        assert settings.is_feature_enabled("enable_postgresql") is True
        assert settings.is_feature_enabled("enable_redis_cache") is False
        assert settings.is_feature_enabled("non_existent_feature") is False

    def test_supports_transactions(self) -> None:
        """Tests supports_transactions method."""
        settings = DatabaseSettings(primary_db=DatabaseType.POSTGRESQL)
        assert settings.supports_transactions() is True

        settings = DatabaseSettings(primary_db=DatabaseType.FIRESTORE)
        assert settings.supports_transactions() is True

        settings = DatabaseSettings(primary_db=DatabaseType.REDIS)
        assert settings.supports_transactions() is False

        settings = DatabaseSettings(primary_db=DatabaseType.IN_MEMORY)
        assert settings.supports_transactions() is False

    def test_supports_acid(self) -> None:
        """Tests supports_acid method."""
        settings = DatabaseSettings(primary_db=DatabaseType.POSTGRESQL)
        assert settings.supports_acid() is True

        settings = DatabaseSettings(primary_db=DatabaseType.FIRESTORE)
        assert settings.supports_acid() is False

        settings = DatabaseSettings(primary_db=DatabaseType.REDIS)
        assert settings.supports_acid() is False

    def test_requires_schema_migrations(self) -> None:
        """Tests requires_schema_migrations method."""
        settings = DatabaseSettings(primary_db=DatabaseType.POSTGRESQL)
        assert settings.requires_schema_migrations() is True

        settings = DatabaseSettings(primary_db=DatabaseType.FIRESTORE)
        assert settings.requires_schema_migrations() is False

        settings = DatabaseSettings(primary_db=DatabaseType.IN_MEMORY)
        assert settings.requires_schema_migrations() is False

    def test_supports_full_text_search(self) -> None:
        """Tests supports_full_text_search method."""
        settings = DatabaseSettings(primary_db=DatabaseType.POSTGRESQL)
        assert settings.supports_full_text_search() is True

        settings = DatabaseSettings(primary_db=DatabaseType.FIRESTORE)
        assert settings.supports_full_text_search() is True

        settings = DatabaseSettings(primary_db=DatabaseType.REDIS)
        assert settings.supports_full_text_search() is False

        settings = DatabaseSettings(primary_db=DatabaseType.IN_MEMORY)
        assert settings.supports_full_text_search() is False

    def test_validates_pool_size_range(self) -> None:
        """Validates pool size is within valid range."""
        with pytest.raises(ValidationError):
            DatabaseSettings(pool_size=0)

        with pytest.raises(ValidationError):
            DatabaseSettings(pool_size=51)


class TestSecuritySettings:
    """Tests for SecuritySettings configuration."""

    def test_creates_with_default_values(self) -> None:
        """Creates security settings with default values."""
        settings = SecuritySettings()
        assert len(settings.api_keys) == 1
        assert "sample-api-key" in settings.api_keys[0]
        assert "http://localhost:3000" in settings.cors_origins
        assert settings.cors_allow_credentials is True
        assert settings.rate_limit_requests_per_minute == 100

    def test_creates_with_custom_values(self) -> None:
        """Creates security settings with custom values."""
        settings = SecuritySettings(
            api_keys=["key1", "key2"],
            cors_origins=["https://example.com"],
            cors_allow_credentials=False,
            rate_limit_requests_per_minute=500,
        )
        assert settings.api_keys == ["key1", "key2"]
        assert settings.cors_origins == ["https://example.com"]
        assert settings.cors_allow_credentials is False
        assert settings.rate_limit_requests_per_minute == 500

    def test_validates_rate_limit_range(self) -> None:
        """Validates rate limit is within valid range."""
        with pytest.raises(ValidationError):
            SecuritySettings(rate_limit_requests_per_minute=0)

        with pytest.raises(ValidationError):
            SecuritySettings(rate_limit_requests_per_minute=10001)


class TestObservabilitySettings:
    """Tests for ObservabilitySettings configuration."""

    def test_creates_with_default_values(self) -> None:
        """Creates observability settings with default values."""
        settings = ObservabilitySettings()
        assert settings.log_level == "INFO"
        assert settings.log_format == "structured"
        assert settings.log_file is None
        assert settings.metrics_enabled is True
        assert settings.metrics_port == 9090
        assert settings.health_check_enabled is True

    def test_creates_with_custom_values(self) -> None:
        """Creates observability settings with custom values."""
        settings = ObservabilitySettings(
            log_level="DEBUG",
            log_format="simple",
            log_file="/var/log/app.log",
            metrics_enabled=False,
            health_check_timeout=10.0,
        )
        assert settings.log_level == "DEBUG"
        assert settings.log_format == "simple"
        assert settings.log_file == "/var/log/app.log"
        assert settings.metrics_enabled is False
        assert settings.health_check_timeout == 10.0

    def test_validates_metrics_port_range(self) -> None:
        """Validates metrics port is within valid range."""
        with pytest.raises(ValidationError):
            ObservabilitySettings(metrics_port=999)

        with pytest.raises(ValidationError):
            ObservabilitySettings(metrics_port=70000)

    def test_validates_health_check_timeout_range(self) -> None:
        """Validates health check timeout is within valid range."""
        with pytest.raises(ValidationError):
            ObservabilitySettings(health_check_timeout=0.05)

        with pytest.raises(ValidationError):
            ObservabilitySettings(health_check_timeout=31.0)


class TestFeatureFlagSettings:
    """Tests for FeatureFlagSettings configuration."""

    def test_creates_with_default_values(self) -> None:
        """Creates feature flag settings with default values."""
        settings = FeatureFlagSettings()
        assert settings.new_user_onboarding_enabled is True
        assert settings.advanced_search_enabled is False
        assert settings.email_notifications_enabled is True
        assert settings.sms_notifications_enabled is False
        assert settings.push_notifications_enabled is False

    def test_creates_with_custom_values(self) -> None:
        """Creates feature flag settings with custom values."""
        settings = FeatureFlagSettings(
            new_user_onboarding_enabled=False,
            advanced_search_enabled=True,
            push_notifications_enabled=True,
        )
        assert settings.new_user_onboarding_enabled is False
        assert settings.advanced_search_enabled is True
        assert settings.push_notifications_enabled is True


class TestExternalServicesSettings:
    """Tests for ExternalServicesSettings configuration."""

    def test_creates_with_default_values(self) -> None:
        """Creates external services settings with default values."""
        settings = ExternalServicesSettings()
        assert settings.email_service_enabled is False
        assert settings.email_service_api_key == ""
        assert settings.email_from_address == "noreply@example.com"
        assert settings.sms_service_enabled is False
        assert settings.analytics_enabled is False

    def test_creates_with_custom_values(self) -> None:
        """Creates external services settings with custom values."""
        settings = ExternalServicesSettings(
            email_service_enabled=True,
            email_service_api_key="email-key",
            email_from_address="support@company.com",
            sms_service_enabled=True,
            sms_service_api_key="sms-key",
        )
        assert settings.email_service_enabled is True
        assert settings.email_service_api_key == "email-key"
        assert settings.email_from_address == "support@company.com"
        assert settings.sms_service_enabled is True
        assert settings.sms_service_api_key == "sms-key"


class TestApplicationSettings:
    """Tests for ApplicationSettings main configuration class."""

    def test_creates_with_default_values(self) -> None:
        """Creates application settings with default values."""
        reset_settings()  # Clear any cached settings
        with patch.dict(os.environ, {"APP_NAME": "fastapi-template"}, clear=True):
            settings = ApplicationSettings()
            assert settings.app_name == "fastapi-template"
            assert settings.environment == Environment.DEVELOPMENT
            assert settings.debug is False
            assert settings.timezone == "UTC"
            assert isinstance(settings.api, APISettings)
            assert isinstance(settings.database, DatabaseSettings)

    def test_creates_with_environment_variables(self) -> None:
        """Creates application settings from environment variables."""
        with patch.dict(
            os.environ,
            {
                "APP_NAME": "test-app",
                "ENVIRONMENT": "testing",
                "DEBUG": "true",
                "API__PORT": "5000",
                "DATABASE__PRIMARY_DB": "postgresql",
            },
        ):
            settings = ApplicationSettings()
            assert settings.app_name == "test-app"
            assert settings.environment == Environment.TESTING
            assert settings.debug is True
            assert settings.api.port == 5000
            assert settings.database.primary_db == DatabaseType.POSTGRESQL

    def test_is_development_method(self) -> None:
        """Tests is_development method."""
        settings = ApplicationSettings(environment=Environment.DEVELOPMENT)
        assert settings.is_development() is True
        assert settings.is_production() is False
        assert settings.is_testing() is False

    def test_is_production_method(self) -> None:
        """Tests is_production method."""
        settings = ApplicationSettings(environment=Environment.PRODUCTION)
        assert settings.is_production() is True
        assert settings.is_development() is False
        assert settings.is_testing() is False

    def test_is_testing_method(self) -> None:
        """Tests is_testing method."""
        settings = ApplicationSettings(environment=Environment.TESTING)
        assert settings.is_testing() is True
        assert settings.is_development() is False
        assert settings.is_production() is False

    def test_validate_production_settings_raises_for_debug(self) -> None:
        """Raises error when debug is enabled in production."""
        settings = ApplicationSettings(
            environment=Environment.PRODUCTION,
            debug=True,
        )
        with pytest.raises(ConfigurationException, match="Debug mode cannot be enabled"):
            settings.validate_configuration()

    def test_validate_production_settings_raises_for_sample_api_keys(self) -> None:
        """Raises error when sample API keys are used in production."""
        settings = ApplicationSettings(
            environment=Environment.PRODUCTION,
            security=SecuritySettings(
                api_keys=["sample-api-key-123"],
            ),
        )
        with pytest.raises(ConfigurationException, match="Sample API keys cannot be used"):
            settings.validate_configuration()

    def test_validate_production_settings_raises_for_in_memory_db(self) -> None:
        """Raises error when in-memory database is used in production."""
        settings = ApplicationSettings(
            environment=Environment.PRODUCTION,
            database=DatabaseSettings(primary_db=DatabaseType.IN_MEMORY),
            security=SecuritySettings(api_keys=["real-key"]),
        )
        with pytest.raises(ConfigurationException, match="In-memory database cannot be used"):
            settings.validate_configuration()

    def test_validate_database_configuration_postgresql_mismatch(self) -> None:
        """Raises error when PostgreSQL is enabled but URL doesn't match."""
        settings = ApplicationSettings(
            database=DatabaseSettings(
                enable_postgresql=True,
                database_url="mongodb://localhost",
            ),
        )
        with pytest.raises(ConfigurationException, match="PostgreSQL enabled but database URL"):
            settings.validate_configuration()

    def test_validate_database_configuration_redis_no_url(self) -> None:
        """Raises error when Redis cache is enabled but no URL provided."""
        settings = ApplicationSettings(
            database=DatabaseSettings(
                enable_redis_cache=True,
                cache_url=None,
            ),
        )
        with pytest.raises(ConfigurationException, match="Redis cache enabled but no cache URL"):
            settings.validate_configuration()

    def test_validate_database_configuration_cache_db_no_url(self) -> None:
        """Raises error when cache database is specified but no URL provided."""
        settings = ApplicationSettings(
            database=DatabaseSettings(
                cache_db=DatabaseType.REDIS,
                cache_url=None,
            ),
        )
        with pytest.raises(ConfigurationException, match="Cache database specified but no cache"):
            settings.validate_configuration()

    def test_validate_external_services_email_no_key(self) -> None:
        """Raises error when email service is enabled but no API key provided."""
        settings = ApplicationSettings(
            external_services=ExternalServicesSettings(
                email_service_enabled=True,
                email_service_api_key="",
            ),
        )
        with pytest.raises(ConfigurationException, match="Email service API key required"):
            settings.validate_configuration()

    def test_validate_external_services_sms_no_key(self) -> None:
        """Raises error when SMS service is enabled but no API key provided."""
        settings = ApplicationSettings(
            external_services=ExternalServicesSettings(
                sms_service_enabled=True,
                sms_service_api_key="",
            ),
        )
        with pytest.raises(ConfigurationException, match="SMS service API key required"):
            settings.validate_configuration()

    def test_validation_passes_for_valid_configuration(self) -> None:
        """Validation passes for valid configuration."""
        settings = ApplicationSettings(
            environment=Environment.DEVELOPMENT,
            database=DatabaseSettings(
                enable_postgresql=True,
                database_url="postgresql://localhost/db",
            ),
            external_services=ExternalServicesSettings(
                email_service_enabled=True,
                email_service_api_key="valid-key",
            ),
        )
        settings.validate_configuration()  # Should not raise


class TestGetSettings:
    """Tests for get_settings function."""

    def test_returns_singleton_instance(self) -> None:
        """Returns the same singleton instance."""
        reset_settings()  # Clear any existing instance
        with patch.dict(os.environ, {"APP_NAME": "singleton-test"}):
            settings1 = get_settings()
            settings2 = get_settings()
            assert settings1 is settings2
            assert settings1.app_name == "singleton-test"

    def test_validates_configuration_on_creation(self) -> None:
        """Validates configuration when creating settings."""
        reset_settings()
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "production",
                    "DEBUG": "true",
                },
            ),
            pytest.raises(ConfigurationException, match="Debug mode cannot be enabled"),
        ):
            get_settings()

    def test_reset_settings_clears_singleton(self) -> None:
        """Reset settings clears the singleton instance."""
        reset_settings()
        with patch.dict(os.environ, {"APP_NAME": "first"}):
            settings1 = get_settings()
            assert settings1.app_name == "first"

        reset_settings()
        with patch.dict(os.environ, {"APP_NAME": "second"}):
            settings2 = get_settings()
            assert settings2.app_name == "second"
            assert settings1 is not settings2


class TestEnvironmentSpecificBehavior:
    """Tests for environment-specific behavior."""

    def test_development_environment_allows_debug(self) -> None:
        """Development environment allows debug mode."""
        settings = ApplicationSettings(
            environment=Environment.DEVELOPMENT,
            debug=True,
        )
        settings.validate_configuration()  # Should not raise

    def test_staging_environment_configuration(self) -> None:
        """Staging environment configuration works correctly."""
        settings = ApplicationSettings(
            environment=Environment.STAGING,
            database=DatabaseSettings(primary_db=DatabaseType.POSTGRESQL),
        )
        assert settings.environment == Environment.STAGING
        assert not settings.is_development()
        assert not settings.is_production()
        settings.validate_configuration()  # Should not raise

    def test_nested_configuration_with_delimiter(self) -> None:
        """Nested configuration works with double underscore delimiter."""
        with patch.dict(
            os.environ,
            {
                "API__HOST": "192.168.1.1",
                "API__PORT": "4000",
                "DATABASE__POOL_SIZE": "20",
                "SECURITY__RATE_LIMIT_REQUESTS_PER_MINUTE": "200",
            },
        ):
            settings = ApplicationSettings()
            assert settings.api.host == "192.168.1.1"
            assert settings.api.port == 4000
            assert settings.database.pool_size == 20
            assert settings.security.rate_limit_requests_per_minute == 200
