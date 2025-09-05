"""WhatsApp Group ID value object with validation and privacy features."""

import hashlib
import re
from typing import Any

from pydantic import BaseModel, model_validator

from src.shared.exceptions import GroupIDValidationError

# WhatsApp group domain constant
WHATSAPP_GROUP_DOMAIN = "@g.us"


class GroupID(BaseModel):
    """
    Immutable WhatsApp group identifier value object.

    Validates WhatsApp group ID format for GREEN-API compatibility,
    provides privacy-safe representations for logging, and normalizes
    group identifiers to standard @g.us format.
    """

    model_config = {"frozen": True}

    value: str

    @model_validator(mode="before")
    @classmethod
    def validate_group_data(cls, data: Any) -> Any:
        """Validate and normalize WhatsApp group ID format."""
        if not isinstance(data, dict):
            return data

        value = data.get("value", "")

        if not value or not str(value).strip():
            # Empty value validation failed
            raise GroupIDValidationError("Group ID cannot be empty", field="value")

        cleaned_value = str(value).strip()
        normalized_value = cls._normalize_group_id(cleaned_value)
        cls._validate_group_format(normalized_value)

        data["value"] = normalized_value
        # Group ID validated successfully
        return data

    @classmethod
    def _normalize_group_id(cls, value: str) -> str:
        """Normalize group ID to standard @g.us format."""
        # Replace various WhatsApp domains with standard @g.us
        patterns = [
            (r"@c\.us$", WHATSAPP_GROUP_DOMAIN),
            (r"@s\.whatsapp\.net$", WHATSAPP_GROUP_DOMAIN),
        ]

        normalized = value
        for pattern, replacement in patterns:
            normalized = re.sub(pattern, replacement, normalized)

        return normalized

    @classmethod
    def _validate_group_format(cls, value: str) -> None:
        """Validate WhatsApp group ID format."""
        if "@" not in value:
            raise GroupIDValidationError(
                "Invalid WhatsApp group ID format: missing @ symbol",
                field="value",
            )

        if not value.endswith(WHATSAPP_GROUP_DOMAIN):
            raise GroupIDValidationError(
                "Invalid WhatsApp group ID format: invalid domain",
                field="value",
            )

        # Extract the local part (before @)
        local_part = value.split("@")[0]

        if len(local_part) < 10:
            raise GroupIDValidationError("Group ID too short", field="value")

        if len(value) > 50:
            raise GroupIDValidationError("Group ID too long", field="value")

        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not re.match(r"^[a-zA-Z0-9\-_]+$", local_part):
            raise GroupIDValidationError(
                "Invalid characters in group ID",
                field="value",
            )

    def __str__(self) -> str:
        """Return the normalized group ID value."""
        return self.value

    def __repr__(self) -> str:
        """Return string representation of GroupID."""
        return f"GroupID(value='{self.value}')"

    def __hash__(self) -> int:
        """Return hash based on normalized value."""
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        """Compare group IDs based on normalized values."""
        if not isinstance(other, GroupID):
            return False
        return self.value == other.value

    def masked(self) -> str:
        """
        Return masked group ID for safe logging.

        Masks the middle portion of the group ID to protect privacy
        while keeping identifiable prefix and suffix for debugging.
        """
        if "@" not in self.value:
            return self.value

        local_part, domain = self.value.split("@", 1)

        if len(local_part) <= 8:
            # For short IDs, mask all but first 4 characters
            masked_local = local_part[:4] + "*" * (len(local_part) - 4)
        else:
            # For longer IDs, show first 8 and mask the rest
            masked_local = local_part[:8] + "*" * (len(local_part) - 8)

        return f"{masked_local}@{domain}"

    def short_hash(self) -> str:
        """
        Return short hash for safe group identification.

        Provides a unique 8-character identifier that can be used
        safely in logs and debugging without exposing the actual group ID.
        """
        hash_object = hashlib.sha256(self.value.encode())
        return hash_object.hexdigest()[:8]

    def format_for_green_api(self) -> str:
        """Format group ID for GREEN-API requests."""
        return self.value
