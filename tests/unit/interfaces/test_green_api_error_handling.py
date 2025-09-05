"""Tests for GREEN-API error handling in webhook processing."""

import pytest

from src.interfaces.api.routers.webhooks import _handle_green_api_errors
from src.interfaces.api.schemas.webhooks import GreenAPIMessageWebhook

WebhookTestData = dict[str, object]


class TestGreenAPIErrorHandling:
    """Test GREEN-API specific error code detection and handling."""

    @pytest.fixture
    def base_webhook_data(self) -> WebhookTestData:
        """Base webhook data for testing."""
        return {
            "typeWebhook": "incomingMessageReceived",
            "instanceData": {
                "idInstance": 7105282932,
                "wid": "27123456789@c.us",
                "typeInstance": "whatsapp",
            },
            "timestamp": 1693574400,
            "idMessage": "test_message_123",
            "senderData": {
                "chatId": "27987654321-group@g.us",
                "sender": "27123456789@c.us",
                "senderName": "Test User",
                "chatName": "Test Group",
            },
            "messageData": {
                "typeMessage": "textMessage",
                "textMessageData": {
                    "textMessage": "Normal message",
                    "isTemplateMessage": False,
                },
            },
        }

    def test_should_return_none_for_normal_messages(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test that normal messages without SWE errors return None."""
        # Arrange
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is None

    def test_should_return_none_for_empty_text_message(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test that empty text messages return None."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"]["textMessage"] = ""  # type: ignore[index]
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is None

    def test_should_handle_swe001_first_message_error(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test handling of SWE001 - first incoming message error."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][  # type: ignore[index]
            "textMessage"
        ] = "{{SWE001}} Error receiving first message"
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is not None
        assert result["status"] == "acknowledged_with_error"
        assert result["error_code"] == "{{SWE001}}"
        assert "First incoming message error" in result["error_description"]
        assert result["recommended_action"] == "request_message_resend"

    def test_should_handle_swe002_large_file_error(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test handling of SWE002 - large file download error."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][  # type: ignore[index]
            "textMessage"
        ] = "{{SWE002}} File too large to download"
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is not None
        assert result["status"] == "acknowledged_with_error"
        assert result["error_code"] == "{{SWE002}}"
        assert "Large file download error" in result["error_description"]
        assert result["recommended_action"] == "check_message_on_phone"

    def test_should_handle_swe003_decryption_error(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test handling of SWE003 - message decryption error."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][  # type: ignore[index]
            "textMessage"
        ] = "{{SWE003}} Cannot decrypt message"
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is not None
        assert result["status"] == "acknowledged_with_error"
        assert result["error_code"] == "{{SWE003}}"
        assert "authorization keys lost" in result["error_description"]
        assert result["recommended_action"] == "reauthorize_device"

    def test_should_handle_swe004_group_size_error(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test handling of SWE004 - group size exceeded error."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][  # type: ignore[index]
            "textMessage"
        ] = "{{SWE004}} Group too large"
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is not None
        assert result["status"] == "acknowledged_with_error"
        assert result["error_code"] == "{{SWE004}}"
        assert "exceeds 1024 members" in result["error_description"]
        assert result["recommended_action"] == "reduce_group_size"

    def test_should_handle_swe999_encryption_keys_error(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test handling of SWE999 - missing encryption keys error."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][  # type: ignore[index]
            "textMessage"
        ] = "{{SWE999}} No encryption keys available"
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is not None
        assert result["status"] == "acknowledged_with_error"
        assert result["error_code"] == "{{SWE999}}"
        assert "without encryption keys" in result["error_description"]
        assert result["recommended_action"] == "request_message_resend"

    def test_should_handle_multiple_error_codes_in_message(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test that first error code found is handled when multiple exist."""
        # Arrange - Message with multiple error codes
        base_webhook_data["messageData"]["textMessageData"][  # type: ignore[index]
            "textMessage"
        ] = "{{SWE001}} First error {{SWE002}} Second error"
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert - Should handle the first error found (SWE001)
        assert result is not None
        assert result["error_code"] == "{{SWE001}}"
        assert "First incoming message error" in result["error_description"]

    def test_should_handle_error_code_with_surrounding_text(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test error detection with surrounding normal text."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][  # type: ignore[index]
            "textMessage"
        ] = "Some normal text before {{SWE003}} and after the error code"
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is not None
        assert result["error_code"] == "{{SWE003}}"

    def test_should_ignore_partial_error_codes(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test that partial or malformed error codes are ignored."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][  # type: ignore[index]
            "textMessage"
        ] = "SWE001 {SWE002} {{SWE incomplete"
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is None

    def test_should_handle_case_sensitive_error_codes(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test that error codes are case-sensitive."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][  # type: ignore[index]
            "textMessage"
        ] = "{{swe001}} lowercase should not match"
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is None

    def test_should_return_none_for_contact_messages(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test that contact messages without text return None."""
        # Arrange - Convert to contact message
        base_webhook_data["messageData"] = {
            "typeMessage": "contactMessage",
            "contactMessageData": {
                "displayName": "John Smith",
                "vcard": "BEGIN:VCARD\\nFN:John Smith\\nEND:VCARD",
            },
        }
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is None

    def test_should_include_error_message_in_response(
        self,
        base_webhook_data: WebhookTestData,
    ) -> None:
        """Test that error response includes descriptive message."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][  # type: ignore[index]
            "textMessage"
        ] = "{{SWE001}} Test error message"
        webhook = GreenAPIMessageWebhook(**base_webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert
        assert result is not None
        assert "message" in result
        assert "GREEN-API error detected" in result["message"]
        assert "First incoming message error" in result["message"]


class TestGreenAPIErrorIntegration:
    """Test GREEN-API error handling integration with webhook processing."""

    def test_should_handle_unknown_error_codes_gracefully(
        self,
    ) -> None:
        """Test that unknown SWE error codes don't break processing."""
        # Arrange - Create webhook data with unknown error code
        webhook_data = {
            "typeWebhook": "incomingMessageReceived",
            "instanceData": {
                "idInstance": 7105282932,
                "wid": "27123456789@c.us",
                "typeInstance": "whatsapp",
            },
            "timestamp": 1693574400,
            "idMessage": "test_message_123",
            "senderData": {
                "chatId": "27987654321-group@g.us",
                "sender": "27123456789@c.us",
                "senderName": "Test User",
                "chatName": "Test Group",
            },
            "messageData": {
                "typeMessage": "textMessage",
                "textMessageData": {
                    "textMessage": "{{SWE999}} Unknown future error code",
                    "isTemplateMessage": False,
                },
            },
        }
        webhook = GreenAPIMessageWebhook(**webhook_data)  # type: ignore[arg-type]

        # Act
        result = _handle_green_api_errors(webhook)

        # Assert - Should handle SWE999 (known error)
        assert result is not None
        assert result["error_code"] == "{{SWE999}}"

    def test_should_preserve_webhook_immutability(
        self,
    ) -> None:
        """Test that error processing doesn't modify webhook objects."""
        # Arrange
        webhook_data = {
            "typeWebhook": "incomingMessageReceived",
            "instanceData": {
                "idInstance": 7105282932,
                "wid": "27123456789@c.us",
                "typeInstance": "whatsapp",
            },
            "timestamp": 1693574400,
            "idMessage": "test_message_123",
            "senderData": {
                "chatId": "27987654321-group@g.us",
                "sender": "27123456789@c.us",
                "senderName": "Test User",
                "chatName": "Test Group",
            },
            "messageData": {
                "typeMessage": "textMessage",
                "textMessageData": {
                    "textMessage": "{{SWE001}} Error message",
                    "isTemplateMessage": False,
                },
            },
        }
        webhook = GreenAPIMessageWebhook(**webhook_data)  # type: ignore[arg-type]
        original_text = webhook.textMessage

        # Act
        _handle_green_api_errors(webhook)

        # Assert - Webhook should be unchanged
        assert webhook.textMessage == original_text
        assert webhook.senderName == "Test User"
        assert webhook.chatId == "27987654321-group@g.us"
