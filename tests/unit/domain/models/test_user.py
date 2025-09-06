"""Behavioural tests for User domain entity.

These tests focus on user behavior in real-world scenarios rather than
individual method testing. They validate business rules, workflows,
and domain event publishing patterns.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.domain.events.user_events import (
    UserCreated,
    UserDeleted,
    UserEmailVerified,
    UserStatusChanged,
    UserUpdated,
)
from src.domain.models.user import User, UserStatus
from src.domain.value_objects.email import Email
from src.shared.exceptions import ValidationException


class TestUserRegistrationWorkflow:
    """Test complete user registration workflows."""

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_new_user_registration_creates_pending_account(self, mock_publish: MagicMock) -> None:
        """New user registration creates account in pending status with proper event."""
        user = User.create_new(email="john@example.com", name="John Doe", age=25)

        assert user.status == UserStatus.PENDING
        assert not user.email_verified
        assert user.email.value == "john@example.com"
        assert user.name == "John Doe"
        assert user.age == 25
        assert isinstance(user.id, UUID)

        # Verify domain event was published
        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert isinstance(event, UserCreated)
        assert event.user_email == "john@example.com"
        assert event.user_name == "John Doe"
        assert event.user_id == str(user.id)

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_auto_verified_registration_creates_active_account(
        self, mock_publish: MagicMock
    ) -> None:
        """Registration with auto-verification creates active account."""
        user = User.create_new(
            email="admin@company.com", name="Admin User", age=30, auto_verify_email=True
        )

        assert user.status == UserStatus.ACTIVE
        assert user.email_verified

        # Should still publish creation event
        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert isinstance(event, UserCreated)

    def test_registration_enforces_business_rules(self) -> None:
        """Registration validates all business rules for new users."""
        # Test age restriction
        with pytest.raises(ValidationException) as exc_info:
            User.create_new(email="child@example.com", name="Child", age=10)
        assert "Users must be at least 13 years old" in str(exc_info.value)

        # Test name validation
        with pytest.raises(ValidationException) as exc_info:
            User.create_new(email="test@example.com", name="A", age=20)
        assert "Name must be at least 2 characters" in str(exc_info.value)

        # Test name with numbers
        with pytest.raises(ValidationException) as exc_info:
            User.create_new(email="test@example.com", name="John123", age=20)
        assert "Name cannot contain numbers" in str(exc_info.value)

    def test_registration_accepts_email_objects(self) -> None:
        """Registration accepts both string emails and Email value objects."""
        email_vo = Email(value="test@example.com")
        user = User.create_new(email=email_vo, name="Test User", age=25)

        assert user.email == email_vo
        assert user.email.value == "test@example.com"


class TestEmailVerificationWorkflow:
    """Test email verification behavior and workflows."""

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_email_verification_workflow(self, mock_publish: MagicMock) -> None:
        """Complete email verification workflow publishes events correctly."""
        # Create pending user
        user = User.create_new(email="verify@example.com", name="Verify User", age=25)
        mock_publish.reset_mock()

        # Verify email
        verified_user = user.verify_email()

        assert verified_user.email_verified
        assert verified_user.updated_at > user.updated_at

        # Verify domain event was published
        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert isinstance(event, UserEmailVerified)
        assert event.user_id == str(user.id)
        assert event.email == "verify@example.com"

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_already_verified_email_skips_verification(self, mock_publish: MagicMock) -> None:
        """Attempting to verify already verified email returns same user."""
        user = User.create_new(
            email="already@verified.com", name="Already Verified", age=30, auto_verify_email=True
        )
        mock_publish.reset_mock()

        # Attempt verification again
        same_user = user.verify_email()

        assert same_user is user  # Same object returned
        mock_publish.assert_not_called()  # No event published


class TestUserActivationWorkflow:
    """Test user activation behavior across different states."""

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_pending_user_activation_workflow(self, mock_publish: MagicMock) -> None:
        """Pending user can be activated with proper status change event."""
        user = User.create_new(email="pending@example.com", name="Pending User", age=25)
        mock_publish.reset_mock()

        activated_user = user.activate()

        assert activated_user.status == UserStatus.ACTIVE
        assert activated_user.updated_at > user.updated_at

        # Verify status change event
        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert isinstance(event, UserStatusChanged)
        assert event.user_id == str(user.id)
        assert event.previous_status == UserStatus.PENDING.value
        assert event.new_status == UserStatus.ACTIVE.value
        assert event.status_change_reason == "activation_requested"

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_inactive_user_can_be_reactivated(self, mock_publish: MagicMock) -> None:
        """Inactive user can be reactivated."""
        user = User(
            email=Email(value="inactive@example.com"),
            name="Inactive User",
            age=25,
            status=UserStatus.INACTIVE,
        )

        activated_user = user.activate()

        assert activated_user.status == UserStatus.ACTIVE
        mock_publish.assert_called_once()

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_active_user_activation_returns_same_user(self, mock_publish: MagicMock) -> None:
        """Activating already active user returns same instance."""
        user = User.create_new(
            email="active@example.com", name="Active User", age=25, auto_verify_email=True
        )
        mock_publish.reset_mock()

        same_user = user.activate()

        assert same_user is user
        mock_publish.assert_not_called()

    def test_suspended_user_cannot_be_activated(self) -> None:
        """Suspended users cannot be activated directly."""
        user = User(
            email=Email(value="suspended@example.com"),
            name="Suspended User",
            age=25,
            status=UserStatus.SUSPENDED,
        )

        with pytest.raises(ValidationException) as exc_info:
            user.activate()
        assert "Cannot activate user with status suspended" in str(exc_info.value)

    def test_deleted_user_cannot_be_activated(self) -> None:
        """Deleted users cannot be activated."""
        user = User(
            email=Email(value="deleted@example.com"),
            name="Deleted User",
            age=25,
            status=UserStatus.DELETED,
        )

        with pytest.raises(ValidationException) as exc_info:
            user.activate()
        assert "Cannot activate user with status deleted" in str(exc_info.value)


class TestUserSuspensionWorkflow:
    """Test user suspension behavior and business rules."""

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_active_user_suspension_workflow(self, mock_publish: MagicMock) -> None:
        """Active user can be suspended with proper event publishing."""
        user = User.create_new(
            email="active@example.com", name="Active User", age=25, auto_verify_email=True
        )
        mock_publish.reset_mock()

        suspended_user = user.suspend(reason="policy_violation")

        assert suspended_user.status == UserStatus.SUSPENDED
        assert suspended_user.updated_at > user.updated_at

        # Verify status change event
        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert isinstance(event, UserStatusChanged)
        assert event.user_id == str(user.id)
        assert event.previous_status == UserStatus.ACTIVE.value
        assert event.new_status == UserStatus.SUSPENDED.value
        assert event.status_change_reason == "policy_violation"

    def test_non_active_user_cannot_be_suspended(self) -> None:
        """Only active users can be suspended."""
        pending_user = User.create_new(email="pending@example.com", name="Pending", age=25)

        with pytest.raises(ValidationException) as exc_info:
            pending_user.suspend()
        assert "Cannot suspend user with status pending" in str(exc_info.value)


class TestProfileUpdateWorkflow:
    """Test profile update behavior with change tracking."""

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_profile_update_with_changes_publishes_event(self, mock_publish: MagicMock) -> None:
        """Profile updates with changes publish proper domain events."""
        user = User.create_new(email="update@example.com", name="Original Name", age=25)
        mock_publish.reset_mock()

        updated_user = user.update_profile(name="New Name", age=30)

        assert updated_user.name == "New Name"
        assert updated_user.age == 30
        assert updated_user.updated_at > user.updated_at

        # Verify update event with change tracking
        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert isinstance(event, UserUpdated)
        assert event.user_id == str(user.id)
        assert set(event.fields_updated) == {"name", "age"}
        assert event.previous_values == {"name": "Original Name", "age": 25}
        assert event.new_values == {"name": "New Name", "age": 30}

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_profile_update_with_no_changes_skips_event(self, mock_publish: MagicMock) -> None:
        """Profile updates with no actual changes return same user."""
        user = User.create_new(email="nochange@example.com", name="Same Name", age=25)
        mock_publish.reset_mock()

        same_user = user.update_profile(name="Same Name", age=25)

        assert same_user is user
        mock_publish.assert_not_called()

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_partial_profile_updates_track_only_changed_fields(
        self, mock_publish: MagicMock
    ) -> None:
        """Partial updates only track fields that actually changed."""
        user = User.create_new(email="partial@example.com", name="Keep Name", age=25)
        mock_publish.reset_mock()

        updated_user = user.update_profile(age=30)  # Only update age

        assert updated_user.name == "Keep Name"  # Unchanged
        assert updated_user.age == 30  # Changed

        event = mock_publish.call_args[0][0]
        assert isinstance(event, UserUpdated)
        assert event.fields_updated == ["age"]
        assert event.previous_values == {"age": 25}
        assert event.new_values == {"age": 30}


class TestUserDeletionWorkflow:
    """Test soft deletion behavior and constraints."""

    @patch("src.domain.events.DomainEventRegistry.publish")
    def test_user_soft_deletion_workflow(self, mock_publish: MagicMock) -> None:
        """User soft deletion marks status and publishes deletion event."""
        user = User.create_new(
            email="delete@example.com", name="Delete User", age=25, auto_verify_email=True
        )
        mock_publish.reset_mock()

        deleted_user = user.soft_delete(reason="user_requested")

        assert deleted_user.status == UserStatus.DELETED
        assert deleted_user.updated_at > user.updated_at

        # Verify deletion event
        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert isinstance(event, UserDeleted)
        assert event.user_id == str(user.id)
        assert event.user_email == "delete@example.com"
        assert event.deletion_reason == "user_requested"

    def test_already_deleted_user_cannot_be_deleted_again(self) -> None:
        """Cannot delete already deleted users."""
        user = User(
            email=Email(value="deleted@example.com"),
            name="Already Deleted",
            age=25,
            status=UserStatus.DELETED,
        )

        with pytest.raises(ValidationException) as exc_info:
            user.soft_delete()
        assert "User is already deleted" in str(exc_info.value)


class TestUserLoginBehavior:
    """Test login-related business logic and constraints."""

    def test_active_verified_user_can_login(self) -> None:
        """Active users with verified emails can login."""
        user = User.create_new(
            email="canlogin@example.com", name="Can Login", age=25, auto_verify_email=True
        )

        assert user.can_login()
        assert user.status == UserStatus.ACTIVE
        assert user.email_verified

    def test_pending_user_cannot_login(self) -> None:
        """Pending users cannot login even if email verified."""
        user = User.create_new(email="pending@example.com", name="Pending", age=25)
        verified_user = user.verify_email()

        assert not verified_user.can_login()
        assert verified_user.status == UserStatus.PENDING

    def test_active_unverified_user_cannot_login(self) -> None:
        """Active users with unverified emails cannot login."""
        user = User.create_new(email="unverified@example.com", name="Unverified", age=25)
        activated_user = user.activate()

        assert not activated_user.can_login()
        assert not activated_user.email_verified

    def test_login_tracking_updates_timestamp(self) -> None:
        """Recording login updates last login timestamp."""
        user = User.create_new(
            email="tracklogin@example.com", name="Track Login", age=25, auto_verify_email=True
        )

        assert not user.has_logged_in()
        assert user.last_login_at is None

        logged_in_user = user.record_login()

        assert logged_in_user.has_logged_in()
        assert logged_in_user.last_login_at is not None
        assert logged_in_user.updated_at > user.updated_at


class TestUserAgeBusinessLogic:
    """Test age-related business logic and calculations."""

    def test_adult_user_classification(self) -> None:
        """Users 18 and over are classified as adults."""
        adult = User.create_new(email="adult@example.com", name="Adult", age=18)
        older_adult = User.create_new(email="older@example.com", name="Older", age=30)
        minor = User.create_new(email="minor@example.com", name="Minor", age=16)

        assert adult.is_adult()
        assert older_adult.is_adult()
        assert not minor.is_adult()

    @patch("src.domain.models.user.datetime")
    def test_new_user_classification(self, mock_datetime: MagicMock) -> None:
        """New users are classified based on creation date threshold."""
        # Mock current time to be 20 days after creation
        creation_time = datetime(2024, 1, 1, tzinfo=UTC)
        current_time = datetime(2024, 1, 21, tzinfo=UTC)

        mock_datetime.now.return_value = current_time

        user = User(
            email=Email(value="newuser@example.com"),
            name="New User",
            age=25,
            created_at=creation_time,
        )

        assert user.days_since_creation() == 20
        assert user.is_new_user(days_threshold=30)  # Within 30 days
        assert not user.is_new_user(days_threshold=15)  # Outside 15 days


class TestUserMetadataManagement:
    """Test user metadata functionality."""

    def test_metadata_addition_creates_new_user(self) -> None:
        """Adding metadata creates new user instance with updated metadata."""
        user = User.create_new(email="meta@example.com", name="Meta User", age=25)

        updated_user = user.add_metadata("preference", "dark_mode")

        assert updated_user.metadata == {"preference": "dark_mode"}
        assert user.metadata == {}  # Original unchanged
        assert updated_user.updated_at > user.updated_at

    def test_metadata_preserves_existing_values(self) -> None:
        """Adding metadata preserves existing metadata values."""
        user = User(
            email=Email(value="existing@example.com"),
            name="Existing Meta",
            age=25,
            metadata={"existing_key": "existing_value"},
        )

        updated_user = user.add_metadata("new_key", "new_value")

        expected_metadata = {"existing_key": "existing_value", "new_key": "new_value"}
        assert updated_user.metadata == expected_metadata


class TestUserEquality:
    """Test user equality and identity behavior."""

    def test_users_equal_by_id(self) -> None:
        """Users are equal if they have the same ID."""
        user_id = UUID("12345678-1234-5678-1234-123456789012")

        user1 = User(id=user_id, email=Email(value="test1@example.com"), name="User One", age=25)

        user2 = User(
            id=user_id,
            email=Email(value="test2@example.com"),  # Different email
            name="User Two",  # Different name
            age=30,  # Different age
        )

        assert user1 == user2
        assert hash(user1) == hash(user2)

    def test_users_not_equal_with_different_ids(self) -> None:
        """Users with different IDs are not equal."""
        user1 = User.create_new(email="user1@example.com", name="User One", age=25)
        user2 = User.create_new(email="user2@example.com", name="User Two", age=25)

        assert user1 != user2
        assert hash(user1) != hash(user2)

    def test_user_string_representations(self) -> None:
        """User string representations show key information."""
        user = User.create_new(email="repr@example.com", name="Repr User", age=25)

        assert str(user) == "Repr User (repr@example.com)"
        assert "User(id=" in repr(user)
        assert "name='Repr User'" in repr(user)
        assert "email='repr@example.com'" in repr(user)


class TestUserImmutability:
    """Test immutability constraints of User entity."""

    def test_user_is_frozen_model(self) -> None:
        """User model is immutable - direct field modification should fail."""
        user = User.create_new(email="frozen@example.com", name="Frozen", age=25)

        with pytest.raises(ValidationError):
            user.name = "Changed Name"  # type: ignore[misc]

    def test_mutating_methods_return_new_instances(self) -> None:
        """All mutating methods return new User instances."""
        original_user = User.create_new(email="original@example.com", name="Original", age=25)

        activated = original_user.activate()
        verified = original_user.verify_email()
        updated = original_user.update_profile(name="Updated")
        with_login = original_user.record_login()
        with_metadata = original_user.add_metadata("key", "value")

        # All should be different instances
        instances = [activated, verified, updated, with_login, with_metadata]
        for instance in instances:
            assert instance is not original_user
            assert isinstance(instance, User)


class TestUserValidationRules:
    """Test comprehensive validation rules and edge cases."""

    def test_name_validation_edge_cases(self) -> None:
        """Name validation handles various edge cases properly."""
        valid_names = ["Jo", "Mary Jane", "Jean-Luc", "O'Connor", "José María"]

        for name in valid_names:
            user = User.create_new(email="valid@example.com", name=name, age=25)
            assert user.name == name

    def test_name_validation_failures(self) -> None:
        """Name validation rejects invalid inputs."""
        invalid_cases = [
            ("", "Name cannot be empty"),
            ("   ", "Name must be at least 2 characters"),  # Whitespace gets stripped
            ("A", "Name must be at least 2 characters"),
            ("John123", "Name cannot contain numbers"),
            ("A" * 101, "Name cannot exceed 100 characters"),
        ]

        for invalid_name, expected_error in invalid_cases:
            with pytest.raises(ValidationException) as exc_info:
                User.create_new(email="test@example.com", name=invalid_name, age=25)
            assert expected_error in str(exc_info.value)

    def test_age_boundary_conditions(self) -> None:
        """Age validation handles boundary conditions correctly."""
        # Valid boundary ages
        min_age_user = User.create_new(email="min@example.com", name="Min Age", age=13)
        max_age_user = User.create_new(email="max@example.com", name="Max Age", age=120)

        assert min_age_user.age == 13
        assert max_age_user.age == 120

        # Invalid boundary ages
        with pytest.raises(ValidationException):
            User.create_new(email="under@example.com", name="Under Age", age=12)

        with pytest.raises(ValidationException):
            User.create_new(email="over@example.com", name="Over Age", age=121)

    def test_email_format_validation_integration(self) -> None:
        """Email validation integrates properly with Email value object."""
        # Test various email input formats
        email_formats: list[str | Email] = ["simple@example.com", Email(value="vo@example.com")]

        for email_input in email_formats:
            user = User.create_new(email=email_input, name="Email Test", age=25)
            assert isinstance(user.email, Email)

        # Test invalid email format - create_new expects string or Email object
        with pytest.raises((ValidationException, ValidationError)):
            User(email={"invalid": "format"}, name="Invalid", age=25)  # type: ignore[arg-type]
