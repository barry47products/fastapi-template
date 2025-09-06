"""
Sample application service demonstrating business logic patterns.

This module shows how to implement application services that:
- Orchestrate domain operations
- Handle business workflows
- Coordinate with infrastructure
- Maintain separation of concerns

Replace this with your actual business services.
"""

from datetime import datetime, UTC
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel

from src.domain.events import DomainEventRegistry
from src.infrastructure.observability import get_logger, get_metrics_collector


class SampleDomainEvent(BaseModel):
    """Sample domain event for demonstration."""

    event_type: str = "sample_operation_completed"
    entity_id: str
    operation_type: str
    timestamp: datetime
    metadata: dict[str, Any]


class UserRepository(Protocol):
    """Sample repository interface - implement this in infrastructure layer."""

    def save(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Save user data and return saved entity."""
        ...

    def find_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Find user by ID."""
        ...

    def find_by_email(self, email: str) -> dict[str, Any] | None:
        """Find user by email."""
        ...


class NotificationService(Protocol):
    """Sample notification service interface."""

    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email to new user."""
        ...


class BusinessLogicError(Exception):
    """Business logic validation error."""

    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class UserOnboardingResult(BaseModel):
    """Result of user onboarding process."""

    success: bool
    user_id: str
    welcome_email_sent: bool
    processing_duration_seconds: float
    errors: list[str] = []


class SampleApplicationService:
    """
    Sample application service demonstrating business orchestration.

    This service shows how to:
    - Coordinate multiple domain operations
    - Handle business workflows
    - Integrate with infrastructure services
    - Publish domain events
    - Handle errors and validation

    Replace this with your actual business services.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        notification_service: NotificationService,
    ) -> None:
        """Initialize service with dependencies."""
        self.user_repository = user_repository
        self.notification_service = notification_service
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()

    async def onboard_new_user(
        self,
        user_name: str,
        user_email: str,
        user_age: int,
    ) -> UserOnboardingResult:
        """
        Complete user onboarding workflow.

        This demonstrates a typical application service that:
        1. Validates business rules
        2. Coordinates with multiple repositories/services
        3. Publishes domain events
        4. Handles errors gracefully
        5. Returns structured results
        """
        operation_start = datetime.now(UTC)
        errors = []

        self.logger.info(
            "Starting user onboarding",
            user_name=user_name,
            user_email=user_email,
            user_age=user_age,
        )

        try:
            # Step 1: Business rule validation
            await self._validate_user_eligibility(user_name, user_email, user_age)

            # Step 2: Check for existing user
            existing_user = self.user_repository.find_by_email(user_email)
            if existing_user:
                raise BusinessLogicError(
                    f"User with email {user_email} already exists",
                    "DUPLICATE_EMAIL",
                )

            # Step 3: Create user entity
            user_data = {
                "id": str(uuid4()),
                "name": user_name,
                "email": user_email,
                "age": user_age,
                "created_at": datetime.now(UTC),
                "onboarding_completed": True,
            }

            # Step 4: Save user
            saved_user = self.user_repository.save(user_data)

            # Step 5: Send welcome email
            welcome_email_sent = False
            try:
                welcome_email_sent = self.notification_service.send_welcome_email(
                    user_email, user_name
                )
                if not welcome_email_sent:
                    errors.append("Failed to send welcome email")
                    self.logger.warning("Welcome email failed", user_email=user_email)
            except Exception as e:
                errors.append(f"Welcome email error: {str(e)}")
                self.logger.error("Welcome email exception", error=str(e), user_email=user_email)

            # Step 6: Publish domain event
            domain_event = SampleDomainEvent(
                entity_id=saved_user["id"],
                operation_type="user_onboarding_completed",
                timestamp=datetime.now(UTC),
                metadata={
                    "user_name": user_name,
                    "user_email": user_email,
                    "welcome_email_sent": welcome_email_sent,
                },
            )

            DomainEventRegistry.publish(domain_event)

            # Step 7: Record metrics
            processing_duration = (datetime.now(UTC) - operation_start).total_seconds()
            self.metrics.increment_counter("user_onboarding_completed_total", {})
            self.metrics.record_histogram(
                "user_onboarding_duration_seconds",
                processing_duration,
                {"success": "true"},
            )

            self.logger.info(
                "User onboarding completed successfully",
                user_id=saved_user["id"],
                processing_duration=processing_duration,
                welcome_email_sent=welcome_email_sent,
            )

            return UserOnboardingResult(
                success=True,
                user_id=saved_user["id"],
                welcome_email_sent=welcome_email_sent,
                processing_duration_seconds=processing_duration,
                errors=errors,
            )

        except BusinessLogicError as e:
            processing_duration = (datetime.now(UTC) - operation_start).total_seconds()
            self.metrics.increment_counter("user_onboarding_failed_total", {"reason": e.error_code})

            self.logger.error(
                "User onboarding failed - business logic error",
                error=str(e),
                error_code=e.error_code,
                user_email=user_email,
            )

            return UserOnboardingResult(
                success=False,
                user_id="",
                welcome_email_sent=False,
                processing_duration_seconds=processing_duration,
                errors=[str(e)],
            )

        except Exception as e:
            processing_duration = (datetime.now(UTC) - operation_start).total_seconds()
            self.metrics.increment_counter("user_onboarding_failed_total", {"reason": "unexpected"})

            self.logger.error(
                "User onboarding failed - unexpected error",
                error=str(e),
                user_email=user_email,
            )

            return UserOnboardingResult(
                success=False,
                user_id="",
                welcome_email_sent=False,
                processing_duration_seconds=processing_duration,
                errors=[f"Unexpected error: {str(e)}"],
            )

    async def _validate_user_eligibility(
        self,
        user_name: str,
        user_email: str,
        user_age: int,
    ) -> None:
        """
        Validate business rules for user eligibility.

        Demonstrates business rule validation at the application layer.
        """
        if not user_name or len(user_name.strip()) < 2:
            raise BusinessLogicError("User name must be at least 2 characters", "INVALID_NAME")

        if not user_email or "@" not in user_email:
            raise BusinessLogicError("Valid email address is required", "INVALID_EMAIL")

        if user_age < 13:
            raise BusinessLogicError(
                "Users must be at least 13 years old due to privacy regulations",
                "AGE_REQUIREMENT",
            )

        if user_age > 120:
            raise BusinessLogicError("Please enter a valid age", "INVALID_AGE")

    async def get_user_profile_summary(self, user_id: str) -> dict[str, Any]:
        """
        Get comprehensive user profile summary.

        Demonstrates service that aggregates data from multiple sources.
        """
        self.logger.info("Retrieving user profile summary", user_id=user_id)

        try:
            user = self.user_repository.find_by_id(user_id)
            if not user:
                raise BusinessLogicError(f"User {user_id} not found", "USER_NOT_FOUND")

            # Sample business logic: calculate user status
            registration_date = user.get("created_at", datetime.now(UTC))
            days_since_registration = (datetime.now(UTC) - registration_date).days

            user_status = "new" if days_since_registration < 30 else "established"

            profile_summary = {
                "user_id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "age": user["age"],
                "registration_date": registration_date.isoformat(),
                "days_since_registration": days_since_registration,
                "user_status": user_status,
                "onboarding_completed": user.get("onboarding_completed", False),
            }

            self.metrics.increment_counter("user_profile_retrieved_total", {})
            return profile_summary

        except BusinessLogicError:
            self.metrics.increment_counter("user_profile_not_found_total", {})
            raise

        except Exception as e:
            self.logger.error(
                "Failed to retrieve user profile summary",
                user_id=user_id,
                error=str(e),
            )
            self.metrics.increment_counter("user_profile_errors_total", {})
            raise BusinessLogicError("Failed to retrieve user profile", "PROFILE_ERROR")
