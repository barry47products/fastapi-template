"""Webhook signature verification system for GREEN-API security."""

import hashlib
import hmac

from fastapi import HTTPException, Request

from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import NeighbourApprovedError


class WebhookVerificationError(NeighbourApprovedError):
    """Exception raised when webhook verification fails or configuration is invalid."""

    error_code: str = "WEBHOOK_VERIFICATION_ERROR"


class WebhookVerifier:
    """HMAC-SHA256 webhook signature verifier for GREEN-API webhooks."""

    def __init__(self, secret_key: str) -> None:
        """Initialize webhook verifier with secret key.

        Args:
            secret_key: Secret key for HMAC signature generation
        """
        self.secret_key = secret_key

    def verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify webhook1 signature using HMAC-SHA256.

        Args:
            body: Raw request body as bytes
            signature: Provided signature to verify

        Returns:
            True if signature is valid, False otherwise
        """
        if not signature:
            return False

        # Calculate expected signature
        expected_signature = hmac.new(
            self.secret_key.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        # Use timing-safe comparison to prevent timing attacks
        return hmac.compare_digest(signature, expected_signature)


class _WebhookVerifierSingleton:
    """Singleton for webhook verifier configuration."""

    _instance: WebhookVerifier | None = None

    @classmethod
    def set_instance(cls, verifier: WebhookVerifier) -> None:
        """Set the singleton webhook verifier instance."""
        cls._instance = verifier

    @classmethod
    def get_instance(cls) -> WebhookVerifier:
        """Get the singleton webhook verifier instance.

        Returns:
            Webhook verifier instance

        Raises:
            WebhookVerificationError: If verifier not configured
        """
        if cls._instance is None:
            raise WebhookVerificationError("Webhook verifier not configured")
        return cls._instance


def configure_webhook_verifier(secret_key: str) -> None:
    """Configure the webhook verifier with secret key.

    Args:
        secret_key: Secret key for webhook signature verification
    """
    verifier = WebhookVerifier(secret_key=secret_key)

    # Register with service registry (primary method)
    try:
        from src.infrastructure.service_registry import get_service_registry

        service_registry = get_service_registry()
        service_registry.register_webhook_verifier(verifier)
    except Exception:
        # Service registry might not be initialized yet
        pass

    # Also set in singleton for backward compatibility during transition
    _WebhookVerifierSingleton.set_instance(verifier)


def get_webhook_verifier() -> WebhookVerifier:
    """Get the configured webhook verifier instance via service registry.

    Returns:
        Configured webhook verifier

    Raises:
        WebhookVerificationError: If verifier not configured
    """
    # Try to get from service registry first (new DI pattern)
    try:
        from src.infrastructure.service_registry import get_service_registry

        service_registry = get_service_registry()
        if service_registry.has_webhook_verifier():
            return service_registry.get_webhook_verifier()
    except Exception:
        # Fall back to singleton pattern for backward compatibility
        pass

    # Fallback to singleton for backward compatibility during transition
    return _WebhookVerifierSingleton.get_instance()


async def verify_webhook_signature(request: Request) -> bytes:
    """FastAPI dependency function for webhook signature verification.

    Args:
        request: FastAPI request object

    Returns:
        Original body if signature is valid

    Raises:
        HTTPException: If signature verification fails
    """
    logger = get_logger(__name__)
    metrics_collector = get_metrics_collector()

    # Read the request body
    body = await request.body()

    # Get client IP for logging
    client_ip = request.client.host if request.client else "unknown"

    # Check for signature header
    signature = request.headers.get("X-Webhook-Signature")
    if not signature:
        logger.warning(
            "Webhook signature verification failed",
            client_ip=client_ip,
            signature_provided=False,
        )
        metrics_collector.increment_counter(
            "webhook_verification_failures_total",
            {"client_ip": client_ip},
        )
        raise HTTPException(
            status_code=401,
            detail="Missing webhook signature",
            headers={"WWW-Authenticate": "Webhook"},
        )

    # Verify signature
    verifier = get_webhook_verifier()
    if not verifier.verify_signature(body, signature):
        logger.warning(
            "Webhook signature verification failed",
            client_ip=client_ip,
            signature_provided=True,
        )
        metrics_collector.increment_counter(
            "webhook_verification_failures_total",
            {"client_ip": client_ip},
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
            headers={"WWW-Authenticate": "Webhook"},
        )

    # Log successful verification
    logger.info("Webhook signature verified successfully", client_ip=client_ip)
    metrics_collector.increment_counter(
        "webhook_verification_successes_total",
        {"client_ip": client_ip},
    )

    return body
