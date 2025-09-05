"""Application settings using Pydantic Settings."""

import os
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
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


class MessageClassificationSettings(BaseModel):
    """Message classification configuration."""

    # Engine enablement flags
    keyword_engine_enabled: bool = Field(
        default=True,
        description="Enable keyword rule engine",
    )
    pattern_engine_enabled: bool = Field(
        default=True,
        description="Enable pattern rule engine",
    )
    service_category_engine_enabled: bool = Field(
        default=True,
        description="Enable service category rule engine",
    )
    ai_engine_enabled: bool = Field(default=False, description="Enable AI rule engine")

    # AI configuration (for future use)
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    ai_model: str = Field(default="claude-3-sonnet", description="AI model to use")
    ai_confidence_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="AI confidence threshold",
    )

    # Rule file paths
    keywords_config_file: str = Field(
        default="config/classification/keywords.yaml",
        description="Keywords config file path",
    )
    patterns_config_file: str = Field(
        default="config/classification/patterns.yaml",
        description="Patterns config file path",
    )
    engines_config_file: str = Field(
        default="config/classification/engines.yaml",
        description="Engines config file path",
    )

    # Classification thresholds
    request_confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Request classification threshold",
    )
    recommendation_confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Recommendation classification threshold",
    )


class MentionExtractionSettings(BaseModel):
    """Mention extraction configuration."""

    # Extraction strategy enablement flags
    name_pattern_extraction_enabled: bool = Field(
        default=True,
        description="Enable name pattern extraction",
    )
    phone_pattern_extraction_enabled: bool = Field(
        default=True,
        description="Enable phone number pattern extraction",
    )
    service_keyword_extraction_enabled: bool = Field(
        default=True,
        description="Enable service keyword extraction",
    )
    location_extraction_enabled: bool = Field(
        default=True,
        description="Enable location pattern extraction",
    )

    # Confidence and scoring thresholds
    minimum_confidence_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for mention extraction",
    )
    name_pattern_confidence_weight: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence weight for name pattern matches",
    )
    phone_pattern_confidence_weight: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Confidence weight for phone pattern matches",
    )
    service_keyword_confidence_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence weight for service keyword matches",
    )
    location_confidence_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Confidence weight for location pattern matches",
    )

    # Validation rules
    minimum_mention_length: int = Field(
        default=2,
        ge=1,
        le=100,
        description="Minimum length for valid mentions",
    )
    maximum_mention_length: int = Field(
        default=200,
        ge=10,
        le=1000,
        description="Maximum length for valid mentions",
    )

    # Configuration file paths
    name_patterns_config_file: str = Field(
        default="config/extraction/name_patterns.yaml",
        description="Name patterns config file path",
    )
    service_keywords_config_file: str = Field(
        default="config/extraction/service_keywords.yaml",
        description="Service keywords config file path",
    )
    location_patterns_config_file: str = Field(
        default="config/extraction/location_patterns.yaml",
        description="Location patterns config file path",
    )
    blacklisted_terms_config_file: str = Field(
        default="config/extraction/blacklisted_terms.yaml",
        description="Blacklisted terms config file path",
    )

    # Extraction behaviour settings
    deduplicate_similar_mentions: bool = Field(
        default=True,
        description="Enable deduplication of similar mentions",
    )
    similarity_threshold_for_deduplication: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for mention deduplication",
    )
    maximum_mentions_per_message: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of mentions to extract per message",
    )


class SummaryTriggerMode(str, Enum):
    """When summary generation should be triggered."""

    ON_REQUEST = "on_request"
    ALWAYS_ON = "always_on"
    SCHEDULED_ONLY = "scheduled_only"
    HYBRID = "hybrid"


class SummaryDeliveryMode(str, Enum):
    """How summaries should be delivered to groups."""

    BASIC_ONLY = "basic_only"
    MULTI_TYPE = "multi_type"
    ADAPTIVE = "adaptive"


