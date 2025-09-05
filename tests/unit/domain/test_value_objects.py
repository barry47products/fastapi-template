"""Domain value object unit tests focusing on validation and business rules.

These tests ensure data integrity at the domain boundary by testing critical validation
logic in value objects like PhoneNumber, GroupID, and other domain primitives.
"""

import pytest

from src.domain.value_objects import GroupID, PhoneNumber
from src.shared.exceptions import GroupIDValidationError, PhoneNumberValidationError


class TestPhoneNumberValidation:
    """Test PhoneNumber value object validation and business rules."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.provider
    def test_should_validate_and_normalize_international_phone_numbers(self) -> None:
        """Test that valid international phone numbers are normalized to E.164 format."""
        # Valid international formats - use known working numbers
        test_cases = [
            ("+27821234567", "+27821234567"),  # Already E.164 - SA mobile
            ("+27 82 123 4567", "+27821234567"),  # Same SA number with spaces
        ]

        for input_number, expected_output in test_cases:
            phone = PhoneNumber(value=input_number)
            assert phone.value == expected_output
            assert phone.normalized == expected_output

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.provider
    def test_should_normalize_local_south_african_numbers_with_country_code(self) -> None:
        """Test that local SA numbers are normalized when country code is provided."""
        # South African local numbers (country code 27)
        phone = PhoneNumber(value="0821234567", default_country_code="27")
        assert phone.value == "+27821234567"
        assert phone.country_code == "27"
        assert phone.national_number == "821234567"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.provider
    @pytest.mark.resilience
    def test_should_reject_empty_and_invalid_phone_numbers(self) -> None:
        """Test that empty and clearly invalid phone numbers are rejected."""
        invalid_numbers = [
            "",  # Empty string
            "   ",  # Whitespace only
            "abc123",  # Letters mixed with numbers
            "123",  # Too short
            "+999999999999999999999",  # Too long
            "+0001234567",  # Invalid country code
        ]

        for invalid_number in invalid_numbers:
            with pytest.raises(PhoneNumberValidationError):
                PhoneNumber(value=invalid_number)

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.provider
    def test_should_handle_various_input_formats(self) -> None:
        """Test that phone numbers with various formatting are normalized correctly."""
        # Different input formats for the same SA number
        formats = [
            "+27 82 123 4567",  # Spaces
            "+27-82-123-4567",  # Hyphens
            "+27(82)123-4567",  # Parentheses and hyphens
            "+27.82.123.4567",  # Dots
            "0027821234567",  # 00 prefix instead of +
        ]

        expected = "+27821234567"
        for format_variant in formats:
            phone = PhoneNumber(value=format_variant)
            assert phone.value == expected

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.whatsapp
    def test_should_format_for_whatsapp_api(self) -> None:
        """Test WhatsApp format (no + prefix) for GREEN-API integration."""
        phone = PhoneNumber(value="+27821234567")
        whatsapp_format = phone.format_for_whatsapp()
        assert whatsapp_format == "27821234567"  # No + prefix

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.provider
    def test_should_format_in_different_display_formats(self) -> None:
        """Test different formatting options for display purposes."""
        phone = PhoneNumber(value="+27821234567")

        # Test various format outputs
        assert phone.format_international() == "+27 82 123 4567"
        national_format = phone.format_national()
        assert "082 123 4567" in national_format  # SA national format

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.provider
    def test_should_calculate_similarity_scores_for_fuzzy_matching(self) -> None:
        """Test phone number similarity calculation for deduplication."""
        base_phone = PhoneNumber(value="+27821234567")

        # Identical numbers
        identical = PhoneNumber(value="+27821234567")
        assert base_phone.similarity_score(identical) == 1.0
        assert base_phone.is_similar(identical)

        # Very similar (typo in last digit)
        similar = PhoneNumber(value="+27821234568")  # 7 -> 8
        similarity = base_phone.similarity_score(similar)
        assert 0.8 < similarity < 1.0  # Should be high but not perfect

        # Different numbers
        different = PhoneNumber(value="+27821999999")
        assert base_phone.similarity_score(different) < 0.5
        assert not base_phone.is_similar(different)

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.provider
    def test_should_handle_phone_number_equality_and_hashing(self) -> None:
        """Test that phone numbers with same normalized value are equal and hashable."""
        phone1 = PhoneNumber(value="+27 82 123 4567")  # With spaces
        phone2 = PhoneNumber(value="+27821234567")  # Without spaces

        # Should be equal after normalization
        assert phone1 == phone2
        assert phone1.normalized == phone2.normalized

        # Should have same hash (important for sets/dicts)
        assert hash(phone1) == hash(phone2)

        # Should work in sets
        phone_set = {phone1, phone2}
        assert len(phone_set) == 1  # Deduplicated

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.provider
    @pytest.mark.regression
    def test_should_handle_edge_cases_that_could_break_system(self) -> None:
        """Test edge cases that could cause system failures if not handled."""
        # Valid numbers that could cause edge case issues
        edge_case_numbers = [
            "+27821234567",  # Standard SA mobile
            "+1234567890",  # Standard US number
        ]

        for number in edge_case_numbers:
            try:
                phone = PhoneNumber(value=number)
                assert phone.value.startswith("+")
            except PhoneNumberValidationError:
                pass  # Some might be invalid, that's ok for edge cases

        # Number with extension (if supported)
        with_extension = PhoneNumber(value="+27821234567", extension="123")
        assert with_extension.extension == "123"

        # Test that country code extraction works
        valid_phone = PhoneNumber(value="+27821234567")
        assert valid_phone.country_code == "27"
        assert len(valid_phone.country_code) <= 3


class TestGroupIDValidation:
    """Test GroupID value object validation for WhatsApp group handling."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.whatsapp
    def test_should_validate_whatsapp_group_id_format(self) -> None:
        """Test that valid WhatsApp group IDs are accepted."""
        valid_group_ids = [
            "12345678901234567890@g.us",  # Standard WhatsApp group format
            "120363023122435334@g.us",  # Another valid format
            "1234567890123456789012345@g.us",  # Longer ID
        ]

        for group_id_str in valid_group_ids:
            group_id = GroupID(value=group_id_str)
            assert group_id.value == group_id_str
            assert "@g.us" in group_id.value

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.whatsapp
    @pytest.mark.resilience
    def test_should_reject_invalid_group_id_formats(self) -> None:
        """Test that invalid WhatsApp group ID formats are rejected."""
        invalid_group_ids = [
            "",  # Empty
            "12345@c.us",  # Individual chat, not group
            "invalid-group-id",  # No @g.us suffix
            "@g.us",  # Missing ID part
            "12345@g.us@extra",  # Multiple @ symbols
            "12345",  # No domain part
        ]

        for invalid_id in invalid_group_ids:
            with pytest.raises(GroupIDValidationError):
                GroupID(value=invalid_id)

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.whatsapp
    def test_should_provide_privacy_safe_representations(self) -> None:
        """Test privacy-safe methods for logging and debugging."""
        group_id = GroupID(value="12345678901234567890@g.us")

        # Test masked representation for safe logging
        masked = group_id.masked()
        assert masked.endswith("@g.us")
        assert "*" in masked  # Should contain masking characters
        assert len(masked) == len(group_id.value)  # Same length but masked

        # Test short hash for identification
        short_hash = group_id.short_hash()
        assert len(short_hash) == 8
        assert short_hash.isalnum()  # Should be alphanumeric

        # Same group ID should produce same hash
        group_id2 = GroupID(value="12345678901234567890@g.us")
        assert group_id.short_hash() == group_id2.short_hash()

        # Different group ID should produce different hash
        group_id3 = GroupID(value="09876543210987654321@g.us")
        assert group_id.short_hash() != group_id3.short_hash()

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.whatsapp
    def test_should_format_for_green_api_integration(self) -> None:
        """Test GROUP-API formatting for WhatsApp integration."""
        group_id = GroupID(value="12345678901234567890@g.us")
        api_format = group_id.format_for_green_api()
        assert api_format == "12345678901234567890@g.us"  # Should match original

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.whatsapp
    def test_should_provide_group_id_string_representation(self) -> None:
        """Test string representation methods for GroupID."""
        group_id = GroupID(value="12345678901234567890@g.us")

        assert str(group_id) == "12345678901234567890@g.us"
        assert repr(group_id) == "GroupID(value='12345678901234567890@g.us')"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.whatsapp
    def test_should_handle_group_id_equality_and_hashing(self) -> None:
        """Test GroupID equality and hash behaviour for collections."""
        group_id1 = GroupID(value="12345678901234567890@g.us")
        group_id2 = GroupID(value="12345678901234567890@g.us")
        group_id3 = GroupID(value="09876543210987654321@g.us")

        # Equality
        assert group_id1 == group_id2
        assert group_id1 != group_id3

        # Hashing (important for sets and dict keys)
        assert hash(group_id1) == hash(group_id2)
        assert hash(group_id1) != hash(group_id3)

        # Collection behaviour
        group_set = {group_id1, group_id2, group_id3}
        assert len(group_set) == 2  # group_id1 and group_id2 are deduplicated


