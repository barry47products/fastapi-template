"""User domain entity demonstrating clean domain patterns."""

from datetime import datetime, UTC
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from src.domain.events import DomainEventRegistry
from src.domain.events.user_events import (
    UserCreated,
    UserDeleted,
    UserEmailVerified,
    UserStatusChanged,
    UserUpdated,
)
from src.domain.value_objects.email import Email
from src.shared.exceptions import ValidationException


class UserStatus(str, Enum):
    """User status enumeration."""

    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(BaseModel):
    """
    User domain entity demonstrating clean domain model patterns.

    This sample entity shows:
    - Rich domain behavior
    - Business rule enforcement
    - Domain event publishing
    - Value object usage
    - Immutability with controlled mutations
    - Self-validation

    Replace this with your actual domain entities.
    """

    model_config = {"frozen": True}

    id: UUID = Field(default_factory=uuid4)
    email: Email
    name: str
    age: int
    status: UserStatus = UserStatus.PENDING
    email_verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_login_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate user name."""
        if not v or not isinstance(v, str):
            raise ValidationException("Name cannot be empty", field="name")

        name = v.strip()
        if len(name) < 2:
            raise ValidationException("Name must be at least 2 characters", field="name")

        if len(name) > 100:
            raise ValidationException("Name cannot exceed 100 characters", field="name")

        # Business rule: No numbers in names
        if any(char.isdigit() for char in name):
            raise ValidationException("Name cannot contain numbers", field="name")

        return name

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: int) -> int:
        """Validate user age with business rules."""
        if not isinstance(v, int):
            raise ValidationException("Age must be a number", field="age")

        # Business rule: Minimum age requirement
        if v < 13:
            raise ValidationException(
                "Users must be at least 13 years old due to privacy regulations", field="age"
            )

        # Business rule: Maximum reasonable age
        if v > 120:
            raise ValidationException("Please enter a valid age", field="age")

        return v

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: Email | str | dict[str, Any]) -> Email:
        """Validate email field is Email value object."""
        if isinstance(v, Email):
            return v
        elif isinstance(v, str):
            return Email(value=v)
        elif isinstance(v, dict) and "value" in v:
            return Email(value=v["value"])
        else:
            raise ValidationException("Invalid email format", field="email")

    def __str__(self) -> str:
        """Return user string representation."""
        return f"{self.name} ({self.email.value})"

    def __repr__(self) -> str:
        """Return detailed user representation."""
        return f"User(id={self.id}, name='{self.name}', email='{self.email.value}')"

    def __hash__(self) -> int:
        """Return hash based on user ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Compare users by ID."""
        if not isinstance(other, User):
            return False
        return self.id == other.id

    def activate(self) -> "User":
        """
        Activate user account.

        Business rule: Only pending or inactive users can be activated.
        """
        if self.status in [UserStatus.SUSPENDED, UserStatus.DELETED]:
            raise ValidationException(
                f"Cannot activate user with status {self.status.value}", field="status"
            )

        if self.status == UserStatus.ACTIVE:
            return self  # Already active

        new_user = self.model_copy(
            update={"status": UserStatus.ACTIVE, "updated_at": datetime.now(UTC)}
        )

        # Publish domain event
        DomainEventRegistry.publish(
            UserStatusChanged(
                user_id=str(self.id),
                previous_status=self.status.value,
                new_status=UserStatus.ACTIVE.value,
                status_change_reason="activation_requested",
            )
        )

        return new_user

    def suspend(self, reason: str = "admin_action") -> "User":
        """
        Suspend user account.

        Business rule: Only active users can be suspended.
        """
        if self.status != UserStatus.ACTIVE:
            raise ValidationException(
                f"Cannot suspend user with status {self.status.value}", field="status"
            )

        new_user = self.model_copy(
            update={"status": UserStatus.SUSPENDED, "updated_at": datetime.now(UTC)}
        )

        # Publish domain event
        DomainEventRegistry.publish(
            UserStatusChanged(
                user_id=str(self.id),
                previous_status=self.status.value,
                new_status=UserStatus.SUSPENDED.value,
                status_change_reason=reason,
            )
        )

        return new_user

    def verify_email(self) -> "User":
        """
        Verify user email address.

        Business rule: Can only verify unverified emails.
        """
        if self.email_verified:
            return self  # Already verified

        new_user = self.model_copy(update={"email_verified": True, "updated_at": datetime.now(UTC)})

        # Publish domain event
        DomainEventRegistry.publish(UserEmailVerified(user_id=str(self.id), email=self.email.value))

        return new_user

    def update_profile(self, name: str | None = None, age: int | None = None) -> "User":
        """
        Update user profile information.

        Returns new User instance with updated information.
        """
        updates = {"updated_at": datetime.now(UTC)}
        fields_updated = []
        previous_values = {}
        new_values = {}

        if name is not None and name != self.name:
            updates["name"] = name
            fields_updated.append("name")
            previous_values["name"] = self.name
            new_values["name"] = name

        if age is not None and age != self.age:
            updates["age"] = age
            fields_updated.append("age")
            previous_values["age"] = self.age
            new_values["age"] = age

        if not fields_updated:
            return self  # No changes

        new_user = self.model_copy(update=updates)

        # Publish domain event
        DomainEventRegistry.publish(
            UserUpdated(
                user_id=str(self.id),
                fields_updated=fields_updated,
                previous_values=previous_values,
                new_values=new_values,
            )
        )

        return new_user

    def record_login(self) -> "User":
        """Record user login timestamp."""
        return self.model_copy(
            update={"last_login_at": datetime.now(UTC), "updated_at": datetime.now(UTC)}
        )

    def soft_delete(self, reason: str = "user_requested") -> "User":
        """
        Soft delete user (mark as deleted but keep data).

        Business rule: Cannot delete already deleted users.
        """
        if self.status == UserStatus.DELETED:
            raise ValidationException("User is already deleted", field="status")

        new_user = self.model_copy(
            update={"status": UserStatus.DELETED, "updated_at": datetime.now(UTC)}
        )

        # Publish domain event
        DomainEventRegistry.publish(
            UserDeleted(user_id=str(self.id), user_email=self.email.value, deletion_reason=reason)
        )

        return new_user

    def can_login(self) -> bool:
        """Check if user can login based on business rules."""
        return self.status in [UserStatus.ACTIVE] and self.email_verified

    def is_adult(self) -> bool:
        """Check if user is considered an adult (18+)."""
        return self.age >= 18

    def days_since_creation(self) -> int:
        """Calculate days since user account creation."""
        return (datetime.now(UTC) - self.created_at).days

    def is_new_user(self, days_threshold: int = 30) -> bool:
        """Check if user is considered new (within threshold days)."""
        return self.days_since_creation() <= days_threshold

    def has_logged_in(self) -> bool:
        """Check if user has ever logged in."""
        return self.last_login_at is not None

    def add_metadata(self, key: str, value: Any) -> "User":
        """Add metadata to user profile."""
        new_metadata = dict(self.metadata)
        new_metadata[key] = value

        return self.model_copy(update={"metadata": new_metadata, "updated_at": datetime.now(UTC)})

    @classmethod
    def create_new(
        cls, email: str | Email, name: str, age: int, auto_verify_email: bool = False
    ) -> "User":
        """
        Factory method to create a new user with proper domain event publishing.

        This demonstrates the factory pattern for domain entities.
        """
        # Convert email to value object if needed
        if isinstance(email, str):
            email_vo = Email(value=email)
        else:
            email_vo = email

        # Create user
        user = cls(
            email=email_vo,
            name=name,
            age=age,
            email_verified=auto_verify_email,
            status=UserStatus.ACTIVE if auto_verify_email else UserStatus.PENDING,
        )

        # Publish domain event
        DomainEventRegistry.publish(
            UserCreated(user_id=str(user.id), user_email=email_vo.value, user_name=name)
        )

        return user