class SummaryGenerationSettings(BaseModel):
    """Comprehensive configuration for summary generation system."""

    model_config = ConfigDict(frozen=True)

    # Core enablement
    summary_generation_enabled: bool = Field(
        default=True,
        description="Enable summary generation system",
    )

    # Trigger configuration
    trigger_mode: SummaryTriggerMode = Field(
        default=SummaryTriggerMode.ON_REQUEST,
        description="When to trigger summary generation",
    )

    # Delivery configuration
    delivery_mode: SummaryDeliveryMode = Field(
        default=SummaryDeliveryMode.BASIC_ONLY,
        description="How to deliver summaries to groups",
    )

    # Content filtering
    min_endorsements_for_inclusion: int = Field(
        default=1,
        ge=0,
        description="Minimum endorsements required for inclusion",
    )
    max_providers_per_summary: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum providers to include in summary",
    )
    confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for provider inclusion",
    )

    # Time-based filtering
    recent_activity_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days to consider for recent activity summaries",
    )
    high_activity_threshold_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Days to consider provider as recently active",
    )

    # Summary types configuration
    enable_comprehensive_summary: bool = Field(
        default=True,
        description="Enable comprehensive summary generation",
    )
    enable_top_rated_summary: bool = Field(
        default=True,
        description="Enable top-rated providers summary",
    )
    enable_recent_activity_summary: bool = Field(
        default=False,
        description="Enable recent activity summary",
    )
    enable_category_focused_summary: bool = Field(
        default=False,
        description="Enable category-focused summaries",
    )

    # Top-rated criteria
    top_rated_min_endorsements: int = Field(
        default=3,
        ge=1,
        description="Minimum endorsements for top-rated classification",
    )
    top_rated_confidence_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for top-rated classification",
    )

    # Category grouping
    enable_category_grouping: bool = Field(
        default=True,
        description="Group providers by service categories",
    )
    max_categories_per_summary: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum service categories to include",
    )

    # Response timing
    response_delay_seconds: int = Field(
        default=30,
        ge=0,
        le=300,
        description="Delay before posting summary to allow for more responses",
    )
    batch_processing_enabled: bool = Field(
        default=True,
        description="Batch multiple requests to reduce message frequency",
    )

    # Message formatting
    include_endorsement_counts: bool = Field(
        default=True,
        description="Include endorsement counts in summaries",
    )
    include_confidence_indicators: bool = Field(
        default=False,
        description="Include confidence indicators for technical users",
    )

    # Privacy and data handling
    anonymize_endorser_details: bool = Field(
        default=True,
        description="Anonymize who provided endorsements",
    )

    @model_validator(mode="after")
    def validate_summary_settings(self) -> "SummaryGenerationSettings":
        """Validate summary generation configuration consistency."""
        if not any(
            [
                self.enable_comprehensive_summary,
                self.enable_top_rated_summary,
                self.enable_recent_activity_summary,
                self.enable_category_focused_summary,
            ],
        ):
            raise ConfigurationException("At least one summary type must be enabled")

        return self


class APISettings(BaseModel):
    """API configuration settings for FastAPI application."""

    model_config = ConfigDict(frozen=True)

    # API versioning and paths
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="API v1 prefix path",
    )

    # CORS configuration (comma-separated string, parsed to list)
    cors_allowed_origins_str: str = Field(
        default="*",  # Development default - should be restricted in production
        alias="cors_allowed_origins",
        description="CORS allowed origins (comma-separated)",
    )

    # Request/Response limits
    max_request_size_mb: int = Field(
        default=10,
        gt=0,
        description="Maximum request size in MB",
    )

    request_timeout_seconds: int = Field(
        default=30,
        gt=0,
        description="Request timeout in seconds",
    )

    # Documentation and schema
    docs_enabled: bool = Field(
        default=True,
        description="Enable API documentation (Swagger/OpenAPI)",
    )

    include_in_schema: bool = Field(
        default=True,
        description="Include endpoints in OpenAPI schema",
    )

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        """Validate API prefix format."""
        if not value.startswith("/"):
            raise ValueError("API prefix must start with '/'")
        if value.endswith("/") and value != "/":
            raise ValueError("API prefix must not end with '/'")
        return value

    @property
    def cors_allowed_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if not self.cors_allowed_origins_str.strip():
            return ["*"]
        # Split by comma and strip whitespace
        origins = [
            origin.strip() for origin in self.cors_allowed_origins_str.split(",") if origin.strip()
        ]
        return origins if origins else ["*"]


