"""Health check response schemas using Pydantic V2."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Basic health check response schema."""

    model_config = ConfigDict(frozen=True)

    status: Literal["healthy", "unhealthy"] = Field(
        description="Overall health status",
    )
    modules: list[str] = Field(
        description="List of loaded/active modules",
    )
    timestamp: str = Field(
        description="ISO 8601 timestamp of health check",
    )


class HealthCheckDetail(BaseModel):
    """Individual health check component detail."""

    model_config = ConfigDict(frozen=True)

    status: Literal["healthy", "unhealthy"] = Field(
        description="Component health status",
    )
    response_time_ms: float = Field(
        ge=0.0,
        description="Response time in milliseconds",
    )
    error: str | None = Field(
        default=None,
        description="Error message if component is unhealthy",
    )


class DetailedHealthResponse(BaseModel):
    """Detailed health check response with component breakdown."""

    model_config = ConfigDict(frozen=True)

    status: Literal["healthy", "unhealthy"] = Field(
        description="Overall system health status",
    )
    checks: dict[str, HealthCheckDetail] = Field(
        description="Individual component health check results",
    )
    timestamp: str = Field(
        description="ISO 8601 timestamp of health check",
    )
