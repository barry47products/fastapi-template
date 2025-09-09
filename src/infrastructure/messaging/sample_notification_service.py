"""Sample notification service for template demonstration."""

from datetime import UTC, datetime
from typing import Any

from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import MessageDeliveryException


class SampleNotificationService:
    """
    Sample notification service demonstrating messaging patterns.

    This service shows how to implement notification/messaging infrastructure
    without external dependencies. In production, replace with actual services
    like email providers, SMS gateways, push notification services, etc.
    """

    def __init__(self) -> None:
        """Initialize notification service."""
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()
        self._sent_messages: list[dict[str, Any]] = []

    def send_email_notification(
        self,
        recipient_email: str,
        subject: str,
        message: str,
        priority: str = "normal",
    ) -> dict[str, str]:
        """
        Send email notification.

        Args:
            recipient_email: Email address to send to
            subject: Email subject line
            message: Email body content
            priority: Message priority (low, normal, high)

        Returns:
            Response with message ID and status

        Raises:
            MessageDeliveryException: If sending fails
        """
        operation_start = datetime.now(UTC)

        try:
            self.logger.info(
                "Sending email notification",
                recipient_email=self._mask_email(recipient_email),
                subject=subject[:50] + "..." if len(subject) > 50 else subject,
                priority=priority,
            )

            # Simulate email sending logic
            message_id = f"email_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{len(self._sent_messages) + 1:04d}"

            # Store message for demonstration
            message_record = {
                "id": message_id,
                "type": "email",
                "recipient": recipient_email,
                "subject": subject,
                "message": message,
                "priority": priority,
                "sent_at": datetime.now(UTC),
                "status": "sent",
            }
            self._sent_messages.append(message_record)

            operation_duration = (datetime.now(UTC) - operation_start).total_seconds()

            self.metrics.increment_counter("email_notifications_sent_total", {"priority": priority})
            self.metrics.record_histogram(
                "notification_send_duration_seconds",
                operation_duration,
                {"type": "email"},
            )

            self.logger.info(
                "Email notification sent successfully",
                message_id=message_id,
                duration_seconds=operation_duration,
            )

            return {
                "message_id": message_id,
                "status": "sent",
                "recipient": self._mask_email(recipient_email),
                "sent_at": operation_start.isoformat(),
            }

        except Exception as e:
            self.metrics.increment_counter("email_send_errors_total", {})
            self.logger.error(
                "Failed to send email notification",
                recipient_email=self._mask_email(recipient_email),
                error=str(e),
            )
            raise MessageDeliveryException(f"Failed to send email: {e}") from e

    def send_sms_notification(
        self,
        phone_number: str,
        message: str,
        priority: str = "normal",
    ) -> dict[str, str]:
        """
        Send SMS notification.

        Args:
            phone_number: Phone number to send SMS to
            message: SMS message content
            priority: Message priority (low, normal, high)

        Returns:
            Response with message ID and status
        """
        operation_start = datetime.now(UTC)

        try:
            self.logger.info(
                "Sending SMS notification",
                phone_number=self._mask_phone(phone_number),
                message_length=len(message),
                priority=priority,
            )

            # Simulate SMS sending logic
            message_id = f"sms_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{len(self._sent_messages) + 1:04d}"

            # Store message for demonstration
            message_record = {
                "id": message_id,
                "type": "sms",
                "recipient": phone_number,
                "message": message,
                "priority": priority,
                "sent_at": datetime.now(UTC),
                "status": "sent",
            }
            self._sent_messages.append(message_record)

            operation_duration = (datetime.now(UTC) - operation_start).total_seconds()

            self.metrics.increment_counter("sms_notifications_sent_total", {"priority": priority})
            self.metrics.record_histogram(
                "notification_send_duration_seconds",
                operation_duration,
                {"type": "sms"},
            )

            self.logger.info(
                "SMS notification sent successfully",
                message_id=message_id,
                duration_seconds=operation_duration,
            )

            return {
                "message_id": message_id,
                "status": "sent",
                "recipient": self._mask_phone(phone_number),
                "sent_at": operation_start.isoformat(),
            }

        except Exception as e:
            self.metrics.increment_counter("sms_send_errors_total", {})
            self.logger.error(
                "Failed to send SMS notification",
                phone_number=self._mask_phone(phone_number),
                error=str(e),
            )
            raise MessageDeliveryException(f"Failed to send SMS: {e}") from e

    def send_push_notification(
        self,
        device_token: str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """
        Send push notification.

        Args:
            device_token: Device token for push notification
            title: Notification title
            message: Notification message
            data: Optional additional data payload

        Returns:
            Response with message ID and status
        """
        operation_start = datetime.now(UTC)

        try:
            self.logger.info(
                "Sending push notification",
                device_token=self._mask_token(device_token),
                title=title[:30] + "..." if len(title) > 30 else title,
                has_data=data is not None,
            )

            # Simulate push notification sending logic
            message_id = f"push_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{len(self._sent_messages) + 1:04d}"

            # Store message for demonstration
            message_record = {
                "id": message_id,
                "type": "push",
                "recipient": device_token,
                "title": title,
                "message": message,
                "data": data or {},
                "sent_at": datetime.now(UTC),
                "status": "sent",
            }
            self._sent_messages.append(message_record)

            operation_duration = (datetime.now(UTC) - operation_start).total_seconds()

            self.metrics.increment_counter("push_notifications_sent_total", {})
            self.metrics.record_histogram(
                "notification_send_duration_seconds",
                operation_duration,
                {"type": "push"},
            )

            self.logger.info(
                "Push notification sent successfully",
                message_id=message_id,
                duration_seconds=operation_duration,
            )

            return {
                "message_id": message_id,
                "status": "sent",
                "device_token": self._mask_token(device_token),
                "sent_at": operation_start.isoformat(),
            }

        except Exception as e:
            self.metrics.increment_counter("push_send_errors_total", {})
            self.logger.error(
                "Failed to send push notification",
                device_token=self._mask_token(device_token),
                error=str(e),
            )
            raise MessageDeliveryException(f"Failed to send push notification: {e}") from e

    def get_message_status(self, message_id: str) -> dict[str, Any] | None:
        """
        Get status of a sent message.

        Args:
            message_id: ID of the message to check

        Returns:
            Message status information or None if not found
        """
        try:
            for message in self._sent_messages:
                if message["id"] == message_id:
                    return {
                        "id": message["id"],
                        "type": message["type"],
                        "status": message["status"],
                        "sent_at": message["sent_at"].isoformat(),
                    }

            self.logger.debug("Message not found", message_id=message_id)
            return None

        except Exception as e:
            self.logger.error(
                "Failed to get message status",
                message_id=message_id,
                error=str(e),
            )
            return None

    def get_sent_messages_count(self) -> dict[str, int]:
        """Get count of sent messages by type."""
        try:
            counts = {"email": 0, "sms": 0, "push": 0}
            for message in self._sent_messages:
                message_type = message.get("type", "unknown")
                if message_type in counts:
                    counts[message_type] += 1

            return counts

        except Exception as e:
            self.logger.error("Failed to get message counts", error=str(e))
            return {"email": 0, "sms": 0, "push": 0}

    def is_healthy(self) -> bool:
        """
        Check if notification service is healthy.

        Returns:
            True if service is ready to send notifications
        """
        try:
            # Basic health check - verify service is initialized
            return True

        except Exception as e:
            self.logger.error("Notification service health check failed", error=str(e))
            return False

    def _mask_email(self, email: str) -> str:
        """Mask email address for privacy-safe logging."""
        if "@" in email:
            local, domain = email.split("@", 1)
            if len(local) > 2:
                return f"{local[0]}***{local[-1]}@{domain}"
            return f"***@{domain}"
        return "***"

    def _mask_phone(self, phone: str) -> str:
        """Mask phone number for privacy-safe logging."""
        if len(phone) > 4:
            return f"***{phone[-4:]}"
        return "***"

    def _mask_token(self, token: str) -> str:
        """Mask device token for privacy-safe logging."""
        if len(token) > 8:
            return f"{token[:4]}...{token[-4:]}"
        return "***"