class FirestoreSettings(BaseModel):
    """Firestore database configuration settings."""

    model_config = ConfigDict(frozen=True)

    # Core Firestore configuration
    firestore_project_id: str = Field(
        default="neighbour-approved-dev",
        description="Google Cloud Project ID for Firestore",
    )

    firestore_database_id: str = Field(
        default="(default)",
        description="Firestore database ID within the project",
    )

    # Local development configuration
    firestore_emulator_host: str = Field(
        default="",
        description="Firestore emulator host:port (empty means use production)",
    )

    # Connection and performance settings
    firestore_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Request timeout for Firestore operations in seconds",
    )

    firestore_retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of retry attempts for failed operations",
    )

    firestore_batch_size: int = Field(
        default=500,
        ge=1,
        le=500,
        description="Maximum documents per batch operation",
    )

    # Health check configuration
    firestore_health_check_collection: str = Field(
        default="_health_checks",
        description="Collection name for health check operations",
    )

    @field_validator("firestore_emulator_host")
    @classmethod
    def validate_emulator_host(cls, value: str) -> str:
        """Validate emulator host format if provided."""
        if value.strip():
            # Basic validation for host:port format
            if ":" not in value:
                raise ValueError(
                    "Emulator host must include port (e.g., localhost:8080)",
                )
            parts = value.split(":")
            if len(parts) != 2:
                raise ValueError("Emulator host must be in format host:port")
            try:
                port = int(parts[1])
                if not 1000 <= port <= 65535:
                    raise ValueError("Port must be between 1000 and 65535")
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError("Port must be a valid number") from e
                raise
        return value

    @property
    def is_emulator_enabled(self) -> bool:
        """Check if Firestore emulator is configured."""
        return bool(self.firestore_emulator_host.strip())


