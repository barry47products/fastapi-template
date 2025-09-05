"""Tests for ContactParser service."""

import pytest

from src.application.services.contact_parser import ContactParser
from src.domain.value_objects import PhoneNumber


class TestContactParser:  # pylint: disable=too-many-public-methods
    """Test ContactParser vCard parsing functionality."""

    @pytest.fixture
    def parser(self) -> ContactParser:
        """Contact parser instance for testing."""
        return ContactParser()

    @pytest.fixture
    def sample_vcard(self) -> str:
        """Sample vCard data for testing."""
        return """BEGIN:VCARD
VERSION:3.0
FN:John Smith
TEL:+27123456789
ORG:Plumbing Services
EMAIL:john@example.com
END:VCARD"""

    @pytest.fixture
    def multi_phone_vcard(self) -> str:
        """vCard with multiple phone numbers."""
        return """BEGIN:VCARD
VERSION:3.0
FN:Jane Doe
TEL;TYPE=HOME:+27111111111
TEL;TYPE=WORK:+27222222222
TEL:+27333333333
ORG:Electrical Services
END:VCARD"""

    @pytest.fixture
    def minimal_vcard(self) -> str:
        """Minimal vCard with just name and phone."""
        return """BEGIN:VCARD
VERSION:3.0
FN:Mike Wilson
TEL:+27823456789
END:VCARD"""

    def test_should_parse_complete_vcard_successfully(
        self,
        parser: ContactParser,
        sample_vcard: str,
    ) -> None:
        """Test parsing a complete vCard with all fields."""
        # Act
        contact = parser.parse_vcard(sample_vcard, "John Smith")

        # Assert
        assert contact.display_name == "John Smith"
        assert len(contact.phone_numbers) == 1
        assert contact.phone_numbers[0] == PhoneNumber(value="+27123456789")
        assert contact.organization == "Plumbing Services"
        assert contact.email == "john@example.com"
        assert contact.raw_vcard == sample_vcard

    def test_should_parse_vcard_with_multiple_phone_numbers(
        self,
        parser: ContactParser,
        multi_phone_vcard: str,
    ) -> None:
        """Test parsing vCard with multiple phone numbers."""
        # Act
        contact = parser.parse_vcard(multi_phone_vcard, "Jane Doe")

        # Assert
        assert contact.display_name == "Jane Doe"
        assert len(contact.phone_numbers) == 3
        phone_values = [str(p) for p in contact.phone_numbers]
        assert "+27111111111" in phone_values
        assert "+27222222222" in phone_values
        assert "+27333333333" in phone_values
        assert contact.organization == "Electrical Services"

    def test_should_parse_minimal_vcard(
        self,
        parser: ContactParser,
        minimal_vcard: str,
    ) -> None:
        """Test parsing minimal vCard with just name and phone."""
        # Act
        contact = parser.parse_vcard(minimal_vcard, "Mike Wilson")

        # Assert
        assert contact.display_name == "Mike Wilson"
        assert len(contact.phone_numbers) == 1
        assert contact.phone_numbers[0] == PhoneNumber(value="+27823456789")
        assert contact.organization is None
        assert contact.email is None

    def test_should_handle_vcard_with_no_phone_numbers(
        self,
        parser: ContactParser,
    ) -> None:
        """Test handling vCard without phone numbers."""
        vcard_no_phone = """BEGIN:VCARD
VERSION:3.0
FN:No Phone Person
EMAIL:nophone@example.com
END:VCARD"""

        # Act
        contact = parser.parse_vcard(vcard_no_phone, "No Phone Person")

        # Assert
        assert contact.display_name == "No Phone Person"
        assert len(contact.phone_numbers) == 0
        assert contact.email == "nophone@example.com"

    def test_should_handle_invalid_phone_numbers_gracefully(
        self,
        parser: ContactParser,
    ) -> None:
        """Test handling vCard with invalid phone numbers."""
        vcard_invalid = """BEGIN:VCARD
VERSION:3.0
FN:Invalid Phone Person
TEL:invalid-phone
TEL:+27123456789
END:VCARD"""

        # Act
        contact = parser.parse_vcard(vcard_invalid, "Invalid Phone Person")

        # Assert
        assert contact.display_name == "Invalid Phone Person"
        assert len(contact.phone_numbers) == 1
        assert contact.phone_numbers[0] == PhoneNumber(value="+27123456789")

    def test_should_convert_contact_to_mentions(
        self,
        parser: ContactParser,
        sample_vcard: str,
    ) -> None:
        """Test converting parsed contact to ExtractedMention objects."""
        # Arrange
        contact = parser.parse_vcard(sample_vcard, "John Smith")

        # Act
        mentions = parser.contact_to_mentions(contact, confidence=0.95)

        # Assert
        assert len(mentions) == 3  # name, phone, organization

        # Check display name mention
        name_mention = next(m for m in mentions if m.extraction_type == "contact_display_name")
        assert name_mention.text == "John Smith"
        assert name_mention.confidence == 0.95

        # Check phone mention
        phone_mention = next(m for m in mentions if m.extraction_type == "contact_phone_number")
        assert phone_mention.text == "+27123456789"
        assert phone_mention.confidence == 0.95

        # Check organization mention
        org_mention = next(m for m in mentions if m.extraction_type == "contact_organization")
        assert org_mention.text == "Plumbing Services"
        assert org_mention.confidence == 0.95

    def test_should_create_mentions_for_multiple_phones(
        self,
        parser: ContactParser,
        multi_phone_vcard: str,
    ) -> None:
        """Test mention creation for contact with multiple phones."""
        # Arrange
        contact = parser.parse_vcard(multi_phone_vcard, "Jane Doe")

        # Act
        mentions = parser.contact_to_mentions(contact)

        # Assert
        phone_mentions = [m for m in mentions if m.extraction_type == "contact_phone_number"]
        assert len(phone_mentions) == 3

        phone_texts = [m.text for m in phone_mentions]
        assert "+27111111111" in phone_texts
        assert "+27222222222" in phone_texts
        assert "+27333333333" in phone_texts

    def test_should_handle_contact_without_organization(
        self,
        parser: ContactParser,
        minimal_vcard: str,
    ) -> None:
        """Test mention creation for contact without organization."""
        # Arrange
        contact = parser.parse_vcard(minimal_vcard, "Mike Wilson")

        # Act
        mentions = parser.contact_to_mentions(contact)

        # Assert
        # Should only have name and phone mentions, no organization
        mention_types = [m.extraction_type for m in mentions]
        assert "contact_display_name" in mention_types
        assert "contact_phone_number" in mention_types
        assert "contact_organization" not in mention_types
        assert len(mentions) == 2

    def test_should_set_custom_confidence_score(
        self,
        parser: ContactParser,
        sample_vcard: str,
    ) -> None:
        """Test setting custom confidence score for mentions."""
        # Arrange
        contact = parser.parse_vcard(sample_vcard, "John Smith")
        custom_confidence = 0.85

        # Act
        mentions = parser.contact_to_mentions(contact, confidence=custom_confidence)

        # Assert
        for mention in mentions:
            assert mention.confidence == custom_confidence

    def test_should_create_proper_mention_positions(
        self,
        parser: ContactParser,
        sample_vcard: str,
    ) -> None:
        """Test that mentions have proper start/end positions."""
        # Arrange
        contact = parser.parse_vcard(sample_vcard, "John Smith")

        # Act
        mentions = parser.contact_to_mentions(contact)

        # Assert
        for mention in mentions:
            assert mention.start_position >= 0
            assert mention.end_position > mention.start_position
            assert mention.end_position == len(mention.text)

    def test_should_handle_malformed_vcard_gracefully(
        self,
        parser: ContactParser,
    ) -> None:
        """Test graceful handling of malformed vCard."""
        malformed_vcard = "This is not a vCard at all"

        # Act
        contact = parser.parse_vcard(malformed_vcard, "Test Name")

        # Assert - Should handle gracefully with empty data
        assert contact.display_name == "Test Name"
        assert len(contact.phone_numbers) == 0
        assert contact.organization is None
        assert contact.email is None

    def test_should_handle_empty_vcard_gracefully(
        self,
        parser: ContactParser,
    ) -> None:
        """Test handling empty vCard content."""
        empty_vcard = ""

        # Act
        contact = parser.parse_vcard(empty_vcard, "Empty Contact")

        # Assert
        assert contact.display_name == "Empty Contact"
        assert len(contact.phone_numbers) == 0
        assert contact.organization is None
        assert contact.email is None

    def test_should_handle_vcard_with_whitespace_fields(
        self,
        parser: ContactParser,
    ) -> None:
        """Test handling vCard with whitespace-only fields."""
        whitespace_vcard = """BEGIN:VCARD
VERSION:3.0
FN:   John Spaces
TEL:+27123456789
ORG:
EMAIL:
END:VCARD"""

        # Act
        contact = parser.parse_vcard(whitespace_vcard, "John Spaces")

        # Assert
        assert contact.display_name == "John Spaces"
        assert len(contact.phone_numbers) == 1
        assert contact.organization is None  # Empty org should be None
        assert contact.email is None  # Empty email should be None

    def test_should_handle_case_insensitive_vcard_fields(
        self,
        parser: ContactParser,
    ) -> None:
        """Test handling vCard with mixed case field names."""
        mixed_case_vcard = """begin:vcard
version:3.0
fn:Mixed Case Person
tel:+27123456789
org:Mixed Case Org
email:mixed@example.com
end:vcard"""

        # Act
        contact = parser.parse_vcard(mixed_case_vcard, "Mixed Case Person")

        # Assert
        assert contact.display_name == "Mixed Case Person"
        assert len(contact.phone_numbers) == 1
        assert contact.phone_numbers[0] == PhoneNumber(value="+27123456789")
        assert contact.organization == "Mixed Case Org"
        assert contact.email == "mixed@example.com"

    def test_should_extract_organization_with_attributes(
        self,
        parser: ContactParser,
    ) -> None:
        """Test organization extraction with vCard attributes."""
        # Arrange - vCard with organization that has attributes
        vcard_with_org_attrs = """BEGIN:VCARD
VERSION:3.0
FN:Test
ORG;TYPE=WORK:Business Corp
END:VCARD"""

        # Act
        result = parser._extract_organization(vcard_with_org_attrs)

        # Assert
        assert result == "Business Corp"

    def test_should_extract_email_with_attributes(
        self,
        parser: ContactParser,
    ) -> None:
        """Test email extraction with vCard attributes."""
        # Arrange - vCard with email that has attributes
        vcard_with_email_attrs = """BEGIN:VCARD
VERSION:3.0
FN:Test
EMAIL;TYPE=WORK:business@example.com
END:VCARD"""

        # Act
        result = parser._extract_email(vcard_with_email_attrs)

        # Assert
        assert result == "business@example.com"

    def test_should_handle_email_without_proper_format(
        self,
        parser: ContactParser,
    ) -> None:
        """Test email extraction rejects emails without @ or . symbols."""
        # Arrange - vCard with valid email that meets basic validation
        vcard_with_valid_email = """BEGIN:VCARD
VERSION:3.0
FN:Test
EMAIL:valid@domain.com
END:VCARD"""

        # Act
        result = parser._extract_email(vcard_with_valid_email)

        # Assert - Should extract valid email with both @ and .
        assert result == "valid@domain.com"

    def test_should_reject_emails_without_at_symbol(
        self,
        parser: ContactParser,
    ) -> None:
        """Test that emails without @ symbol are rejected."""
        # Arrange
        vcard_no_at = """BEGIN:VCARD
VERSION:3.0
FN:Test
EMAIL:invalid.email.com
END:VCARD"""

        # Act
        result = parser._extract_email(vcard_no_at)

        # Assert
        assert result is None

    def test_should_reject_emails_without_dot_symbol(
        self,
        parser: ContactParser,
    ) -> None:
        """Test that emails without . symbol are rejected."""
        # Arrange
        vcard_no_dot = """BEGIN:VCARD
VERSION:3.0
FN:Test
EMAIL:invalid@email
END:VCARD"""

        # Act
        result = parser._extract_email(vcard_no_dot)

        # Assert
        assert result is None


