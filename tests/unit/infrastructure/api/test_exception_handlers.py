"""Unit tests for FastAPI exception handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from config.settings import ApplicationSettings, Environment
from src.infrastructure.api.exception_handlers import (
    ErrorResponse,
    RateLimitErrorResponse,
    ValidationErrorResponse,
    infrastructure_exception_handler,
    not_found_exception_handler,
    rate_limit_exception_handler,
    validation_exception_handler,
)
from src.shared.exceptions import (
    AuthenticationException,
    EntityNotFoundException,
    RateLimitExceededException,
    ValidationException,
)


class TestErrorResponseModels:
    """Test error response model structure."""

    def test_error_response_has_required_fields(self) -> None:
        """ErrorResponse has required fields."""
        response = ErrorResponse(
            error_code="TEST_ERROR", message="Test message", timestamp="2024-01-01T00:00:00"
        )

        assert response.error_code == "TEST_ERROR"
        assert response.message == "Test message"
        assert response.timestamp == "2024-01-01T00:00:00"

    def test_validation_error_response_extends_base(self) -> None:
        """ValidationErrorResponse extends ErrorResponse with field."""
        response = ValidationErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Field validation failed",
            timestamp="2024-01-01T00:00:00",
            field="email",
        )

        assert response.error_code == "VALIDATION_ERROR"
        assert response.message == "Field validation failed"
        assert response.timestamp == "2024-01-01T00:00:00"
        assert response.field == "email"

    def test_validation_error_response_field_optional(self) -> None:
        """ValidationErrorResponse field is optional."""
        response = ValidationErrorResponse(
            error_code="VALIDATION_ERROR",
            message="General validation failed",
            timestamp="2024-01-01T00:00:00",
        )

        assert response.field is None

    def test_rate_limit_error_response_has_retry_after(self) -> None:
        """RateLimitErrorResponse has retry_after_seconds."""
        response = RateLimitErrorResponse(
            error_code="RATE_LIMIT_EXCEEDED",
            message="Too many requests",
            timestamp="2024-01-01T00:00:00",
            retry_after_seconds=60,
        )

        assert response.retry_after_seconds == 60

    def test_error_response_model_dump_excludes_none(self) -> None:
        """Error response model_dump excludes None values."""
        response = ValidationErrorResponse(
            error_code="TEST_ERROR", message="Test message", timestamp="2024-01-01T00:00:00"
        )

        data = response.model_dump(exclude_none=True)
        assert "field" not in data
        assert data["error_code"] == "TEST_ERROR"


class TestValidationExceptionHandler:
    """Test validation exception handler."""

    @pytest.fixture
    def mock_request(self) -> Request:
        """Create mock request."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"
        return mock_request

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_handles_validation_exception(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Handles ValidationException correctly."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = ValidationException("Email is required", field="email")

        response = await validation_exception_handler(mock_request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 422

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_logs_validation_error_with_context(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Logs validation error with context."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = ValidationException("Email is required", field="email")

        await validation_exception_handler(mock_request, exc)

        mock_logger.warning.assert_called_once_with(
            "Validation error occurred",
            error_code=exc.error_code,
            message=exc.message,
            field="email",
            path="/api/test",
        )

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_records_validation_error_metrics(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Records validation error metrics."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = ValidationException("Email is required", field="email")

        await validation_exception_handler(mock_request, exc)

        mock_metrics.increment_counter.assert_called_once_with(
            "validation_errors_total",
            {"error_code": exc.error_code, "field": "email"},
        )

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_handles_validation_exception_without_field(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Handles validation exception without field attribute."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = ValidationException("General validation error")

        response = await validation_exception_handler(mock_request, exc)

        assert response.status_code == 422
        mock_metrics.increment_counter.assert_called_once_with(
            "validation_errors_total",
            {"error_code": exc.error_code, "field": "unknown"},
        )

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @patch("src.infrastructure.api.exception_handlers.datetime")
    @pytest.mark.asyncio
    async def test_includes_timestamp_in_response(
        self,
        mock_datetime: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_request: Request,
    ) -> None:
        """Includes timestamp in response."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = fixed_time

        exc = ValidationException("Test error")

        response = await validation_exception_handler(mock_request, exc)

        response_data = bytes(response.body).decode()
        assert "2024-01-01T12:00:00" in response_data

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_simulates_async_work(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Handler simulates async work with sleep."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = ValidationException("Test error")

        # Handler should complete successfully (sleep is brief)
        response = await validation_exception_handler(mock_request, exc)
        assert response.status_code == 422


class TestNotFoundExceptionHandler:
    """Test not found exception handler."""

    @pytest.fixture
    def mock_request(self) -> Request:
        """Create mock request."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/users/123"
        return mock_request

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_handles_not_found_exception(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Handles EntityNotFoundException correctly."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = EntityNotFoundException("User not found")

        response = await not_found_exception_handler(mock_request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_logs_not_found_error_as_info(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Logs not found error as info level (not warning)."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = EntityNotFoundException("User not found")

        await not_found_exception_handler(mock_request, exc)

        mock_logger.info.assert_called_once_with(
            "Resource not found",
            error_code=exc.error_code,
            message=exc.message,
            path="/api/users/123",
        )

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_records_not_found_metrics(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Records not found error metrics."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = EntityNotFoundException("User not found")

        await not_found_exception_handler(mock_request, exc)

        mock_metrics.increment_counter.assert_called_once_with(
            "not_found_errors_total", {"error_code": exc.error_code}
        )

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_creates_standard_error_response(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Creates standard error response structure."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = EntityNotFoundException("User not found")

        response = await not_found_exception_handler(mock_request, exc)

        response_data = bytes(response.body).decode()
        assert "ENTITY_NOT_FOUND" in response_data
        assert "User not found" in response_data
        assert "timestamp" in response_data


class TestRateLimitExceptionHandler:
    """Test rate limit exception handler."""

    @pytest.fixture
    def mock_request(self) -> Request:
        """Create mock request with client info."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/data"
        mock_request.client.host = "192.168.1.100"
        return mock_request

    @pytest.fixture
    def mock_request_no_client(self) -> Request:
        """Create mock request without client info."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/data"
        mock_request.client = None
        return mock_request

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_handles_rate_limit_exception(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Handles RateLimitExceededException correctly."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = RateLimitExceededException("Rate limit exceeded")

        response = await rate_limit_exception_handler(mock_request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 429

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_logs_rate_limit_with_client_ip(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Logs rate limit error with client IP."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = RateLimitExceededException("Rate limit exceeded")

        await rate_limit_exception_handler(mock_request, exc)

        mock_logger.warning.assert_called_once_with(
            "Rate limit exceeded",
            error_code=exc.error_code,
            message=exc.message,
            path="/api/data",
            client_ip="192.168.1.100",
        )

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_handles_missing_client_info(
        self,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_request_no_client: Request,
    ) -> None:
        """Handles missing client info gracefully."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = RateLimitExceededException("Rate limit exceeded")

        await rate_limit_exception_handler(mock_request_no_client, exc)

        mock_logger.warning.assert_called_once_with(
            "Rate limit exceeded",
            error_code=exc.error_code,
            message=exc.message,
            path="/api/data",
            client_ip="unknown",
        )

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_includes_retry_after_header(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Includes Retry-After header in response."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = RateLimitExceededException("Rate limit exceeded")

        response = await rate_limit_exception_handler(mock_request, exc)

        assert response.headers.get("Retry-After") == "60"

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_response_includes_retry_after_seconds(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Response body includes retry_after_seconds."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = RateLimitExceededException("Rate limit exceeded")

        response = await rate_limit_exception_handler(mock_request, exc)

        response_data = bytes(response.body).decode()
        assert "retry_after_seconds" in response_data
        assert "60" in response_data

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_records_rate_limit_metrics(
        self, mock_get_metrics: MagicMock, mock_get_logger: MagicMock, mock_request: Request
    ) -> None:
        """Records rate limit error metrics."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        exc = RateLimitExceededException("Rate limit exceeded")

        await rate_limit_exception_handler(mock_request, exc)

        mock_metrics.increment_counter.assert_called_once_with(
            "rate_limit_errors_total", {"error_code": exc.error_code}
        )


class TestInfrastructureExceptionHandler:
    """Test infrastructure exception handler."""

    @pytest.fixture
    def mock_request(self) -> Request:
        """Create mock request."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/external"
        return mock_request

    @pytest.fixture
    def debug_settings(self) -> ApplicationSettings:
        """Create debug settings."""
        return ApplicationSettings(debug=True, environment=Environment.DEVELOPMENT)

    @pytest.fixture
    def production_settings(self) -> ApplicationSettings:
        """Create production settings."""
        return ApplicationSettings(debug=False, environment=Environment.PRODUCTION)

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @patch("src.infrastructure.api.exception_handlers.get_settings")
    @pytest.mark.asyncio
    async def test_handles_infrastructure_exception(
        self,
        mock_get_settings: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_request: Request,
        debug_settings: ApplicationSettings,
    ) -> None:
        """Handles infrastructure exceptions correctly."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_get_settings.return_value = debug_settings

        exc = AuthenticationException("Invalid API key")

        response = await infrastructure_exception_handler(mock_request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @patch("src.infrastructure.api.exception_handlers.get_settings")
    @pytest.mark.asyncio
    async def test_logs_infrastructure_error(
        self,
        mock_get_settings: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_request: Request,
        debug_settings: ApplicationSettings,
    ) -> None:
        """Logs infrastructure error with context."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_get_settings.return_value = debug_settings

        exc = AuthenticationException("Invalid API key")

        await infrastructure_exception_handler(mock_request, exc)

        mock_logger.error.assert_called_once_with(
            "Infrastructure error occurred",
            error_code=exc.error_code,
            message=exc.message,
            path="/api/external",
            debug_mode=True,
        )

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @patch("src.infrastructure.api.exception_handlers.get_settings")
    @pytest.mark.asyncio
    async def test_debug_mode_includes_original_message(
        self,
        mock_get_settings: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_request: Request,
        debug_settings: ApplicationSettings,
    ) -> None:
        """Debug mode includes original error message."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_get_settings.return_value = debug_settings

        exc = AuthenticationException("Invalid API key format")

        response = await infrastructure_exception_handler(mock_request, exc)

        response_data = bytes(response.body).decode()
        assert "Invalid API key format" in response_data

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @patch("src.infrastructure.api.exception_handlers.get_settings")
    @pytest.mark.asyncio
    async def test_production_mode_uses_generic_message(
        self,
        mock_get_settings: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_request: Request,
        production_settings: ApplicationSettings,
    ) -> None:
        """Production mode uses generic error message."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_get_settings.return_value = production_settings

        exc = AuthenticationException("Invalid API key format")

        response = await infrastructure_exception_handler(mock_request, exc)

        response_data = bytes(response.body).decode()
        assert "An internal server error occurred" in response_data
        assert "Invalid API key format" not in response_data

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @patch("src.infrastructure.api.exception_handlers.get_settings")
    @pytest.mark.asyncio
    async def test_records_infrastructure_error_metrics(
        self,
        mock_get_settings: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_request: Request,
        debug_settings: ApplicationSettings,
    ) -> None:
        """Records infrastructure error metrics."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_get_settings.return_value = debug_settings

        exc = AuthenticationException("Invalid API key")

        await infrastructure_exception_handler(mock_request, exc)

        mock_metrics.increment_counter.assert_called_once_with(
            "infrastructure_errors_total", {"error_code": exc.error_code}
        )

    @patch("src.infrastructure.api.exception_handlers.get_logger")
    @patch("src.infrastructure.api.exception_handlers.get_metrics_collector")
    @patch("src.infrastructure.api.exception_handlers.get_settings")
    @pytest.mark.asyncio
    async def test_handles_different_infrastructure_exceptions(
        self,
        mock_get_settings: MagicMock,
        mock_get_metrics: MagicMock,
        mock_get_logger: MagicMock,
        mock_request: Request,
        debug_settings: ApplicationSettings,
    ) -> None:
        """Handles different types of infrastructure exceptions."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_get_settings.return_value = debug_settings

        for exc_class in [AuthenticationException]:
            exc = exc_class("Test error")
            response = await infrastructure_exception_handler(mock_request, exc)
            assert response.status_code == 500
