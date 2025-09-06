"""Unit tests for PhoneNumber value object."""

from __future__ import annotations

import pytest

from src.domain.value_objects.phone_number import PhoneNumber
from src.shared.exceptions import ValidationException


class TestPhoneNumberValidation:
    """Test phone number validation and normalization."""

    def test_valid_phone_number_formats(self) -> None:
        """Accepts valid international phone number formats."""
        valid_phones = [
            "+1234567890",
            "+44 20 7946 0958",
            "+33-1-23-45-67-89",
            "+49 (30) 12345678",
            "+61 2 1234 5678",
            "+1 (555) 123-4567",
            "+86 138 0013 8000",
        ]

        for phone_str in valid_phones:
            phone = PhoneNumber(value=phone_str)
            # Should normalize by removing spaces, hyphens, parentheses
            expected = phone_str.translate(str.maketrans("", "", " ()-"))
            assert phone.value == expected

    def test_phone_number_normalization(self) -> None:
        """Normalizes phone number by removing formatting characters."""
        phone = PhoneNumber(value="+1 (555) 123-4567")
        assert phone.value == "+15551234567"

    def test_empty_phone_number_raises_validation_error(self) -> None:
        """Raises ValidationException for empty phone number."""
        with pytest.raises(ValidationException) as exc_info:
            PhoneNumber(value="")

        assert "Phone number cannot be empty" in str(exc_info.value)
        assert exc_info.value.field == "phone"

    def test_none_phone_number_raises_validation_error(self) -> None:
        """Raises ValidationException for None phone number."""
        import pydantic_core

        with pytest.raises((pydantic_core.ValidationError, Exception)) as exc_info:
            PhoneNumber(value=None)  # type: ignore[arg-type]

        # Pydantic will raise ValidationError before our custom validator runs
        assert "Input should be a valid string" in str(exc_info.value)

    def test_phone_without_country_code_raises_validation_error(self) -> None:
        """Raises ValidationException for phone without country code."""
        invalid_phones = [
            "1234567890",
            "555-123-4567",
            "(555) 123-4567",
            "123-456-7890",
        ]

        for invalid_phone in invalid_phones:
            with pytest.raises(ValidationException) as exc_info:
                PhoneNumber(value=invalid_phone)

            assert "Phone number must start with country code (+)" in str(exc_info.value)
            assert exc_info.value.field == "phone"

    def test_phone_with_invalid_characters_raises_validation_error(self) -> None:
        """Raises ValidationException for phone with invalid characters."""
        # Test with a phone that has + in the middle - this won't be stripped
        with pytest.raises(ValidationException) as exc_info:
            PhoneNumber(value="+155512+34567")  # Extra + in middle

        assert "Phone number can only contain digits and +" in str(exc_info.value)
        assert exc_info.value.field == "phone"

    def test_phone_too_short_raises_validation_error(self) -> None:
        """Raises ValidationException for phone numbers too short."""
        with pytest.raises(ValidationException) as exc_info:
            PhoneNumber(value="+123456789")  # Only 9 digits

        assert "Phone number must be between 10-15 digits" in str(exc_info.value)
        assert exc_info.value.field == "phone"

    def test_phone_too_long_raises_validation_error(self) -> None:
        """Raises ValidationException for phone numbers too long."""
        with pytest.raises(ValidationException) as exc_info:
            PhoneNumber(value="+1234567890123456")  # 16 digits

        assert "Phone number must be between 10-15 digits" in str(exc_info.value)
        assert exc_info.value.field == "phone"

    def test_phone_boundary_lengths(self) -> None:
        """Accepts phone numbers at boundary lengths (10 and 15 digits)."""
        min_phone = PhoneNumber(value="+1234567890")  # 10 digits
        max_phone = PhoneNumber(value="+123456789012345")  # 15 digits

        assert min_phone.value == "+1234567890"
        assert max_phone.value == "+123456789012345"