class TestContactParserErrorHandling:
    """Test ContactParser error handling and resilience."""

    @pytest.fixture
    def parser(self) -> ContactParser:
        """Contact parser instance for testing."""
        return ContactParser()

    def test_should_raise_contact_parsing_exception_on_critical_failure(
        self,
        parser: ContactParser,
    ) -> None:
        """Test that critical failures raise ContactParsingException."""
        # Arrange - Force an exception by mocking the phone number extraction to fail
        import unittest.mock

        with unittest.mock.patch.object(
            parser,
            "_extract_phone_numbers",
            side_effect=RuntimeError("Critical parsing error"),
        ):
            # Act & Assert
            from src.shared.exceptions import ContactParsingException

            with pytest.raises(ContactParsingException) as parsing_exc:
                parser.parse_vcard("BEGIN:VCARD\nEND:VCARD", "Test Contact")

            assert "vCard parsing failed" in str(parsing_exc.value)
            assert "Critical parsing error" in str(parsing_exc.value)

    def test_should_raise_contact_parsing_exception_on_mention_conversion_failure(
        self,
        parser: ContactParser,
    ) -> None:
        """Test that mention conversion failures raise ContactParsingException."""
        # Arrange - Create a contact that will fail during mention conversion
        from src.application.services.contact_parser import ParsedContact

        contact = ParsedContact(
            display_name="Test Contact",
            phone_numbers=[PhoneNumber(value="+27123456789")],
        )

        # Force an exception by mocking ExtractedMention to fail
        import unittest.mock

        with unittest.mock.patch(
            "src.application.services.contact_parser.ExtractedMention",
            side_effect=RuntimeError("Mention creation failed"),
        ):
            # Act & Assert
            from src.shared.exceptions import ContactParsingException

            with pytest.raises(ContactParsingException) as exc:
                parser.contact_to_mentions(contact)

            assert "Contact mention conversion failed" in str(exc.value)
            assert "Mention creation failed" in str(exc.value)

    def test_should_handle_phone_number_validation_errors_gracefully(
        self,
        parser: ContactParser,
    ) -> None:
        """Test graceful handling of phone number validation errors."""
        # Arrange - vCard with phone that will fail validation
        vcard_with_bad_phone = """BEGIN:VCARD
VERSION:3.0
FN:Test Contact
TEL:invalid-phone-format
END:VCARD"""

        # Mock PhoneNumber to raise validation error
        import unittest.mock

        from src.shared.exceptions import PhoneNumberValidationError

        with unittest.mock.patch(
            "src.application.services.contact_parser.PhoneNumber",
            side_effect=PhoneNumberValidationError("Invalid phone format"),
        ):
            # Act
            contact = parser.parse_vcard(vcard_with_bad_phone, "Test Contact")

            # Assert - Should handle validation errors and continue
            assert contact.display_name == "Test Contact"
            assert len(contact.phone_numbers) == 0  # No valid phones extracted
