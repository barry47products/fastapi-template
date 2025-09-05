"""Phone number value object with international validation and fuzzy matching."""

# mypy: disable-error-code="call-arg"
# Note: MyPy false positive - event_type has init=False, set by __init_subclass__

import re
from typing import Any

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat
from phonenumbers.phonenumber import PhoneNumber as ParsedPhoneNumber
from pydantic import BaseModel, model_validator

from src.domain.events import DomainEventRegistry, PhoneNumberParseError, PhoneNumberValidated
from src.domain.events import PhoneNumberValidationError as PhoneNumberValidationEvent
from src.shared.exceptions import PhoneNumberValidationError


class PhoneNumber(BaseModel):
    """
    Immutable phone number value object with international validation.

    Supports E.164 normalization, fuzzy matching for PostgreSQL pg_trgm,
    and WhatsApp format compatibility for GREEN-API integration.
    """

    model_config = {"frozen": True}

    value: str
    extension: str | None = None
    default_country_code: str | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_phone_data(cls, data: Any) -> Any:
        """Validate and normalize phone number to E.164 format."""
        if not isinstance(data, dict):
            return data

        value = data.get("value", "")
        default_country_code = data.get("default_country_code")

        if not value or not str(value).strip():
            # Publish domain event for empty value validation error
            DomainEventRegistry.publish(
                PhoneNumberValidationEvent(
                    phone_number=str(value),
                    error_type="empty_value",
                    error_message="Phone number cannot be empty",
                ),
            )
            raise PhoneNumberValidationError(
                "Phone number cannot be empty",
                field="value",
            )

        cleaned_value = cls._clean_phone_number(str(value))
        region = cls._get_region_for_country_code(default_country_code)

        try:
            parsed_number = phonenumbers.parse(cleaned_value, region)
            cls._validate_parsed_number(parsed_number)

            formatted = phonenumbers.format_number(
                parsed_number,
                PhoneNumberFormat.E164,
            )
            data["value"] = formatted

            # Publish domain event for successful validation
            DomainEventRegistry.publish(
                PhoneNumberValidated(
                    phone_number=str(value)[:10] + "***",  # Mask for privacy
                    normalized_number=formatted,
                    region=region or "unknown",
                ),
            )
            return data

        except NumberParseException as e:
            # Publish domain event for parse error
            DomainEventRegistry.publish(
                PhoneNumberParseError(
                    phone_number=str(value)[:10] + "***",  # Mask for privacy
                    error_message=(str(e.error_type) if hasattr(e, "error_type") else str(e)),
                ),
            )
            cls._handle_parse_exception(e)
            return data  # This will never execute but satisfies return consistency

    @classmethod
    def _clean_phone_number(cls, value: str) -> str:
        """Clean and format phone number string."""
        cleaned = re.sub(r"[^\d\+]", "", value.strip())
        if cleaned.startswith("00"):
            cleaned = "+" + cleaned[2:]
        return cleaned

    @classmethod
    def _get_region_for_country_code(
        cls,
        default_country_code: str | None,
    ) -> str | None:
        """Get region code for default country code."""
        if not default_country_code:
            return None
        region: str | None = phonenumbers.region_code_for_country_code(
            int(default_country_code),
        )
        return region

    @classmethod
    def _validate_parsed_number(cls, parsed_number: ParsedPhoneNumber) -> None:
        """Validate parsed phone number."""
        if not phonenumbers.is_valid_number(parsed_number):
            raise PhoneNumberValidationError(
                "Invalid phone number format",
                field="value",
            )

        national_len = len(str(parsed_number.national_number))
        if national_len < 4:
            raise PhoneNumberValidationError("Phone number too short", field="value")
        if national_len > 15:
            raise PhoneNumberValidationError("Phone number too long", field="value")

        region: str | None = phonenumbers.region_code_for_number(parsed_number)
        country_code = parsed_number.country_code
        if not region or not country_code or country_code > 999:
            raise PhoneNumberValidationError("Invalid country code", field="value")

    @classmethod
    def _handle_parse_exception(cls, e: NumberParseException) -> None:
        """Handle NumberParseException with appropriate error messages."""
        error_type = e.error_type
        if error_type == NumberParseException.INVALID_COUNTRY_CODE:
            raise PhoneNumberValidationError(
                "Invalid country code",
                field="value",
            ) from e
        if error_type == NumberParseException.TOO_SHORT_NSN:
            raise PhoneNumberValidationError(
                "Phone number too short",
                field="value",
            ) from e
        if error_type == NumberParseException.TOO_LONG:
            raise PhoneNumberValidationError(
                "Phone number too long",
                field="value",
            ) from e
        raise PhoneNumberValidationError(
            "Invalid phone number format",
            field="value",
        ) from e

    @property
    def normalized(self) -> str:
        """Returns the normalized E.164 format."""
        return self.value

    @property
    def country_code(self) -> str:
        """Extract country code from E.164 number."""
        parsed: ParsedPhoneNumber = phonenumbers.parse(self.value, None)
        return str(parsed.country_code)

    @property
    def national_number(self) -> str:
        """Extract national number part."""
        parsed: ParsedPhoneNumber = phonenumbers.parse(self.value, None)
        return str(parsed.national_number)

    def __str__(self) -> str:
        """Return normalized E.164 format."""
        return self.normalized

    def __repr__(self) -> str:
        """Return string representation of PhoneNumber."""
        return f"PhoneNumber(value='{self.value}')"

    def __hash__(self) -> int:
        """Return hash based on normalized value."""
        return hash(self.normalized)

    def __eq__(self, other: object) -> bool:
        """Compare phone numbers based on normalized values."""
        if not isinstance(other, PhoneNumber):
            return False
        return self.normalized == other.normalized

    def format_for_whatsapp(self) -> str:
        """Format phone number for WhatsApp/GREEN-API (without plus sign)."""
        return self.normalized[1:]  # Remove the + prefix

    def format_national(self) -> str:
        """Format phone number in national format."""
        parsed: ParsedPhoneNumber = phonenumbers.parse(self.value, None)
        formatted: str = phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL)
        return formatted.strip()

    def format_international(self) -> str:
        """Format phone number in international format with spaces."""
        parsed: ParsedPhoneNumber = phonenumbers.parse(self.value, None)
        formatted: str = phonenumbers.format_number(
            parsed,
            PhoneNumberFormat.INTERNATIONAL,
        )
        return formatted

    def similarity_score(self, other: "PhoneNumber") -> float:
        """
        Calculate similarity score with another phone number for fuzzy matching.

        Uses digit-by-digit comparison for PostgreSQL pg_trgm compatibility.
        Returns value between 0.0 (completely different) and 1.0 (identical).
        """
        if not isinstance(other, PhoneNumber):
            return 0.0

        # Use normalized numbers without + for comparison
        num1 = self.normalized[1:]
        num2 = other.normalized[1:]

        if num1 == num2:
            return 1.0

        # Calculate trigram-style similarity
        min_len = min(len(num1), len(num2))
        max_len = max(len(num1), len(num2))

        if max_len == 0:
            return 0.0

        # Count matching positions
        matches = sum(1 for i in range(min_len) if num1[i] == num2[i])

        # Add penalty for different lengths
        length_penalty = abs(len(num1) - len(num2)) / max_len

        # Calculate similarity (trigram-like approach)
        similarity = (matches / max_len) - (length_penalty * 0.5)
        final_score = max(0.0, similarity)

        return final_score

    def is_similar(self, other: "PhoneNumber", threshold: float = 0.85) -> bool:
        """
        Check if another phone number is similar within given threshold.

        Default threshold of 0.85 works well for provider deduplication.
        """
        return self.similarity_score(other) >= threshold

    def to_postgres_trigram_format(self) -> str:
        """
        Format phone number for PostgreSQL pg_trgm similarity matching.

        Returns digits only (no +) for optimal trigram indexing.
        """
        return self.normalized[1:]  # Remove + prefix for pg_trgm
