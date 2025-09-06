"""Unit tests for API key validator security component."""

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
        assert isinstance(validator.api_keys, set)

    def test_validates_valid_api_key(self) -> None:
        """Validates valid API key."""
        validator = APIKeyValidator(["valid_key", "another_key"])

        assert validator.validate("valid_key") is True
        assert validator.validate("another_key") is True

    def test_rejects_invalid_api_key(self) -> None:
        """Rejects invalid API key."""
        validator = APIKeyValidator(["valid_key"])

        assert validator.validate("invalid_key") is False
        assert validator.validate("wrong_key") is False

    def test_rejects_none_api_key(self) -> None:
        """Rejects None API key."""
        validator = APIKeyValidator(["valid_key"])

        assert validator.validate(None) is False

    def test_rejects_empty_string_api_key(self) -> None:
        """Rejects empty string API key."""
        validator = APIKeyValidator(["valid_key"])

        assert validator.validate("") is False
        assert validator.validate("   ") is False

    def test_handles_empty_api_keys_list(self) -> None:
        """Handles empty API keys list."""
        validator = APIKeyValidator([])

        assert validator.validate("any_key") is False
        assert validator.api_keys == set()

    def test_case_sensitive_validation(self) -> None:
        """Performs case-sensitive validation."""
        validator = APIKeyValidator(["CaseSensitive"])

        assert validator.validate("CaseSensitive") is True
        assert validator.validate("casesensitive") is False
        assert validator.validate("CASESENSITIVE") is False


class TestAPIKeyValidatorSingleton:
    """Test API key validator singleton behavior."""

    def test_raises_error_when_not_configured(self) -> None:
        """Raises error when validator not configured."""
        _APIKeyValidatorSingleton._instance = None

        with pytest.raises(APIKeyValidationError, match="API key validator not configured"):
            _APIKeyValidatorSingleton.get_instance()

    def test_returns_configured_instance(self) -> None:
        """Returns configured instance."""
        validator = APIKeyValidator(["test_key"])
        _APIKeyValidatorSingleton.set_instance(validator)

        result = _APIKeyValidatorSingleton.get_instance()
        assert result is validator

    def test_sets_singleton_instance(self) -> None:
        """Sets singleton instance."""
        validator = APIKeyValidator(["test_key"])

        _APIKeyValidatorSingleton.set_instance(validator)

        assert _APIKeyValidatorSingleton._instance is validator


class TestConfigureAPIKeyValidator:
    """Test API key validator configuration behavior."""

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_registers_with_service_registry(self, mock_get_registry: MagicMock) -> None:
        """Registers validator with service registry."""
        mock_registry = MagicMock()
        mock_get_registry.return_value = mock_registry
        api_keys = ["key1", "key2"]

        configure_api_key_validator(api_keys)

        mock_registry.register_api_key_validator.assert_called_once()
        validator_arg = mock_registry.register_api_key_validator.call_args[0][0]
        assert isinstance(validator_arg, APIKeyValidator)
        assert validator_arg.api_keys == {"key1", "key2"}

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_handles_service_registry_import_error(self, mock_get_registry: MagicMock) -> None:
        """Handles service registry import error gracefully."""
        mock_get_registry.side_effect = ImportError("Module not found")
        api_keys = ["key1", "key2"]

        # Should not raise exception
        configure_api_key_validator(api_keys)

        # Should still set singleton
        validator = _APIKeyValidatorSingleton.get_instance()
        assert validator.api_keys == {"key1", "key2"}

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_handles_service_registry_runtime_error(self, mock_get_registry: MagicMock) -> None:
        """Handles service registry runtime error gracefully."""
        mock_get_registry.side_effect = RuntimeError("Registry not initialized")
        api_keys = ["key1", "key2"]

        # Should not raise exception
        configure_api_key_validator(api_keys)

        # Should still set singleton
        validator = _APIKeyValidatorSingleton.get_instance()
        assert validator.api_keys == {"key1", "key2"}

    def test_sets_singleton_instance(self) -> None:
        """Sets singleton instance."""
        api_keys = ["test_key"]

        configure_api_key_validator(api_keys)

        validator = _APIKeyValidatorSingleton.get_instance()
        assert validator.api_keys == {"test_key"}


