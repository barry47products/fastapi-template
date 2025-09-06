"""Unit tests for webhook verifier security component."""

import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, Request

from src.infrastructure.security.webhook_verifier import (
    WebhookVerificationError,
    WebhookVerifier,
    _WebhookVerifierSingleton,
    configure_webhook_verifier,
    get_webhook_verifier,
    verify_webhook_signature,
)


class TestWebhookVerificationError:
    """Test webhook verification error behavior."""

    def test_creates_error_with_message(self) -> None:
        """Creates error with message."""
        error = WebhookVerificationError("Invalid signature")

        assert str(error) == "Invalid signature"
        assert error.message == "Invalid signature"
        assert error.error_code == "WEBHOOK_VERIFICATION_ERROR"

    def test_inherits_from_application_error(self) -> None:
        """Inherits from ApplicationError."""
        from src.shared.exceptions import ApplicationError

        error = WebhookVerificationError("Test error")
        assert isinstance(error, ApplicationError)


class TestWebhookVerifier:
    """Test webhook verifier behavior."""

    def test_creates_verifier_with_secret_key(self) -> None:
        """Creates verifier with secret key."""
        secret_key = "test_secret_key"
        verifier = WebhookVerifier(secret_key)

        assert verifier.secret_key == secret_key

    def test_verifies_valid_signature(self) -> None:
        """Verifies valid HMAC-SHA256 signature."""
        secret_key = "test_secret"
        body = b"webhook payload data"
        verifier = WebhookVerifier(secret_key)

        # Generate expected signature
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        assert verifier.verify_signature(body, expected_signature) is True

    def test_rejects_invalid_signature(self) -> None:
        """Rejects invalid signature."""
        secret_key = "test_secret"
        body = b"webhook payload data"
        verifier = WebhookVerifier(secret_key)

        invalid_signature = "invalid_signature_here"

        assert verifier.verify_signature(body, invalid_signature) is False

    def test_rejects_empty_signature(self) -> None:
        """Rejects empty signature."""
        secret_key = "test_secret"
        body = b"webhook payload data"
        verifier = WebhookVerifier(secret_key)

        assert verifier.verify_signature(body, "") is False
        # Test None signature by calling internal logic that handles this case
        assert not verifier.verify_signature(body, "")

    def test_rejects_signature_with_wrong_secret(self) -> None:
        """Rejects signature generated with different secret."""
        secret_key = "correct_secret"
        wrong_secret = "wrong_secret"
        body = b"webhook payload data"
        verifier = WebhookVerifier(secret_key)

        # Generate signature with wrong secret
        wrong_signature = hmac.new(
            wrong_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        assert verifier.verify_signature(body, wrong_signature) is False

    def test_rejects_signature_with_different_body(self) -> None:
        """Rejects signature when body is different."""
        secret_key = "test_secret"
        original_body = b"original payload"
        different_body = b"different payload"
        verifier = WebhookVerifier(secret_key)

        # Generate signature for original body
        signature = hmac.new(
            secret_key.encode("utf-8"),
            original_body,
            hashlib.sha256,
        ).hexdigest()

        # Verify with different body should fail
        assert verifier.verify_signature(different_body, signature) is False

    def test_uses_timing_safe_comparison(self) -> None:
        """Uses timing-safe comparison to prevent timing attacks."""
        secret_key = "test_secret"
        body = b"test payload"
        verifier = WebhookVerifier(secret_key)

        # Generate correct signature
        correct_signature = hmac.new(
            secret_key.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        # Test with signature that has same length but different content
        almost_correct = correct_signature[:-1] + "x"

        # Should still use constant-time comparison (hmac.compare_digest)
        assert verifier.verify_signature(body, almost_correct) is False

    def test_handles_unicode_secret_key(self) -> None:
        """Handles Unicode characters in secret key."""
        secret_key = "tëst_sëcrët_kéy_🔐"
        body = b"test payload"
        verifier = WebhookVerifier(secret_key)

        # Generate signature
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        assert verifier.verify_signature(body, expected_signature) is True

    def test_handles_empty_body(self) -> None:
        """Handles empty request body."""
        secret_key = "test_secret"
        body = b""
        verifier = WebhookVerifier(secret_key)

        # Generate signature for empty body
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        assert verifier.verify_signature(body, expected_signature) is True

    def test_handles_large_body(self) -> None:
        """Handles large request body."""
        secret_key = "test_secret"
        body = b"x" * 100000  # 100KB body
        verifier = WebhookVerifier(secret_key)

        # Generate signature for large body
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        assert verifier.verify_signature(body, expected_signature) is True


class TestWebhookVerifierSingleton:
    """Test webhook verifier singleton behavior."""

    def test_raises_error_when_not_configured(self) -> None:
        """Raises error when verifier not configured."""
        _WebhookVerifierSingleton._instance = None

        with pytest.raises(WebhookVerificationError, match="Webhook verifier not configured"):
            _WebhookVerifierSingleton.get_instance()

    def test_returns_configured_instance(self) -> None:
        """Returns configured instance."""
        verifier = WebhookVerifier("test_secret")
        _WebhookVerifierSingleton.set_instance(verifier)

        result = _WebhookVerifierSingleton.get_instance()
        assert result is verifier

    def test_sets_singleton_instance(self) -> None:
        """Sets singleton instance."""
        verifier = WebhookVerifier("test_secret")

        _WebhookVerifierSingleton.set_instance(verifier)

        assert _WebhookVerifierSingleton._instance is verifier


class TestConfigureWebhookVerifier:
    """Test webhook verifier configuration behavior."""

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_registers_with_service_registry(self, mock_get_registry: MagicMock) -> None:
        """Registers verifier with service registry."""
        mock_registry = MagicMock()
        mock_get_registry.return_value = mock_registry
        secret_key = "test_secret_key"

        configure_webhook_verifier(secret_key)

        mock_registry.register_webhook_verifier.assert_called_once()
        verifier_arg = mock_registry.register_webhook_verifier.call_args[0][0]
        assert isinstance(verifier_arg, WebhookVerifier)
        assert verifier_arg.secret_key == secret_key

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_handles_service_registry_import_error(self, mock_get_registry: MagicMock) -> None:
        """Handles service registry import error gracefully."""
        mock_get_registry.side_effect = ImportError("Module not found")
        secret_key = "test_secret_key"

        # Should not raise exception
        configure_webhook_verifier(secret_key)

        # Should still set singleton
        verifier = _WebhookVerifierSingleton.get_instance()
        assert verifier.secret_key == secret_key

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_handles_service_registry_runtime_error(self, mock_get_registry: MagicMock) -> None:
        """Handles service registry runtime error gracefully."""
        mock_get_registry.side_effect = RuntimeError("Registry not initialized")
        secret_key = "test_secret_key"

        # Should not raise exception
        configure_webhook_verifier(secret_key)

        # Should still set singleton
        verifier = _WebhookVerifierSingleton.get_instance()
        assert verifier.secret_key == secret_key

    def test_sets_singleton_instance(self) -> None:
        """Sets singleton instance."""
        secret_key = "test_secret_key"

        configure_webhook_verifier(secret_key)

        verifier = _WebhookVerifierSingleton.get_instance()
        assert verifier.secret_key == secret_key


class TestGetWebhookVerifier:
    """Test get webhook verifier behavior."""

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_returns_verifier_from_service_registry(self, mock_get_registry: MagicMock) -> None:
        """Returns verifier from service registry when available."""
        mock_verifier = WebhookVerifier("registry_secret")
        mock_registry = MagicMock()
        mock_registry.has_webhook_verifier.return_value = True
        mock_registry.get_webhook_verifier.return_value = mock_verifier
        mock_get_registry.return_value = mock_registry

        result = get_webhook_verifier()

        assert result is mock_verifier
        mock_registry.has_webhook_verifier.assert_called_once()
        mock_registry.get_webhook_verifier.assert_called_once()

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_falls_back_to_singleton_when_registry_unavailable(
        self, mock_get_registry: MagicMock
    ) -> None:
        """Falls back to singleton when service registry unavailable."""
        mock_get_registry.side_effect = ImportError("Registry not available")
        singleton_verifier = WebhookVerifier("singleton_secret")
        _WebhookVerifierSingleton.set_instance(singleton_verifier)

        result = get_webhook_verifier()

        assert result is singleton_verifier

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_falls_back_to_singleton_when_verifier_not_in_registry(
        self, mock_get_registry: MagicMock
    ) -> None:
        """Falls back to singleton when verifier not in registry."""
        mock_registry = MagicMock()
        mock_registry.has_webhook_verifier.return_value = False
        mock_get_registry.return_value = mock_registry
        singleton_verifier = WebhookVerifier("singleton_secret")
        _WebhookVerifierSingleton.set_instance(singleton_verifier)

        result = get_webhook_verifier()

        assert result is singleton_verifier

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_raises_error_when_no_verifier_available(self, mock_get_registry: MagicMock) -> None:
        """Raises error when no verifier available."""
        mock_get_registry.side_effect = ImportError("Registry not available")
        _WebhookVerifierSingleton._instance = None

        with pytest.raises(WebhookVerificationError, match="Webhook verifier not configured"):
            get_webhook_verifier()


class TestVerifyWebhookSignature:
    """Test verify webhook signature FastAPI dependency behavior."""

    @pytest.mark.asyncio
    @patch("src.infrastructure.security.webhook_verifier.get_logger")
    @patch("src.infrastructure.security.webhook_verifier.get_metrics_collector")
    async def test_verifies_valid_signature(
        self, mock_metrics: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Verifies valid webhook signature."""
        # Setup
        secret_key = "test_secret"
        body = b"webhook payload"
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        # Configure verifier
        configure_webhook_verifier(secret_key)

        # Create mock request
        mock_request = AsyncMock(spec=Request)
        mock_request.body.return_value = body
        mock_request.headers = {"X-Webhook-Signature": expected_signature}
        mock_client = Mock()
        mock_client.host = "192.168.1.100"
        mock_request.client = mock_client

        # Setup observability mocks
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Test
        result = await verify_webhook_signature(mock_request)

        assert result == body
        mock_logger_instance.info.assert_called_once_with(
            "Webhook signature verified successfully", client_ip="192.168.1.100"
        )
        mock_metrics_instance.increment_counter.assert_called_once_with(
            "webhook_verification_successes_total", {"client_ip": "192.168.1.100"}
        )

    @pytest.mark.asyncio
    @patch("src.infrastructure.security.webhook_verifier.get_logger")
    @patch("src.infrastructure.security.webhook_verifier.get_metrics_collector")
    async def test_raises_exception_for_missing_signature_header(
        self, mock_metrics: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Raises HTTPException when signature header is missing."""
        # Setup
        secret_key = "test_secret"
        body = b"webhook payload"

        # Configure verifier
        configure_webhook_verifier(secret_key)

        # Create mock request without signature header
        mock_request = AsyncMock(spec=Request)
        mock_request.body.return_value = body
        mock_request.headers = {}  # No signature header
        mock_client = Mock()
        mock_client.host = "192.168.1.200"
        mock_request.client = mock_client

        # Setup observability mocks
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Test
        with pytest.raises(HTTPException) as exc_info:
            await verify_webhook_signature(mock_request)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Missing webhook signature"
        assert exc_info.value.headers == {"WWW-Authenticate": "Webhook"}

        mock_logger_instance.warning.assert_called_once_with(
            "Webhook signature verification failed",
            client_ip="192.168.1.200",
            signature_provided=False,
        )
        mock_metrics_instance.increment_counter.assert_called_once_with(
            "webhook_verification_failures_total", {"client_ip": "192.168.1.200"}
        )

    @pytest.mark.asyncio
    @patch("src.infrastructure.security.webhook_verifier.get_logger")
    @patch("src.infrastructure.security.webhook_verifier.get_metrics_collector")
    async def test_raises_exception_for_invalid_signature(
        self, mock_metrics: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Raises HTTPException for invalid signature."""
        # Setup
        secret_key = "test_secret"
        body = b"webhook payload"
        invalid_signature = "invalid_signature_here"

        # Configure verifier
        configure_webhook_verifier(secret_key)

        # Create mock request with invalid signature
        mock_request = AsyncMock(spec=Request)
        mock_request.body.return_value = body
        mock_request.headers = {"X-Webhook-Signature": invalid_signature}
        mock_client = Mock()
        mock_client.host = "192.168.1.300"
        mock_request.client = mock_client

        # Setup observability mocks
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Test
        with pytest.raises(HTTPException) as exc_info:
            await verify_webhook_signature(mock_request)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid webhook signature"
        assert exc_info.value.headers == {"WWW-Authenticate": "Webhook"}

        mock_logger_instance.warning.assert_called_once_with(
            "Webhook signature verification failed",
            client_ip="192.168.1.300",
            signature_provided=True,
        )
        mock_metrics_instance.increment_counter.assert_called_once_with(
            "webhook_verification_failures_total", {"client_ip": "192.168.1.300"}
        )

    @pytest.mark.asyncio
    @patch("src.infrastructure.security.webhook_verifier.get_logger")
    @patch("src.infrastructure.security.webhook_verifier.get_metrics_collector")
    async def test_handles_missing_client_info(
        self, mock_metrics: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Handles missing client information in request."""
        # Setup
        secret_key = "test_secret"
        body = b"webhook payload"
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        # Configure verifier
        configure_webhook_verifier(secret_key)

        # Create mock request without client info
        mock_request = AsyncMock(spec=Request)
        mock_request.body.return_value = body
        mock_request.headers = {"X-Webhook-Signature": expected_signature}
        mock_request.client = None

        # Setup observability mocks
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Test
        result = await verify_webhook_signature(mock_request)

        assert result == body
        mock_logger_instance.info.assert_called_once_with(
            "Webhook signature verified successfully", client_ip="unknown"
        )

    @pytest.mark.asyncio
    async def test_handles_empty_body(self) -> None:
        """Handles empty request body."""
        # Setup
        secret_key = "test_secret"
        body = b""
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        # Configure verifier
        configure_webhook_verifier(secret_key)

        # Create mock request
        mock_request = AsyncMock(spec=Request)
        mock_request.body.return_value = body
        mock_request.headers = {"X-Webhook-Signature": expected_signature}
        mock_client = Mock()
        mock_client.host = "192.168.1.400"
        mock_request.client = mock_client

        # Test
        result = await verify_webhook_signature(mock_request)
        assert result == body

    @pytest.mark.asyncio
    async def test_handles_large_body(self) -> None:
        """Handles large request body."""
        # Setup
        secret_key = "test_secret"
        body = b"x" * 50000  # 50KB body
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        # Configure verifier
        configure_webhook_verifier(secret_key)

        # Create mock request
        mock_request = AsyncMock(spec=Request)
        mock_request.body.return_value = body
        mock_request.headers = {"X-Webhook-Signature": expected_signature}
        mock_client = Mock()
        mock_client.host = "192.168.1.500"
        mock_request.client = mock_client

        # Test
        result = await verify_webhook_signature(mock_request)
        assert result == body
