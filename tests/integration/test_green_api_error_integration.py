"""Integration tests for GREEN-API error handling in webhook processing."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.api.app_factory import create_app

WebhookData = dict[str, Any]


@pytest.fixture
def green_api_test_client() -> TestClient:
    """FastAPI test client for GREEN-API error testing with dependency overrides."""
    from src.infrastructure.security import check_rate_limit, verify_api_key

    app = create_app()

    # Override dependencies to avoid configuration issues
    def mock_verify_api_key() -> None:
        """Mock API key verification - always passes."""
        return None

    def mock_check_rate_limit() -> None:
        """Mock rate limit check - always passes."""
        return None

    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    app.dependency_overrides[check_rate_limit] = mock_check_rate_limit

    return TestClient(app)


class TestGreenAPIErrorIntegration:
    """Integration tests for GREEN-API error handling in webhook processing."""

    @pytest.fixture
    def base_webhook_data(self) -> WebhookData:
        """Base webhook data with valid structure."""
        return {
            "typeWebhook": "incomingMessageReceived",
            "instanceData": {
                "idInstance": 7105282932,
                "wid": "27123456789@c.us",
                "typeInstance": "whatsapp",
            },
            "timestamp": 1693574400,
            "idMessage": "test_message_swe_error",
            "senderData": {
                "chatId": "27987654321-group@g.us",
                "sender": "27123456789@c.us",
                "senderName": "Error Test User",
                "chatName": "Test Group",
            },
            "messageData": {
                "typeMessage": "textMessage",
                "textMessageData": {
                    "textMessage": "Normal message without errors",
                    "isTemplateMessage": False,
                },
            },
        }

    def test_should_handle_swe001_error_in_webhook_endpoint(
        self,
        green_api_test_client: TestClient,  # pylint: disable=redefined-outer-name
        base_webhook_data: WebhookData,
    ) -> None:
        """Test SWE001 error handling through webhook endpoint."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][
            "textMessage"
        ] = "{{SWE001}} First message error on additional devices"

        # Act
        response = green_api_test_client.post(
            "/webhooks/whatsapp/message",
            json=base_webhook_data,
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "acknowledged_with_error"
        assert response_data["error_code"] == "{{SWE001}}"
        assert "First incoming message error" in response_data["error_description"]
        assert response_data["recommended_action"] == "request_message_resend"

    def test_should_handle_swe002_error_in_webhook_endpoint(
        self,
        green_api_test_client: TestClient,  # pylint: disable=redefined-outer-name
        base_webhook_data: WebhookData,
    ) -> None:
        """Test SWE002 error handling through webhook endpoint."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][
            "textMessage"
        ] = "{{SWE002}} Large file download error over 100MB"

        # Act
        response = green_api_test_client.post(
            "/webhooks/whatsapp/message",
            json=base_webhook_data,
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "acknowledged_with_error"
        assert response_data["error_code"] == "{{SWE002}}"
        assert "Large file download error" in response_data["error_description"]
        assert response_data["recommended_action"] == "check_message_on_phone"

    def test_should_handle_swe003_error_in_webhook_endpoint(
        self,
        green_api_test_client: TestClient,  # pylint: disable=redefined-outer-name
        base_webhook_data: WebhookData,
    ) -> None:
        """Test SWE003 error handling through webhook endpoint."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][
            "textMessage"
        ] = "{{SWE003}} Message decryption failed - authorization keys lost"

        # Act
        response = green_api_test_client.post(
            "/webhooks/whatsapp/message",
            json=base_webhook_data,
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "acknowledged_with_error"
        assert response_data["error_code"] == "{{SWE003}}"
        assert "authorization keys lost" in response_data["error_description"]
        assert response_data["recommended_action"] == "reauthorize_device"

    def test_should_handle_swe004_error_in_webhook_endpoint(
        self,
        green_api_test_client: TestClient,  # pylint: disable=redefined-outer-name
        base_webhook_data: WebhookData,
    ) -> None:
        """Test SWE004 error handling through webhook endpoint."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][
            "textMessage"
        ] = "{{SWE004}} Group chat error - too many members"

        # Act
        response = green_api_test_client.post(
            "/webhooks/whatsapp/message",
            json=base_webhook_data,
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "acknowledged_with_error"
        assert response_data["error_code"] == "{{SWE004}}"
        assert "exceeds 1024 members" in response_data["error_description"]
        assert response_data["recommended_action"] == "reduce_group_size"

    def test_should_handle_swe999_error_in_webhook_endpoint(
        self,
        green_api_test_client: TestClient,  # pylint: disable=redefined-outer-name
        base_webhook_data: WebhookData,
    ) -> None:
        """Test SWE999 error handling through webhook endpoint."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"][
            "textMessage"
        ] = "{{SWE999}} Incoming message without encryption keys"

        # Act
        response = green_api_test_client.post(
            "/webhooks/whatsapp/message",
            json=base_webhook_data,
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "acknowledged_with_error"
        assert response_data["error_code"] == "{{SWE999}}"
        assert "without encryption keys" in response_data["error_description"]
        assert response_data["recommended_action"] == "request_message_resend"

    def test_should_process_normal_messages_after_error_handling(
        self,
        green_api_test_client: TestClient,  # pylint: disable=redefined-outer-name
        base_webhook_data: WebhookData,
    ) -> None:
        """Test that normal messages are processed correctly after error checking."""
        # Arrange - Normal message without SWE errors
        base_webhook_data["messageData"]["textMessageData"][
            "textMessage"
        ] = "Looking for a good plumber in Cape Town. Any recommendations?"

        # Act
        response = green_api_test_client.post(
            "/webhooks/whatsapp/message",
            json=base_webhook_data,
        )

        # Assert - Should process normally (not return error response)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"
        assert "error_code" not in response_data
        assert "recommended_action" not in response_data

    def test_should_handle_swe_errors_in_individual_chats(
        self,
        green_api_test_client: TestClient,  # pylint: disable=redefined-outer-name
        base_webhook_data: WebhookData,
    ) -> None:
        """Test SWE error handling in individual (non-group) chats."""
        # Arrange - Individual chat with SWE error
        base_webhook_data["senderData"]["chatId"] = "27123456789@c.us"  # Individual chat
        base_webhook_data["messageData"]["textMessageData"][
            "textMessage"
        ] = "{{SWE001}} Error in individual chat"

        # Act
        response = green_api_test_client.post(
            "/webhooks/whatsapp/message",
            json=base_webhook_data,
        )

        # Assert - Should still handle error even in individual chats
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "acknowledged_with_error"
        assert response_data["error_code"] == "{{SWE001}}"

    def test_should_handle_swe_errors_with_simplified_webhook_format(
        self,
        green_api_test_client: TestClient,  # pylint: disable=redefined-outer-name
    ) -> None:
        """Test SWE error handling with simplified webhook format."""
        # Arrange - Simplified format with SWE error
        simplified_webhook_data = {
            "chatId": "27987654321-group@g.us",
            "senderName": "Simplified Test User",
            "textMessage": "{{SWE003}} Simplified format error message",
            "timestamp": 1693574400,
            "typeWebhook": "incomingMessageReceived",
        }

        # Act
        response = green_api_test_client.post(
            "/webhooks/whatsapp/message",
            json=simplified_webhook_data,
        )

        # Assert - Should handle error even with simplified format
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "acknowledged_with_error"
        assert response_data["error_code"] == "{{SWE003}}"

    def test_should_handle_mixed_normal_and_error_content(
        self,
        green_api_test_client: TestClient,  # pylint: disable=redefined-outer-name
        base_webhook_data: WebhookData,
    ) -> None:
        """Test handling messages with both normal content and SWE errors."""
        # Arrange
        base_webhook_data["messageData"]["textMessageData"]["textMessage"] = (
            "I was trying to send you a recommendation but got this error: "
            "{{SWE001}} and now I need to resend it."
        )

        # Act
        response = green_api_test_client.post(
            "/webhooks/whatsapp/message",
            json=base_webhook_data,
        )

        # Assert - Should detect and handle the SWE error
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "acknowledged_with_error"
        assert response_data["error_code"] == "{{SWE001}}"

    def test_should_handle_authentication_with_green_api_errors(
        self,
        green_api_test_client: TestClient,  # pylint: disable=redefined-outer-name
        base_webhook_data: WebhookData,
    ) -> None:
        """Test that SWE error handling works with mocked authentication."""
        # Arrange - SWE error message
        base_webhook_data["messageData"]["textMessageData"][
            "textMessage"
        ] = "{{SWE002}} Authentication test error"

        # Act - Request with mocked authentication
        response = green_api_test_client.post(
            "/webhooks/whatsapp/message",
            json=base_webhook_data,
        )

        # Assert - Should handle error successfully with mocked auth
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "acknowledged_with_error"
        assert response_data["error_code"] == "{{SWE002}}"

    def test_should_handle_performance_with_long_error_messages(
        self,
        green_api_test_client: TestClient,  # pylint: disable=redefined-outer-name
        base_webhook_data: WebhookData,
    ) -> None:
        """Test performance with long messages containing SWE errors."""
        # Arrange - Long message with SWE error
        long_text = "A" * 1000 + "{{SWE001}}" + "B" * 1000
        base_webhook_data["messageData"]["textMessageData"]["textMessage"] = long_text

        # Act
        response = green_api_test_client.post(
            "/webhooks/whatsapp/message",
            json=base_webhook_data,
        )

        # Assert - Should handle efficiently
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "acknowledged_with_error"
        assert response_data["error_code"] == "{{SWE001}}"
