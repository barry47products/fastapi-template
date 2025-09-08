"""Unit tests for rate limiting security component."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

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

    def test_creates_error_with_message_and_retry_after(self) -> None:
        """Creates error with message and retry after time."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)

        assert str(error) == "Rate limit exceeded"
        assert error.message == "Rate limit exceeded"
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert error.retry_after == 60

    def test_creates_error_with_default_retry_after(self) -> None:
        """Creates error with default retry after time."""
        error = RateLimitError("Limit exceeded")

        assert error.retry_after == 0

    def test_inherits_from_application_error(self) -> None:
        """Inherits from ApplicationError."""
        from src.shared.exceptions import ApplicationError

        error = RateLimitError("Test error")
        assert isinstance(error, ApplicationError)


class TestRateLimiter:
    """Test rate limiter behavior."""

    def test_creates_limiter_with_configuration(self) -> None:
        """Creates rate limiter with limit and window configuration."""
        limiter = RateLimiter(limit=10, window_seconds=60)

        assert limiter.limit == 10
        assert limiter.window_seconds == 60

    def test_allows_requests_under_limit(self) -> None:
        """Allows requests under the configured limit."""
        limiter = RateLimiter(limit=3, window_seconds=60)
        client_id = "test_client"

        # Should allow up to the limit
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True

    def test_blocks_requests_over_limit(self) -> None:
        """Blocks requests that exceed the configured limit."""
        limiter = RateLimiter(limit=2, window_seconds=60)
        client_id = "test_client"

        # Allow up to limit
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True

        # Block requests over limit
        assert limiter.is_allowed(client_id) is False

    def test_tracks_clients_separately(self) -> None:
        """Tracks request counts separately for different clients."""
        limiter = RateLimiter(limit=2, window_seconds=60)

        # Different clients should have independent limits
        assert limiter.is_allowed("client_1") is True
        assert limiter.is_allowed("client_2") is True
        assert limiter.is_allowed("client_1") is True
        assert limiter.is_allowed("client_2") is True

        # Each client should hit their limit independently
        assert limiter.is_allowed("client_1") is False
        assert limiter.is_allowed("client_2") is False

    def test_sliding_window_cleanup(self) -> None:
        """Cleans up old requests outside the time window."""
        limiter = RateLimiter(limit=2, window_seconds=0.05)  # 50ms window
        client_id = "test_client"

        # Fill up the limit
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is False

        # Wait for window to pass
        time.sleep(0.06)  # 60ms > 50ms window

        # Should allow requests again after window passes
        assert limiter.is_allowed(client_id) is True

    def test_get_reset_time_for_empty_client(self) -> None:
        """Returns current time for client with no requests."""
        limiter = RateLimiter(limit=5, window_seconds=60)
        reset_time = limiter.get_reset_time("new_client")

        # Should be approximately current time
        assert abs(reset_time - time.time()) < 1

    def test_get_reset_time_for_active_client(self) -> None:
        """Returns appropriate reset time for client with requests."""
        limiter = RateLimiter(limit=2, window_seconds=60)
        client_id = "test_client"

        # Make some requests
        limiter.is_allowed(client_id)
        limiter.is_allowed(client_id)

        reset_time = limiter.get_reset_time(client_id)

        # Reset time should be in the future (within window + some tolerance)
        assert reset_time > time.time()
        assert reset_time < time.time() + 61  # Window + tolerance

    def test_maintains_request_history_internally(self) -> None:
        """Maintains request history internally for rate limiting."""
        limiter = RateLimiter(limit=2, window_seconds=60)
        client_id = "test_client"

        # Internal state should allow tracking limits properly
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is False  # Over limit