class GreenAPISettings(BaseModel):
    """GREEN-API WhatsApp integration configuration."""

    model_config = ConfigDict(frozen=True)

    # GREEN-API credentials
    instance_id: str = Field(
        default="",
        description="GREEN-API instance ID from console.green-api.com",
    )

    api_token: str = Field(
        default="",
        description="GREEN-API token from console.green-api.com",
    )

    # Integration settings
    webhook_enabled: bool = Field(
        default=True,
        description="Enable webhook processing for incoming WhatsApp messages",
    )

    base_url: str = Field(
        default="https://api.green-api.com",
        description="GREEN-API base URL for API requests",
    )

    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Request timeout for GREEN-API operations in seconds",
    )

    retry_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Number of retry attempts for failed GREEN-API operations",
    )

    @property
    def is_configured(self) -> bool:
        """Check if GREEN-API is properly configured."""
        return bool(self.instance_id.strip() and self.api_token.strip())


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All configuration comes from environment or .env file.
    No hardcoded values allowed.
    """

    model_config = SettingsConfigDict(
        env_file=_get_env_files(),  # Dynamic env file loading
        env_file_encoding="utf-8",
        case_sensitive=False,
        frozen=True,  # Make immutable
        # Support nested env vars like MESSAGE_CLASSIFICATION__AI_ENGINE_ENABLED
        env_nested_delimiter="__",
    )

    # Core Application
    app_name: str = Field(description="Application name")
    environment: Environment = Field(description="Application environment")
    debug: bool = Field(description="Debug mode")

    # API Configuration
    api_host: str = Field(description="API host")
    api_port: int = Field(description="API port", ge=1000, le=65535)

    # Observability
    log_level: str = Field(description="Logging level")
    metrics_enabled: bool = Field(description="Enable metrics collection")
    metrics_port: int = Field(description="Metrics port")

    # Feature Flags
    feature_flags_enabled: bool = Field(description="Enable feature flags")
    feature_flags_file: str = Field(
        description="Feature flags configuration file",
    )

    # Security
    api_keys: str = Field(
        default="",
        description="Comma-separated list of valid API keys for webhook authentication",
    )
    rate_limit_requests: int = Field(
        default=60,
        description="Maximum requests per client per time window",
        ge=1,
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        description="Time window in seconds for rate limiting",
        ge=1,
    )
    webhook_secret_key: str = Field(
        default="",
        description="Secret key for HMAC-SHA256 webhook signature verification",
    )
    health_check_timeout_seconds: int = Field(
        default=30,
        description="Maximum time in seconds to wait for health checks",
        ge=1,
        le=300,
    )

    # Message Classification Settings
    message_classification: MessageClassificationSettings = MessageClassificationSettings()

    # Mention Extraction Settings
    mention_extraction: MentionExtractionSettings = MentionExtractionSettings()

    # Summary Generation Settings
    summary_generation: SummaryGenerationSettings = SummaryGenerationSettings()

    # API Settings
    api: APISettings = APISettings()

    # Firestore Settings
    firestore: FirestoreSettings = FirestoreSettings()

    # GREEN-API Settings
    green_api: GreenAPISettings = GreenAPISettings()

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        """Validate configuration settings and dependencies."""
        self._validate_environment_specific_requirements()
        self._validate_security_configuration()
        self._validate_observability_configuration()
        self._validate_firestore_configuration()
        self._validate_green_api_configuration()
        return self

    def _validate_environment_specific_requirements(self) -> None:
        """Validate environment-specific configuration requirements."""
        if self.environment == Environment.PRODUCTION:
            api_keys_value = str(self.api_keys)
            if not api_keys_value.strip():
                raise ConfigurationException(
                    "API keys are required in production environment",
                )
            webhook_secret_value = str(self.webhook_secret_key)
            if not webhook_secret_value.strip():
                raise ConfigurationException(
                    "Webhook secret key is required in production environment",
                )
            if self.debug:
                raise ConfigurationException(
                    "Debug mode must be disabled in production environment",
                )
            log_level_value = str(self.log_level)
            if log_level_value.upper() == "DEBUG":
                raise ConfigurationException(
                    "Debug log level not allowed in production environment",
                )

    def _validate_security_configuration(self) -> None:
        """Validate security-related configuration."""
        api_keys_value = str(self.api_keys)
        if api_keys_value.strip():
            api_key_list = [k.strip() for k in api_keys_value.split(",")]
            for api_key in api_key_list:
                if len(api_key) < 16:
                    raise ConfigurationException(
                        "All API keys must be at least 16 characters long",
                    )

        webhook_secret_value = str(self.webhook_secret_key)
        if webhook_secret_value.strip() and len(webhook_secret_value) < 32:
            raise ConfigurationException(
                "Webhook secret key must be at least 32 characters long",
            )

    def _validate_observability_configuration(self) -> None:
        """Validate observability configuration."""
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        log_level_value = str(self.log_level)
        if log_level_value.upper() not in valid_log_levels:
            valid_levels_str = ", ".join(valid_log_levels)
            message = f"Invalid log level '{log_level_value}'. Must be one of: {valid_levels_str}"
            raise ConfigurationException(message)

        if self.metrics_enabled and self.metrics_port == self.api_port:
            raise ConfigurationException(
                "Metrics port cannot be the same as API port",
            )

    def _validate_firestore_configuration(self) -> None:
        """Validate Firestore configuration."""
        if self.environment == Environment.PRODUCTION:
            # Production-specific validations
            if not self.firestore.firestore_project_id.strip():
                raise ConfigurationException(
                    "Firestore project ID is required in production",
                )
            if self.firestore.firestore_project_id == "neighbour-approved-dev":
                raise ConfigurationException(
                    "Cannot use development project ID in production",
                )
            if self.firestore.is_emulator_enabled:
                raise ConfigurationException(
                    "Firestore emulator cannot be used in production",
                )

        # General validations completed - timeout limits enforced by field validation

    def _validate_green_api_configuration(self) -> None:
        """Validate GREEN-API configuration."""
        if self.environment == Environment.PRODUCTION:
            # Production requires GREEN-API credentials
            if not self.green_api.is_configured:
                raise ConfigurationException(
                    "GREEN-API instance ID and token are required in production",
                )
            if not self.green_api.instance_id.strip():
                raise ConfigurationException(
                    "GREEN-API instance ID cannot be empty in production",
                )
            if not self.green_api.api_token.strip():
                raise ConfigurationException(
                    "GREEN-API token cannot be empty in production",
                )

        # Development allows unconfigured GREEN-API for testing


def validate_startup_configuration(
    settings_instance: "Settings | None" = None,
) -> "Settings":
    """Validate all configuration at application startup."""
    from src.infrastructure.observability import get_logger

    logger = get_logger(__name__)

    try:
        config = settings_instance or Settings()

        # Handle both enum and string values for environment
        env_value = (
            config.environment.value
            if hasattr(config.environment, "value")
            else str(config.environment)
        )

        logger.info(
            "Configuration validation started",
            environment=env_value,
            debug_mode=config.debug,
        )

        logger.info(
            "Configuration validation completed successfully",
            api_port=config.api_port,
            metrics_enabled=config.metrics_enabled,
            feature_flags_enabled=config.feature_flags_enabled,
            api_keys_configured=bool(config.api_keys.strip()),
            webhook_secret_configured=bool(config.webhook_secret_key.strip()),
        )

        return config

    except Exception as e:
        # Log with basic info we might have
        environment_info = "unknown"
        if hasattr(e, "__dict__") and "environment" in str(e):
            environment_info = "production"  # Common case

        logger.error(
            "Configuration validation failed",
            error=str(e),
            environment=environment_info,
        )
        raise


class _SettingsSingleton:
    """Settings singleton container."""

    _instance: Settings | None = None

    @classmethod
    def get_instance(cls) -> Settings:
        """Get the singleton Settings instance."""
        if cls._instance is None:
            cls._instance = Settings()
        return cls._instance


def get_settings() -> Settings:
    """Get the global settings instance (singleton pattern)."""
    return _SettingsSingleton.get_instance()


# Backward compatibility - maintain existing singleton instance
settings = get_settings()  # pylint: disable=invalid-name
