"""Unit tests for API key validator security component."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.infrastructure.security.api_key_validator import (
    APIKeyValidationError,
    APIKeyValidator,
    _APIKeyValidatorSingleton,
    configure_api_key_validator,
    get_api_key_validator,
    verify_api_key,
)


class TestAPIKeyValidationError:
    """Test API key validation error behavior."""

    def test_creates_error_with_message(self) -> None:
        """Creates error with message."""
        error = APIKeyValidationError("Invalid key")

        assert str(error) == "Invalid key"
        assert error.message == "Invalid key"
        assert error.error_code == "API_KEY_INVALID"

    def test_inherits_from_application_error(self) -> None:
        """Inherits from ApplicationError."""
        from src.shared.exceptions import ApplicationError

        error = APIKeyValidationError("Test error")
        assert isinstance(error, ApplicationError)


class TestAPIKeyValidator:
    """Test API key validator behavior."""

    def test_creates_validator_with_api_keys(self) -> None:
        """Creates validator with API keys."""
        api_keys = ["key1", "key2", "key3"]
        validator = APIKeyValidator(api_keys)

        assert validator.api_keys == {"key1", "key2", "key3"}

    def test_converts_api_keys_to_set(self) -> None:
        """Converts API keys list to set for O(1) lookup."""
        api_keys = ["key1", "key2", "key1"]  # Duplicate key
        validator = APIKeyValidator(api_keys)

        assert validator.api_keys == {"key1", "key2"}
        assert len(validator.api_keys) == 2

    def test_validates_correct_api_key(self) -> None:
        """Validates correct API key successfully."""
        validator = APIKeyValidator(["valid_key", "another_key"])

        assert validator.validate("valid_key") is True
        assert validator.validate("another_key") is True

    def test_rejects_invalid_api_key(self) -> None:
        """Rejects invalid API key."""
        validator = APIKeyValidator(["valid_key"])

        assert validator.validate("invalid_key") is False
        assert validator.validate("") is False
        assert validator.validate("VALID_KEY") is False  # Case sensitive

    def test_handles_empty_api_keys(self) -> None:
        """Handles empty API keys list."""
        validator = APIKeyValidator([])

        assert validator.api_keys == set()
        assert validator.validate("any_key") is False

    def test_handles_none_api_key_validation(self) -> None:
        """Handles None API key validation."""
        validator = APIKeyValidator(["valid_key"])

        assert validator.validate(None) is False


class TestAPIKeyValidatorSingleton:
    """Test singleton pattern for API key validator."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _APIKeyValidatorSingleton._instance = None

    def test_raises_error_when_no_instance_set(self) -> None:
        """Raises error when trying to get instance before configuration."""
        with pytest.raises(APIKeyValidationError, match="API key validator not configured"):
            _APIKeyValidatorSingleton.get_instance()

    def test_returns_set_instance(self) -> None:
        """Returns the set singleton instance."""
        validator = APIKeyValidator(["test_key"])
        _APIKeyValidatorSingleton.set_instance(validator)

        retrieved_validator = _APIKeyValidatorSingleton.get_instance()
        assert retrieved_validator is validator

    def test_replaces_existing_instance(self) -> None:
        """Replaces existing singleton instance when new one is set."""
        old_validator = APIKeyValidator(["old_key"])
        new_validator = APIKeyValidator(["new_key"])

        _APIKeyValidatorSingleton.set_instance(old_validator)
        _APIKeyValidatorSingleton.set_instance(new_validator)

        retrieved_validator = _APIKeyValidatorSingleton.get_instance()
        assert retrieved_validator is new_validator
        assert retrieved_validator is not old_validator


class TestConfigureAPIKeyValidator:
    """Test API key validator configuration behavior."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _APIKeyValidatorSingleton._instance = None

    def test_sets_singleton_instance_for_backward_compatibility(self) -> None:
        """Sets singleton instance for backward compatibility."""
        api_keys = ["singleton_key"]

        configure_api_key_validator(api_keys)

        singleton_validator = _APIKeyValidatorSingleton.get_instance()
        assert singleton_validator.api_keys == {"singleton_key"}

    def test_replaces_existing_singleton(self) -> None:
        """Replaces existing singleton instance when reconfigured."""
        # Set initial configuration
        configure_api_key_validator(["old_key"])
        old_validator = _APIKeyValidatorSingleton.get_instance()

        # Reconfigure with new keys
        configure_api_key_validator(["new_key1", "new_key2"])
        new_validator = _APIKeyValidatorSingleton.get_instance()

        assert new_validator is not old_validator
        assert new_validator.api_keys == {"new_key1", "new_key2"}

    def test_configures_with_empty_keys_list(self) -> None:
        """Configures validator with empty API keys list."""
        configure_api_key_validator([])

        singleton_validator = _APIKeyValidatorSingleton.get_instance()
        assert singleton_validator.api_keys == set()

    def test_configures_with_duplicate_keys(self) -> None:
        """Removes duplicate keys when configuring validator."""
        api_keys = ["key1", "key2", "key1", "key3"]

        configure_api_key_validator(api_keys)

        singleton_validator = _APIKeyValidatorSingleton.get_instance()
        assert singleton_validator.api_keys == {"key1", "key2", "key3"}


class TestGetAPIKeyValidator:
    """Test get API key validator behavior."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _APIKeyValidatorSingleton._instance = None

    def test_returns_singleton_instance_when_configured(self) -> None:
        """Returns singleton instance when properly configured."""
        configure_api_key_validator(["test_key"])

        validator = get_api_key_validator()

        assert isinstance(validator, APIKeyValidator)
        assert validator.api_keys == {"test_key"}

    def test_raises_error_when_not_configured(self) -> None:
        """Raises error when validator not configured."""
        with pytest.raises(APIKeyValidationError, match="API key validator not configured"):
            get_api_key_validator()

    def test_returns_same_instance_on_subsequent_calls(self) -> None:
        """Returns same instance on subsequent calls."""
        configure_api_key_validator(["consistent_key"])

        validator1 = get_api_key_validator()
        validator2 = get_api_key_validator()

        assert validator1 is validator2


