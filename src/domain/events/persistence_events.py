"""Domain events for persistence layer operations."""

from pydantic import Field

from .base import DomainEvent


class FirestoreOperationEvent(DomainEvent):
    """Event published when Firestore operations are performed."""

    event_type: str = Field(default="FirestoreOperationEvent", init=False)
    operation: str = Field(
        description="Type of operation (create, read, update, delete, query)",
    )
    collection: str = Field(description="Firestore collection name")
    document_id: str = Field(description="Document ID (empty for collection queries)")
    duration_seconds: float = Field(description="Operation duration in seconds")


class RepositoryOperationEvent(DomainEvent):
    """Event published when repository operations are performed."""

    event_type: str = Field(default="RepositoryOperationEvent", init=False)
    repository_type: str = Field(
        description="Type of repository (provider, endorsement)",
    )
    operation: str = Field(description="Type of operation (save, find, delete, query)")
    entity_id: str = Field(description="Entity ID being operated on")
    duration_seconds: float = Field(description="Operation duration in seconds")


class PersistenceHealthCheckEvent(DomainEvent):
    """Event published during persistence layer health checks."""

    event_type: str = Field(default="PersistenceHealthCheckEvent", init=False)
    component: str = Field(
        description="Persistence component (firestore_client, repository)",
    )
    status: str = Field(description="Health check status (healthy, unhealthy)")
    details: str = Field(default="", description="Additional health check details")