class TestGetAPIKeyValidator:
    """Test get API key validator behavior."""

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_returns_validator_from_service_registry(self, mock_get_registry: MagicMock) -> None:
        """Returns validator from service registry when available."""
        mock_validator = APIKeyValidator(["registry_key"])
        mock_registry = MagicMock()
        mock_registry.has_api_key_validator.return_value = True
        mock_registry.get_api_key_validator.return_value = mock_validator
        mock_get_registry.return_value = mock_registry

        result = get_api_key_validator()

        assert result is mock_validator
        mock_registry.has_api_key_validator.assert_called_once()
        mock_registry.get_api_key_validator.assert_called_once()

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_falls_back_to_singleton_when_registry_unavailable(
        self, mock_get_registry: MagicMock
    ) -> None:
        """Falls back to singleton when service registry unavailable."""
        mock_get_registry.side_effect = ImportError("Registry not available")
        singleton_validator = APIKeyValidator(["singleton_key"])
        _APIKeyValidatorSingleton.set_instance(singleton_validator)

        result = get_api_key_validator()

        assert result is singleton_validator

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_falls_back_to_singleton_when_validator_not_in_registry(
        self, mock_get_registry: MagicMock
    ) -> None:
        """Falls back to singleton when validator not in registry."""
        mock_registry = MagicMock()
        mock_registry.has_api_key_validator.return_value = False
        mock_get_registry.return_value = mock_registry
        singleton_validator = APIKeyValidator(["singleton_key"])
        _APIKeyValidatorSingleton.set_instance(singleton_validator)

        result = get_api_key_validator()

        assert result is singleton_validator

    @patch("src.infrastructure.service_registry.get_service_registry")
    def test_raises_error_when_no_validator_available(self, mock_get_registry: MagicMock) -> None:
        """Raises error when no validator available."""
        mock_get_registry.side_effect = ImportError("Registry not available")
        _APIKeyValidatorSingleton._instance = None

        with pytest.raises(APIKeyValidationError, match="API key validator not configured"):
            get_api_key_validator()


