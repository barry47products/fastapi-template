"""Endorsement domain model with business logic and relationships."""

# mypy: disable-error-code="call-arg"
# Note: MyPy false positive - event_type has init=False, set by __init_subclass__

from datetime import datetime, UTC
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from src.domain.events import (
    DomainEventRegistry,
    EndorsementConfidenceUpdated,
    EndorsementStatusChanged,
)
from src.domain.value_objects import EndorsementID, GroupID, PhoneNumber, ProviderID
from src.shared.exceptions import EndorsementValidationError


class EndorsementType(str, Enum):
    """
    Endorsement type classification.

    AUTOMATIC: Generated automatically when provider is mentioned multiple times
    MANUAL: Created explicitly by a satisfied customer after service delivery
    """

    AUTOMATIC = "AUTOMATIC"
    MANUAL = "MANUAL"

    def __str__(self) -> str:
        """Return the enum value as string."""
        return self.value


class EndorsementStatus(str, Enum):
    """
    Endorsement status classification.

    ACTIVE: Currently valid and counting towards provider endorsement totals
    REVOKED: No longer valid, excluded from endorsement counts
    """

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"

    def __str__(self) -> str:
        """Return the enum value as string."""
        return self.value


class Endorsement(BaseModel):
    """
    Immutable endorsement domain model.

    Represents a recommendation or validation of a service provider within a
    specific WhatsApp group context. Links providers to groups through
    endorsement relationships with full audit trail and business logic.
    """

    model_config = {"frozen": True}

    id: EndorsementID = Field(default_factory=EndorsementID)
    provider_id: ProviderID
    group_id: GroupID
    endorser_phone: PhoneNumber
    endorsement_type: EndorsementType
    message_context: str
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    status: EndorsementStatus = Field(default=EndorsementStatus.ACTIVE)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_message_id: str | None = Field(
        default=None,
        description="ID of the original request message this endorsement responds to",
    )
    response_delay_seconds: int | None = Field(
        default=None,
        description="Time delay in seconds between request and response",
    )
    attribution_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for request-response attribution",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_endorsement_data(cls, data: Any) -> Any:
        """Validate and normalize endorsement data."""
        if not isinstance(data, dict):
            return data

        cls._validate_message_context(data)
        cls._validate_confidence_score(data)
        cls._validate_created_at(data)
        cls._validate_attribution_fields(data)
        cls._set_default_confidence_score(data)

        return data

    @classmethod
    def _validate_message_context(cls, data: dict[str, Any]) -> None:
        """Validate message context field."""
        message_context = data.get("message_context", "")
        if not message_context or not str(message_context).strip():
            raise EndorsementValidationError(
                "Message context cannot be empty",
                field="message_context",
            )

        message_context = str(message_context).strip()
        if len(message_context) > 2000:
            raise EndorsementValidationError(
                "Message context too long",
                field="message_context",
            )
        data["message_context"] = message_context

    @classmethod
    def _validate_confidence_score(cls, data: dict[str, Any]) -> None:
        """Validate confidence score field."""
        confidence_score = data.get("confidence_score")
        if confidence_score is not None:
            if confidence_score < 0.0 or confidence_score > 1.0:
                raise EndorsementValidationError(
                    "Confidence score must be between 0.0 and 1.0",
                    field="confidence_score",
                )

    @classmethod
    def _validate_created_at(cls, data: dict[str, Any]) -> None:
        """Validate created_at field."""
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, datetime):
            if created_at > datetime.now(UTC):
                raise EndorsementValidationError(
                    "Created date cannot be in the future",
                    field="created_at",
                )

    @classmethod
    def _validate_attribution_fields(cls, data: dict[str, Any]) -> None:
        """Validate attribution-related fields."""
        attribution_confidence = data.get("attribution_confidence")
        if attribution_confidence is not None:
            if attribution_confidence < 0.0 or attribution_confidence > 1.0:
                raise EndorsementValidationError(
                    "Attribution confidence must be between 0.0 and 1.0",
                    field="attribution_confidence",
                )

        response_delay = data.get("response_delay_seconds")
        if response_delay is not None and response_delay < 0:
            raise EndorsementValidationError(
                "Response delay must be positive",
                field="response_delay_seconds",
            )

    @classmethod
    def _set_default_confidence_score(cls, data: dict[str, Any]) -> None:
        """Set default confidence score based on endorsement type."""
        # Only set default if confidence_score is not provided or is None
        if "confidence_score" not in data or data.get("confidence_score") is None:
            endorsement_type = data.get("endorsement_type")
            if endorsement_type == EndorsementType.AUTOMATIC:
                data["confidence_score"] = 0.8
            elif endorsement_type == EndorsementType.MANUAL:
                data["confidence_score"] = 1.0

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_field(
        cls,
        v: EndorsementID | dict[str, Any] | str,
    ) -> EndorsementID:
        """Validate id field is EndorsementID instance."""
        if not isinstance(v, EndorsementID):
            if isinstance(v, dict):
                return EndorsementID(**v)
            return EndorsementID(value=str(v))
        return v

    @field_validator("provider_id", mode="before")
    @classmethod
    def validate_provider_id_field(
        cls,
        v: ProviderID | dict[str, Any] | str,
    ) -> ProviderID:
        """Validate provider_id field is ProviderID instance."""
        if not isinstance(v, ProviderID):
            if isinstance(v, dict):
                return ProviderID(**v)
            return ProviderID(value=str(v))
        return v

    @field_validator("group_id", mode="before")
    @classmethod
    def validate_group_id_field(cls, v: GroupID | dict[str, Any] | str) -> GroupID:
        """Validate group_id field is GroupID instance."""
        if not isinstance(v, GroupID):
            if isinstance(v, dict):
                return GroupID(**v)
            return GroupID(value=str(v))
        return v

    @field_validator("endorser_phone", mode="before")
    @classmethod
    def validate_endorser_phone_field(
        cls,
        v: PhoneNumber | dict[str, Any] | str,
    ) -> PhoneNumber:
        """Validate endorser_phone field is PhoneNumber instance."""
        if not isinstance(v, PhoneNumber):
            if isinstance(v, dict):
                return PhoneNumber(**v)
            return PhoneNumber(value=str(v))
        return v

    def __str__(self) -> str:
        """Return string representation of Endorsement."""
        return (
            f"{self.endorsement_type} endorsement by {self.endorser_phone.normalized} "
            f"in group {self.group_id.short_hash()}"
        )

    def __repr__(self) -> str:
        """Return detailed string representation of Endorsement."""
        return (
            f"Endorsement(id='{str(self.id)}', provider_id='{str(self.provider_id)}', "
            f"type='{self.endorsement_type}')"
        )

    def __hash__(self) -> int:
        """Return hash based on endorsement ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Compare endorsements based on ID."""
        if not isinstance(other, Endorsement):
            return False
        return self.id == other.id

    def revoke(self) -> "Endorsement":
        """Return new Endorsement with status set to REVOKED."""
        # Publish domain event for endorsement revocation
        DomainEventRegistry.publish(
            EndorsementStatusChanged(
                endorsement_id=str(self.id.short_hash()),
                provider_id=str(self.provider_id.short_hash()),
                operation="revoke",
                endorsement_type=self.endorsement_type.value,
            ),
        )
        return self.model_copy(update={"status": EndorsementStatus.REVOKED})

    def restore(self) -> "Endorsement":
        """Return new Endorsement with status set to ACTIVE."""
        # Publish domain event for endorsement restoration
        DomainEventRegistry.publish(
            EndorsementStatusChanged(
                endorsement_id=str(self.id.short_hash()),
                provider_id=str(self.provider_id.short_hash()),
                operation="restore",
                endorsement_type=self.endorsement_type.value,
            ),
        )
        return self.model_copy(update={"status": EndorsementStatus.ACTIVE})

    def is_active(self) -> bool:
        """Check if endorsement is currently active."""
        return self.status == EndorsementStatus.ACTIVE

    def is_automatic(self) -> bool:
        """Check if endorsement was created automatically."""
        return self.endorsement_type == EndorsementType.AUTOMATIC

    def update_confidence_score(self, new_score: float) -> "Endorsement":
        """Return new Endorsement with updated confidence score."""
        # Publish domain event for confidence score update
        DomainEventRegistry.publish(
            EndorsementConfidenceUpdated(
                endorsement_id=str(self.id.short_hash()),
                provider_id=str(self.provider_id.short_hash()),
                old_score=self.confidence_score,
                new_score=new_score,
            ),
        )
        return self.model_copy(update={"confidence_score": new_score})

    def has_request_context(self) -> bool:
        """Check if this endorsement has request-response context attribution."""
        return self.request_message_id is not None and self.attribution_confidence > 0.0

    def is_high_confidence_attribution(self) -> bool:
        """Check if this endorsement has high confidence context attribution."""
        return self.attribution_confidence >= 0.7

    def to_postgres_data(self) -> dict[str, Any]:
        """Convert endorsement to PostgreSQL row data format."""
        return {
            "id": str(self.id),
            "provider_id": str(self.provider_id),
            "group_id": str(self.group_id),
            "endorser_phone": self.endorser_phone.normalized,
            "endorsement_type": str(self.endorsement_type),
            "message_context": self.message_context,
            "confidence_score": self.confidence_score,
            "status": str(self.status),
            "created_at": self.created_at,
            "request_message_id": self.request_message_id,
            "response_delay_seconds": self.response_delay_seconds,
            "attribution_confidence": self.attribution_confidence,
        }

    @classmethod
    def from_postgres_data(cls, data: dict[str, Any]) -> "Endorsement":
        """Create Endorsement from PostgreSQL row data."""
        # Parse created_at from string if needed
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        return cls(
            id=EndorsementID(value=data["id"]),
            provider_id=ProviderID(value=data["provider_id"]),
            group_id=GroupID(value=data["group_id"]),
            endorser_phone=PhoneNumber(value=data["endorser_phone"]),
            endorsement_type=EndorsementType(data["endorsement_type"]),
            message_context=data["message_context"],
            confidence_score=data["confidence_score"],
            status=EndorsementStatus(data["status"]),
            created_at=created_at or datetime.now(UTC),
            request_message_id=data.get("request_message_id"),
            response_delay_seconds=data.get("response_delay_seconds"),
            attribution_confidence=data.get("attribution_confidence", 0.0),
        )