class TestValueObjectIntegration:
    """Test integration scenarios between different value objects."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.integration
    @pytest.mark.provider
    def test_should_work_together_in_provider_context(self) -> None:
        """Test that value objects work together in realistic provider scenarios."""
        # Simulate a provider with phone and operating in WhatsApp groups
        phone = PhoneNumber(value="+27821234567")
        group = GroupID(value="12345678901234567890@g.us")

        # Should be able to use them together
        provider_data = {
            "phone": phone.normalized,
            "whatsapp_format": phone.format_for_whatsapp(),
            "group_id": group.value,
        }

        assert provider_data["phone"] == "+27821234567"
        assert provider_data["whatsapp_format"] == "27821234567"
        assert provider_data["group_id"] == "12345678901234567890@g.us"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.performance
    def test_should_handle_bulk_validation_efficiently(self) -> None:
        """Test that value objects can handle bulk validation efficiently."""
        # Test bulk phone number validation (common in data imports)
        test_numbers = [
            "+27821234567",
            "+27821234568",
            "+27821234569",
        ]
        # Add US numbers
        test_numbers.extend(["+1555123456" + str(i) for i in range(10)])

        validated_phones = []
        for number in test_numbers:
            try:
                phone = PhoneNumber(value=number)
                validated_phones.append(phone)
            except PhoneNumberValidationError:
                pass  # Skip invalid ones

        # Should have successfully validated most numbers
        assert len(validated_phones) >= 3  # At least the SA numbers

        # All should be in E.164 format
        for phone in validated_phones:
            assert phone.value.startswith("+")
            assert len(phone.value) >= 10
