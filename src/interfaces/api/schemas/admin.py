"""Administrative endpoint schemas using Pydantic V2."""

from pydantic import BaseModel, ConfigDict, Field


class AdminInfoResponse(BaseModel):
    """Application information response schema."""

    model_config = ConfigDict(frozen=True)

    app_name: str = Field(
        description="Application name",
    )
    version: str = Field(
        description="Application version",
    )
    environment: str = Field(
        description="Deployment environment",
    )
    build_timestamp: str = Field(
        description="ISO 8601 timestamp when application was built",
    )
    python_version: str = Field(
        description="Python runtime version",
    )


class SafeConfigResponse(BaseModel):
    """Safe configuration response without sensitive data."""

    model_config = ConfigDict(frozen=True)

    api_host: str = Field(
        description="API server host",
    )
    api_port: int = Field(
        ge=1000,
        le=65535,
        description="API server port",
    )
    log_level: str = Field(
        description="Logging level",
    )
    metrics_enabled: bool = Field(
        description="Whether metrics collection is enabled",
    )
    debug_mode: bool = Field(
        description="Whether debug mode is active",
    )
    cors_origins: list[str] = Field(
        description="Configured CORS origins",
    )


class ServiceStatusResponse(BaseModel):
    """Infrastructure service status response schema."""

    model_config = ConfigDict(frozen=True)

    service_registry_active: bool = Field(
        description="Whether service registry is active",
    )
    metrics_collector_active: bool = Field(
        description="Whether metrics collector is active",
    )
    health_checker_active: bool = Field(
        description="Whether health checker is active",
    )
    api_key_validator_configured: bool = Field(
        description="Whether API key validator is configured",
    )
    rate_limiter_configured: bool = Field(
        description="Whether rate limiter is configured",
    )
    webhook_verifier_configured: bool = Field(
        description="Whether webhook verifier is configured",
    )
    services_count: int = Field(
        ge=0,
        description="Total number of registered services",
    )
