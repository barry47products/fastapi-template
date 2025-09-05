"""Phone number domain events for clean architecture separation."""

from .base import DomainEvent


class PhoneNumberValidated(DomainEvent):
    """Event raised when a phone number is successfully validated."""

    phone_number: str
    normalized_number: str
    region: str

    @property
    def aggregate_id(self) -> str:
        """Return the phone number as aggregate ID."""
        return self.phone_number


class PhoneNumberValidationError(DomainEvent):
    """Event raised when phone number validation fails."""

    phone_number: str
    error_type: str
    error_message: str

    @property
    def aggregate_id(self) -> str:
        """Return the phone number as aggregate ID."""
        return self.phone_number


class PhoneNumberParseError(DomainEvent):
    """Event raised when phone number parsing fails."""

    phone_number: str
    error_message: str

    @property
    def aggregate_id(self) -> str:
        """Return the phone number as aggregate ID."""
        return self.phone_number