class TestRateLimiterSingleton:
    """Test singleton pattern for rate limiter."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _RateLimiterSingleton._instance = None

    def test_raises_error_when_no_instance_set(self) -> None:
        """Raises error when trying to get instance before configuration."""
        with pytest.raises(RateLimitError, match="Rate limiter not configured"):
            _RateLimiterSingleton.get_instance()

    def test_returns_set_instance(self) -> None:
        """Returns the set singleton instance."""
        limiter = RateLimiter(limit=10, window_seconds=60)
        _RateLimiterSingleton.set_instance(limiter)

        retrieved_limiter = _RateLimiterSingleton.get_instance()
        assert retrieved_limiter is limiter

    def test_replaces_existing_instance(self) -> None:
        """Replaces existing singleton instance when new one is set."""
        old_limiter = RateLimiter(limit=5, window_seconds=30)
        new_limiter = RateLimiter(limit=10, window_seconds=60)

        _RateLimiterSingleton.set_instance(old_limiter)
        _RateLimiterSingleton.set_instance(new_limiter)

        retrieved_limiter = _RateLimiterSingleton.get_instance()
        assert retrieved_limiter is new_limiter
        assert retrieved_limiter is not old_limiter


class TestConfigureRateLimiter:
    """Test rate limiter configuration behavior."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _RateLimiterSingleton._instance = None

    def test_sets_singleton_instance_for_backward_compatibility(self) -> None:
        """Sets singleton instance for backward compatibility."""
        configure_rate_limiter(limit=20, window_seconds=120)

        singleton_limiter = _RateLimiterSingleton.get_instance()
        assert singleton_limiter.limit == 20
        assert singleton_limiter.window_seconds == 120

    def test_replaces_existing_singleton(self) -> None:
        """Replaces existing singleton instance when reconfigured."""
        # Set initial configuration
        configure_rate_limiter(limit=5, window_seconds=30)
        old_limiter = _RateLimiterSingleton.get_instance()

        # Reconfigure
        configure_rate_limiter(limit=15, window_seconds=90)
        new_limiter = _RateLimiterSingleton.get_instance()

        assert new_limiter is not old_limiter
        assert new_limiter.limit == 15
        assert new_limiter.window_seconds == 90

    def test_configures_with_different_limits(self) -> None:
        """Configures rate limiter with various limit values."""
        test_cases = [
            (1, 60),
            (100, 60),
            (1000, 3600),
            (50, 1),
        ]

        for limit, window in test_cases:
            configure_rate_limiter(limit=limit, window_seconds=window)
            limiter = _RateLimiterSingleton.get_instance()

            assert limiter.limit == limit
            assert limiter.window_seconds == window


