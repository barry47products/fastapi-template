"""Unit tests for webhook verification security component."""

from __future__ import annotations

import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

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
        """Creates webhook verifier with secret key."""
        secret_key = "test_secret_key_123"
        verifier = WebhookVerifier(secret_key)

        # Secret key should be stored (but not directly accessible for security)
        assert isinstance(verifier, WebhookVerifier)

    def test_verifies_valid_signature(self) -> None:
        """Verifies valid HMAC-SHA256 signature."""
        secret_key = "test_secret"
        payload = b"test payload data"
        verifier = WebhookVerifier(secret_key)

        # Create valid signature
        expected_signature = hmac.new(
            secret_key.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

        assert verifier.verify_signature(payload, expected_signature) is True

    def test_rejects_invalid_signature(self) -> None:
        """Rejects invalid HMAC-SHA256 signature."""
        secret_key = "test_secret"
        payload = b"test payload data"
        verifier = WebhookVerifier(secret_key)

        invalid_signature = "invalid_signature_value"

        assert verifier.verify_signature(payload, invalid_signature) is False

    def test_rejects_signature_with_wrong_secret(self) -> None:
        """Rejects signature created with different secret key."""
        correct_secret = "correct_secret"
        wrong_secret = "wrong_secret"
        payload = b"test payload data"

        verifier = WebhookVerifier(correct_secret)

        # Create signature with wrong secret
        wrong_signature = hmac.new(
            wrong_secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

        assert verifier.verify_signature(payload, wrong_signature) is False

    def test_handles_empty_payload(self) -> None:
        """Handles empty payload correctly."""
        secret_key = "test_secret"
        payload = b""
        verifier = WebhookVerifier(secret_key)

        # Create valid signature for empty payload
        expected_signature = hmac.new(
            secret_key.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

        assert verifier.verify_signature(payload, expected_signature) is True

    def test_handles_empty_signature(self) -> None:
        """Handles empty signature (should reject)."""
        secret_key = "test_secret"
        payload = b"test data"
        verifier = WebhookVerifier(secret_key)

        # Test with empty string instead of None (type-safe)
        assert verifier.verify_signature(payload, "") is False

    def test_signature_verification_timing_safe(self) -> None:
        """Signature verification should be timing-safe."""
        secret_key = "test_secret"
        payload = b"sensitive data"
        verifier = WebhookVerifier(secret_key)

        # Generate correct signature
        correct_signature = hmac.new(
            secret_key.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

        # Test multiple invalid signatures of same length
        invalid_signatures = [
            "a" * len(correct_signature),
            "1" * len(correct_signature),
            "z" * len(correct_signature),
        ]

        # All should be rejected
        for invalid_sig in invalid_signatures:
            assert verifier.verify_signature(payload, invalid_sig) is False

        # Correct signature should still work
        assert verifier.verify_signature(payload, correct_signature) is True


class TestWebhookVerifierSingleton:
    """Test singleton pattern for webhook verifier."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _WebhookVerifierSingleton._instance = None

    def test_raises_error_when_no_instance_set(self) -> None:
        """Raises error when trying to get instance before configuration."""
        with pytest.raises(WebhookVerificationError, match="Webhook verifier not configured"):
            _WebhookVerifierSingleton.get_instance()

    def test_returns_set_instance(self) -> None:
        """Returns the set singleton instance."""
        verifier = WebhookVerifier("test_secret")
        _WebhookVerifierSingleton.set_instance(verifier)

        retrieved_verifier = _WebhookVerifierSingleton.get_instance()
        assert retrieved_verifier is verifier

    def test_replaces_existing_instance(self) -> None:
        """Replaces existing singleton instance when new one is set."""
        old_verifier = WebhookVerifier("old_secret")
        new_verifier = WebhookVerifier("new_secret")

        _WebhookVerifierSingleton.set_instance(old_verifier)
        _WebhookVerifierSingleton.set_instance(new_verifier)

        retrieved_verifier = _WebhookVerifierSingleton.get_instance()
        assert retrieved_verifier is new_verifier
        assert retrieved_verifier is not old_verifier


class TestConfigureWebhookVerifier:
    """Test webhook verifier configuration behavior."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _WebhookVerifierSingleton._instance = None

    def test_sets_singleton_instance_for_backward_compatibility(self) -> None:
        """Sets singleton instance for backward compatibility."""
        secret_key = "singleton_secret_123"

        configure_webhook_verifier(secret_key)

        singleton_verifier = _WebhookVerifierSingleton.get_instance()
        assert isinstance(singleton_verifier, WebhookVerifier)

        # Test that it works with a signature
        payload = b"test data"
        expected_signature = hmac.new(
            secret_key.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        assert singleton_verifier.verify_signature(payload, expected_signature) is True

    def test_replaces_existing_singleton(self) -> None:
        """Replaces existing singleton instance when reconfigured."""
        # Set initial configuration
        configure_webhook_verifier("old_secret")
        old_verifier = _WebhookVerifierSingleton.get_instance()

        # Reconfigure with new secret
        configure_webhook_verifier("new_secret")
        new_verifier = _WebhookVerifierSingleton.get_instance()

        assert new_verifier is not old_verifier

        # Test that old secret doesn't work with new verifier
        payload = b"test data"
        old_signature = hmac.new(b"old_secret", payload, hashlib.sha256).hexdigest()
        new_signature = hmac.new(b"new_secret", payload, hashlib.sha256).hexdigest()

        assert new_verifier.verify_signature(payload, old_signature) is False
        assert new_verifier.verify_signature(payload, new_signature) is True

    def test_configures_with_different_secret_keys(self) -> None:
        """Configures webhook verifier with various secret keys."""
        test_secrets = [
            "simple_secret",
            "complex-secret.with@special#chars!",
            "very_long_secret_key_" + "x" * 100,
            "123456789",
        ]

        for secret in test_secrets:
            configure_webhook_verifier(secret)
            verifier = _WebhookVerifierSingleton.get_instance()

            # Test that it works with the configured secret
            payload = b"test payload"
            signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
            assert verifier.verify_signature(payload, signature) is True


class TestGetWebhookVerifier:
    """Test get webhook verifier behavior."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _WebhookVerifierSingleton._instance = None

    def test_returns_singleton_instance_when_configured(self) -> None:
        """Returns singleton instance when properly configured."""
        configure_webhook_verifier("test_secret_key")

        verifier = get_webhook_verifier()

        assert isinstance(verifier, WebhookVerifier)

    def test_raises_error_when_not_configured(self) -> None:
        """Raises error when webhook verifier not configured."""
        with pytest.raises(WebhookVerificationError, match="Webhook verifier not configured"):
            get_webhook_verifier()

    def test_returns_same_instance_on_subsequent_calls(self) -> None:
        """Returns same instance on subsequent calls."""
        configure_webhook_verifier("consistent_secret")

        verifier1 = get_webhook_verifier()
        verifier2 = get_webhook_verifier()

        assert verifier1 is verifier2


class TestVerifyWebhookSignature:
    """Test FastAPI dependency for webhook signature verification."""

    def setup_method(self) -> None:
        """Reset singleton state and configure verifier for each test."""
        _WebhookVerifierSingleton._instance = None
        configure_webhook_verifier("webhook_test_secret")

    @pytest.mark.asyncio
    async def test_verifies_valid_webhook_signature(self) -> None:
        """Verifies valid webhook signature successfully."""
        payload = b"webhook payload data"
        signature = hmac.new(b"webhook_test_secret", payload, hashlib.sha256).hexdigest()

        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"X-Webhook-Signature": signature}
        mock_request.body.return_value = payload

        verified_payload = await verify_webhook_signature(mock_request)

        assert verified_payload == payload

    @pytest.mark.asyncio
    async def test_rejects_invalid_webhook_signature(self) -> None:
        """Rejects invalid webhook signature with HTTP 401."""
        payload = b"webhook payload data"
        invalid_signature = "invalid_signature_value"

        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"X-Webhook-Signature": invalid_signature}
        mock_request.body.return_value = payload

        with pytest.raises(HTTPException) as exc_info:
            await verify_webhook_signature(mock_request)

        assert exc_info.value.status_code == 401
        assert "Invalid webhook signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_rejects_missing_signature_header(self) -> None:
        """Rejects request with missing signature header."""
        payload = b"webhook payload data"

        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {}  # No signature header
        mock_request.body.return_value = payload

        with pytest.raises(HTTPException) as exc_info:
            await verify_webhook_signature(mock_request)

        assert exc_info.value.status_code == 401
        assert "Missing webhook signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_handles_different_signature_formats(self) -> None:
        """Handles different signature header formats."""
        payload = b"webhook payload data"
        signature = hmac.new(b"webhook_test_secret", payload, hashlib.sha256).hexdigest()

        # Test different header formats
        test_cases = [
            f"sha256={signature}",  # Standard format
            signature,  # Raw signature
        ]

        for sig_header in test_cases:
            mock_request = AsyncMock(spec=Request)
            mock_request.headers = {"X-Webhook-Signature": sig_header}
            mock_request.body.return_value = payload
            mock_request.client.host = "192.168.1.100"

            verified_payload = await verify_webhook_signature(mock_request)
            assert verified_payload == payload

    @pytest.mark.asyncio
    @patch("src.infrastructure.security.webhook_verifier.get_logger")
    @patch("src.infrastructure.security.webhook_verifier.get_metrics_collector")
    async def test_records_success_metrics(
        self, mock_metrics: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Records success metrics on valid signature."""
        mock_logger_instance = MagicMock()
        mock_metrics_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics.return_value = mock_metrics_instance

        payload = b"success test payload"
        signature = hmac.new(b"webhook_test_secret", payload, hashlib.sha256).hexdigest()

        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"X-Webhook-Signature": signature}
        mock_request.body.return_value = payload
        mock_request.client.host = "192.168.1.100"

        await verify_webhook_signature(mock_request)

        mock_metrics_instance.increment_counter.assert_called_with(
            "webhook_verification_successes_total", {"client_ip": "192.168.1.100"}
        )

    @pytest.mark.asyncio
    @patch("src.infrastructure.security.webhook_verifier.get_logger")
    @patch("src.infrastructure.security.webhook_verifier.get_metrics_collector")
    async def test_records_failure_metrics(
        self, mock_metrics: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Records failure metrics on invalid signature."""
        mock_logger_instance = MagicMock()
        mock_metrics_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics.return_value = mock_metrics_instance

        payload = b"failure test payload"
        invalid_signature = "invalid_signature"

        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"X-Webhook-Signature": invalid_signature}
        mock_request.body.return_value = payload
        mock_request.client.host = "192.168.1.200"

        with pytest.raises(HTTPException):
            await verify_webhook_signature(mock_request)

        mock_metrics_instance.increment_counter.assert_called_with(
            "webhook_verification_failures_total", {"client_ip": "192.168.1.200"}
        )


class TestWebhookVerifierWorkflows:
    """Test complete webhook verifier workflows and use cases."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _WebhookVerifierSingleton._instance = None

    def test_typical_webhook_verification_lifecycle(self) -> None:
        """Test complete lifecycle of webhook verification."""
        # Initial configuration
        configure_webhook_verifier("initial_secret")
        verifier = get_webhook_verifier()

        # Test verification works
        payload = b"test webhook payload"
        signature = hmac.new(b"initial_secret", payload, hashlib.sha256).hexdigest()
        assert verifier.verify_signature(payload, signature) is True

        # Reconfigure with new secret (e.g., secret rotation)
        configure_webhook_verifier("rotated_secret")
        updated_verifier = get_webhook_verifier()

        # Old signature should no longer work
        assert updated_verifier.verify_signature(payload, signature) is False

        # New signature should work
        new_signature = hmac.new(b"rotated_secret", payload, hashlib.sha256).hexdigest()
        assert updated_verifier.verify_signature(payload, new_signature) is True

    @pytest.mark.asyncio
    async def test_fastapi_integration_workflow(self) -> None:
        """Test FastAPI integration workflow."""
        configure_webhook_verifier("integration_secret")

        # Simulate valid webhook request
        payload = b'{"event": "webhook_test", "data": {"id": 123}}'
        signature = hmac.new(b"integration_secret", payload, hashlib.sha256).hexdigest()

        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"X-Webhook-Signature": signature}
        mock_request.body.return_value = payload

        # Should successfully verify and return payload
        verified_payload = await verify_webhook_signature(mock_request)
        assert verified_payload == payload

        # Simulate invalid webhook request
        mock_request.headers = {"X-Signature-256": "sha256=invalid_signature"}

        with pytest.raises(HTTPException) as exc_info:
            await verify_webhook_signature(mock_request)

        assert exc_info.value.status_code == 401

    def test_security_edge_cases(self) -> None:
        """Test security edge cases in webhook verification."""
        secret = "security_test_secret"
        configure_webhook_verifier(secret)
        verifier = get_webhook_verifier()

        payload = b"sensitive webhook data"
        correct_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        # Test various attack scenarios
        attack_cases = [
            "",  # Empty signature
            "not_a_valid_signature",  # Invalid format
            correct_signature[:-2] + "XX",  # Modified signature
            correct_signature.upper(),  # Case changed
            "sha256=" + correct_signature,  # Wrong prefix format in verification
        ]

        for attack_sig in attack_cases:
            assert verifier.verify_signature(payload, attack_sig) is False

        # Correct signature should still work
        assert verifier.verify_signature(payload, correct_signature) is True

    def test_different_payload_types_and_sizes(self) -> None:
        """Test verification with different payload types and sizes."""
        secret = "payload_test_secret"
        configure_webhook_verifier(secret)
        verifier = get_webhook_verifier()

        test_payloads = [
            b"",  # Empty
            b"small",  # Small
            b"medium sized webhook payload with some data",  # Medium
            b"large payload: " + b"x" * 10000,  # Large
            b'{"json": "data", "number": 123, "bool": true}',  # JSON
            b"binary\x00\x01\x02\x03data",  # Binary data
        ]

        for payload in test_payloads:
            signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
            assert verifier.verify_signature(payload, signature) is True
