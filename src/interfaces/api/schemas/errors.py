"""Error response schemas using Pydantic V2."""

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    model_config = ConfigDict(frozen=True)

    detail: str = Field(
        description="Human-readable error description",
    )
    error_code: str = Field(
        description="Machine-readable error code",
    )
    timestamp: str = Field(
        description="ISO 8601 timestamp when error occurred",
    )


class ValidationErrorResponse(ErrorResponse):
    """Validation error response with field-specific details."""

    field_errors: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Field-specific validation error messages",
    )
