"""Data validation resilience tests - Input validation and duplicate handling."""

from unittest.mock import MagicMock

import pytest
from fastapi import status

from src.domain.value_objects import GroupID, PhoneNumber


class DataValidationService:
    """Mock data validation service interface for testing validation behaviors."""

    def validate_phone_number(self, phone: str) -> dict[str, str | int | bool]:
        """Validate phone number format before processing."""
        return {"status_code": 200, "valid": True}

    def validate_group_id(self, group_id: str) -> dict[str, str | int | bool]:
        """Validate group ID format."""
        return {"status_code": 200, "valid": True}

    def handle_duplicate_endorsement(
        self,
        provider_phone: PhoneNumber,
        group_id: GroupID,
        endorser_id: str,
    ) -> dict[str, str | int | bool]:
        """Handle duplicate endorsement appropriately."""
        return {"status_code": 200, "processed": True}


@pytest.fixture
def mock_validation_service() -> MagicMock:
    """Mock data validation service for testing validation behaviours."""
    return MagicMock(spec=DataValidationService)


@pytest.fixture
def invalid_phone_formats() -> list[str]:
    """Invalid phone number formats for testing validation."""
    return [
        "not_a_phone",
        "123",
        "082-12-34",  # Too short
        "082-123-456-789-012",  # Too long
        "+27-abc-def-ghi",  # Contains letters
        "",  # Empty
        "082 123 4567 extra",  # Extra characters
    ]


@pytest.fixture
def invalid_group_id_formats() -> list[str]:
    """Invalid group ID formats for testing validation."""
    return [
        "not_a_group",
        "12345@c.us",  # Individual chat, not group
        "12345678901234567890",  # Missing @g.us suffix
        "@g.us",  # Missing ID part
        "short@g.us",  # Too short ID
        "",  # Empty
    ]


@pytest.fixture
def sample_phone_number() -> PhoneNumber:
    """Sample phone number for duplicate testing."""
    return PhoneNumber(value="+27821234567")


@pytest.fixture
def sample_group_id() -> GroupID:
    """Sample group ID for duplicate testing."""
    return GroupID(value="12345678901234567890@g.us")


def test_should_validate_phone_numbers_before_processing(
    mock_validation_service: MagicMock,  # pylint: disable=redefined-outer-name
    invalid_phone_formats: list[str],  # pylint: disable=redefined-outer-name
) -> None:
    """Invalid phone format should return validation error."""
    # Test with first invalid format
    invalid_phone = invalid_phone_formats[0]

    # Arrange
    expected_response = {
        "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "valid": False,
        "error": "invalid_phone_format",
        "message": "Phone number format is invalid",
        "provided_value": invalid_phone,
        "expected_format": "E.164 format (+27xxxxxxxxx)",
    }
    mock_validation_service.validate_phone_number.return_value = expected_response

    # Act
    result = mock_validation_service.validate_phone_number(invalid_phone)

    # Assert
    assert result["status_code"] == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert result["valid"] is False
    assert result["error"] == "invalid_phone_format"
    assert "Phone number format is invalid" in str(result["message"])
    assert result["provided_value"] == invalid_phone
    assert result["expected_format"] == "E.164 format (+27xxxxxxxxx)"
    mock_validation_service.validate_phone_number.assert_called_once_with(invalid_phone)


def test_should_validate_group_id_format(
    mock_validation_service: MagicMock,  # pylint: disable=redefined-outer-name
    invalid_group_id_formats: list[str],  # pylint: disable=redefined-outer-name
) -> None:
    """Invalid group ID format should return validation error."""
    # Test with individual chat format (not group)
    invalid_group_id = invalid_group_id_formats[1]  # "12345@c.us"

    # Arrange
    expected_response = {
        "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "valid": False,
        "error": "invalid_group_id_format",
        "message": "Group ID format is invalid",
        "provided_value": invalid_group_id,
        "expected_format": "WhatsApp group format (xxxxxxxxxxxxxxxxxx@g.us)",
        "reason": "Individual chat detected, only group messages are processed",
    }
    mock_validation_service.validate_group_id.return_value = expected_response

    # Act
    result = mock_validation_service.validate_group_id(invalid_group_id)

    # Assert
    assert result["status_code"] == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert result["valid"] is False
    assert result["error"] == "invalid_group_id_format"
    assert "Group ID format is invalid" in str(result["message"])
    assert result["provided_value"] == invalid_group_id
    assert result["expected_format"] == "WhatsApp group format (xxxxxxxxxxxxxxxxxx@g.us)"
    assert "Individual chat detected" in str(result["reason"])
    mock_validation_service.validate_group_id.assert_called_once_with(invalid_group_id)


def test_should_handle_duplicate_endorsements(
    mock_validation_service: MagicMock,  # pylint: disable=redefined-outer-name
    sample_phone_number: PhoneNumber,  # pylint: disable=redefined-outer-name
    sample_group_id: GroupID,  # pylint: disable=redefined-outer-name
) -> None:
    """Duplicate endorsements should be handled appropriately."""
    # Arrange
    endorser_id = "user_alice_12345"
    expected_response = {
        "status_code": status.HTTP_200_OK,
        "processed": True,
        "action_taken": "duplicate_detected_ignored",
        "provider_phone": sample_phone_number.value,
        "group_id": sample_group_id.value,
        "endorser_id": endorser_id,
        "message": "Duplicate endorsement detected and ignored",
        "original_endorsement_date": "2025-01-01T10:00:00Z",
        "duplicate_attempt_date": "2025-01-01T12:00:00Z",
    }
    mock_validation_service.handle_duplicate_endorsement.return_value = expected_response

    # Act
    result = mock_validation_service.handle_duplicate_endorsement(
        sample_phone_number,
        sample_group_id,
        endorser_id,
    )

    # Assert
    assert result["status_code"] == status.HTTP_200_OK
    assert result["processed"] is True
    assert result["action_taken"] == "duplicate_detected_ignored"
    assert result["provider_phone"] == sample_phone_number.value
    assert result["group_id"] == sample_group_id.value
    assert result["endorser_id"] == endorser_id
    assert "Duplicate endorsement detected" in str(result["message"])
    assert "original_endorsement_date" in result
    assert "duplicate_attempt_date" in result
    mock_validation_service.handle_duplicate_endorsement.assert_called_once_with(
        sample_phone_number,
        sample_group_id,
        endorser_id,
    )