class TestVerifyAPIKeyBasics:
    """Test basic verify API key functionality."""

    def setup_method(self) -> None:
        """Reset singleton state and configure validator for each test."""
        _APIKeyValidatorSingleton._instance = None
        configure_api_key_validator(["valid_key_123", "another_valid_key"])

    def test_accepts_valid_api_key_from_x_api_key_header(self) -> None:
        """Accepts valid API key from X-API-Key header."""
        api_key = verify_api_key(x_api_key="valid_key_123", authorization=None)

        assert api_key == "valid_key_123"

    def test_accepts_valid_api_key_from_authorization_header(self) -> None:
        """Accepts valid API key from Authorization header."""
        api_key = verify_api_key(x_api_key=None, authorization="Bearer valid_key_123")

        assert api_key == "valid_key_123"

    def test_rejects_invalid_api_key(self) -> None:
        """Rejects invalid API key and raises HTTP 401."""
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(x_api_key="invalid_key", authorization=None)

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    def test_rejects_missing_api_key(self) -> None:
        """Rejects request with no API key and raises HTTP 401."""
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(x_api_key=None, authorization=None)

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    def test_prefers_x_api_key_header(self) -> None:
        """Prefers X-API-Key header when both are provided."""
        api_key = verify_api_key(
            x_api_key="valid_key_123", authorization="Bearer another_valid_key"
        )

        assert api_key == "valid_key_123"

    def test_handles_authorization_without_bearer_prefix(self) -> None:
        """Handles Authorization header without Bearer prefix."""
        api_key = verify_api_key(x_api_key=None, authorization="valid_key_123")

        assert api_key == "valid_key_123"

    def test_strips_bearer_prefix_from_authorization(self) -> None:
        """Strips Bearer prefix from Authorization header."""
        api_key = verify_api_key(x_api_key=None, authorization="Bearer valid_key_123")

        assert api_key == "valid_key_123"

    @patch("src.infrastructure.security.api_key_validator.get_logger")
    @patch("src.infrastructure.security.api_key_validator.get_metrics_collector")
    def test_records_success_metrics(self, mock_metrics: MagicMock, mock_logger: MagicMock) -> None:
        """Records success metrics on valid API key."""
        mock_logger_instance = MagicMock()
        mock_metrics_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics.return_value = mock_metrics_instance

        verify_api_key(x_api_key="valid_key_123", authorization=None)

        mock_metrics_instance.increment_counter.assert_called_with(
            "api_key_validations_total", {"status": "success"}
        )

    @patch("src.infrastructure.security.api_key_validator.get_logger")
    @patch("src.infrastructure.security.api_key_validator.get_metrics_collector")
    def test_records_failure_metrics(self, mock_metrics: MagicMock, mock_logger: MagicMock) -> None:
        """Records failure metrics on invalid API key."""
        mock_logger_instance = MagicMock()
        mock_metrics_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics.return_value = mock_metrics_instance

        with pytest.raises(HTTPException):
            verify_api_key(x_api_key="invalid_key", authorization=None)

        mock_metrics_instance.increment_counter.assert_called_with(
            "api_key_validations_total", {"status": "failure"}
        )


class TestAPIKeyValidatorWorkflows:
    """Test complete API key validator workflows and use cases."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _APIKeyValidatorSingleton._instance = None

    def test_typical_validator_lifecycle(self) -> None:
        """Test complete lifecycle of API key validator."""
        # Initial configuration
        configure_api_key_validator(["api_key_1", "api_key_2"])
        validator = get_api_key_validator()

        # Validate keys
        assert validator.validate("api_key_1") is True
        assert validator.validate("api_key_2") is True
        assert validator.validate("invalid_key") is False

        # Reconfigure with new keys
        configure_api_key_validator(["new_key_1", "new_key_2", "new_key_3"])
        updated_validator = get_api_key_validator()

        # Old keys no longer valid
        assert updated_validator.validate("api_key_1") is False
        assert updated_validator.validate("api_key_2") is False

        # New keys are valid
        assert updated_validator.validate("new_key_1") is True
        assert updated_validator.validate("new_key_2") is True
        assert updated_validator.validate("new_key_3") is True

    def test_fastapi_integration_workflow(self) -> None:
        """Test FastAPI integration workflow."""
        configure_api_key_validator(["integration_key"])

        # Simulate FastAPI dependency injection - successful case
        verified_key = verify_api_key(x_api_key="integration_key", authorization=None)
        assert verified_key == "integration_key"

        # Simulate authentication failure
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(x_api_key="wrong_key", authorization=None)

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    def test_edge_case_handling(self) -> None:
        """Test edge case handling in validator workflows."""
        # Configure with edge case keys (excluding empty string for security)
        edge_keys = ["key-with-special-chars!@#$%", "very-long-key-" + "x" * 100]
        configure_api_key_validator(edge_keys)
        validator = get_api_key_validator()

        # Special character and long keys should be handled
        assert validator.validate("key-with-special-chars!@#$%") is True
        assert validator.validate("very-long-key-" + "x" * 100) is True

        # Empty strings and None should always be invalid for security
        assert validator.validate("") is False
        assert validator.validate(None) is False
