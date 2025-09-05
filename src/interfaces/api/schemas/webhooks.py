"""WhatsApp webhook schemas using Pydantic V2."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InstanceData(BaseModel):
    """GREEN-API instance data."""

    model_config = ConfigDict(frozen=True)

    idInstance: int = Field(  # noqa: N815
        description="Instance ID",
    )
    wid: str = Field(
        description="WhatsApp account ID",
    )
    typeInstance: str = Field(  # noqa: N815
        description="Instance type (e.g., 'whatsapp')",
    )


class SenderData(BaseModel):
    """GREEN-API sender information."""

    model_config = ConfigDict(frozen=True, extra="allow")

    chatId: str = Field(  # noqa: N815
        description="Chat ID where message was sent",
    )
    sender: str = Field(
        description="Sender's WhatsApp ID",
    )
    chatName: str | None = Field(  # noqa: N815
        default=None,
        description="Chat/Group name",
    )
    senderName: str = Field(  # noqa: N815
        description="Sender's display name",
    )
    senderContactName: str | None = Field(  # noqa: N815
        default=None,
        description="Sender's contact name",
    )


class TextMessageContent(BaseModel):
    """Text message content."""

    model_config = ConfigDict(frozen=True)

    textMessage: str = Field(  # noqa: N815
        description="The actual text message content",
    )
    isTemplateMessage: bool | None = Field(  # noqa: N815
        default=None,
        description="Whether this is a template message",
    )


class ContactMessageContent(BaseModel):
    """Contact message content (vCard)."""

    model_config = ConfigDict(frozen=True)

    displayName: str = Field(  # noqa: N815
        description="Display name of the contact",
    )
    vcard: str = Field(
        description="vCard formatted contact data",
    )
    contactName: str | None = Field(  # noqa: N815
        default=None,
        description="Contact name if available",
    )


class ContactsArrayMessageContent(BaseModel):
    """Contacts array message content (multiple vCards)."""

    model_config = ConfigDict(frozen=True)

    contacts: list[ContactMessageContent] = Field(
        description="Array of contact information",
    )


class ExtendedTextMessageContent(BaseModel):
    """Extended text message content with quoted message support."""

    model_config = ConfigDict(frozen=True)

    text: str = Field(
        description="Text message content below the quoted message",
    )
    stanzaId: str = Field(  # noqa: N815
        description="Unique identifier of the quoted/replied-to message",
    )
    participant: str = Field(
        description="Chat ID of the quoted message sender",
    )


class MessageData(BaseModel):
    """GREEN-API message data structure."""

    model_config = ConfigDict(frozen=True, extra="allow")

    typeMessage: str = Field(  # noqa: N815
        description="Message type (e.g., 'textMessage', 'contactMessage', 'contactsArrayMessage')",
    )
    textMessageData: TextMessageContent | None = Field(  # noqa: N815
        default=None,
        description="Text message content when typeMessage is 'textMessage'",
    )
    contactMessageData: ContactMessageContent | None = Field(  # noqa: N815
        default=None,
        description="Contact message content when typeMessage is 'contactMessage'",
    )
    contactsArrayMessageData: ContactsArrayMessageContent | None = Field(  # noqa: N815
        default=None,
        description="Contacts array content when typeMessage is 'contactsArrayMessage'",
    )
    extendedTextMessageData: ExtendedTextMessageContent | None = Field(  # noqa: N815
        default=None,
        description="Extended text message content when typeMessage is 'quotedMessage'",
    )
    downloadUrl: str | None = Field(  # noqa: N815
        default=None,
        description="Download URL for media messages",
    )
    caption: str | None = Field(
        default=None,
        description="Caption for media messages",
    )


class GreenAPIBaseWebhook(BaseModel):
    """Base GREEN-API webhook schema."""

    model_config = ConfigDict(frozen=True, extra="allow")

    typeWebhook: str = Field(  # noqa: N815
        description="GREEN-API webhook type",
    )
    instanceData: InstanceData = Field(  # noqa: N815
        description="Instance information",
    )
    timestamp: int = Field(
        description="Unix timestamp of event",
    )


class GreenAPIMessageWebhook(GreenAPIBaseWebhook):
    """GREEN-API incoming message webhook schema (actual structure from docs)."""

    typeWebhook: Literal["incomingMessageReceived"] = Field(  # noqa: N815
        description="GREEN-API webhook type for incoming messages",
    )
    idMessage: str = Field(  # noqa: N815
        description="Unique message ID",
    )
    senderData: SenderData = Field(  # noqa: N815
        description="Sender information",
    )
    messageData: MessageData = Field(  # noqa: N815
        description="Message content data",
    )

    #  pylint: disable=C0103
    @property
    def chatId(self) -> str:  # noqa: N802
        """Get chat ID from senderData."""
        return self.senderData.chatId

    @property
    def senderId(self) -> str:  # noqa: N802
        """Get sender ID from senderData."""
        return self.senderData.sender

    @property
    def senderName(self) -> str:  # noqa: N802
        """Get sender name from senderData."""
        return self.senderData.senderName

    @property
    def textMessage(self) -> str:  # noqa: N802
        """Extract text message content."""
        if self.messageData.textMessageData:
            return self.messageData.textMessageData.textMessage
        return ""

    @property
    def contactMessage(self) -> ContactMessageContent | None:  # noqa: N802
        """Extract contact message content."""
        return self.messageData.contactMessageData

    @property
    def isContactMessage(self) -> bool:  # noqa: N802
        """Check if this is a single contact message."""
        return self.messageData.typeMessage == "contactMessage"

    @property
    def contactsArrayMessage(self) -> ContactsArrayMessageContent | None:  # noqa: N802
        """Extract contacts array message content."""
        return self.messageData.contactsArrayMessageData

    @property
    def isContactsArrayMessage(self) -> bool:  # noqa: N802
        """Check if this is a contacts array message."""
        return self.messageData.typeMessage == "contactsArrayMessage"

    @property
    def isAnyContactMessage(self) -> bool:  # noqa: N802
        """Check if this is any type of contact message."""
        return self.isContactMessage or self.isContactsArrayMessage

    @property
    def isQuotedMessage(self) -> bool:  # noqa: N802
        """Check if this is a quoted/reply message."""
        return self.messageData.typeMessage == "quotedMessage"

    @property
    def extendedTextMessage(self) -> ExtendedTextMessageContent | None:  # noqa: N802
        """Extract extended text message content with quote information."""
        return self.messageData.extendedTextMessageData

    @property
    def quotedMessageId(self) -> str | None:  # noqa: N802
        """Get the ID of the message being quoted/replied to."""
        if self.extendedTextMessage:
            return self.extendedTextMessage.stanzaId
        return None

    @property
    def quotedMessageParticipant(self) -> str | None:  # noqa: N802
        """Get the participant (sender) of the quoted message."""
        if self.extendedTextMessage:
            return self.extendedTextMessage.participant
        return None

    @property
    def replyText(self) -> str:  # noqa: N802
        """Get the reply text for quoted messages."""
        if self.extendedTextMessage:
            return self.extendedTextMessage.text
        return ""

    #  pylint: enable=C0103


class GreenAPIStateWebhook(GreenAPIBaseWebhook):
    """GREEN-API state change webhook schema."""

    typeWebhook: Literal["stateInstanceChanged"] = Field(  # noqa: N815
        description="GREEN-API webhook type for state changes",
    )
    stateInstance: str = Field(  # noqa: N815
        description="Current instance state (e.g., 'authorized', 'notAuthorized')",
    )


class GreenAPIStatusWebhook(GreenAPIBaseWebhook):
    """GREEN-API message status webhook schema."""

    typeWebhook: Literal["outgoingMessageStatus"] = Field(  # noqa: N815
        description="GREEN-API webhook type for message status updates",
    )
    status: str = Field(
        description="Message delivery status",
    )
    idMessage: str | None = Field(  # noqa: N815
        default=None,
        description="Message ID for status update",
    )
    sendByApi: bool | None = Field(  # noqa: N815
        default=None,
        description="Whether message was sent via API",
    )


class GreenAPIGenericWebhook(BaseModel):
    """Generic GREEN-API webhook for handling any webhook type."""

    model_config = ConfigDict(frozen=True, extra="allow")

    typeWebhook: str = Field(  # noqa: N815
        description="GREEN-API webhook type",
    )
    timestamp: int = Field(
        description="Unix timestamp of event",
    )


class WebhookRequest(BaseModel):
    """WhatsApp webhook request schema."""

    model_config = ConfigDict(frozen=True)

    webhook_type: Literal["message", "status", "notification"] = Field(
        description="Type of webhook event",
    )
    sender_id: str = Field(
        description="Sender phone number or ID",
    )
    message_content: str = Field(
        description="Message content or status information",
    )
    timestamp: str = Field(
        description="ISO 8601 timestamp when event occurred",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional webhook-specific metadata",
    )


class WebhookResponse(BaseModel):
    """WhatsApp webhook processing response schema."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(
        description="Processing status",
    )
    message_id: str = Field(
        description="Unique message identifier",
    )
    processing_time_ms: float = Field(
        ge=0.0,
        description="Time taken to process webhook in milliseconds",
    )
    actions_taken: list[str] = Field(
        default_factory=list,
        description="List of processing actions performed",
    )
