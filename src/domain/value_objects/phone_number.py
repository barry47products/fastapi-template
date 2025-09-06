"""Phone number value object with validation."""

import re
from typing import Any

from pydantic import BaseModel, field_validator

from src.shared.exceptions import ValidationException


class PhoneNumber(BaseModel):
    """
    Phone number value object with basic validation.

    This is a simplified example for template purposes.
    In a real application, consider using the `phonenumbers` library
    for proper international phone number validation and formatting.

    Demonstrates value object patterns:
    - Immutability (frozen=True)
    - Self-validation
    - Normalization
    - Rich behavior methods
    """

    model_config = {"frozen": True}

    value: str

    @field_validator("value")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate and normalize phone number."""
        if not v or not isinstance(v, str):
            raise ValidationException("Phone number cannot be empty", field="phone")

        # Remove all non-digit characters except +
        phone = re.sub(r"[^\d+]", "", v.strip())

        # Basic validation - must start with + and have 10-15 digits
        if not phone.startswith("+"):
            raise ValidationException(
                "Phone number must start with country code (+)", field="phone"
            )

        digits_only = phone[1:]  # Remove the + sign
        if not digits_only.isdigit():
            raise ValidationException("Phone number can only contain digits and +", field="phone")

        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValidationException("Phone number must be between 10-15 digits", field="phone")

        return phone

    def __str__(self) -> str:
        """Return phone number string representation."""
        return self.value

    def __hash__(self) -> int:
        """Return hash for set/dict usage."""
        return hash(self.value)

    def __eq__(self, other: Any) -> bool:
        """Compare phone numbers by normalized value."""
        if isinstance(other, PhoneNumber):
            return self.value == other.value
        if isinstance(other, str):
            try:
                normalized = PhoneNumber(value=other)
                return self.value == normalized.value
            except ValidationException:
                return False
        return False

    @property
    def country_code(self) -> str:
        """Extract country code from phone number."""
        if not self.value.startswith("+"):
            return ""

        # Simple heuristic - most country codes are 1-3 digits
        digits = self.value[1:]
        if len(digits) >= 11:  # US/Canada format
            return digits[:1]
        if len(digits) >= 10:  # Most other countries
            return digits[:2]
        return digits[:3]

    @property
    def national_number(self) -> str:
        """Extract national number (without country code)."""
        country_code = self.country_code
        if country_code:
            return self.value[len(country_code) + 1 :]
        return self.value.removeprefix("+")

    def format_display(self) -> str:
        """Format phone number for display."""
        if len(self.value) == 12 and self.value.startswith("+1"):  # US/Canada
            # Format as +1 (XXX) XXX-XXXX
            national = self.national_number
            if len(national) == 10:
                return f"+1 ({national[:3]}) {national[3:6]}-{national[6:]}"

        # Default format for other countries
        return self.value

    def mask_for_display(self) -> str:
        """Return masked phone number for privacy-safe display."""
        if len(self.value) >= 8:
            # Show country code and last 4 digits
            return self.value[:-6] + "****" + self.value[-2:]
        return "****"

    def is_mobile(self) -> bool:
        """
        Simple heuristic to check if this might be a mobile number.

        Note: This is a very basic implementation. Real applications should
        use proper phone number libraries for accurate mobile detection.
        """
        # This is just a placeholder implementation
        national = self.national_number

        # US mobile numbers often start with certain prefixes
        if self.country_code == "1" and len(national) == 10:
            area_code = national[:3]
            # Some common mobile area codes (this is not comprehensive)
            mobile_prefixes = {"201", "202", "203", "212", "213", "214", "215"}
            return area_code in mobile_prefixes

        return True  # Default to mobile for other countries

    @classmethod
    def from_string(cls, phone_str: str) -> "PhoneNumber":
        """Create PhoneNumber from string with validation."""
        return cls(value=phone_str)
