"""Unit tests for rate limiter security component."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, Request

from src.infrastructure.security.rate_limiter import (
    RateLimiter,
    RateLimitError,
    _RateLimiterSingleton,
    check_rate_limit,
    configure_rate_limiter,
    get_rate_limiter,
)


class TestRateLimitError:
    """Test rate limit error behavior."""

    def test_creates_error_with_message(self) -> None:
        """Creates error with message."""
        error = RateLimitError("Too many requests")

        assert str(error) == "Too many requests"
        assert error.message == "Too many requests"
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert error.retry_after == 0

    def test_creates_error_with_retry_after(self) -> None:
        """Creates error with retry after time."""
        error = RateLimitError("Rate limited", retry_after=60)

        assert error.retry_after == 60

    def test_inherits_from_application_error(self) -> None:
        """Inherits from ApplicationError."""
        from src.shared.exceptions import ApplicationError

        error = RateLimitError("Test error")
        assert isinstance(error, ApplicationError)


class TestRateLimiter:
    """Test rate limiter behavior."""

    def test_creates_limiter_with_config(self) -> None:
        """Creates limiter with configuration."""
        limiter = RateLimiter(limit=10, window_seconds=60)

        assert limiter.limit == 10
        assert limiter.window_seconds == 60
        assert limiter._requests is not None

    def test_allows_requests_under_limit(self) -> None:
        """Allows requests under the limit."""
        limiter = RateLimiter(limit=3, window_seconds=60)
        client_id = "test_client"

        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True

    def test_blocks_requests_over_limit(self) -> None:
        """Blocks requests over the limit."""
        limiter = RateLimiter(limit=2, window_seconds=60)
        client_id = "test_client"

        # Allow first two requests
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True

        # Block third request
        assert limiter.is_allowed(client_id) is False

    def test_allows_different_clients_independently(self) -> None:
        """Allows different clients independently."""
        limiter = RateLimiter(limit=1, window_seconds=60)

        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client2") is True

        # Both clients have used their limit
        assert limiter.is_allowed("client1") is False
        assert limiter.is_allowed("client2") is False

    @patch("src.infrastructure.security.rate_limiter.time.time")
    def test_cleans_up_old_requests(self, mock_time: MagicMock) -> None:
        """Cleans up old requests outside the window."""
        limiter = RateLimiter(limit=2, window_seconds=60)
        client_id = "test_client"

        # First request at time 0
        mock_time.return_value = 0
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True

        # Third request should be blocked
        assert limiter.is_allowed(client_id) is False

        # Move time forward past the window
        mock_time.return_value = 61

        # Should allow requests again after cleanup
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True

    def test_returns_current_time_for_empty_requests(self) -> None:
        """Returns current time for clients with no requests."""
        limiter = RateLimiter(limit=5, window_seconds=60)

        reset_time = limiter.get_reset_time("new_client")
        current_time = time.time()

        # Should be approximately current time (within 1 second)
        assert abs(reset_time - current_time) < 1

    @patch("src.infrastructure.security.rate_limiter.time.time")
    def test_returns_reset_time_for_existing_requests(self, mock_time: MagicMock) -> None:
        """Returns correct reset time for clients with existing requests."""
        limiter = RateLimiter(limit=2, window_seconds=60)
        client_id = "test_client"

        # Make requests at time 100
        mock_time.return_value = 100
        limiter.is_allowed(client_id)
        limiter.is_allowed(client_id)

        # Reset time should be 100 + 60 = 160
        reset_time = limiter.get_reset_time(client_id)
        assert reset_time == 160

    @patch("src.infrastructure.security.rate_limiter.time.time")
    def test_cleanup_removes_expired_requests(self, mock_time: MagicMock) -> None:
        """Cleanup removes expired requests."""
        limiter = RateLimiter(limit=5, window_seconds=10)
        client_id = "test_client"

        # Add requests at different times
        mock_time.return_value = 0
        limiter.is_allowed(client_id)

        mock_time.return_value = 5
        limiter.is_allowed(client_id)

        mock_time.return_value = 15
        limiter.is_allowed(client_id)

        # At time 15, request at time 0 should be cleaned up
        # Only requests from time 5 and 15 should remain
        client_requests = limiter._requests[client_id]
        assert len(client_requests) == 2
        assert 5 in client_requests
        assert 15 in client_requests

    def test_handles_zero_limit(self) -> None:
        """Handles zero limit configuration."""
        limiter = RateLimiter(limit=0, window_seconds=60)

        assert limiter.is_allowed("client") is False

    def test_handles_zero_window(self) -> None:
        """Handles zero window configuration."""
        limiter = RateLimiter(limit=5, window_seconds=0)
        client_id = "test_client"

        # With zero window, all requests should be cleaned up immediately
        assert limiter.is_allowed(client_id) is True


class TestRateLimiterSingleton:
    """Test rate limiter singleton behavior."""

    def test_raises_error_when_not_configured(self) -> None:
        """Raises error when limiter not configured."""
        _RateLimiterSingleton._instance = None

        with pytest.raises(RateLimitError, match="Rate limiter not configured"):
            _RateLimiterSingleton.get_instance()

    def test_returns_configured_instance(self) -> None:
        """Returns configured instance."""
        limiter = RateLimiter(limit=10, window_seconds=60)
        _RateLimiterSingleton.set_instance(limiter)

        result = _RateLimiterSingleton.get_instance()
        assert result is limiter

    def test_sets_singleton_instance(self) -> None:
        """Sets singleton instance."""
        limiter = RateLimiter(limit=10, window_seconds=60)

        _RateLimiterSingleton.set_instance(limiter)

        assert _RateLimiterSingleton._instance is limiter


class TestConfigureRateLimiter:
    """Test rate limiter configuration behavior."""

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_registers_with_service_registry(self, mock_get_registry: MagicMock) -> None:
        """Registers limiter with service registry."""
        mock_registry = MagicMock()
        mock_get_registry.return_value = mock_registry

        configure_rate_limiter(limit=100, window_seconds=300)

        mock_registry.register_rate_limiter.assert_called_once()
        limiter_arg = mock_registry.register_rate_limiter.call_args[0][0]
        assert isinstance(limiter_arg, RateLimiter)
        assert limiter_arg.limit == 100
        assert limiter_arg.window_seconds == 300

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_handles_service_registry_import_error(self, mock_get_registry: MagicMock) -> None:
        """Handles service registry import error gracefully."""
        mock_get_registry.side_effect = ImportError("Module not found")

        # Should not raise exception
        configure_rate_limiter(limit=50, window_seconds=120)

        # Should still set singleton
        limiter = _RateLimiterSingleton.get_instance()
        assert limiter.limit == 50
        assert limiter.window_seconds == 120

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_handles_service_registry_runtime_error(self, mock_get_registry: MagicMock) -> None:
        """Handles service registry runtime error gracefully."""
        mock_get_registry.side_effect = RuntimeError("Registry not initialized")

        # Should not raise exception
        configure_rate_limiter(limit=25, window_seconds=180)

        # Should still set singleton
        limiter = _RateLimiterSingleton.get_instance()
        assert limiter.limit == 25
        assert limiter.window_seconds == 180

    def test_sets_singleton_instance(self) -> None:
        """Sets singleton instance."""
        configure_rate_limiter(limit=15, window_seconds=90)

        limiter = _RateLimiterSingleton.get_instance()
        assert limiter.limit == 15
        assert limiter.window_seconds == 90


class TestGetRateLimiter:
    """Test get rate limiter behavior."""

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_returns_limiter_from_service_registry(self, mock_get_registry: MagicMock) -> None:
        """Returns limiter from service registry when available."""
        mock_limiter = RateLimiter(limit=100, window_seconds=60)
        mock_registry = MagicMock()
        mock_registry.has_rate_limiter.return_value = True
        mock_registry.get_rate_limiter.return_value = mock_limiter
        mock_get_registry.return_value = mock_registry

        result = get_rate_limiter()

        assert result is mock_limiter
        mock_registry.has_rate_limiter.assert_called_once()
        mock_registry.get_rate_limiter.assert_called_once()

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_falls_back_to_singleton_when_registry_unavailable(
        self, mock_get_registry: MagicMock
    ) -> None:
        """Falls back to singleton when service registry unavailable."""
        mock_get_registry.side_effect = ImportError("Registry not available")
        singleton_limiter = RateLimiter(limit=50, window_seconds=30)
        _RateLimiterSingleton.set_instance(singleton_limiter)

        result = get_rate_limiter()

        assert result is singleton_limiter

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_falls_back_to_singleton_when_limiter_not_in_registry(
        self, mock_get_registry: MagicMock
    ) -> None:
        """Falls back to singleton when limiter not in registry."""
        mock_registry = MagicMock()
        mock_registry.has_rate_limiter.return_value = False
        mock_get_registry.return_value = mock_registry
        singleton_limiter = RateLimiter(limit=25, window_seconds=45)
        _RateLimiterSingleton.set_instance(singleton_limiter)

        result = get_rate_limiter()

        assert result is singleton_limiter

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_raises_error_when_no_limiter_available(self, mock_get_registry: MagicMock) -> None:
        """Raises error when no limiter available."""
        mock_get_registry.side_effect = ImportError("Registry not available")
        _RateLimiterSingleton._instance = None

        with pytest.raises(RateLimitError, match="Rate limiter not configured"):
            get_rate_limiter()


class TestCheckRateLimit:
    """Test check rate limit FastAPI dependency behavior."""

    def test_allows_request_when_under_limit(self) -> None:
        """Allows request when under rate limit."""
        # Create mock request
        mock_client = Mock()
        mock_client.host = "192.168.1.100"
        mock_request = Mock(spec=Request)
        mock_request.client = mock_client

        # Configure rate limiter
        limiter = RateLimiter(limit=10, window_seconds=60)
        _RateLimiterSingleton.set_instance(limiter)

        result = check_rate_limit(mock_request)
        assert result == "192.168.1.100"

    @patch("src.infrastructure.security.rate_limiter.get_logger")
    @patch("src.infrastructure.security.rate_limiter.get_metrics_collector")
    def test_blocks_request_when_over_limit(
        self, mock_metrics: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Blocks request when over rate limit."""
        # Create mock request
        mock_client = Mock()
        mock_client.host = "192.168.1.200"
        mock_request = Mock(spec=Request)
        mock_request.client = mock_client

        # Configure rate limiter with very low limit
        limiter = RateLimiter(limit=1, window_seconds=60)
        _RateLimiterSingleton.set_instance(limiter)

        # Setup mocks
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # First request should succeed
        result = check_rate_limit(mock_request)
        assert result == "192.168.1.200"

        # Second request should fail
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(mock_request)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail == "Rate limit exceeded"
        assert exc_info.value.headers is not None
        assert "Retry-After" in exc_info.value.headers

        # Should log warning and increment metrics
        mock_logger_instance.warning.assert_called_once_with(
            "Rate limit exceeded", client_ip="192.168.1.200"
        )
        mock_metrics_instance.increment_counter.assert_called_once_with(
            "rate_limit_blocks_total", {"client_ip": "192.168.1.200"}
        )

    def test_handles_missing_client_info(self) -> None:
        """Handles missing client information."""
        mock_request = Mock(spec=Request)
        mock_request.client = None

        # Configure rate limiter
        limiter = RateLimiter(limit=10, window_seconds=60)
        _RateLimiterSingleton.set_instance(limiter)

        result = check_rate_limit(mock_request)
        assert result == "unknown"

    @patch("src.infrastructure.security.rate_limiter.time.time")
    @patch("src.infrastructure.security.rate_limiter.get_logger")
    @patch("src.infrastructure.security.rate_limiter.get_metrics_collector")
    def test_includes_correct_retry_after_header(
        self, mock_metrics: MagicMock, mock_logger: MagicMock, mock_time: MagicMock
    ) -> None:
        """Includes correct Retry-After header in rate limit response."""
        # Create mock request
        mock_client = Mock()
        mock_client.host = "192.168.1.300"
        mock_request = Mock(spec=Request)
        mock_request.client = mock_client

        # Configure rate limiter
        limiter = RateLimiter(limit=1, window_seconds=60)
        _RateLimiterSingleton.set_instance(limiter)

        # Setup mocks
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Set specific time for predictable retry calculation
        mock_time.return_value = 100

        # Make first request
        check_rate_limit(mock_request)

        # Set time for second request and retry calculation
        mock_time.return_value = 120  # 20 seconds later

        # Second request should fail with correct retry time
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(mock_request)

        # Retry-After should be 40 seconds (160 - 120)
        assert exc_info.value.headers is not None
        assert exc_info.value.headers["Retry-After"] == "40"

    def test_allows_requests_from_different_ips(self) -> None:
        """Allows requests from different IP addresses independently."""
        # Configure rate limiter with limit of 1
        limiter = RateLimiter(limit=1, window_seconds=60)
        _RateLimiterSingleton.set_instance(limiter)

        # Create requests from different IPs
        mock_client1 = Mock()
        mock_client1.host = "192.168.1.1"
        mock_request1 = Mock(spec=Request)
        mock_request1.client = mock_client1

        mock_client2 = Mock()
        mock_client2.host = "192.168.1.2"
        mock_request2 = Mock(spec=Request)
        mock_request2.client = mock_client2

        # Both should be allowed
        result1 = check_rate_limit(mock_request1)
        result2 = check_rate_limit(mock_request2)

        assert result1 == "192.168.1.1"
        assert result2 == "192.168.1.2"
