"""FastAPI exception handlers for domain-specific exceptions."""

import asyncio
from datetime import datetime
from typing import cast

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config.settings import get_settings
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import (
    ApplicationError,
    RateLimitExceededException,
    ValidationException,
)


# Error Response Models
class ErrorResponse(BaseModel):
    """Base error response model."""

    error_code: str
    message: str
    timestamp: str


class ValidationErrorResponse(ErrorResponse):
    """Error response model for validation errors with field context."""

    field: str | None = None


class RateLimitErrorResponse(ErrorResponse):
    """Error response model for rate limit errors."""

    retry_after_seconds: int


async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle validation exceptions with field context."""
    await asyncio.sleep(0.01)  # Simulate async work
    logger = get_logger(__name__)
    metrics = get_metrics_collector()

    # Cast to ValidationException for type safety
    validation_exc = cast(ValidationException, exc)

    # Log validation error with context
    logger.warning(
        "Validation error occurred",
        error_code=validation_exc.error_code,
        message=validation_exc.message,
        field=getattr(validation_exc, "field", None),
        path=request.url.path,
    )

    # Increment validation error metrics
    field_value = getattr(validation_exc, "field", None)
    metrics.increment_counter(
        "validation_errors_total",
        {
            "error_code": validation_exc.error_code,
            "field": field_value if field_value is not None else "unknown",
        },
    )

    # Create response data
    response_data = ValidationErrorResponse(
        error_code=validation_exc.error_code,
        message=validation_exc.message,
        timestamp=datetime.now().isoformat(),
        field=getattr(validation_exc, "field", None),
    )

    return JSONResponse(
        status_code=422,
        content=response_data.model_dump(exclude_none=True),
    )


async def not_found_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle business logic not found exceptions."""
    await asyncio.sleep(0.01)
    logger = get_logger(__name__)
    metrics = get_metrics_collector()

    # Cast to ApplicationError for type safety
    approved_exc = cast(ApplicationError, exc)

    # Log not found error
    logger.info(
        "Resource not found",
        error_code=approved_exc.error_code,
        message=approved_exc.message,
        path=request.url.path,
    )

    # Increment not found metrics
    metrics.increment_counter(
        "not_found_errors_total",
        {"error_code": approved_exc.error_code},
    )

    # Create response data
    response_data = ErrorResponse(
        error_code=approved_exc.error_code,
        message=approved_exc.message,
        timestamp=datetime.now().isoformat(),
    )

    return JSONResponse(
        status_code=404,
        content=response_data.model_dump(),
    )


async def rate_limit_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle rate limit exceeded exceptions."""
    await asyncio.sleep(0.01)
    logger = get_logger(__name__)
    metrics = get_metrics_collector()

    # Cast to RateLimitExceededException for type safety
    rate_limit_exc = cast(RateLimitExceededException, exc)

    # Log rate limit violation
    logger.warning(
        "Rate limit exceeded",
        error_code=rate_limit_exc.error_code,
        message=rate_limit_exc.message,
        path=request.url.path,
        client_ip=request.client.host if request.client else "unknown",
    )

    # Increment rate limit metrics
    metrics.increment_counter(
        "rate_limit_errors_total",
        {"error_code": rate_limit_exc.error_code},
    )

    # Create response data with retry after
    response_data = RateLimitErrorResponse(
        error_code=rate_limit_exc.error_code,
        message=rate_limit_exc.message,
        timestamp=datetime.now().isoformat(),
        retry_after_seconds=60,  # Default retry after 60 seconds
    )

    return JSONResponse(
        status_code=429,
        content=response_data.model_dump(),
        headers={"Retry-After": "60"},
    )


async def infrastructure_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle infrastructure-level exceptions."""
    await asyncio.sleep(0.01)
    logger = get_logger(__name__)
    metrics = get_metrics_collector()
    settings = get_settings()

    # Cast to ApplicationError for type safety
    infra_exc = cast(ApplicationError, exc)

    # Log infrastructure error
    logger.error(
        "Infrastructure error occurred",
        error_code=infra_exc.error_code,
        message=infra_exc.message,
        path=request.url.path,
        debug_mode=settings.debug,
    )

    # Increment infrastructure error metrics
    metrics.increment_counter(
        "infrastructure_errors_total",
        {"error_code": infra_exc.error_code},
    )

    # Create response data with controlled message detail
    if settings.debug:
        # In debug mode, include original error message
        error_message = infra_exc.message
    else:
        # In production, use generic message for security
        error_message = "An internal server error occurred"

    response_data = ErrorResponse(
        error_code=infra_exc.error_code,
        message=error_message,
        timestamp=datetime.now().isoformat(),
    )

    return JSONResponse(
        status_code=500,
        content=response_data.model_dump(),
    )
