"""Unit tests for Email value object."""

from __future__ import annotations

import pytest

from src.domain.value_objects.email import Email
from src.shared.exceptions import ValidationException


class TestEmailValidation:
    """Test email validation and normalization."""

    def test_valid_email_formats(self) -> None:
        """Accepts valid email formats."""
        valid_emails = [
            "user@example.com",
            "test.email@domain.co.uk",
            "user+tag@example.org",
            "123@numbers.com",
            "a@b.cc",
            "very.long.local.part@very.long.domain.name.com",
        ]

        for email_str in valid_emails:
            email = Email(value=email_str)
            assert email.value == email_str.lower().strip()

    def test_email_normalization(self) -> None:
        """Normalizes email by converting to lowercase and trimming."""
        email = Email(value="  USER@EXAMPLE.COM  ")
        assert email.value == "user@example.com"

    def test_empty_email_raises_validation_error(self) -> None:
        """Raises ValidationException for empty email."""
        with pytest.raises(ValidationException) as exc_info:
            Email(value="")

        assert "Email cannot be empty" in str(exc_info.value)
        assert exc_info.value.field == "email"

    def test_none_email_raises_validation_error(self) -> None:
        """Raises ValidationException for None email."""
        import pydantic_core

        with pytest.raises((pydantic_core.ValidationError, Exception)) as exc_info:
            Email(value=None)  # type: ignore[arg-type]

        # Pydantic will raise ValidationError before our custom validator runs
        assert "Input should be a valid string" in str(exc_info.value)

    def test_invalid_email_format_raises_validation_error(self) -> None:
        """Raises ValidationException for invalid email format."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@@example.com",
            "user@.com",
            "user@com",
            "user@example.",
            "user @example.com",
            "user@exam ple.com",
        ]

        for invalid_email in invalid_emails:
            with pytest.raises(ValidationException) as exc_info:
                Email(value=invalid_email)

            assert "Invalid email format" in str(exc_info.value)
            assert exc_info.value.field == "email"

    def test_common_domain_typos_raise_validation_error(self) -> None:
        """Raises ValidationException for common domain typos."""
        typo_emails = ["user@example.con", "user@domain.co"]

        for typo_email in typo_emails:
            with pytest.raises(ValidationException) as exc_info:
                Email(value=typo_email)

            assert "Email domain appears to have a typo" in str(exc_info.value)
            assert exc_info.value.field == "email"

    def test_email_too_long_raises_validation_error(self) -> None:
        """Raises ValidationException for email exceeding RFC 5321 limit."""
        long_email = "a" * 250 + "@example.com"  # Total length > 254

        with pytest.raises(ValidationException) as exc_info:
            Email(value=long_email)

        assert "Email address too long" in str(exc_info.value)
        assert exc_info.value.field == "email"

    def test_local_part_too_long_raises_validation_error(self) -> None:
        """Raises ValidationException for local part exceeding RFC 5321 limit."""
        long_local_email = "a" * 65 + "@example.com"  # Local part > 64 chars

        with pytest.raises(ValidationException) as exc_info:
            Email(value=long_local_email)

        assert "Email local part too long" in str(exc_info.value)
        assert exc_info.value.field == "email"


class TestEmailStringMethods:
    """Test string representation and comparison methods."""

    def test_str_returns_email_value(self) -> None:
        """Returns email string value."""
        email = Email(value="user@example.com")
        assert str(email) == "user@example.com"

    def test_hash_returns_consistent_value(self) -> None:
        """Returns consistent hash for same email value."""
        email1 = Email(value="user@example.com")
        email2 = Email(value="user@example.com")

        assert hash(email1) == hash(email2)

    def test_hash_differs_for_different_emails(self) -> None:
        """Returns different hash for different email values."""
        email1 = Email(value="user1@example.com")
        email2 = Email(value="user2@example.com")

        assert hash(email1) != hash(email2)

    def test_equality_with_same_email_object(self) -> None:
        """Returns True when comparing same Email objects."""
        email1 = Email(value="user@example.com")
        email2 = Email(value="user@example.com")

        assert email1 == email2

    def test_equality_with_string_value(self) -> None:
        """Returns True when comparing with normalized string."""
        email = Email(value="user@example.com")

        assert email == "user@example.com"
        assert email == "USER@EXAMPLE.COM"
        assert email == "  user@example.com  "

    def test_equality_with_invalid_string_returns_false(self) -> None:
        """Returns False when comparing with invalid email string."""
        email = Email(value="user@example.com")

        assert email != "invalid-email"
        assert email != "@example.com"

    def test_equality_with_different_type_returns_false(self) -> None:
        """Returns False when comparing with different types."""
        email = Email(value="user@example.com")

        assert email != 123
        assert email is not None
        assert email != ["user@example.com"]


class TestEmailProperties:
    """Test email property methods."""

    def test_domain_property_extracts_domain(self) -> None:
        """Extracts domain from email address."""
        email = Email(value="user@example.com")
        assert email.domain == "example.com"

    def test_local_part_property_extracts_local_part(self) -> None:
        """Extracts local part from email address."""
        email = Email(value="user@example.com")
        assert email.local_part == "user"

    def test_complex_email_parts_extraction(self) -> None:
        """Extracts parts from complex email addresses."""
        email = Email(value="test.user+tag@sub.domain.co.uk")

        assert email.local_part == "test.user+tag"
        assert email.domain == "sub.domain.co.uk"


class TestEmailBusinessLogic:
    """Test business logic methods."""

    def test_is_business_email_with_personal_domains(self) -> None:
        """Returns False for personal email domains."""
        personal_domains = [
            "gmail.com",
            "yahoo.com",
            "hotmail.com",
            "outlook.com",
            "icloud.com",
            "aol.com",
            "live.com",
            "msn.com",
        ]

        for domain in personal_domains:
            email = Email(value=f"user@{domain}")
            assert not email.is_business_email()

    def test_is_business_email_with_business_domains(self) -> None:
        """Returns True for business email domains."""
        business_domains = [
            "company.com",
            "enterprise.org",
            "business.co.uk",
            "startup.io",
        ]

        for domain in business_domains:
            email = Email(value=f"user@{domain}")
            assert email.is_business_email()

    def test_mask_for_display_short_local_part(self) -> None:
        """Masks short local parts completely."""
        email = Email(value="ab@example.com")
        assert email.mask_for_display() == "**@example.com"

    def test_mask_for_display_medium_local_part(self) -> None:
        """Masks medium local parts showing first and last character."""
        email = Email(value="user@example.com")
        assert email.mask_for_display() == "u**r@example.com"

    def test_mask_for_display_long_local_part(self) -> None:
        """Masks long local parts showing first and last character."""
        email = Email(value="verylongusername@example.com")
        assert email.mask_for_display() == "v**************e@example.com"

    def test_mask_for_display_single_character_local_part(self) -> None:
        """Masks single character local part."""
        email = Email(value="a@example.com")
        assert email.mask_for_display() == "*@example.com"


class TestEmailClassMethods:
    """Test class factory methods."""

    def test_from_string_creates_valid_email(self) -> None:
        """Creates Email from valid string."""
        email = Email.from_string("user@example.com")

        assert isinstance(email, Email)
        assert email.value == "user@example.com"

    def test_from_string_validates_input(self) -> None:
        """Validates input when creating from string."""
        with pytest.raises(ValidationException):
            Email.from_string("invalid-email")

    def test_from_string_normalizes_input(self) -> None:
        """Normalizes input when creating from string."""
        email = Email.from_string("  USER@EXAMPLE.COM  ")
        assert email.value == "user@example.com"


class TestEmailImmutability:
    """Test email immutability."""

    def test_email_is_frozen(self) -> None:
        """Email objects are immutable (frozen)."""
        email = Email(value="user@example.com")

        import pydantic_core

        with pytest.raises((pydantic_core.ValidationError, TypeError)):
            email.value = "new@example.com"  # type: ignore[misc]

    def test_email_model_config_frozen(self) -> None:
        """Email model configuration has frozen=True."""
        assert Email.model_config["frozen"] is True


class TestEmailEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_email_with_numbers_and_symbols(self) -> None:
        """Accepts emails with numbers and allowed symbols."""
        email = Email(value="test123+tag@sub-domain.co.uk")
        assert email.value == "test123+tag@sub-domain.co.uk"

    def test_international_domain_names(self) -> None:
        """Accepts international domain names."""
        email = Email(value="user@xn--domain-example.com")
        assert email.value == "user@xn--domain-example.com"

    def test_maximum_valid_lengths(self) -> None:
        """Accepts maximum valid email lengths."""
        # Local part exactly 64 characters
        local_part = "a" * 64
        domain_part = "example.com"
        email_str = f"{local_part}@{domain_part}"

        email = Email(value=email_str)
        assert email.value == email_str

    def test_minimum_valid_email(self) -> None:
        """Accepts minimum valid email format."""
        email = Email(value="a@b.cc")
        assert email.value == "a@b.cc"
        assert email.local_part == "a"
        assert email.domain == "b.cc"
