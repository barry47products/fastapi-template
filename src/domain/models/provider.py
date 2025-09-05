"""Provider domain model with flexible tag structure and business logic."""

# mypy: disable-error-code="call-arg"
# Note: MyPy false positive - event_type has init=False, set by __init_subclass__

import json
from datetime import datetime, UTC
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from src.domain.events import (
    DomainEventRegistry,
    ProviderEndorsementDecremented,
    ProviderEndorsementIncremented,
    ProviderTagAdded,
    ProviderTagRemoved,
)
from src.domain.value_objects import PhoneNumber, ProviderID
from src.shared.exceptions import ProviderValidationError


class Provider(BaseModel):
    """
    Immutable provider domain model.

    Core business entity representing service providers with flexible tagging
    system for categorization, specialization tracking, and revenue generation.

    Supports PostgreSQL JSONB integration for dynamic tag queries and
    cross-group provider analytics.
    """

    model_config = {"frozen": True}

    id: ProviderID = Field(default_factory=ProviderID)
    name: str
    phone: PhoneNumber
    category: str
    endorsement_count: int = Field(default=0, ge=0)
    tags: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="before")
    @classmethod
    def validate_provider_data(cls, data: Any) -> Any:
        """Validate and normalize provider data."""
        if not isinstance(data, dict):
            return data

        cls._validate_name(data)
        cls._validate_category(data)
        cls._validate_endorsement_count(data)
        cls._validate_created_at(data)
        cls._validate_tags(data)

        return data

    @classmethod
    def _validate_name(cls, data: dict[str, Any]) -> None:
        """Validate and normalize name field."""
        name = data.get("name", "")
        if not name or not str(name).strip():
            raise ProviderValidationError("Name cannot be empty", field="name")

        name = str(name).strip()
        if len(name) < 3:
            raise ProviderValidationError("Name too short", field="name")
        if len(name) > 100:
            raise ProviderValidationError("Name too long", field="name")
        data["name"] = name

    @classmethod
    def _validate_category(cls, data: dict[str, Any]) -> None:
        """Validate and normalize category field."""
        category = data.get("category", "")
        if not category or not str(category).strip():
            raise ProviderValidationError("Category cannot be empty", field="category")

        category = str(category).strip()
        if len(category) > 50:
            raise ProviderValidationError("Category too long", field="category")
        data["category"] = category

    @classmethod
    def _validate_endorsement_count(cls, data: dict[str, Any]) -> None:
        """Validate endorsement_count field."""
        endorsement_count = data.get("endorsement_count", 0)
        if endorsement_count < 0:
            raise ProviderValidationError(
                "Endorsement count cannot be negative",
                field="endorsement_count",
            )

    @classmethod
    def _validate_created_at(cls, data: dict[str, Any]) -> None:
        """Validate created_at field."""
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, datetime):
            if created_at > datetime.now(UTC):
                raise ProviderValidationError(
                    "Created date cannot be in the future",
                    field="created_at",
                )

    @classmethod
    def _validate_tags(cls, data: dict[str, Any]) -> None:
        """Validate tags structure size."""
        tags = data.get("tags", {})
        if tags:
            tags_json = json.dumps(tags)
            if len(tags_json) > 10000:  # 10KB limit for JSONB
                raise ProviderValidationError("Tags structure too large", field="tags")

    @field_validator("phone")
    @classmethod
    def validate_phone_field(
        cls,
        v: PhoneNumber | dict[str, Any] | str,
    ) -> PhoneNumber:
        """Validate phone field is PhoneNumber instance."""
        if not isinstance(v, PhoneNumber):
            if isinstance(v, dict):
                return PhoneNumber(**v)
            return PhoneNumber(value=str(v))
        return v

    @field_validator("id")
    @classmethod
    def validate_id_field(cls, v: ProviderID | dict[str, Any] | str) -> ProviderID:
        """Validate id field is ProviderID instance."""
        if not isinstance(v, ProviderID):
            if isinstance(v, dict):
                return ProviderID(**v)
            return ProviderID(value=str(v))
        return v

    def __str__(self) -> str:
        """Return string representation of Provider."""
        return f"{self.name} ({self.category}) - {self.phone.normalized}"

    def __repr__(self) -> str:
        """Return detailed string representation of Provider."""
        return f"Provider(id='{str(self.id)}', name='{self.name}', category='{self.category}')"

    def __hash__(self) -> int:
        """Return hash based on provider ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Compare providers based on ID."""
        if not isinstance(other, Provider):
            return False
        return self.id == other.id

    def increment_endorsement_count(self) -> "Provider":
        """Return new Provider with incremented endorsement count."""
        new_count = self.endorsement_count + 1
        # Publish domain event for endorsement increment
        DomainEventRegistry.publish(
            ProviderEndorsementIncremented(
                provider_id=str(self.id.short_hash()),
                provider_category=self.category,
                new_endorsement_count=new_count,
            ),
        )
        return self.model_copy(update={"endorsement_count": new_count})

    def decrement_endorsement_count(self) -> "Provider":
        """Return new Provider with decremented endorsement count (minimum 0)."""
        new_count = max(0, self.endorsement_count - 1)
        # Publish domain event for endorsement decrement
        DomainEventRegistry.publish(
            ProviderEndorsementDecremented(
                provider_id=str(self.id.short_hash()),
                provider_category=self.category,
                new_endorsement_count=new_count,
            ),
        )
        return self.model_copy(update={"endorsement_count": new_count})

    def update_tags(self, new_tags: dict[str, Any]) -> "Provider":
        """Return new Provider with updated tags."""
        return self.model_copy(update={"tags": new_tags})

    def add_tag_category(
        self,
        category: str,
        value: str | int | float | bool | list[Any] | dict[str, Any],
    ) -> "Provider":
        """Return new Provider with added tag category."""
        new_tags = dict(self.tags)
        new_tags[category] = value
        # Publish domain event for tag addition
        DomainEventRegistry.publish(
            ProviderTagAdded(
                provider_id=str(self.id.short_hash()),
                tag_category=category,
                tag_value=str(value),
            ),
        )
        return self.model_copy(update={"tags": new_tags})

    def remove_tag_category(self, category: str) -> "Provider":
        """Return new Provider with removed tag category."""
        new_tags = dict(self.tags)
        removed_value = new_tags.pop(category, None)
        if removed_value is not None:
            # Publish domain event for tag removal
            DomainEventRegistry.publish(
                ProviderTagRemoved(
                    provider_id=str(self.id.short_hash()),
                    tag_category=category,
                ),
            )
        return self.model_copy(update={"tags": new_tags})

    def has_tag_category(self, category: str) -> bool:
        """Check if provider has specific tag category."""
        return category in self.tags

    def has_tag_value(self, category: str, value: str | int | float | bool) -> bool:
        """Check if provider has specific value in tag category."""
        if category not in self.tags:
            return False

        category_value = self.tags[category]
        if isinstance(category_value, list):
            return value in category_value

        return False

    def to_postgres_tags_format(self) -> str:
        """Convert tags to PostgreSQL JSONB format string."""
        return json.dumps(self.tags)

    @classmethod
    def from_postgres_data(cls, data: dict[str, Any]) -> "Provider":
        """Create Provider from PostgreSQL row data."""
        # Parse tags from JSON string
        tags_str = data.get("tags")
        if tags_str and isinstance(tags_str, str):
            try:
                tags = json.loads(tags_str)
            except json.JSONDecodeError:
                tags = {}
        else:
            tags = {}

        # Parse created_at from string if needed
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        return cls(
            id=ProviderID(value=data["id"]),
            name=data["name"],
            phone=PhoneNumber(value=data["phone"]),
            category=data["category"],
            endorsement_count=data.get("endorsement_count", 0),
            tags=tags,
            created_at=created_at or datetime.now(UTC),
        )
