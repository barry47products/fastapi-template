"""Endorsement ID value object with UUID generation and privacy features."""

import hashlib
import re
import uuid
from typing import Any

from pydantic import BaseModel, Field, model_validator

from src.shared.exceptions import EndorsementValidationError


class EndorsementID(BaseModel):
    """
    Immutable endorsement identifier value object.

    Automatically generates UUID4-based identifiers for endorsements.
    Provides privacy-safe representations for logging and debugging.
    """

    model_config = {"frozen": True}

    value: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @model_validator(mode="before")
    @classmethod
    def validate_endorsement_data(cls, data: Any) -> Any:
        """Validate and normalize Endorsement ID format."""
        if not isinstance(data, dict):
            return data

        value = data.get("value")

        # Auto-generate UUID if no value provided, but only when
        # no explicit None is passed
        if "value" not in data:
            generated_uuid = str(uuid.uuid4())
            data["value"] = generated_uuid
            # Auto-generated UUID4 for endorsement
            return data

        if value is None or not value or not str(value).strip():
            # Empty value validation failed
            raise EndorsementValidationError(
                "Endorsement ID cannot be empty",
                field="value",
            )

        cleaned_value = str(value).strip()
        cls._validate_endorsement_format(cleaned_value)

        data["value"] = cleaned_value
        # Endorsement ID validated successfully
        return data

    @classmethod
    def _validate_endorsement_format(cls, value: str) -> None:
        """Validate Endorsement ID format."""
        if len(value) < 5:
            raise EndorsementValidationError("Endorsement ID too short", field="value")

        if len(value) > 255:
            raise EndorsementValidationError("Endorsement ID too long", field="value")

        # Check if it's a valid UUID format
        if not cls._is_uuid_format(value):
            raise EndorsementValidationError(
                "Invalid Endorsement ID format: must be UUID",
                field="value",
            )

    @classmethod
    def _is_uuid_format(cls, value: str) -> bool:
        """Check if value matches UUID format."""
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))

    def __str__(self) -> str:
        """Return the endorsement ID value."""
        return self.value

    def __repr__(self) -> str:
        """Return string representation of EndorsementID."""
        return f"EndorsementID(value='{self.value}')"

    def __hash__(self) -> int:
        """Return hash based on value."""
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        """Compare endorsement IDs based on values."""
        if not isinstance(other, EndorsementID):
            return False
        return self.value == other.value

    def masked(self) -> str:
        """
        Return masked endorsement ID for safe logging.

        Shows first 6 characters of UUID followed by asterisks
        to protect privacy while keeping identifiable prefix for debugging.
        """
        return f"{self.value[:6]}****"

    def short_hash(self) -> str:
        """
        Return short hash for safe endorsement identification.

        Provides a unique 8-character identifier that can be used
        safely in logs and debugging without exposing the actual ID.
        """
        hash_object = hashlib.sha256(str(self.value).encode())
        return hash_object.hexdigest()[:8]
