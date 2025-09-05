"""Provider ID value object with UUID generation and cross-group tracking."""

import hashlib
import re
import uuid
from typing import Any

from pydantic import BaseModel, Field, model_validator

from src.shared.exceptions import ProviderIDValidationError


class ProviderID(BaseModel):
    """
    Immutable provider identifier value object.

    Supports both UUID-based and composite key formats for provider identification.
    Enables cross-group provider tracking, deduplication, and analytics aggregation.
    Provides privacy-safe representations for logging and debugging.
    """

    model_config = {"frozen": True}

    value: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @model_validator(mode="before")
    @classmethod
    def validate_provider_data(cls, data: Any) -> Any:
        """Validate and normalize Provider ID format."""
        if not isinstance(data, dict):
            return data

        value = data.get("value")

        # Auto-generate UUID if no value provided, but only when
        # no explicit None is passed
        if "value" not in data:
            generated_uuid = str(uuid.uuid4())
            data["value"] = generated_uuid
            # Auto-generated UUID4 for provider
            return data

        if value is None or not value or not str(value).strip():
            # Empty value validation failed
            raise ProviderIDValidationError(
                "Provider ID cannot be empty",
                field="value",
            )

        cleaned_value = str(value).strip()
        cls._validate_provider_format(cleaned_value)

        data["value"] = cleaned_value
        # Provider ID validated successfully
        return data

    @classmethod
    def _validate_provider_format(cls, value: str) -> None:
        """Validate Provider ID format."""
        if len(value) < 5:
            raise ProviderIDValidationError("Provider ID too short", field="value")

        if len(value) > 255:
            raise ProviderIDValidationError("Provider ID too long", field="value")

        # Check if it's a valid UUID format
        if cls._is_uuid_format(value):
            # UUID regex already validates format, no need for additional check
            pass
        elif cls._is_composite_format(value):
            # Validate composite format structure
            if not re.match(r"^\w+:[^|]+(\|\w+:[^|]+)*$", value):
                raise ProviderIDValidationError(
                    "Invalid Provider ID format: malformed composite key",
                    field="value",
                )
        else:
            raise ProviderIDValidationError(
                "Invalid Provider ID format: must be UUID or composite key",
                field="value",
            )

    @classmethod
    def _is_uuid_format(cls, value: str) -> bool:
        """Check if value matches UUID format."""
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))

    @classmethod
    def _is_composite_format(cls, value: str) -> bool:
        """Check if value matches composite key format."""
        return "|" in value and ":" in value

    def __str__(self) -> str:
        """Return the provider ID value."""
        return self.value

    def __repr__(self) -> str:
        """Return string representation of ProviderID."""
        return f"ProviderID(value='{self.value}')"

    def __hash__(self) -> int:
        """Return hash based on value."""
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        """Compare provider IDs based on values."""
        if not isinstance(other, ProviderID):
            return False
        return self.value == other.value

    def masked(self) -> str:
        """
        Return masked provider ID for safe logging.

        Masks sensitive portions of the ID while keeping identifiable
        prefix and structure for debugging purposes.
        """
        if self.is_uuid_format():
            # For UUID: show first 6 chars, mask the rest
            return f"{self.value[:6]}****"
        if self.is_composite_format():
            # For composite: mask values but keep structure
            parts = []
            for part in str(self.value).split("|"):
                if ":" in part:
                    key, val = part.split(":", 1)
                    if len(val) <= 8:
                        masked_val = val[:4] + "****"
                    else:
                        # For longer values, show more characters (like phone numbers)
                        masked_val = val[:8] + "****"
                    parts.append(f"{key}:{masked_val}")
                else:
                    parts.append(part)
            return "|".join(parts)
        else:
            # Fallback: show first 6 chars
            return f"{self.value[:6]}****"

    def short_hash(self) -> str:
        """
        Return short hash for safe provider identification.

        Provides a unique 8-character identifier that can be used
        safely in logs and debugging without exposing the actual ID.
        """
        hash_object = hashlib.sha256(str(self.value).encode())
        return hash_object.hexdigest()[:8]

    def is_uuid_format(self) -> bool:
        """Check if provider ID is in UUID format."""
        return self._is_uuid_format(self.value)

    def is_composite_format(self) -> bool:
        """Check if provider ID is in composite key format."""
        return self._is_composite_format(self.value)

    def extract_components(self) -> dict[str, str]:
        """
        Extract components from composite format Provider ID.

        Returns dictionary of key-value pairs for composite format,
        or empty dictionary for UUID format.
        """
        if not self.is_composite_format():
            return {}

        components = {}
        for part in str(self.value).split("|"):
            if ":" in part:
                key, value = part.split(":", 1)
                components[key] = value

        return components
