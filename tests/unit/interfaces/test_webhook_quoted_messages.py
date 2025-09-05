"""Tests for quoted/reply message webhook schemas."""

import pytest
from pydantic import ValidationError

from src.interfaces.api.schemas.webhooks import (
    ContactMessageContent,
    ExtendedTextMessageContent,
    GreenAPIMessageWebhook,
    InstanceData,
    MessageData,
    SenderData,
    TextMessageContent,
)


class TestQuotedMessageWebhookSchemas:
    """Test quoted/reply message webhook schema validation."""

    def test_should_parse_quoted_message_webhook(self) -> None:
        """Test parsing webhook with quoted message data."""
        webhook = GreenAPIMessageWebhook(
            typeWebhook="incomingMessageReceived",
            instanceData=InstanceData(
                idInstance=123456,
                wid="27123456789@c.us",
                typeInstance="whatsapp",
            ),
            timestamp=1234567890,
            idMessage="msg_quoted_123",
            senderData=SenderData(
                chatId="27123456789-group@g.us",
                sender="27987654321@c.us",
                senderName="John Doe",
                chatName="Test Group",
            ),
            messageData=MessageData(
                typeMessage="quotedMessage",
                extendedTextMessageData=ExtendedTextMessageContent(
                    text="Here's the plumber you asked for",
                    stanzaId="original_msg_456",
                    participant="27111222333@c.us",
                ),
            ),
        )

        assert webhook.isQuotedMessage is True
        assert webhook.quotedMessageId == "original_msg_456"
        assert webhook.quotedMessageParticipant == "27111222333@c.us"
        assert webhook.replyText == "Here's the plumber you asked for"

    def test_should_handle_non_quoted_messages(self) -> None:
        """Test that non-quoted messages return None for quote properties."""
        webhook = GreenAPIMessageWebhook(
            typeWebhook="incomingMessageReceived",
            instanceData=InstanceData(
                idInstance=123456,
                wid="27123456789@c.us",
                typeInstance="whatsapp",
            ),
            timestamp=1234567890,
            idMessage="msg_text_789",
            senderData=SenderData(
                chatId="27123456789-group@g.us",
                sender="27987654321@c.us",
                senderName="Jane Smith",
                chatName="Test Group",
            ),
            messageData=MessageData(
                typeMessage="textMessage",
                textMessageData=TextMessageContent(
                    textMessage="Regular message without quote",
                ),
            ),
        )

        assert webhook.isQuotedMessage is False
        assert webhook.quotedMessageId is None
        assert webhook.quotedMessageParticipant is None
        assert webhook.replyText == ""

    def test_should_validate_extended_text_message_fields(self) -> None:
        """Test ExtendedTextMessageContent field validation."""
        # Valid extended text message
        extended_msg = ExtendedTextMessageContent(
            text="Reply text content",
            stanzaId="msg_id_123",
            participant="27123456789@c.us",
        )

        assert extended_msg.text == "Reply text content"
        assert extended_msg.stanzaId == "msg_id_123"
        assert extended_msg.participant == "27123456789@c.us"

    def test_should_require_all_extended_text_fields(self) -> None:
        """Test that all ExtendedTextMessageContent fields are required."""
        with pytest.raises(ValidationError) as exc_info:
            ExtendedTextMessageContent(  # type: ignore[call-arg]
                text="Reply text",
                # Missing stanzaId and participant
            )

        errors = exc_info.value.errors()
        assert len(errors) == 2
        field_names = {error["loc"][0] for error in errors}
        assert "stanzaId" in field_names
        assert "participant" in field_names

    def test_should_handle_quoted_message_with_contact_share(self) -> None:
        """Test webhook with quoted message containing contact share context."""
        webhook = GreenAPIMessageWebhook(
            typeWebhook="incomingMessageReceived",
            instanceData=InstanceData(
                idInstance=123456,
                wid="27123456789@c.us",
                typeInstance="whatsapp",
            ),
            timestamp=1234567890,
            idMessage="msg_with_quote",
            senderData=SenderData(
                chatId="27123456789-group@g.us",
                sender="27987654321@c.us",
                senderName="Helper",
                chatName="Neighbourhood Group",
            ),
            messageData=MessageData(
                typeMessage="quotedMessage",
                extendedTextMessageData=ExtendedTextMessageContent(
                    text="Try this plumber, he's excellent",
                    stanzaId="request_msg_789",
                    participant="27555666777@c.us",
                ),
            ),
        )

        assert webhook.isQuotedMessage is True
        assert webhook.extendedTextMessage is not None
        assert webhook.extendedTextMessage.text == "Try this plumber, he's excellent"
        assert webhook.quotedMessageId == "request_msg_789"

    def test_should_handle_contact_message_without_quote(self) -> None:
        """Test that contact messages without quotes work correctly."""
        webhook = GreenAPIMessageWebhook(
            typeWebhook="incomingMessageReceived",
            instanceData=InstanceData(
                idInstance=123456,
                wid="27123456789@c.us",
                typeInstance="whatsapp",
            ),
            timestamp=1234567890,
            idMessage="contact_msg_no_quote",
            senderData=SenderData(
                chatId="27123456789-group@g.us",
                sender="27987654321@c.us",
                senderName="Contact Sharer",
                chatName="Test Group",
            ),
            messageData=MessageData(
                typeMessage="contactMessage",
                contactMessageData=ContactMessageContent(
                    displayName="Mike Plumber",
                    vcard="BEGIN:VCARD\nVERSION:3.0\nFN:Mike\nTEL:+27999888777\nEND:VCARD",
                ),
            ),
        )

        assert webhook.isContactMessage is True
        assert webhook.isQuotedMessage is False
        assert webhook.quotedMessageId is None
        assert webhook.contactMessage is not None

    def test_should_preserve_webhook_immutability(self) -> None:
        """Test that webhook models remain immutable."""
        extended_msg = ExtendedTextMessageContent(
            text="Test text",
            stanzaId="id_123",
            participant="27123456789@c.us",
        )

        # Should not be able to modify fields
        with pytest.raises(ValidationError):
            extended_msg.text = "Modified text"  # type: ignore

    def test_should_handle_quoted_message_edge_cases(self) -> None:
        """Test edge cases for quoted message handling."""
        # Empty text in extended message
        extended_msg = ExtendedTextMessageContent(
            text="",
            stanzaId="msg_id",
            participant="27123456789@c.us",
        )
        assert extended_msg.text == ""

        # Very long stanza ID
        long_id = "a" * 500
        extended_msg = ExtendedTextMessageContent(
            text="Reply",
            stanzaId=long_id,
            participant="27123456789@c.us",
        )
        assert extended_msg.stanzaId == long_id

    def test_should_differentiate_message_types(self) -> None:
        """Test that different message types are correctly identified."""
        instance_data = InstanceData(
            idInstance=123,
            wid="27123456789@c.us",
            typeInstance="whatsapp",
        )
        sender_data = SenderData(
            chatId="group@g.us",
            sender="sender@c.us",
            senderName="Sender",
        )

        # Text message
        text_webhook = GreenAPIMessageWebhook(
            typeWebhook="incomingMessageReceived",
            instanceData=instance_data,
            timestamp=1234567890,
            idMessage="test_msg",
            senderData=sender_data,
            messageData=MessageData(typeMessage="textMessage"),
        )
        assert not text_webhook.isQuotedMessage
        assert not text_webhook.isContactMessage

        # Contact message
        contact_webhook = GreenAPIMessageWebhook(
            typeWebhook="incomingMessageReceived",
            instanceData=instance_data,
            timestamp=1234567890,
            idMessage="test_msg",
            senderData=sender_data,
            messageData=MessageData(typeMessage="contactMessage"),
        )
        assert not contact_webhook.isQuotedMessage
        assert contact_webhook.isContactMessage

        # Quoted message
        quoted_webhook = GreenAPIMessageWebhook(
            typeWebhook="incomingMessageReceived",
            instanceData=instance_data,
            timestamp=1234567890,
            idMessage="test_msg",
            senderData=sender_data,
            messageData=MessageData(typeMessage="quotedMessage"),
        )
        assert quoted_webhook.isQuotedMessage
        assert not quoted_webhook.isContactMessage
