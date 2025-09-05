"""Endorsement domain events for clean architecture separation."""

from .base import DomainEvent


class EndorsementStatusChanged(DomainEvent):
    """Event raised when an endorsement's status changes."""

    endorsement_id: str
    provider_id: str
    operation: str
    endorsement_type: str

    @property
    def aggregate_id(self) -> str:
        """Return the endorsement ID as aggregate ID."""
        return self.endorsement_id


class EndorsementConfidenceUpdated(DomainEvent):
    """Event raised when an endorsement's confidence score is updated."""

    endorsement_id: str
    provider_id: str
    old_score: float
    new_score: float

    @property
    def aggregate_id(self) -> str:
        """Return the endorsement ID as aggregate ID."""
        return self.endorsement_id
