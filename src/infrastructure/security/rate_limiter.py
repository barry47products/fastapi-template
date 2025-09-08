"""Rate limiting system for API protection."""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import ApplicationError


class RateLimitError(ApplicationError):
    """Exception raised when rate limit configuration or validation fails."""

    error_code: str = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: str, retry_after: int = 0) -> None:
        """Initialize rate limit error with message and retry time."""
        super().__init__(message)
        self.retry_after = retry_after


class RateLimiter:
    """Sliding window rate limiter for request throttling."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        """Initialize rate limiter with request limit and time window."""
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for the given client."""
        now = time.time()
        client_requests = self._requests[client_id]

        # Clean up old requests outside the window
        self._cleanup_old_requests(client_requests, now)

        # Check if under limit
        if len(client_requests) < self.limit:
            client_requests.append(now)
            return True

        return False

    def get_reset_time(self, client_id: str) -> float:
        """Get the time when rate limit will reset for client."""
        client_requests = self._requests[client_id]
        if not client_requests:
            return time.time()

        # Reset time is when the oldest request expires
        oldest_request = client_requests[0]
        return oldest_request + self.window_seconds

    def _cleanup_old_requests(self, client_requests: deque[float], now: float) -> None:
        """Remove requests older than the current window."""
        cutoff_time = now - self.window_seconds
        while client_requests and client_requests[0] < cutoff_time:
            client_requests.popleft()


class _RateLimiterSingleton:
    """Singleton for managing rate limiter configuration."""

    _instance: RateLimiter | None = None

    @classmethod
    def get_instance(cls) -> RateLimiter:
        """Get the singleton rate limiter instance."""
        if cls._instance is None:
            raise RateLimitError("Rate limiter not configured")
        return cls._instance

    @classmethod
    def set_instance(cls, limiter: RateLimiter) -> None:
        """Set the singleton rate limiter instance."""
        cls._instance = limiter


def configure_rate_limiter(limit: int, window_seconds: int) -> None:
    """Configure the global rate limiter instance.

    This function is kept for backward compatibility during initialization.
    With dependency injection, configuration is handled via get_rate_limiter().

    Args:
        limit: Maximum number of requests allowed
        window_seconds: Time window in seconds for rate limiting
    """
    # For backward compatibility, set the singleton instance
    limiter = RateLimiter(limit=limit, window_seconds=window_seconds)
    _RateLimiterSingleton.set_instance(limiter)


def get_rate_limiter() -> RateLimiter:
    """Get the configured rate limiter instance via singleton fallback.

    Returns:
        RateLimiter instance

    Raises:
        RateLimitError: If rate limiter not configured
    """
    # Fallback to singleton for backward compatibility during transition
    return _RateLimiterSingleton.get_instance()


def check_rate_limit(request: Request) -> str:
    """FastAPI dependency for rate limiting based on client IP."""
    client_ip = request.client.host if request.client else "unknown"
    limiter = get_rate_limiter()
    logger = get_logger(__name__)
    metrics = get_metrics_collector()

    if limiter.is_allowed(client_ip):
        return client_ip

    # Rate limit exceeded
    reset_time = limiter.get_reset_time(client_ip)
    retry_after = int(reset_time - time.time())

    logger.warning("Rate limit exceeded", client_ip=client_ip)
    metrics.increment_counter("rate_limit_blocks_total", {"client_ip": client_ip})

    raise HTTPException(
        status_code=429,
        detail="Rate limit exceeded",
        headers={"Retry-After": str(retry_after)},
    )
