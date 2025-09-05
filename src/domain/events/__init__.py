"""Domain events package for clean architecture separation."""

from .base import DomainEvent, DomainEventPublisher
from .endorsement_events import EndorsementConfidenceUpdated, EndorsementStatusChanged
from .persistence_events import (
    FirestoreOperationEvent,
    PersistenceHealthCheckEvent,
    RepositoryOperationEvent,
)
from .phone_number_events import (
    PhoneNumberParseError,
    PhoneNumberValidated,
    PhoneNumberValidationError,
)
from .provider_events import (
    ProviderEndorsementDecremented,
    ProviderEndorsementIncremented,
    ProviderTagAdded,
    ProviderTagRemoved,
)
from .registry import DomainEventRegistry

__all__ = [
    "DomainEvent",
    "DomainEventPublisher",
    "DomainEventRegistry",
    "EndorsementConfidenceUpdated",
    "EndorsementStatusChanged",
    "FirestoreOperationEvent",
    "PersistenceHealthCheckEvent",
    "PhoneNumberParseError",
    "PhoneNumberValidated",
    "PhoneNumberValidationError",
    "ProviderEndorsementDecremented",
    "ProviderEndorsementIncremented",
    "ProviderTagAdded",
    "ProviderTagRemoved",
    "RepositoryOperationEvent",
]
