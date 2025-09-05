"""Firestore implementation of Endorsement repository."""

from datetime import datetime, timedelta, UTC
from typing import Any

from google.cloud.firestore_v1.base_query import FieldFilter

from src.domain.models import Endorsement
from src.domain.models.endorsement import EndorsementStatus, EndorsementType
from src.domain.value_objects import EndorsementID, GroupID, PhoneNumber, ProviderID
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.infrastructure.persistence.firestore_client import FirestoreClient
from src.shared.exceptions import RepositoryException


class FirestoreEndorsementRepository:
    """
    Firestore implementation of the Endorsement repository.

    Provides persistence operations for Endorsement entities using Google Cloud
    Firestore
    as the underlying storage backend. Implements the EndorsementRepository protocol
    while maintaining clean architecture boundaries.
    """

    COLLECTION_NAME = "endorsements"

    def __init__(self, firestore_client: FirestoreClient) -> None:
        """Initialize repository with Firestore client."""
        self.client = firestore_client
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()

    def save(self, endorsement: Endorsement) -> None:
        """Save or update an endorsement."""
        try:
            endorsement_data = self._to_document(endorsement)

            self.client.create_document(
                self.COLLECTION_NAME,
                endorsement_data,
                endorsement.id.value,
            )

            self.metrics.increment_counter("endorsement_saves_total", {})
            self.logger.info(
                "Endorsement saved successfully",
                endorsement_id=endorsement.id.value,
            )

        except Exception as e:
            self.metrics.increment_counter("endorsement_save_errors_total", {})
            self.logger.error(
                "Failed to save endorsement",
                endorsement_id=endorsement.id.value,
                error=str(e),
            )
            raise RepositoryException(f"Failed to save endorsement: {e}") from e

    def find_by_id(self, endorsement_id: EndorsementID) -> Endorsement | None:
        """Find an endorsement by its unique identifier."""
        try:
            document_path = f"{self.COLLECTION_NAME}/{endorsement_id.value}"
            document_data = self.client.get_document(document_path)

            if document_data is None:
                self.logger.debug(
                    "Endorsement not found",
                    endorsement_id=endorsement_id.value,
                )
                return None

            endorsement = self._from_document(document_data, endorsement_id.value)
            self.metrics.increment_counter("endorsement_finds_total", {})

            return endorsement

        except Exception as e:
            self.metrics.increment_counter("endorsement_find_errors_total", {})
            self.logger.error(
                "Failed to find endorsement by ID",
                endorsement_id=endorsement_id.value,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find endorsement: {e}") from e

    def find_by_provider(
        self,
        provider_id: ProviderID,
        status: EndorsementStatus | None = None,
    ) -> list[Endorsement]:
        """Find endorsements for a specific provider."""
        try:
            filters = [FieldFilter("provider_id", "==", provider_id.value)]
            if status:
                filters.append(FieldFilter("status", "==", status.value))

            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
            )

            endorsements = []
            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    endorsement = self._from_document(doc_data, doc_id)
                    endorsements.append(endorsement)

            self.metrics.increment_counter("endorsement_provider_searches_total", {})
            self.logger.debug(
                "Found endorsements by provider",
                provider_id=provider_id.value,
                status=status.value if status else None,
                count=len(endorsements),
            )

            return endorsements

        except Exception as e:
            self.metrics.increment_counter(
                "endorsement_provider_search_errors_total",
                {},
            )
            self.logger.error(
                "Failed to find endorsements by provider",
                provider_id=provider_id.value,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to find endorsements by provider: {e}",
            ) from e

    def find_by_group(
        self,
        group_id: GroupID,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """Find endorsements within a specific group."""
        try:
            filters = [FieldFilter("group_id", "==", group_id.value)]
            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
                limit=limit,
            )

            endorsements = []
            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    endorsement = self._from_document(doc_data, doc_id)
                    endorsements.append(endorsement)

            self.metrics.increment_counter("endorsement_group_searches_total", {})
            self.logger.debug(
                "Found endorsements by group",
                group_id=group_id.value,
                count=len(endorsements),
            )

            return endorsements

        except Exception as e:
            self.metrics.increment_counter("endorsement_group_search_errors_total", {})
            self.logger.error(
                "Failed to find endorsements by group",
                group_id=group_id.value,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to find endorsements by group: {e}",
            ) from e

    def find_by_endorser(
        self,
        endorser_phone: PhoneNumber,
        status: EndorsementStatus | None = None,
    ) -> list[Endorsement]:
        """Find endorsements created by a specific endorser."""
        try:
            filters = [FieldFilter("endorser_phone", "==", endorser_phone.value)]
            if status:
                filters.append(FieldFilter("status", "==", status.value))

            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
            )

            endorsements = []
            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    endorsement = self._from_document(doc_data, doc_id)
                    endorsements.append(endorsement)

            self.metrics.increment_counter("endorsement_endorser_searches_total", {})
            self.logger.debug(
                "Found endorsements by endorser",
                endorser_phone=endorser_phone.value,
                status=status.value if status else None,
                count=len(endorsements),
            )

            return endorsements

        except Exception as e:
            self.metrics.increment_counter(
                "endorsement_endorser_search_errors_total",
                {},
            )
            self.logger.error(
                "Failed to find endorsements by endorser",
                endorser_phone=endorser_phone.value,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to find endorsements by endorser: {e}",
            ) from e

    def find_by_type(
        self,
        endorsement_type: EndorsementType,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """Find endorsements by type."""
        try:
            filters = [FieldFilter("endorsement_type", "==", endorsement_type.value)]
            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
                limit=limit,
            )

            endorsements = []
            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    endorsement = self._from_document(doc_data, doc_id)
                    endorsements.append(endorsement)

            self.metrics.increment_counter("endorsement_type_searches_total", {})
            self.logger.debug(
                "Found endorsements by type",
                endorsement_type=endorsement_type.value,
                count=len(endorsements),
            )

            return endorsements

        except Exception as e:
            self.metrics.increment_counter("endorsement_type_search_errors_total", {})
            self.logger.error(
                "Failed to find endorsements by type",
                endorsement_type=endorsement_type.value,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to find endorsements by type: {e}",
            ) from e

    def find_recent(
        self,
        days: int = 30,
        status: EndorsementStatus | None = None,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """Find recent endorsements within specified time period."""
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            filters = [FieldFilter("created_at", ">=", cutoff_date)]
            if status:
                filters.append(FieldFilter("status", "==", status.value))

            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
                order_by="created_at desc",
                limit=limit,
            )

            endorsements = []
            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    endorsement = self._from_document(doc_data, doc_id)
                    endorsements.append(endorsement)

            self.metrics.increment_counter("endorsement_recent_searches_total", {})
            self.logger.debug(
                "Found recent endorsements",
                days=days,
                status=status.value if status else None,
                count=len(endorsements),
            )

            return endorsements

        except Exception as e:
            self.metrics.increment_counter("endorsement_recent_search_errors_total", {})
            self.logger.error(
                "Failed to find recent endorsements",
                days=days,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find recent endorsements: {e}") from e

    def find_by_confidence_range(
        self,
        min_confidence: float,
        max_confidence: float,
        limit: int | None = None,
    ) -> list[Endorsement]:
        """Find endorsements within confidence score range."""
        try:
            filters = [
                FieldFilter("confidence_score", ">=", min_confidence),
                FieldFilter("confidence_score", "<=", max_confidence),
            ]

            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
                limit=limit,
            )

            endorsements = []
            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    endorsement = self._from_document(doc_data, doc_id)
                    endorsements.append(endorsement)

            self.metrics.increment_counter("endorsement_confidence_searches_total", {})
            self.logger.debug(
                "Found endorsements by confidence range",
                min_confidence=min_confidence,
                max_confidence=max_confidence,
                count=len(endorsements),
            )

            return endorsements

        except Exception as e:
            self.metrics.increment_counter(
                "endorsement_confidence_search_errors_total",
                {},
            )
            self.logger.error(
                "Failed to find endorsements by confidence range",
                min_confidence=min_confidence,
                max_confidence=max_confidence,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to find endorsements by confidence: {e}",
            ) from e

    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        status: EndorsementStatus | None = None,
    ) -> list[Endorsement]:
        """Find endorsements within date range."""
        try:
            filters = [
                FieldFilter("created_at", ">=", start_date),
                FieldFilter("created_at", "<=", end_date),
            ]
            if status:
                filters.append(FieldFilter("status", "==", status.value))

            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
            )

            endorsements = []
            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    endorsement = self._from_document(doc_data, doc_id)
                    endorsements.append(endorsement)

            self.metrics.increment_counter("endorsement_date_range_searches_total", {})
            self.logger.debug(
                "Found endorsements by date range",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                status=status.value if status else None,
                count=len(endorsements),
            )

            return endorsements

        except Exception as e:
            self.metrics.increment_counter(
                "endorsement_date_range_search_errors_total",
                {},
            )
            self.logger.error(
                "Failed to find endorsements by date range",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to find endorsements by date range: {e}",
            ) from e

    def exists(self, endorsement_id: EndorsementID) -> bool:
        """Check if an endorsement exists."""
        try:
            document_path = f"{self.COLLECTION_NAME}/{endorsement_id.value}"
            document_data = self.client.get_document(document_path)

            exists = document_data is not None
            self.metrics.increment_counter("endorsement_exists_checks_total", {})

            return exists

        except Exception as e:
            self.metrics.increment_counter("endorsement_exists_check_errors_total", {})
            self.logger.error(
                "Failed to check endorsement existence",
                endorsement_id=endorsement_id.value,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to check endorsement existence: {e}",
            ) from e

    def delete(self, endorsement_id: EndorsementID) -> None:
        """Delete an endorsement by ID."""
        try:
            document_path = f"{self.COLLECTION_NAME}/{endorsement_id.value}"
            self.client.delete_document(document_path)

            self.metrics.increment_counter("endorsement_deletes_total", {})
            self.logger.info(
                "Endorsement deleted successfully",
                endorsement_id=endorsement_id.value,
            )

        except Exception as e:
            self.metrics.increment_counter("endorsement_delete_errors_total", {})
            self.logger.error(
                "Failed to delete endorsement",
                endorsement_id=endorsement_id.value,
                error=str(e),
            )
            raise RepositoryException(f"Failed to delete endorsement: {e}") from e

    def count(self) -> int:
        """Get total number of endorsements."""
        try:
            documents = self.client.query_collection(self.COLLECTION_NAME)
            count = len(documents)

            self.metrics.increment_counter("endorsement_counts_total", {})
            self.logger.debug("Endorsement count retrieved", count=count)

            return count

        except Exception as e:
            self.metrics.increment_counter("endorsement_count_errors_total", {})
            self.logger.error("Failed to count endorsements", error=str(e))
            raise RepositoryException(f"Failed to count endorsements: {e}") from e

    def count_by_provider(
        self,
        provider_id: ProviderID,
        status: EndorsementStatus | None = None,
    ) -> int:
        """Get number of endorsements for a provider."""
        try:
            filters = [FieldFilter("provider_id", "==", provider_id.value)]
            if status:
                filters.append(FieldFilter("status", "==", status.value))

            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
            )

            count = len(documents)
            self.metrics.increment_counter("endorsement_provider_counts_total", {})
            self.logger.debug(
                "Endorsement provider count retrieved",
                provider_id=provider_id.value,
                status=status.value if status else None,
                count=count,
            )

            return count

        except Exception as e:
            self.metrics.increment_counter(
                "endorsement_provider_count_errors_total",
                {},
            )
            self.logger.error(
                "Failed to count endorsements by provider",
                provider_id=provider_id.value,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to count endorsements by provider: {e}",
            ) from e

    def count_by_group(self, group_id: GroupID) -> int:
        """Get number of endorsements in a group."""
        try:
            filters = [FieldFilter("group_id", "==", group_id.value)]
            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
            )

            count = len(documents)
            self.metrics.increment_counter("endorsement_group_counts_total", {})
            self.logger.debug(
                "Endorsement group count retrieved",
                group_id=group_id.value,
                count=count,
            )

            return count

        except Exception as e:
            self.metrics.increment_counter("endorsement_group_count_errors_total", {})
            self.logger.error(
                "Failed to count endorsements by group",
                group_id=group_id.value,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to count endorsements by group: {e}",
            ) from e

    def count_by_type(self, endorsement_type: EndorsementType) -> int:
        """Get number of endorsements by type."""
        try:
            filters = [FieldFilter("endorsement_type", "==", endorsement_type.value)]
            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
            )

            count = len(documents)
            self.metrics.increment_counter("endorsement_type_counts_total", {})
            self.logger.debug(
                "Endorsement type count retrieved",
                endorsement_type=endorsement_type.value,
                count=count,
            )

            return count

        except Exception as e:
            self.metrics.increment_counter("endorsement_type_count_errors_total", {})
            self.logger.error(
                "Failed to count endorsements by type",
                endorsement_type=endorsement_type.value,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to count endorsements by type: {e}",
            ) from e

    def _to_document(self, endorsement: Endorsement) -> dict[str, Any]:
        """Convert Endorsement entity to Firestore document."""
        return {
            "_id": endorsement.id.value,
            "provider_id": endorsement.provider_id.value,
            "group_id": endorsement.group_id.value,
            "endorser_phone": endorsement.endorser_phone.value,
            "endorsement_type": endorsement.endorsement_type.value,
            "status": endorsement.status.value,
            "message_context": endorsement.message_context,
            "confidence_score": endorsement.confidence_score,
            "created_at": endorsement.created_at,
        }

    def _from_document(self, doc_data: dict[str, Any], doc_id: str) -> Endorsement:
        """Convert Firestore document to Endorsement entity."""
        return Endorsement(
            id=EndorsementID(value=doc_id),
            provider_id=ProviderID(value=doc_data["provider_id"]),
            group_id=GroupID(value=doc_data["group_id"]),
            endorser_phone=PhoneNumber(value=doc_data["endorser_phone"]),
            endorsement_type=EndorsementType(doc_data["endorsement_type"]),
            status=EndorsementStatus(doc_data["status"]),
            message_context=doc_data["message_context"],
            confidence_score=doc_data["confidence_score"],
            created_at=doc_data["created_at"],
        )
