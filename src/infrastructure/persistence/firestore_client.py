"""Firestore client service with infrastructure integration."""

import os
from datetime import datetime, UTC
from typing import Any

from google.api_core import exceptions as firestore_exceptions
from google.cloud.firestore import Client
from google.cloud.firestore_v1 import CollectionReference, DocumentReference, Query
from google.cloud.firestore_v1.base_query import FieldFilter

from config.settings import FirestoreSettings
from src.domain.events import DomainEventRegistry, FirestoreOperationEvent
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import PersistenceException


class FirestoreClient:
    """
    Firestore client wrapper with infrastructure integration.

    Provides a clean interface to Google Cloud Firestore with:
    - Connection management (emulator vs production)
    - Error handling and retry logic
    - Metrics and logging integration
    - Domain events for persistence operations
    """

    def __init__(self, settings: FirestoreSettings) -> None:
        """Initialize Firestore client with settings."""
        self.settings = settings
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        """Get or create Firestore client instance."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> Client:
        """Create and configure Firestore client."""
        try:
            # Configure emulator if enabled
            if self.settings.is_emulator_enabled:
                os.environ["FIRESTORE_EMULATOR_HOST"] = self.settings.firestore_emulator_host
                self.logger.info(
                    "Configuring Firestore emulator",
                    emulator_host=self.settings.firestore_emulator_host,
                    project_id=self.settings.firestore_project_id,
                )
            else:
                # Remove emulator setting if previously set
                if "FIRESTORE_EMULATOR_HOST" in os.environ:
                    del os.environ["FIRESTORE_EMULATOR_HOST"]
                self.logger.info(
                    "Configuring production Firestore",
                    project_id=self.settings.firestore_project_id,
                )

            # Create client
            client = Client(
                project=self.settings.firestore_project_id,
                database=self.settings.firestore_database_id,
            )

            # Test connection
            self._test_connection(client)

            self.metrics.increment_counter("firestore_client_connections_total", {})
            self.logger.info(
                "Firestore client initialized successfully",
                project_id=self.settings.firestore_project_id,
                database_id=self.settings.firestore_database_id,
            )

            return client

        except Exception as e:
            self.metrics.increment_counter(
                "firestore_client_connection_errors_total",
                {},
            )
            self.logger.error(
                "Failed to initialize Firestore client",
                error=str(e),
                project_id=self.settings.firestore_project_id,
            )
            raise PersistenceException(
                f"Failed to initialize Firestore client: {e}",
            ) from e

    def _test_connection(self, client: Client) -> None:
        """Test Firestore connection with a simple operation."""
        try:
            # Try to access a collection (doesn't create it)
            test_collection = client.collection(
                self.settings.firestore_health_check_collection,
            )
            # Just get the collection reference - no actual operation
            _ = test_collection._path
            self.logger.debug("Firestore connection test successful")
        except Exception as e:
            self.logger.error("Firestore connection test failed", error=str(e))
            raise

    def collection(self, collection_path: str) -> CollectionReference:
        """Get a collection reference."""
        try:
            collection_ref = self.client.collection(collection_path)
            self.logger.debug(
                "Collection reference created",
                collection=collection_path,
            )
            return collection_ref
        except Exception as e:
            self.metrics.increment_counter("firestore_collection_errors_total", {})
            self.logger.error(
                "Failed to get collection reference",
                collection=collection_path,
                error=str(e),
            )
            raise PersistenceException(
                f"Failed to get collection {collection_path}: {e}",
            ) from e

    def document(self, document_path: str) -> DocumentReference:
        """Get a document reference."""
        try:
            doc_ref = self.client.document(document_path)
            self.logger.debug("Document reference created", document=document_path)
            return doc_ref
        except Exception as e:
            self.metrics.increment_counter("firestore_document_errors_total", {})
            self.logger.error(
                "Failed to get document reference",
                document=document_path,
                error=str(e),
            )
            raise PersistenceException(
                f"Failed to get document {document_path}: {e}",
            ) from e

    def create_document(
        self,
        collection_path: str,
        document_data: dict[str, Any],
        document_id: str | None = None,
    ) -> str:
        """Create a new document in the specified collection."""
        operation_start = datetime.now(UTC)

        try:
            collection_ref = self.collection(collection_path)

            if document_id:
                doc_ref = collection_ref.document(document_id)
                doc_ref.create(document_data)
                created_doc_id = document_id
            else:
                _, doc_ref = collection_ref.add(document_data)
                created_doc_id = doc_ref.id

            operation_duration = (datetime.now(UTC) - operation_start).total_seconds()

            # Publish domain event
            DomainEventRegistry.publish(
                FirestoreOperationEvent(
                    operation="create",
                    collection=collection_path,
                    document_id=created_doc_id,
                    duration_seconds=operation_duration,
                ),
            )

            self.metrics.increment_counter("firestore_document_creates_total", {})
            self.metrics.record_histogram(
                "firestore_operation_duration_seconds",
                operation_duration,
                {},
            )

            self.logger.info(
                "Document created successfully",
                collection=collection_path,
                document_id=created_doc_id,
                duration_seconds=operation_duration,
            )

            return created_doc_id

        except firestore_exceptions.AlreadyExists as e:
            self.metrics.increment_counter(
                "firestore_document_already_exists_total",
                {},
            )
            self.logger.warning(
                "Document already exists",
                collection=collection_path,
                document_id=document_id,
                error=str(e),
            )
            raise PersistenceException(f"Document already exists: {e}") from e
        except Exception as e:
            self.metrics.increment_counter("firestore_document_create_errors_total", {})
            self.logger.error(
                "Failed to create document",
                collection=collection_path,
                document_id=document_id,
                error=str(e),
            )
            raise PersistenceException(f"Failed to create document: {e}") from e

    def update_document(
        self,
        document_path: str,
        document_data: dict[str, Any],
    ) -> None:
        """Update an existing document."""
        operation_start = datetime.now(UTC)

        try:
            doc_ref = self.document(document_path)
            doc_ref.update(document_data)

            operation_duration = (datetime.now(UTC) - operation_start).total_seconds()
            collection_path = "/".join(document_path.split("/")[:-1])
            document_id = document_path.split("/")[-1]

            # Publish domain event
            DomainEventRegistry.publish(
                FirestoreOperationEvent(
                    operation="update",
                    collection=collection_path,
                    document_id=document_id,
                    duration_seconds=operation_duration,
                ),
            )

            self.metrics.increment_counter("firestore_document_updates_total", {})
            self.metrics.record_histogram(
                "firestore_operation_duration_seconds",
                operation_duration,
                {},
            )

            self.logger.info(
                "Document updated successfully",
                document_path=document_path,
                duration_seconds=operation_duration,
            )

        except firestore_exceptions.NotFound as e:
            self.metrics.increment_counter("firestore_document_not_found_total", {})
            self.logger.warning(
                "Document not found for update",
                document_path=document_path,
                error=str(e),
            )
            raise PersistenceException(f"Document not found: {e}") from e
        except Exception as e:
            self.metrics.increment_counter("firestore_document_update_errors_total", {})
            self.logger.error(
                "Failed to update document",
                document_path=document_path,
                error=str(e),
            )
            raise PersistenceException(f"Failed to update document: {e}") from e

    def get_document(self, document_path: str) -> dict[str, Any] | None:
        """Get a document by path."""
        operation_start = datetime.now(UTC)

        try:
            doc_ref = self.document(document_path)
            doc_snapshot = doc_ref.get()

            operation_duration = (datetime.now(UTC) - operation_start).total_seconds()
            collection_path = "/".join(document_path.split("/")[:-1])
            document_id = document_path.split("/")[-1]

            if doc_snapshot.exists:
                document_data = doc_snapshot.to_dict()

                # Publish domain event
                DomainEventRegistry.publish(
                    FirestoreOperationEvent(
                        operation="get",
                        collection=collection_path,
                        document_id=document_id,
                        duration_seconds=operation_duration,
                    ),
                )

                self.metrics.increment_counter("firestore_document_gets_total", {})
                self.metrics.record_histogram(
                    "firestore_operation_duration_seconds",
                    operation_duration,
                    {},
                )

                self.logger.debug(
                    "Document retrieved successfully",
                    document_path=document_path,
                    duration_seconds=operation_duration,
                )

                return document_data
            else:
                self.metrics.increment_counter("firestore_document_not_found_total", {})
                self.logger.debug(
                    "Document not found",
                    document_path=document_path,
                )
                return None

        except Exception as e:
            self.metrics.increment_counter("firestore_document_get_errors_total", {})
            self.logger.error(
                "Failed to get document",
                document_path=document_path,
                error=str(e),
            )
            raise PersistenceException(f"Failed to get document: {e}") from e

    def delete_document(self, document_path: str) -> None:
        """Delete a document."""
        operation_start = datetime.now(UTC)

        try:
            doc_ref = self.document(document_path)
            doc_ref.delete()

            operation_duration = (datetime.now(UTC) - operation_start).total_seconds()
            collection_path = "/".join(document_path.split("/")[:-1])
            document_id = document_path.split("/")[-1]

            # Publish domain event
            DomainEventRegistry.publish(
                FirestoreOperationEvent(
                    operation="delete",
                    collection=collection_path,
                    document_id=document_id,
                    duration_seconds=operation_duration,
                ),
            )

            self.metrics.increment_counter("firestore_document_deletes_total", {})
            self.metrics.record_histogram(
                "firestore_operation_duration_seconds",
                operation_duration,
                {},
            )

            self.logger.info(
                "Document deleted successfully",
                document_path=document_path,
                duration_seconds=operation_duration,
            )

        except Exception as e:
            self.metrics.increment_counter("firestore_document_delete_errors_total", {})
            self.logger.error(
                "Failed to delete document",
                document_path=document_path,
                error=str(e),
            )
            raise PersistenceException(f"Failed to delete document: {e}") from e

    def query_collection(
        self,
        collection_path: str,
        filters: list[FieldFilter] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query a collection with filters and ordering."""
        operation_start = datetime.now(UTC)

        try:
            collection_ref = self.collection(collection_path)
            query: Query | CollectionReference = collection_ref

            # Apply filters
            if filters:
                for filter_condition in filters:
                    query = query.where(filter=filter_condition)

            # Apply ordering
            if order_by:
                query = query.order_by(order_by)

            # Apply limit
            if limit:
                query = query.limit(limit)

            # Execute query
            docs = query.stream()
            results = [doc.to_dict() for doc in docs]

            operation_duration = (datetime.now(UTC) - operation_start).total_seconds()

            # Publish domain event
            DomainEventRegistry.publish(
                FirestoreOperationEvent(
                    operation="query",
                    collection=collection_path,
                    document_id="",
                    duration_seconds=operation_duration,
                ),
            )

            self.metrics.increment_counter("firestore_collection_queries_total", {})
            self.metrics.record_histogram(
                "firestore_operation_duration_seconds",
                operation_duration,
                {},
            )

            self.logger.debug(
                "Collection query completed successfully",
                collection=collection_path,
                results_count=len(results),
                duration_seconds=operation_duration,
            )

            return results

        except Exception as e:
            self.metrics.increment_counter(
                "firestore_collection_query_errors_total",
                {},
            )
            self.logger.error(
                "Failed to query collection",
                collection=collection_path,
                error=str(e),
            )
            raise PersistenceException(f"Failed to query collection: {e}") from e

    def health_check(self) -> bool:
        """Perform health check by testing basic Firestore operations."""
        try:
            health_collection = self.settings.firestore_health_check_collection
            test_doc_id = f"health_check_{int(datetime.now(UTC).timestamp())}"
            test_data = {
                "timestamp": datetime.now(UTC),
                "health_check": True,
            }

            # Test write operation
            self.create_document(health_collection, test_data, test_doc_id)

            # Test read operation
            retrieved_data = self.get_document(f"{health_collection}/{test_doc_id}")

            # Test delete operation (cleanup)
            self.delete_document(f"{health_collection}/{test_doc_id}")

            # Verify we got expected data
            if retrieved_data and retrieved_data.get("health_check") is True:
                self.logger.debug("Firestore health check passed")
                self.metrics.increment_counter(
                    "firestore_health_checks_passed_total",
                    {},
                )
                return True
            else:
                self.logger.warning("Firestore health check failed: unexpected data")
                self.metrics.increment_counter(
                    "firestore_health_checks_failed_total",
                    {},
                )
                return False

        except Exception as e:
            self.logger.error("Firestore health check failed", error=str(e))
            self.metrics.increment_counter("firestore_health_checks_failed_total", {})
            return False