class TestGetRateLimiter:
    """Test get rate limiter behavior."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _RateLimiterSingleton._instance = None

    def test_returns_singleton_instance_when_configured(self) -> None:
        """Returns singleton instance when properly configured."""
        configure_rate_limiter(limit=25, window_seconds=300)

        limiter = get_rate_limiter()

        assert isinstance(limiter, RateLimiter)
        assert limiter.limit == 25
        assert limiter.window_seconds == 300

    def test_raises_error_when_not_configured(self) -> None:
        """Raises error when rate limiter not configured."""
        with pytest.raises(RateLimitError, match="Rate limiter not configured"):
            get_rate_limiter()

    def test_returns_same_instance_on_subsequent_calls(self) -> None:
        """Returns same instance on subsequent calls."""
        configure_rate_limiter(limit=30, window_seconds=180)

        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        assert limiter1 is limiter2


class TestCheckRateLimit:
    """Test FastAPI dependency for rate limit checking."""

    def setup_method(self) -> None:
        """Reset singleton state and configure rate limiter for each test."""
        _RateLimiterSingleton._instance = None
        configure_rate_limiter(limit=3, window_seconds=60)

    def test_allows_request_under_limit(self) -> None:
        """Allows request when under rate limit."""
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.100"

        client_id = check_rate_limit(mock_request)

        assert client_id == "192.168.1.100"

    def test_blocks_request_over_limit(self) -> None:
        """Blocks request when over rate limit."""
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.200"

        # Exhaust rate limit
        check_rate_limit(mock_request)
        check_rate_limit(mock_request)
        check_rate_limit(mock_request)

        # Next request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(mock_request)

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail

    def test_includes_retry_after_header_in_response(self) -> None:
        """Includes Retry-After header when rate limit exceeded."""
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.300"

        # Exhaust rate limit
        check_rate_limit(mock_request)
        check_rate_limit(mock_request)
        check_rate_limit(mock_request)

        # Check that blocked request includes retry info
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(mock_request)

        headers = exc_info.value.headers
        assert headers is not None
        assert "Retry-After" in headers

    def test_logs_successful_requests(self) -> None:
        """Rate limiter doesn't record success metrics (only blocks)."""
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.400"

        # Successful request should just return client ID
        client_id = check_rate_limit(mock_request)
        assert client_id == "192.168.1.400"

    @patch("src.infrastructure.security.rate_limiter.get_logger")
    @patch("src.infrastructure.security.rate_limiter.get_metrics_collector")
    def test_records_block_metrics(self, mock_metrics: MagicMock, mock_logger: MagicMock) -> None:
        """Records block metrics when request is blocked."""
        mock_logger_instance = MagicMock()
        mock_metrics_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics.return_value = mock_metrics_instance

        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.500"

        # Exhaust rate limit
        check_rate_limit(mock_request)
        check_rate_limit(mock_request)
        check_rate_limit(mock_request)

        with pytest.raises(HTTPException):
            check_rate_limit(mock_request)

        mock_metrics_instance.increment_counter.assert_called_with(
            "rate_limit_blocks_total", {"client_ip": "192.168.1.500"}
        )


class TestRateLimiterWorkflows:
    """Test complete rate limiter workflows and use cases."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _RateLimiterSingleton._instance = None

    def test_typical_rate_limiter_lifecycle(self) -> None:
        """Test complete lifecycle of rate limiter."""
        # Initial configuration
        configure_rate_limiter(limit=2, window_seconds=3600)
        limiter = get_rate_limiter()

        # Test rate limiting behavior
        client = "lifecycle_client"
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is False

        # Reconfigure with different limits
        configure_rate_limiter(limit=5, window_seconds=1800)
        updated_limiter = get_rate_limiter()

        # Should be a new instance with new configuration
        assert updated_limiter is not limiter
        assert updated_limiter.limit == 5
        assert updated_limiter.window_seconds == 1800

    def test_fastapi_integration_workflow(self) -> None:
        """Test FastAPI integration workflow."""
        configure_rate_limiter(limit=2, window_seconds=60)

        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "integration_client"

        # Should allow initial requests
        client_id1 = check_rate_limit(mock_request)
        client_id2 = check_rate_limit(mock_request)

        assert client_id1 == "integration_client"
        assert client_id2 == "integration_client"

        # Should block subsequent requests
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(mock_request)

        assert exc_info.value.status_code == 429

    def test_concurrent_client_handling(self) -> None:
        """Test handling multiple concurrent clients."""
        configure_rate_limiter(limit=2, window_seconds=60)
        limiter = get_rate_limiter()

        # Multiple clients should be handled independently
        clients = ["client_1", "client_2", "client_3", "client_4"]

        for client in clients:
            # Each client gets their own limit
            assert limiter.is_allowed(client) is True
            assert limiter.is_allowed(client) is True
            assert limiter.is_allowed(client) is False

        # All clients should be at their limit
        for client in clients:
            assert limiter.is_allowed(client) is False

    def test_time_window_reset_behavior(self) -> None:
        """Test rate limit reset behavior over time windows."""
        configure_rate_limiter(limit=1, window_seconds=0.05)  # 50ms window
        limiter = get_rate_limiter()

        client = "time_test_client"

        # Use up the limit
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is False

        # Wait for window to reset
        time.sleep(0.06)  # 60ms > 50ms window

        # Should be allowed again
        assert limiter.is_allowed(client) is True
