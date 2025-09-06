"""Email value object for user identification and communication."""

import re
from typing import Any

from pydantic import BaseModel, field_validator

from src.shared.exceptions import ValidationException


class Email(BaseModel):
    """
    Email value object with validation and normalization.

    Demonstrates value object patterns:
    - Immutability (frozen=True)
    - Self-validation
    - Domain events on validation
    - Rich behavior methods
    """

    model_config = {"frozen": True}

    value: str

    @field_validator("value")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format and domain."""
        if not v or not isinstance(v, str):
            raise ValidationException("Email cannot be empty", field="email")

        # Normalize email
        email = v.strip().lower()

        # Basic email pattern validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValidationException("Invalid email format", field="email")

        # Check for common typos
        if email.endswith((".con", ".co")):
            raise ValidationException("Email domain appears to have a typo", field="email")

        # Length validation
        if len(email) > 254:  # RFC 5321 limit
            raise ValidationException("Email address too long", field="email")

        local_part = email.split("@")[0]
        if len(local_part) > 64:  # RFC 5321 limit
            raise ValidationException("Email local part too long", field="email")

        return email

    def __str__(self) -> str:
        """Return email string representation."""
        return self.value

    def __hash__(self) -> int:
        """Return hash for set/dict usage."""
        return hash(self.value)

    def __eq__(self, other: Any) -> bool:
        """Compare emails by normalized value."""
        if isinstance(other, Email):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other.lower().strip()
        return False

    @property
    def domain(self) -> str:
        """Extract domain from email address."""
        return self.value.split("@")[1]

    @property
    def local_part(self) -> str:
        """Extract local part from email address."""
        return self.value.split("@")[0]

    def is_business_email(self) -> bool:
        """Check if email appears to be a business email."""
        personal_domains = {
            "gmail.com",
            "yahoo.com",
            "hotmail.com",
            "outlook.com",
            "icloud.com",
            "aol.com",
            "live.com",
            "msn.com",
        }
        return self.domain not in personal_domains

    def mask_for_display(self) -> str:
        """Return masked email for privacy-safe display."""
        local, domain = self.value.split("@")
        if len(local) <= 2:
            masked_local = "*" * len(local)
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"

    @classmethod
    def from_string(cls, email_str: str) -> "Email":
        """Create Email from string with validation."""
        return cls(value=email_str)
