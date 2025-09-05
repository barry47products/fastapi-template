"""Tests for contact message webhook schemas."""

from typing import Any

import pytest
from pydantic import ValidationError

from src.interfaces.api.schemas.webhooks import (
    ContactMessageContent,
    ContactsArrayMessageContent,
    GreenAPIMessageWebhook,
    MessageData,
)

WebhookData = dict[str, Any]


class TestContactMessageSchemas:
    """Test contact message webhook schema validation."""

    @pytest.fixture
    def valid_contact_webhook_data(self) -> WebhookData:
        """Valid contact message webhook data."""
        return {
            "typeWebhook": "incomingMessageReceived",
            "instanceData": {
                "idInstance": 7105282932,
                "wid": "27123456789@c.us",
                "typeInstance": "whatsapp",
            },
            "timestamp": 1693574400,
            "idMessage": "contact_message_123",
            "senderData": {
                "chatId": "27987654321-group@g.us",
                "sender": "27123456789@c.us",
                "senderName": "Alice Johnson",
                "chatName": "Test Group",
            },
            "messageData": {
                "typeMessage": "contactMessage",
                "contactMessageData": {
                    "displayName": "John Smith Plumbing",
                    "vcard": "BEGIN:VCARD\nVERSION:3.0\nFN:John Smith\nTEL:+27123456789\nEND:VCARD",
                    "contactName": "John Smith",
                },
            },
        }

    @pytest.fixture
    def valid_contacts_array_webhook_data(self) -> WebhookData:
        """Valid contacts array message webhook data."""
        return {
            "typeWebhook": "incomingMessageReceived",
            "instanceData": {
                "idInstance": 7105282932,
                "wid": "27123456789@c.us",
                "typeInstance": "whatsapp",
            },
            "timestamp": 1693574400,
            "idMessage": "contacts_array_message_123",
            "senderData": {
                "chatId": "27987654321-group@g.us",
                "sender": "27123456789@c.us",
                "senderName": "Bob Wilson",
                "chatName": "Test Group",
            },
            "messageData": {
                "typeMessage": "contactsArrayMessage",
                "contactsArrayMessageData": {
                    "contacts": [
                        {
                            "displayName": "John Smith",
                            "vcard": (
                                "BEGIN:VCARD\nVERSION:3.0\n"
                                "FN:John Smith\nTEL:+27111111111\nEND:VCARD"
                            ),
                            "contactName": "John Smith",
                        },
                        {
                            "displayName": "Jane Doe",
                            "vcard": (
                                "BEGIN:VCARD\nVERSION:3.0\nFN:Jane Doe\nTEL:+27222222222\nEND:VCARD"
                            ),
                            "contactName": "Jane Doe",
                        },
                    ],
                },
            },
        }

    def test_should_parse_contact_message_webhook(
        self,
        valid_contact_webhook_data: WebhookData,
    ) -> None:
        """Test parsing valid contact message webhook."""
        # Act
        webhook = GreenAPIMessageWebhook(**valid_contact_webhook_data)

        # Assert
        assert webhook.typeWebhook == "incomingMessageReceived"
        assert webhook.messageData.typeMessage == "contactMessage"
        assert webhook.isContactMessage is True
        assert webhook.isContactsArrayMessage is False
        assert webhook.isAnyContactMessage is True

        # Check contact data
        contact = webhook.contactMessage
        assert contact is not None
        assert contact.displayName == "John Smith Plumbing"
        assert contact.contactName == "John Smith"
        assert "John Smith" in contact.vcard
        assert "+27123456789" in contact.vcard

    def test_should_parse_contacts_array_message_webhook(
        self,
        valid_contacts_array_webhook_data: WebhookData,
    ) -> None:
        """Test parsing valid contacts array message webhook."""
        # Act
        webhook = GreenAPIMessageWebhook(**valid_contacts_array_webhook_data)

        # Assert
        assert webhook.typeWebhook == "incomingMessageReceived"
        assert webhook.messageData.typeMessage == "contactsArrayMessage"
        assert webhook.isContactMessage is False
        assert webhook.isContactsArrayMessage is True
        assert webhook.isAnyContactMessage is True

        # Check contacts array data
        contacts_array = webhook.contactsArrayMessage
        assert contacts_array is not None
        assert len(contacts_array.contacts) == 2

        # Check first contact
        first_contact = contacts_array.contacts[0]
        assert first_contact.displayName == "John Smith"
        assert first_contact.contactName == "John Smith"
        assert "+27111111111" in first_contact.vcard

        # Check second contact
        second_contact = contacts_array.contacts[1]
        assert second_contact.displayName == "Jane Doe"
        assert second_contact.contactName == "Jane Doe"
        assert "+27222222222" in second_contact.vcard

    def test_should_handle_text_message_webhook_properties(
        self,
        valid_contact_webhook_data: WebhookData,
    ) -> None:
        """Test that contact webhooks handle text message properties correctly."""
        # Arrange - Convert to text message
        valid_contact_webhook_data["messageData"] = {
            "typeMessage": "textMessage",
            "textMessageData": {
                "textMessage": "Hello world",
                "isTemplateMessage": False,
            },
        }

        # Act
        webhook = GreenAPIMessageWebhook(**valid_contact_webhook_data)

        # Assert
        assert webhook.isContactMessage is False
        assert webhook.isContactsArrayMessage is False
        assert webhook.isAnyContactMessage is False
        assert webhook.textMessage == "Hello world"
        assert webhook.contactMessage is None
        assert webhook.contactsArrayMessage is None

    def test_should_validate_contact_message_content(self) -> None:
        """Test ContactMessageContent validation."""
        # Valid contact
        valid_contact = ContactMessageContent(
            displayName="John Smith",
            vcard="BEGIN:VCARD\nFN:John Smith\nEND:VCARD",
            contactName="John Smith",
        )

        assert valid_contact.displayName == "John Smith"
        assert valid_contact.contactName == "John Smith"
        assert "John Smith" in valid_contact.vcard

    def test_should_validate_contacts_array_content(self) -> None:
        """Test ContactsArrayMessageContent validation."""
        # Valid contacts array
        contacts = [
            ContactMessageContent(
                displayName="Contact 1",
                vcard="BEGIN:VCARD\nFN:Contact 1\nEND:VCARD",
            ),
            ContactMessageContent(
                displayName="Contact 2",
                vcard="BEGIN:VCARD\nFN:Contact 2\nEND:VCARD",
            ),
        ]

        array_content = ContactsArrayMessageContent(contacts=contacts)

        assert len(array_content.contacts) == 2
        assert array_content.contacts[0].displayName == "Contact 1"
        assert array_content.contacts[1].displayName == "Contact 2"

    def test_should_require_display_name_in_contact(self) -> None:
        """Test that displayName is required in contact message."""
        with pytest.raises(ValidationError) as exc_info:
            ContactMessageContent(  # type: ignore[call-arg]
                vcard="BEGIN:VCARD\nEND:VCARD",
            )

        assert "displayName" in str(exc_info.value)

    def test_should_require_vcard_in_contact(self) -> None:
        """Test that vcard is required in contact message."""
        with pytest.raises(ValidationError) as exc_info:
            ContactMessageContent(  # type: ignore[call-arg]
                displayName="John Smith",
            )

        assert "vcard" in str(exc_info.value)

    def test_should_allow_optional_contact_name(self) -> None:
        """Test that contactName is optional in contact message."""
        # Act
        contact = ContactMessageContent(
            displayName="John Smith",
            vcard="BEGIN:VCARD\nFN:John Smith\nEND:VCARD",
            # contactName omitted
        )

        # Assert
        assert contact.displayName == "John Smith"
        assert contact.contactName is None

    def test_should_handle_message_data_with_contact_fields(self) -> None:
        """Test MessageData with contact message fields."""
        # Act
        message_data = MessageData(
            typeMessage="contactMessage",
            contactMessageData=ContactMessageContent(
                displayName="Test Contact",
                vcard="BEGIN:VCARD\nFN:Test\nEND:VCARD",
            ),
        )

        # Assert
        assert message_data.typeMessage == "contactMessage"
        assert message_data.contactMessageData is not None
        assert message_data.contactMessageData.displayName == "Test Contact"
        assert message_data.textMessageData is None
        assert message_data.contactsArrayMessageData is None

    def test_should_handle_message_data_with_contacts_array_fields(self) -> None:
        """Test MessageData with contacts array message fields."""
        # Act
        message_data = MessageData(
            typeMessage="contactsArrayMessage",
            contactsArrayMessageData=ContactsArrayMessageContent(
                contacts=[
                    ContactMessageContent(
                        displayName="Contact 1",
                        vcard="BEGIN:VCARD\nFN:Contact 1\nEND:VCARD",
                    ),
                ],
            ),
        )

        # Assert
        assert message_data.typeMessage == "contactsArrayMessage"
        assert message_data.contactsArrayMessageData is not None
        assert len(message_data.contactsArrayMessageData.contacts) == 1
        assert message_data.textMessageData is None
        assert message_data.contactMessageData is None

    def test_should_handle_empty_contacts_array(self) -> None:
        """Test handling contacts array with no contacts."""
        # Act
        array_content = ContactsArrayMessageContent(contacts=[])

        # Assert
        assert len(array_content.contacts) == 0

    def test_should_preserve_webhook_immutability(
        self,
        valid_contact_webhook_data: WebhookData,
    ) -> None:
        """Test that contact webhook objects are immutable."""
        # Act
        webhook = GreenAPIMessageWebhook(**valid_contact_webhook_data)

        # Assert - Pydantic frozen models raise ValidationError on direct assignment
        with pytest.raises(ValidationError):
            webhook.typeWebhook = "modified"  # type: ignore[assignment,misc]

        # Contact message should exist for this test
        assert webhook.contactMessage is not None
        with pytest.raises(ValidationError):
            webhook.contactMessage.displayName = "Modified Name"  # type: ignore[misc]