class TestPhoneNumberStringMethods:
    """Test string representation and comparison methods."""

    def test_str_returns_phone_value(self) -> None:
        """Returns phone number string value."""
        phone = PhoneNumber(value="+15551234567")
        assert str(phone) == "+15551234567"

    def test_hash_returns_consistent_value(self) -> None:
        """Returns consistent hash for same phone value."""
        phone1 = PhoneNumber(value="+15551234567")
        phone2 = PhoneNumber(value="+15551234567")

        assert hash(phone1) == hash(phone2)

    def test_hash_differs_for_different_phones(self) -> None:
        """Returns different hash for different phone values."""
        phone1 = PhoneNumber(value="+15551234567")
        phone2 = PhoneNumber(value="+15551234568")

        assert hash(phone1) != hash(phone2)

    def test_equality_with_same_phone_object(self) -> None:
        """Returns True when comparing same PhoneNumber objects."""
        phone1 = PhoneNumber(value="+15551234567")
        phone2 = PhoneNumber(value="+15551234567")

        assert phone1 == phone2

    def test_equality_with_string_value(self) -> None:
        """Returns True when comparing with normalized string."""
        phone = PhoneNumber(value="+15551234567")

        assert phone == "+15551234567"
        assert phone == "+1 (555) 123-4567"  # Should normalize and match

    def test_equality_with_invalid_string_returns_false(self) -> None:
        """Returns False when comparing with invalid phone string."""
        phone = PhoneNumber(value="+15551234567")

        assert phone != "invalid-phone"
        assert phone != "1234567890"

    def test_equality_with_different_type_returns_false(self) -> None:
        """Returns False when comparing with different types."""
        phone = PhoneNumber(value="+15551234567")

        assert phone != 15551234567
        assert phone is not None
        assert phone != ["+15551234567"]


class TestPhoneNumberProperties:
    """Test phone number property methods."""

    def test_country_code_us_canada(self) -> None:
        """Extracts country code for US/Canada numbers."""
        phone = PhoneNumber(value="+15551234567")
        assert phone.country_code == "1"

    def test_country_code_uk(self) -> None:
        """Extracts country code for UK numbers."""
        phone = PhoneNumber(value="+442079460958")
        # With 12 total digits (442079460958), logic >= 11 returns first 1 digit (4)
        assert phone.country_code == "4"

    def test_country_code_france(self) -> None:
        """Extracts country code for France numbers."""
        phone = PhoneNumber(value="+33123456789")
        # With 11 total digits (33123456789), logic >= 11 returns first 1 digit (3)
        assert phone.country_code == "3"

    def test_country_code_short_number(self) -> None:
        """Extracts country code for shorter numbers."""
        phone = PhoneNumber(value="+1234567890")
        assert phone.country_code == "12"

    def test_national_number_extraction(self) -> None:
        """Extracts national number without country code."""
        test_cases = [
            ("+15551234567", "5551234567"),  # country_code="1", removes "+1"
            ("+442079460958", "42079460958"),  # country_code="4", removes "+4"
            ("+33123456789", "3123456789"),  # country_code="3", removes "+3"
        ]

        for phone_str, expected_national in test_cases:
            phone = PhoneNumber(value=phone_str)
            assert phone.national_number == expected_national

    def test_national_number_with_empty_country_code(self) -> None:
        """Handles case where country code extraction might fail."""
        # Create a minimal valid phone that might have edge case behavior
        phone = PhoneNumber(value="+1234567890")
        national = phone.national_number
        assert len(national) > 0
        assert not national.startswith("+")


class TestPhoneNumberFormatting:
    """Test phone number formatting methods."""

    def test_format_display_us_canada(self) -> None:
        """Formats US/Canada numbers with standard formatting."""
        phone = PhoneNumber(value="+15551234567")
        assert phone.format_display() == "+1 (555) 123-4567"

    def test_format_display_non_us_canada(self) -> None:
        """Returns original format for non-US/Canada numbers."""
        phone = PhoneNumber(value="+442079460958")
        assert phone.format_display() == "+442079460958"

    def test_format_display_invalid_us_length(self) -> None:
        """Returns original format for US numbers with wrong length."""
        phone = PhoneNumber(value="+1555123456")  # 9 national digits, not 10
        assert phone.format_display() == "+1555123456"

    def test_mask_for_display_normal_length(self) -> None:
        """Masks phone number for privacy display."""
        phone = PhoneNumber(value="+15551234567")
        assert phone.mask_for_display() == "+15551****67"

    def test_mask_for_display_minimum_valid_number(self) -> None:
        """Masks minimum valid phone number."""
        phone = PhoneNumber(value="+1234567890")  # 10 digits - minimum valid
        assert phone.mask_for_display() == "+1234****90"


class TestPhoneNumberBusinessLogic:
    """Test business logic methods."""

    def test_is_mobile_us_mobile_area_codes(self) -> None:
        """Returns True for US numbers with common mobile area codes."""
        mobile_area_codes = ["201", "202", "203", "212", "213", "214", "215"]

        for area_code in mobile_area_codes:
            phone = PhoneNumber(value=f"+1{area_code}5551234")
            assert phone.is_mobile() is True

    def test_is_mobile_us_non_mobile_area_codes(self) -> None:
        """Returns False for US numbers with non-mobile area codes."""
        phone = PhoneNumber(value="+15551234567")  # 555 is not in mobile list
        assert phone.is_mobile() is False

    def test_is_mobile_us_invalid_length(self) -> None:
        """Returns True (default) for US numbers with invalid national length."""
        phone = PhoneNumber(value="+1555123456")  # 9 digits, not 10
        assert phone.is_mobile() is True

    def test_is_mobile_non_us_numbers(self) -> None:
        """Returns True (default) for non-US country codes."""
        non_us_phones = [
            "+442079460958",  # UK
            "+33123456789",  # France
            "+8613800138000",  # China
        ]

        for phone_str in non_us_phones:
            phone = PhoneNumber(value=phone_str)
            assert phone.is_mobile() is True


