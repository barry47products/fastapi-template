"""Integration tests for contact card webhook processing."""

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.api.app_factory import create_app

WebhookData = dict[str, Any]


@pytest.fixture
def whatsapp_test_client() -> TestClient:
    """FastAPI test client for WhatsApp integration testing with dependency overrides."""
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


class TestContactWebhookIntegration:
    """Integration tests for contact card webhook processing."""

    @pytest.fixture
    def valid_contact_webhook(self) -> WebhookData:
        """Valid contact message webhook payload."""
        return {
            "typeWebhook": "incomingMessageReceived",
            "instanceData": {
                "idInstance": 7105282932,
                "wid": "27123456789@c.us",
                "typeInstance": "whatsapp",
            },
            "timestamp": 1693574400,
            "idMessage": "contact_message_test",
            "senderData": {
                "chatId": "27987654321-group@g.us",
                "sender": "27123456789@c.us",
                "senderName": "Alice Johnson",
                "chatName": "NA Test Group",
            },
            "messageData": {
                "typeMessage": "contactMessage",
                "contactMessageData": {
                    "displayName": "John Smith Plumbing",
                    "vcard": """BEGIN:VCARD
VERSION:3.0
FN:John Smith
TEL:+27123456789
ORG:Plumbing Services
EMAIL:john@example.com
END:VCARD""",
                    "contactName": "John Smith",
                },
            },
        }

    @pytest.fixture
    def valid_contacts_array_webhook(self) -> WebhookData:
        """Valid contacts array webhook payload."""
        return {
            "typeWebhook": "incomingMessageReceived",
            "instanceData": {
                "idInstance": 7105282932,
                "wid": "27123456789@c.us",
                "typeInstance": "whatsapp",
            },
            "timestamp": 1693574400,
            "idMessage": "contacts_array_test",
            "senderData": {
                "chatId": "27987654321-group@g.us",
                "sender": "27111111111@c.us",
                "senderName": "Bob Wilson",
                "chatName": "NA Test Group",
            },
            "messageData": {
                "typeMessage": "contactsArrayMessage",
                "contactsArrayMessageData": {
                    "contacts": [
                        {
                            "displayName": "Plumber John",
                            "vcard": """BEGIN:VCARD
VERSION:3.0
FN:John Smith
TEL:+27123456789
ORG:Plumbing Services
END:VCARD""",
                        },
                        {
                            "displayName": "Electrician Jane",
                            "vcard": """BEGIN:VCARD
VERSION:3.0
FN:Jane Doe
TEL:+27987654321
ORG:Electrical Services
END:VCARD""",
                        },
                    ],
                },
            },
        }

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_process_contact_message_successfully(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contact_webhook: WebhookData,
    ) -> None:
        """Test successful processing of contact message webhook."""
        # Arrange - Mock metrics to verify they're called
        with patch("src.interfaces.api.routers.webhooks.metrics") as mock_metrics:
            # Act
            response = whatsapp_test_client.post(
                "/webhooks/whatsapp/message",
                json=valid_contact_webhook,
            )

            # Assert
            assert response.status_code == 200
            response_data = response.json()

            # Check response structure
            assert "status" in response_data
            assert "action" in response_data
            assert "processing_time_ms" in response_data

            # Should indicate contact endorsement processing
            assert response_data["status"] == "processed"
            assert "contact_endorsement" in response_data["action"]

            # Performance validation
            processing_time_ms = float(response_data["processing_time_ms"])
            assert 0 < processing_time_ms < 5000

            # Verify metrics were recorded
            mock_metrics.increment_counter.assert_called()
            mock_metrics.record_histogram.assert_called()

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_process_contacts_array_message_successfully(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contacts_array_webhook: WebhookData,
    ) -> None:
        """Test successful processing of contacts array message webhook."""
        # Arrange - Mock metrics to verify they're called
        with patch("src.interfaces.api.routers.webhooks.metrics") as mock_metrics:
            # Act
            response = whatsapp_test_client.post(
                "/webhooks/whatsapp/message",
                json=valid_contacts_array_webhook,
            )

            # Assert
            assert response.status_code == 200
            response_data = response.json()

            # Check response structure
            assert "status" in response_data
            assert "action" in response_data
            assert "processing_time_ms" in response_data

            # Should indicate contact endorsement processing
            assert response_data["status"] == "processed"
            assert "contact_endorsement" in response_data["action"]

            # Performance validation
            processing_time_ms = float(response_data["processing_time_ms"])
            assert 0 < processing_time_ms < 5000

            # Verify metrics were recorded
            mock_metrics.increment_counter.assert_called()
            mock_metrics.record_histogram.assert_called()

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_handle_contact_message_in_individual_chat(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contact_webhook: WebhookData,
    ) -> None:
        """Test contact message in individual chat (should be skipped)."""
        # Arrange - Change to individual chat
        valid_contact_webhook["senderData"]["chatId"] = "27123456789@c.us"  # Individual chat

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contact_webhook,
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()

        # Should skip individual messages
        assert response_data["status"] == "processed"
        assert "individual_message" in response_data["action"]

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_handle_malformed_contact_message(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contact_webhook: WebhookData,
    ) -> None:
        """Test handling malformed contact message."""
        # Arrange - Corrupt the contact data
        valid_contact_webhook["messageData"]["contactMessageData"]["vcard"] = "Invalid vCard"

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contact_webhook,
        )

        # Assert - Should still process successfully (graceful degradation)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_handle_contact_message_without_phone(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contact_webhook: WebhookData,
    ) -> None:
        """Test contact message with vCard that has no phone number."""
        # Arrange - vCard without phone
        valid_contact_webhook["messageData"]["contactMessageData"][
            "vcard"
        ] = """BEGIN:VCARD
VERSION:3.0
FN:No Phone Person
EMAIL:nophone@example.com
END:VCARD"""

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contact_webhook,
        )

        # Assert - Should still process successfully
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_handle_empty_contacts_array(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contacts_array_webhook: WebhookData,
    ) -> None:
        """Test contacts array message with no contacts."""
        # Arrange - Empty contacts array
        valid_contacts_array_webhook["messageData"]["contactsArrayMessageData"]["contacts"] = []

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contacts_array_webhook,
        )

        # Assert - Should process but log warning
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_handle_mixed_valid_invalid_contacts_in_array(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contacts_array_webhook: WebhookData,
    ) -> None:
        """Test contacts array with mix of valid and invalid contacts."""
        # Arrange - Add invalid contact to array
        valid_contacts_array_webhook["messageData"]["contactsArrayMessageData"]["contacts"].append(
            {
                "displayName": "Invalid Contact",
                "vcard": "This is not a vCard",
            },
        )

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contacts_array_webhook,
        )

        # Assert - Should still process successfully (graceful handling)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_handle_missing_contact_message_data(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contact_webhook: WebhookData,
    ) -> None:
        """Test contact message webhook with missing contactMessageData."""
        # Arrange - Remove contact data
        valid_contact_webhook["messageData"] = {
            "typeMessage": "contactMessage",
            # contactMessageData missing
        }

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contact_webhook,
        )

        # Assert - Should still process (no contact data found)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.performance
    def test_should_process_large_contacts_array_efficiently(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contacts_array_webhook: WebhookData,
    ) -> None:
        """Test processing large contacts array efficiently."""
        # Arrange - Create large contacts array
        large_contacts = []
        for i in range(50):  # 50 contacts
            large_contacts.append(
                {
                    "displayName": f"Contact {i}",
                    "vcard": f"""BEGIN:VCARD
VERSION:3.0
FN:Contact {i}
TEL:+2712345{i:04d}
ORG:Service Provider {i}
END:VCARD""",
                },
            )

        contacts_data = valid_contacts_array_webhook["messageData"]["contactsArrayMessageData"]
        contacts_data["contacts"] = large_contacts

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contacts_array_webhook,
        )

        # Assert - Should process efficiently
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"

        # Performance validation - should complete within 10 seconds even for 50 contacts
        processing_time_ms = float(response_data["processing_time_ms"])
        assert processing_time_ms < 10000  # 10 seconds max

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_maintain_backward_compatibility_with_text_messages(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contact_webhook: WebhookData,
    ) -> None:
        """Test that contact message support doesn't break text message processing."""
        # Arrange - Convert to text message
        valid_contact_webhook["messageData"] = {
            "typeMessage": "textMessage",
            "textMessageData": {
                "textMessage": "I recommend John the plumber 082-123-4567!",
                "isTemplateMessage": False,
            },
        }

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contact_webhook,
        )

        # Assert - Should process as regular text endorsement
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"
        assert "group_endorsement" in response_data["action"]  # Not contact_endorsement

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_handle_contact_with_multiple_service_types(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contact_webhook: WebhookData,
    ) -> None:
        """Test contact with multiple service classifications (plumber + electrician)."""
        # Arrange - Contact that offers multiple services
        valid_contact_webhook["messageData"]["contactMessageData"] = {
            "displayName": "MultiService Pro",
            "vcard": """BEGIN:VCARD
VERSION:3.0
FN:John Multi
TEL:+27123456789
ORG:Plumbing & Electrical Services
TITLE:Licensed Plumber & Electrician
EMAIL:john@multiservice.co.za
END:VCARD""",
            "contactName": "John Multi",
        }

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contact_webhook,
        )

        # Assert - Should process and extract multiple service types
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"
        assert "contact_endorsement" in response_data["action"]

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_handle_contact_with_international_phone_format(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contact_webhook: WebhookData,
    ) -> None:
        """Test contact with international phone number formatting variations."""
        # Arrange - Contact with various phone formats
        valid_contact_webhook["messageData"]["contactMessageData"] = {
            "displayName": "International Plumber",
            "vcard": """BEGIN:VCARD
VERSION:3.0
FN:Global Services
TEL;TYPE=WORK:+27-11-123-4567
TEL;TYPE=CELL:(082) 987-6543
TEL;TYPE=HOME:011 555 0123
ORG:Global Plumbing
EMAIL:global@plumbing.com
END:VCARD""",
            "contactName": "Global Services",
        }

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contact_webhook,
        )

        # Assert - Should normalize and process all phone formats
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"
        assert "contact_endorsement" in response_data["action"]

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_handle_contact_from_different_group_types(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contact_webhook: WebhookData,
    ) -> None:
        """Test contact shared in different neighbourhood group types."""
        # Arrange - Contact from estate/suburb group vs community group
        valid_contact_webhook["senderData"]["chatName"] = "Sandton Estate Residents"
        valid_contact_webhook["senderData"]["chatId"] = "27111223344-estate@g.us"

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contact_webhook,
        )

        # Assert - Should process regardless of group type
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"
        assert "contact_endorsement" in response_data["action"]

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_handle_contact_with_comprehensive_business_info(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contact_webhook: WebhookData,
    ) -> None:
        """Test contact with complete business information (address, website, hours)."""
        # Arrange - Comprehensive business contact
        valid_contact_webhook["messageData"]["contactMessageData"] = {
            "displayName": "Premium Plumbing Services",
            "vcard": """BEGIN:VCARD
VERSION:3.0
FN:Premium Plumbing Services
ORG:Premium Plumbing (Pty) Ltd
TITLE:24/7 Emergency Plumbing
TEL;TYPE=WORK:+27-11-123-4567
TEL;TYPE=CELL:+27-82-987-6543
EMAIL:info@premiumplumbing.co.za
URL:https://premiumplumbing.co.za
ADR;TYPE=WORK:;;123 Main St;Johannesburg;Gauteng;2000;South Africa
NOTE:Licensed plumber with 15 years experience. Available 24/7.
END:VCARD""",
            "contactName": "Premium Plumbing Services",
        }

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contact_webhook,
        )

        # Assert - Should extract comprehensive business data
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"
        assert "contact_endorsement" in response_data["action"]

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.fast
    def test_should_handle_contacts_array_with_mixed_service_types(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contacts_array_webhook: WebhookData,
    ) -> None:
        """Test contacts array containing different service provider types."""
        # Arrange - Mixed service types in array
        mixed_contacts = [
            {
                "displayName": "Emergency Plumber",
                "vcard": """BEGIN:VCARD
VERSION:3.0
FN:Emergency Plumbing
TEL:+27821234567
ORG:24/7 Plumbing Services
END:VCARD""",
            },
            {
                "displayName": "Master Electrician",
                "vcard": """BEGIN:VCARD
VERSION:3.0
FN:Electrical Expert
TEL:+27829876543
ORG:Certified Electrical Solutions
EMAIL:master@electrical.co.za
END:VCARD""",
            },
            {
                "displayName": "Garden Services",
                "vcard": """BEGIN:VCARD
VERSION:3.0
FN:Green Thumb Gardens
TEL:+27821112233
ORG:Landscaping & Maintenance
END:VCARD""",
            },
        ]

        contacts_data = valid_contacts_array_webhook["messageData"]["contactsArrayMessageData"]
        contacts_data["contacts"] = mixed_contacts

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contacts_array_webhook,
        )

        # Assert - Should process all different service types
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"
        assert "contact_endorsement" in response_data["action"]

    @pytest.mark.integration
    @pytest.mark.whatsapp
    @pytest.mark.resilience
    def test_should_handle_contact_with_unicode_and_special_characters(
        self,
        whatsapp_test_client: TestClient,  # pylint: disable=redefined-outer-name
        valid_contact_webhook: WebhookData,
    ) -> None:
        """Test contact with unicode characters and special formatting."""
        # Arrange - Contact with South African names and special characters
        valid_contact_webhook["messageData"]["contactMessageData"] = {
            "displayName": "Thabo's Plumbing & Geyser Repairs",
            "vcard": """BEGIN:VCARD
VERSION:3.0
FN:Thabo Mthembu
ORG:Thabo's Plumbing & Geyser Repairs (Pty) Ltd
TITLE:Certified Plumber & Geyser Specialist
TEL:+27-82-123-4567
EMAIL:thabo@plumbing.co.za
NOTE:Geyser installations & repairs. Mon-Fri 7AM-6PM, Sat 8AM-2PM.
END:VCARD""",
            "contactName": "Thabo Mthembu",
        }

        # Act
        response = whatsapp_test_client.post(
            "/webhooks/whatsapp/message",
            json=valid_contact_webhook,
        )

        # Assert - Should handle unicode and special characters
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "processed"
        assert "contact_endorsement" in response_data["action"]