class TestVerifyAPIKey:
    """Test verify API key FastAPI dependency behavior."""

    @patch("src.infrastructure.security.api_key_validator.get_api_key_validator")
    @patch("src.infrastructure.security.api_key_validator.get_logger")
    @patch("src.infrastructure.security.api_key_validator.get_metrics_collector")
    def test_validates_x_api_key_header(
        self, mock_metrics: MagicMock, mock_logger: MagicMock, mock_get_validator: MagicMock
    ) -> None:
        """Validates X-API-Key header."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = True
        mock_get_validator.return_value = mock_validator
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        result = verify_api_key(x_api_key="valid_key", authorization=None)

        assert result == "valid_key"
        mock_validator.validate.assert_called_once_with("valid_key")
        mock_metrics_instance.increment_counter.assert_called_once_with(
            "api_key_validations_total", {"status": "success"}
        )

    @patch("src.infrastructure.security.api_key_validator.get_api_key_validator")
    @patch("src.infrastructure.security.api_key_validator.get_logger")
    @patch("src.infrastructure.security.api_key_validator.get_metrics_collector")
    def test_validates_authorization_bearer_header(
        self, mock_metrics: MagicMock, mock_logger: MagicMock, mock_get_validator: MagicMock
    ) -> None:
        """Validates Authorization Bearer header."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = True
        mock_get_validator.return_value = mock_validator
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        result = verify_api_key(x_api_key=None, authorization="Bearer valid_token")

        assert result == "valid_token"
        mock_validator.validate.assert_called_once_with("valid_token")

    @patch("src.infrastructure.security.api_key_validator.get_api_key_validator")
    @patch("src.infrastructure.security.api_key_validator.get_logger")
    @patch("src.infrastructure.security.api_key_validator.get_metrics_collector")
    def test_validates_authorization_apikey_header(
        self, mock_metrics: MagicMock, mock_logger: MagicMock, mock_get_validator: MagicMock
    ) -> None:
        """Validates Authorization ApiKey header."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = True
        mock_get_validator.return_value = mock_validator
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        result = verify_api_key(x_api_key=None, authorization="ApiKey valid_key")

        assert result == "valid_key"
        mock_validator.validate.assert_called_once_with("valid_key")

    @patch("src.infrastructure.security.api_key_validator.get_api_key_validator")
    @patch("src.infrastructure.security.api_key_validator.get_logger")
    @patch("src.infrastructure.security.api_key_validator.get_metrics_collector")
    def test_validates_authorization_direct_format(
        self, mock_metrics: MagicMock, mock_logger: MagicMock, mock_get_validator: MagicMock
    ) -> None:
        """Validates Authorization header direct format (GREEN-API)."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = True
        mock_get_validator.return_value = mock_validator
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        result = verify_api_key(x_api_key=None, authorization="direct_api_key")

        assert result == "direct_api_key"
        mock_validator.validate.assert_called_once_with("direct_api_key")

    @patch("src.infrastructure.security.api_key_validator.get_api_key_validator")
    @patch("src.infrastructure.security.api_key_validator.get_logger")
    @patch("src.infrastructure.security.api_key_validator.get_metrics_collector")
    def test_prefers_x_api_key_over_authorization(
        self, mock_metrics: MagicMock, mock_logger: MagicMock, mock_get_validator: MagicMock
    ) -> None:
        """Prefers X-API-Key header over Authorization header."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = True
        mock_get_validator.return_value = mock_validator
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        result = verify_api_key(x_api_key="x_api_key", authorization="Bearer auth_key")

        assert result == "x_api_key"
        mock_validator.validate.assert_called_once_with("x_api_key")

    @patch("src.infrastructure.security.api_key_validator.get_api_key_validator")
    @patch("src.infrastructure.security.api_key_validator.get_logger")
    @patch("src.infrastructure.security.api_key_validator.get_metrics_collector")
    def test_raises_http_exception_for_invalid_key(
        self, mock_metrics: MagicMock, mock_logger: MagicMock, mock_get_validator: MagicMock
    ) -> None:
        """Raises HTTPException for invalid API key."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = False
        mock_get_validator.return_value = mock_validator
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(x_api_key="invalid_key", authorization=None)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid API key"
        assert exc_info.value.headers == {"WWW-Authenticate": "ApiKey"}
        mock_metrics_instance.increment_counter.assert_called_once_with(
            "api_key_validations_total", {"status": "failure"}
        )

    @patch("src.infrastructure.security.api_key_validator.get_api_key_validator")
    @patch("src.infrastructure.security.api_key_validator.get_logger")
    @patch("src.infrastructure.security.api_key_validator.get_metrics_collector")
    def test_raises_http_exception_for_missing_key(
        self, mock_metrics: MagicMock, mock_logger: MagicMock, mock_get_validator: MagicMock
    ) -> None:
        """Raises HTTPException when no API key provided."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = False
        mock_get_validator.return_value = mock_validator
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(x_api_key=None, authorization=None)

        assert exc_info.value.status_code == 401
        mock_validator.validate.assert_called_once_with(None)

    @patch("src.infrastructure.security.api_key_validator.get_api_key_validator")
    @patch("src.infrastructure.security.api_key_validator.get_logger")
    @patch("src.infrastructure.security.api_key_validator.get_metrics_collector")
    def test_logs_successful_validation(
        self, mock_metrics: MagicMock, mock_logger: MagicMock, mock_get_validator: MagicMock
    ) -> None:
        """Logs successful API key validation."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = True
        mock_get_validator.return_value = mock_validator
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        verify_api_key(x_api_key="test12345678", authorization=None)

        mock_logger_instance.info.assert_called_once_with(
            "API key validation successful",
            api_key_prefix="test1234...",
            auth_method="X-API-Key",
        )

    @patch("src.infrastructure.security.api_key_validator.get_api_key_validator")
    @patch("src.infrastructure.security.api_key_validator.get_logger")
    @patch("src.infrastructure.security.api_key_validator.get_metrics_collector")
    def test_logs_failed_validation(
        self, mock_metrics: MagicMock, mock_logger: MagicMock, mock_get_validator: MagicMock
    ) -> None:
        """Logs failed API key validation."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = False
        mock_get_validator.return_value = mock_validator
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        with pytest.raises(HTTPException):
            verify_api_key(x_api_key="invalid12345", authorization=None)

        mock_logger_instance.warning.assert_called_once_with(
            "API key validation failed",
            api_key_prefix="invalid1...",
            auth_method="X-API-Key",
        )
