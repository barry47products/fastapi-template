"""Provider domain events for clean architecture separation."""

from .base import DomainEvent


class ProviderEndorsementIncremented(DomainEvent):
    """Event raised when a provider's endorsement count is incremented."""

    provider_id: str
    provider_category: str
    new_endorsement_count: int

    @property
    def aggregate_id(self) -> str:
        """Return the provider ID as aggregate ID."""
        return self.provider_id


class ProviderTagAdded(DomainEvent):
    """Event raised when a tag is added to a provider."""

    provider_id: str
    tag_category: str
    tag_value: str

    @property
    def aggregate_id(self) -> str:
        """Return the provider ID as aggregate ID."""
        return self.provider_id


class ProviderEndorsementDecremented(DomainEvent):
    """Event raised when a provider's endorsement count is decremented."""

    provider_id: str
    provider_category: str
    new_endorsement_count: int

    @property
    def aggregate_id(self) -> str:
        """Return the provider ID as aggregate ID."""
        return self.provider_id


class ProviderTagRemoved(DomainEvent):
    """Event raised when a tag is removed from a provider."""

    provider_id: str
    tag_category: str

    @property
    def aggregate_id(self) -> str:
        """Return the provider ID as aggregate ID."""
        return self.provider_id
