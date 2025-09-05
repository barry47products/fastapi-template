"""GREEN-API WhatsApp client with domain events integration."""

from datetime import datetime, UTC
from typing import Any

from whatsapp_api_client_python import API

from config.settings import get_settings, GreenAPISettings
from src.domain.events.persistence_events import FirestoreOperationEvent
from src.domain.events.registry import DomainEventRegistry
from src.domain.value_objects import GroupID
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import WhatsAppException


class GreenAPIException(WhatsAppException):
    """Exception raised for GREEN-API related errors."""

    error_code: str = "GREEN_API_ERROR"


class GreenAPIClient:
    """
    GREEN-API WhatsApp client wrapper.
    Provides clean interface for WhatsApp messaging with domain event publishing,
    metrics collection, and error handling.
    """

    def __init__(self, settings: GreenAPISettings | None = None) -> None:
        """
        Initialize GREEN-API client.

        Args:
            settings: GREEN-API configuration settings. If None, loads from global settings.
        """
        if settings is None:
            app_settings = get_settings()
            settings = app_settings.green_api

        self.settings = settings
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()

        # Initialize GREEN-API client if configured
        self._client = None
        if (
            hasattr(self.settings, "instance_id")
            and self.settings.instance_id
            and hasattr(self.settings, "api_token")
            and self.settings.api_token
        ):
            try:
                self._client = API.GreenAPI(
                    idInstance=self.settings.instance_id,
                    apiTokenInstance=self.settings.api_token,
                )
                self.logger.info(
                    "GREEN-API client initialized successfully",
                    instance_id=self.settings.instance_id[:8] + "...",  # Privacy-safe logging
                )
            except Exception as e:
                self.logger.error(
                    "Failed to initialize GREEN-API client",
                    error=str(e),
                )
                raise GreenAPIException(f"Failed to initialize GREEN-API client: {e}") from e
        else:
            self.logger.warning(
                "GREEN-API client not configured - instance_id or api_token missing",
            )

    @property
    def client(self) -> Any:
        """Get the GREEN-API client instance."""
        return self._client

    def send_message(self, chat_id: str, message: str) -> dict[str, Any]:
        """
        Send a text message to a WhatsApp chat.

        Args:
            chat_id: WhatsApp chat ID (e.g., "1234567890@c.us" for individual,
                    "1234567890@g.us" for group)
            message: Text message to send

        Returns:
            Response from GREEN-API

        Raises:
            GreenAPIException: If client is not configured or request fails
        """
        operation_start = datetime.now(UTC)

        if not self._client:
            self.metrics.increment_counter("green_api_not_configured_total", {})
            raise GreenAPIException("GREEN-API client not configured")

        try:
            self.logger.info(
                "Sending WhatsApp message",
                chat_id=self._mask_chat_id(chat_id),
                message_length=len(message),
            )

            response = self._client.sending.sendMessage(chat_id, message)
            response_data: dict[str, Any] = response.json()

            operation_duration = (datetime.now(UTC) - operation_start).total_seconds()

            # Publish domain event
            DomainEventRegistry.publish(
                FirestoreOperationEvent(
                    operation="whatsapp_message_sent",
                    collection="whatsapp_messages",
                    document_id=str(response_data.get("idMessage", "")),
                    duration_seconds=operation_duration,
                ),
            )

            self.metrics.increment_counter("green_api_messages_sent_total", {})
            self.metrics.record_histogram(
                "green_api_operation_duration_seconds",
                operation_duration,
                {},
            )

            self.logger.info(
                "WhatsApp message sent successfully",
                message_id=response_data.get("idMessage"),
                duration_seconds=operation_duration,
            )

            return response_data

        except Exception as e:
            self.metrics.increment_counter("green_api_send_errors_total", {})
            self.logger.error(
                "Failed to send WhatsApp message",
                chat_id=self._mask_chat_id(chat_id),
                error=str(e),
            )
            raise GreenAPIException(f"Failed to send WhatsApp message: {e}") from e

    def send_group_message(self, group_id: GroupID, message: str) -> dict[str, Any]:
        """
        Send a message to a WhatsApp group.

        Args:
            group_id: WhatsApp group identifier
            message: Text message to send

        Returns:
            Response from GREEN-API
        """
        return self.send_message(group_id.value, message)

    def is_healthy(self) -> bool:
        """
        Check if GREEN-API client is healthy and configured.

        Returns:
            True if client is configured and ready to send messages
        """
        try:
            if not self.settings.is_configured:
                return False

            if not self.client:
                return False

            # Could add a ping/status check here if GREEN-API supports it
            return True

        except Exception as e:
            self.logger.error(
                "GREEN-API health check failed",
                error=str(e),
            )
            return False

    def get_instance_info(self) -> dict[str, Any]:
        """
        Get GREEN-API instance information for health monitoring.

        Returns:
            Instance information dict or empty dict if not configured
        """
        if not self.client:
            return {}

        try:
            # This would be implementation-specific based on GREEN-API capabilities
            return {
                "instance_id": self.settings.instance_id[:8] + "...",
                "configured": True,
                "base_url": self.settings.base_url,
            }
        except Exception as e:
            self.logger.error(
                "Failed to get GREEN-API instance info",
                error=str(e),
            )
            return {"configured": False, "error": str(e)}

    def _mask_chat_id(self, chat_id: str) -> str:
        """
        Mask chat ID for privacy-safe logging.

        Args:
            chat_id: Original chat ID

        Returns:
            Masked chat ID for logging
        """
        if "@" in chat_id:
            prefix, suffix = chat_id.split("@", 1)
            if len(prefix) > 4:
                return f"{prefix[:2]}...{prefix[-2:]}@{suffix}"
            return f"***@{suffix}"
        return "***"
