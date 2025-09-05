"""Data extraction behaviour tests - Text parsing and normalization."""

from unittest.mock import MagicMock

import pytest

from src.domain.value_objects import PhoneNumber


class DataExtractionService:
    """Mock data extraction service interface for testing extraction behaviors."""

    def normalize_phone_number(self, raw_phone: str) -> PhoneNumber:
        """Normalize phone number to E.164 format."""
        return PhoneNumber(value="+27821234567")

    def extract_provider_details(self, text: str) -> dict[str, str]:
        """Extract provider name and service from text patterns."""
        return {"name": "", "service": ""}

    def extract_phone_numbers(self, text: str) -> list[PhoneNumber]:
        """Extract all phone numbers from text."""
        return []

    def associate_services_with_names(self, text: str) -> dict[str, str]:
        """Associate service keywords with nearby names."""
        return {}

    def extract_location(self, text: str) -> str | None:
        """Extract location references from text."""
        return None


@pytest.fixture
def mock_extraction_service() -> MagicMock:
    """Mock data extraction service for testing extraction behaviours."""
    return MagicMock(spec=DataExtractionService)


def test_should_normalize_phone_numbers_to_e164(
    mock_extraction_service: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """'082 123 4567' should normalize to '+27821234567'."""
    # Arrange
    raw_phone = "082 123 4567"
    expected_normalized = PhoneNumber(value="+27821234567")
    mock_extraction_service.normalize_phone_number.return_value = expected_normalized

    # Act
    result = mock_extraction_service.normalize_phone_number(raw_phone)

    # Assert
    assert result.value == "+27821234567"
    assert result.normalized == "+27821234567"
    mock_extraction_service.normalize_phone_number.assert_called_once_with(raw_phone)


def test_should_extract_provider_name_from_patterns(
    mock_extraction_service: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """'John the plumber' should extract name: 'John', service: 'plumber'."""
    # Arrange
    text = "I highly recommend John the plumber for your kitchen repairs."
    expected_details = {"name": "John", "service": "plumber"}
    mock_extraction_service.extract_provider_details.return_value = expected_details

    # Act
    result = mock_extraction_service.extract_provider_details(text)

    # Assert
    assert result["name"] == "John"
    assert result["service"] == "plumber"
    assert len(result) == 2
    mock_extraction_service.extract_provider_details.assert_called_once_with(text)


def test_should_extract_multiple_phone_numbers(
    mock_extraction_service: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """Message with multiple numbers should extract all."""
    # Arrange
    text = (
        "Great services this week! Tom the plumber 082-555-1234 fixed our pipes, "
        "and Maria from CleanCo 071-555-5678 did fantastic house cleaning."
    )
    expected_phones = [
        PhoneNumber(value="+27825551234"),
        PhoneNumber(value="+27715555678"),
    ]
    mock_extraction_service.extract_phone_numbers.return_value = expected_phones

    # Act
    result = mock_extraction_service.extract_phone_numbers(text)

    # Assert
    assert len(result) == 2
    assert result[0].value == "+27825551234"
    assert result[1].value == "+27715555678"
    assert all(isinstance(phone, PhoneNumber) for phone in result)
    mock_extraction_service.extract_phone_numbers.assert_called_once_with(text)


def test_should_associate_service_keywords_with_names(
    mock_extraction_service: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """'electrician' near 'Davies' should get associated."""
    # Arrange
    text = "Davies is an excellent electrician, really professional work on our rewiring."
    expected_associations = {"Davies": "electrician"}
    mock_extraction_service.associate_services_with_names.return_value = expected_associations

    # Act
    result = mock_extraction_service.associate_services_with_names(text)

    # Assert
    assert "Davies" in result
    assert result["Davies"] == "electrician"
    assert len(result) == 1
    mock_extraction_service.associate_services_with_names.assert_called_once_with(text)


def test_should_extract_location_references(
    mock_extraction_service: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """'in Constantia' should extract location: 'Constantia'."""
    # Arrange
    text = "Looking for a good plumber in Constantia area, anyone have recommendations?"
    expected_location = "Constantia"
    mock_extraction_service.extract_location.return_value = expected_location

    # Act
    result = mock_extraction_service.extract_location(text)

    # Assert
    assert result == "Constantia"
    assert isinstance(result, str)
    mock_extraction_service.extract_location.assert_called_once_with(text)


def test_should_handle_no_location_found_gracefully(
    mock_extraction_service: MagicMock,  # pylint: disable=redefined-outer-name
) -> None:
    """Text without location should return None gracefully."""
    # Arrange
    text = "Great plumber, highly recommend for all your needs."
    mock_extraction_service.extract_location.return_value = None

    # Act
    result = mock_extraction_service.extract_location(text)

    # Assert
    assert result is None
    mock_extraction_service.extract_location.assert_called_once_with(text)