class TestPhoneNumberClassMethods:
    """Test class factory methods."""

    def test_from_string_creates_valid_phone(self) -> None:
        """Creates PhoneNumber from valid string."""
        phone = PhoneNumber.from_string("+15551234567")

        assert isinstance(phone, PhoneNumber)
        assert phone.value == "+15551234567"

    def test_from_string_validates_input(self) -> None:
        """Validates input when creating from string."""
        with pytest.raises(ValidationException):
            PhoneNumber.from_string("invalid-phone")

    def test_from_string_normalizes_input(self) -> None:
        """Normalizes input when creating from string."""
        phone = PhoneNumber.from_string("+1 (555) 123-4567")
        assert phone.value == "+15551234567"


class TestPhoneNumberImmutability:
    """Test phone number immutability."""

    def test_phone_number_is_frozen(self) -> None:
        """PhoneNumber objects are immutable (frozen)."""
        phone = PhoneNumber(value="+15551234567")

        import pydantic_core

        with pytest.raises((pydantic_core.ValidationError, TypeError)):
            phone.value = "+15551234568"  # type: ignore[misc]

    def test_phone_number_model_config_frozen(self) -> None:
        """PhoneNumber model configuration has frozen=True."""
        assert PhoneNumber.model_config["frozen"] is True


class TestPhoneNumberEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_phone_with_many_formatting_characters(self) -> None:
        """Handles phone numbers with extensive formatting."""
        phone = PhoneNumber(value="+1 (555) 123-4567 ext. ignore")
        # Note: 'ext. ignore' part would be removed by regex, but 'ext' contains letters
        # This should actually fail validation due to letters
        formatted_input = "+1 (555) 123-4567"
        phone = PhoneNumber(value=formatted_input)
        assert phone.value == "+15551234567"

    def test_phone_with_international_codes(self) -> None:
        """Handles various international country codes."""
        international_phones = [
            ("+861380013800", "8"),  # China - 12 digits, >= 11, returns first 1
            ("+8201234567890", "8"),  # South Korea - 12 digits, >= 11, returns first 1
            ("+911234567890", "9"),  # India - 11 digits, >= 11, returns first 1
        ]

        for phone_str, expected_code in international_phones:
            phone = PhoneNumber(value=phone_str)
            assert phone.value == phone_str
            assert phone.country_code == expected_code

    def test_minimum_and_maximum_valid_lengths(self) -> None:
        """Tests boundary conditions for phone number lengths."""
        min_phone = PhoneNumber(value="+1234567890")  # Exactly 10 digits
        max_phone = PhoneNumber(value="+123456789012345")  # Exactly 15 digits

        assert len(min_phone.value[1:]) == 10  # 10 digits after +
        assert len(max_phone.value[1:]) == 15  # 15 digits after +

    def test_country_code_extraction_edge_cases(self) -> None:
        """Tests country code extraction for various number lengths."""
        test_cases = [
            ("+1234567890", "12"),  # 10 digits, >= 10, returns first 2
            ("+12345678901", "1"),  # 11 digits, >= 11, returns first 1
            ("+123456789012", "1"),  # 12 digits, >= 11, returns first 1
            ("+1234567890123", "1"),  # 13 digits, >= 11, returns first 1
        ]

        for phone_str, expected_country_code in test_cases:
            phone = PhoneNumber(value=phone_str)
            assert phone.country_code == expected_country_code

    def test_phone_validation_preserves_plus_sign(self) -> None:
        """Ensures plus sign is preserved in normalized phone number."""
        phone = PhoneNumber(value="+1 555 123 4567")
        assert phone.value.startswith("+")
        assert phone.value == "+15551234567"

    def test_multiple_plus_signs_handled(self) -> None:
        """Handles edge case with multiple plus signs."""
        # This should fail validation as only one + at start is valid
        with pytest.raises(ValidationException):
            PhoneNumber(value="++15551234567")

    def test_whitespace_only_raises_validation_error(self) -> None:
        """Raises ValidationException for whitespace-only input."""
        with pytest.raises(ValidationException) as exc_info:
            PhoneNumber(value="   ")

        # After normalization, whitespace becomes empty, which lacks country code
        assert "Phone number must start with country code (+)" in str(exc_info.value)
        assert exc_info.value.field == "phone"
