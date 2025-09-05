"""Firestore implementation of Provider repository."""

from datetime import datetime

from google.cloud.firestore_v1.base_query import FieldFilter

from src.domain.models import Provider
from src.domain.value_objects import PhoneNumber, ProviderID
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.infrastructure.persistence.firestore_client import FirestoreClient
from src.shared.exceptions import RepositoryException


class FirestoreProviderRepository:
    """
    Firestore implementation of the Provider repository.

    Provides persistence operations for Provider entities using Google Cloud Firestore
    as the underlying storage backend. Implements the ProviderRepository protocol
    while maintaining clean architecture boundaries.
    """

    COLLECTION_NAME = "providers"

    def __init__(self, firestore_client: FirestoreClient) -> None:
        """Initialize repository with Firestore client."""
        self.client = firestore_client
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()

    def save(self, provider: Provider) -> None:
        """Save or update a provider."""
        try:
            provider_data = self._to_document(provider)

            self.client.create_document(
                self.COLLECTION_NAME,
                provider_data,
                provider.id.value,
            )

            self.metrics.increment_counter("provider_saves_total", {})
            self.logger.info(
                "Provider saved successfully",
                provider_id=provider.id.value,
            )

        except Exception as e:
            self.metrics.increment_counter("provider_save_errors_total", {})
            self.logger.error(
                "Failed to save provider",
                provider_id=provider.id.value,
                error=str(e),
            )
            raise RepositoryException(f"Failed to save provider: {e}") from e

    def find_by_id(self, provider_id: ProviderID) -> Provider | None:
        """Find a provider by its unique identifier."""
        try:
            document_path = f"{self.COLLECTION_NAME}/{provider_id.value}"
            document_data = self.client.get_document(document_path)

            if document_data is None:
                self.logger.debug("Provider not found", provider_id=provider_id.value)
                return None

            provider = self._from_document(document_data, provider_id.value)
            self.metrics.increment_counter("provider_finds_total", {})

            return provider

        except Exception as e:
            self.metrics.increment_counter("provider_find_errors_total", {})
            self.logger.error(
                "Failed to find provider by ID",
                provider_id=provider_id.value,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find provider: {e}") from e

    def find_by_phone(self, phone: PhoneNumber) -> list[Provider]:
        """Find providers by phone number."""
        try:
            filters = [FieldFilter("phone", "==", phone.value)]
            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
            )

            providers = []
            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    provider = self._from_document(doc_data, doc_id)
                    providers.append(provider)

            self.metrics.increment_counter("provider_phone_searches_total", {})
            self.logger.debug(
                "Found providers by phone",
                phone=phone.value,
                count=len(providers),
            )

            return providers

        except Exception as e:
            self.metrics.increment_counter("provider_phone_search_errors_total", {})
            self.logger.error(
                "Failed to find providers by phone",
                phone=phone.value,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find providers by phone: {e}") from e

    def find_by_category(
        self,
        category: str,
        limit: int | None = None,
    ) -> list[Provider]:
        """Find providers by service category."""
        try:
            filters = [FieldFilter("category", "==", category)]
            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
                limit=limit,
            )

            providers = []
            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    provider = self._from_document(doc_data, doc_id)
                    providers.append(provider)

            self.metrics.increment_counter("provider_category_searches_total", {})
            self.logger.debug(
                "Found providers by category",
                category=category,
                count=len(providers),
            )

            return providers

        except Exception as e:
            self.metrics.increment_counter("provider_category_search_errors_total", {})
            self.logger.error(
                "Failed to find providers by category",
                category=category,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to find providers by category: {e}",
            ) from e

    def find_top_endorsed(
        self,
        category: str | None = None,
        limit: int = 10,
    ) -> list[Provider]:
        """Find providers with highest endorsement counts."""
        try:
            filters = []
            if category:
                filters.append(FieldFilter("category", "==", category))

            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters if filters else None,
                order_by="endorsement_count desc",
                limit=limit,
            )

            providers = []
            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    provider = self._from_document(doc_data, doc_id)
                    providers.append(provider)

            self.metrics.increment_counter("provider_top_endorsed_searches_total", {})
            self.logger.debug(
                "Found top endorsed providers",
                category=category,
                count=len(providers),
            )

            return providers

        except Exception as e:
            self.metrics.increment_counter(
                "provider_top_endorsed_search_errors_total",
                {},
            )
            self.logger.error(
                "Failed to find top endorsed providers",
                category=category,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to find top endorsed providers: {e}",
            ) from e

    def find_by_name_pattern(self, name_pattern: str) -> list[Provider]:
        """Find providers by name pattern (case-insensitive partial match)."""
        try:
            documents = self.client.query_collection(self.COLLECTION_NAME)

            providers = []
            pattern_lower = name_pattern.lower()

            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    name = doc_data.get("name", "").lower()
                    if pattern_lower in name:
                        provider = self._from_document(doc_data, doc_id)
                        providers.append(provider)

            self.metrics.increment_counter("provider_name_pattern_searches_total", {})
            self.logger.debug(
                "Found providers by name pattern",
                pattern=name_pattern,
                count=len(providers),
            )

            return providers

        except Exception as e:
            self.metrics.increment_counter(
                "provider_name_pattern_search_errors_total",
                {},
            )
            self.logger.error(
                "Failed to find providers by name pattern",
                pattern=name_pattern,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to find providers by name pattern: {e}",
            ) from e

    def find_by_tag(self, tag_key: str, tag_value: str) -> list[Provider]:
        """Find providers by tag key-value pair."""
        try:
            filters = [FieldFilter(f"tags.{tag_key}", "==", tag_value)]
            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
            )

            providers = []
            for doc_data in documents:
                if doc_id := doc_data.get("_id"):
                    provider = self._from_document(doc_data, doc_id)
                    providers.append(provider)

            self.metrics.increment_counter("provider_tag_searches_total", {})
            self.logger.debug(
                "Found providers by tag",
                tag_key=tag_key,
                tag_value=tag_value,
                count=len(providers),
            )

            return providers

        except Exception as e:
            self.metrics.increment_counter("provider_tag_search_errors_total", {})
            self.logger.error(
                "Failed to find providers by tag",
                tag_key=tag_key,
                tag_value=tag_value,
                error=str(e),
            )
            raise RepositoryException(f"Failed to find providers by tag: {e}") from e

    def exists(self, provider_id: ProviderID) -> bool:
        """Check if a provider exists."""
        try:
            document_path = f"{self.COLLECTION_NAME}/{provider_id.value}"
            document_data = self.client.get_document(document_path)

            exists = document_data is not None
            self.metrics.increment_counter("provider_exists_checks_total", {})

            return exists

        except Exception as e:
            self.metrics.increment_counter("provider_exists_check_errors_total", {})
            self.logger.error(
                "Failed to check provider existence",
                provider_id=provider_id.value,
                error=str(e),
            )
            raise RepositoryException(f"Failed to check provider existence: {e}") from e

    def delete(self, provider_id: ProviderID) -> None:
        """Delete a provider by ID."""
        try:
            document_path = f"{self.COLLECTION_NAME}/{provider_id.value}"
            self.client.delete_document(document_path)

            self.metrics.increment_counter("provider_deletes_total", {})
            self.logger.info(
                "Provider deleted successfully",
                provider_id=provider_id.value,
            )

        except Exception as e:
            self.metrics.increment_counter("provider_delete_errors_total", {})
            self.logger.error(
                "Failed to delete provider",
                provider_id=provider_id.value,
                error=str(e),
            )
            raise RepositoryException(f"Failed to delete provider: {e}") from e

    def count(self) -> int:
        """Get total number of providers."""
        try:
            documents = self.client.query_collection(self.COLLECTION_NAME)
            count = len(documents)

            self.metrics.increment_counter("provider_counts_total", {})
            self.logger.debug("Provider count retrieved", count=count)

            return count

        except Exception as e:
            self.metrics.increment_counter("provider_count_errors_total", {})
            self.logger.error("Failed to count providers", error=str(e))
            raise RepositoryException(f"Failed to count providers: {e}") from e

    def count_by_category(self, category: str) -> int:
        """Get number of providers in a specific category."""
        try:
            filters = [FieldFilter("category", "==", category)]
            documents = self.client.query_collection(
                self.COLLECTION_NAME,
                filters=filters,
            )

            count = len(documents)
            self.metrics.increment_counter("provider_category_counts_total", {})
            self.logger.debug(
                "Provider category count retrieved",
                category=category,
                count=count,
            )

            return count

        except Exception as e:
            self.metrics.increment_counter("provider_category_count_errors_total", {})
            self.logger.error(
                "Failed to count providers by category",
                category=category,
                error=str(e),
            )
            raise RepositoryException(
                f"Failed to count providers by category: {e}",
            ) from e

    def _to_document(self, provider: Provider) -> dict[str, str | int | dict[str, str] | datetime]:
        """Convert Provider entity to Firestore document."""
        return {
            "_id": provider.id.value,
            "name": provider.name,
            "phone": provider.phone.value,
            "category": provider.category,
            "tags": dict(provider.tags),
            "endorsement_count": provider.endorsement_count,
            "created_at": provider.created_at,
        }

    def _from_document(
        self,
        doc_data: dict[str, str | int | dict[str, str] | datetime],
        doc_id: str,
    ) -> Provider:
        """Convert Firestore document to Provider entity."""
        # Extract and validate tags data
        tags_data = doc_data.get("tags", {})
        validated_tags = dict(tags_data) if tags_data and isinstance(tags_data, dict) else {}

        # Extract and validate endorsement count
        count_data = doc_data.get("endorsement_count", 0)
        validated_count = count_data if isinstance(count_data, int) else 0

        # Extract and validate created_at timestamp
        created_at_data = doc_data.get("created_at")
        validated_created_at = (
            created_at_data if isinstance(created_at_data, datetime) else datetime.now()
        )

        return Provider(
            id=ProviderID(value=doc_id),
            name=str(doc_data["name"]),
            phone=PhoneNumber(value=str(doc_data["phone"])),
            category=str(doc_data["category"]),
            tags=validated_tags,
            endorsement_count=validated_count,
            created_at=validated_created_at,
        )
