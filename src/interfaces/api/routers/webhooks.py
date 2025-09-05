"""WhatsApp webhook API router for GREEN-API integration."""

from datetime import datetime, UTC
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from src.application.services import ContactParser, MessageProcessor
from src.application.services.nlp import MessageClassifier
from src.domain.models.message_classification import ClassificationResult, MessageType
from src.domain.value_objects import GroupID
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.infrastructure.security import check_rate_limit, verify_api_key
from src.interfaces.api.schemas import (
    GreenAPIGenericWebhook,
    GreenAPIMessageWebhook,
    GreenAPIStateWebhook,
)
from src.shared.exceptions import ValidationException, WhatsAppException

router = APIRouter(
    prefix="/webhooks/whatsapp",
    tags=["webhooks"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)

logger = get_logger(__name__)
metrics = get_metrics_collector()


@router.post("/message")
async def process_whatsapp_message(webhook_data: dict[str, Any]) -> dict[str, Any]:
    """
    Process incoming WhatsApp webhooks from GREEN-API.

    This endpoint receives various webhook notifications from GREEN-API including:
    - incomingMessageReceived: When messages are sent to our WhatsApp number
    - stateInstanceChanged: When WhatsApp connection state changes
    - outgoingMessageStatus: When sent message status updates

    Also supports simplified webhook format for testing compatibility.
    """
    operation_start = datetime.now(UTC)

    # Handle both full GREEN-API format and simplified test format
    try:
        # Check if this looks like the simplified test format
        if _is_simplified_webhook_format(webhook_data):
            webhook_data = _convert_simplified_to_full_format(webhook_data)

        generic_webhook = GreenAPIGenericWebhook(**webhook_data)
        webhook_type = generic_webhook.typeWebhook

        logger.info(
            "Received GREEN-API webhook",
            webhook_type=webhook_type,
            timestamp=generic_webhook.timestamp,
        )

        # Route based on webhook type
        if webhook_type == "incomingMessageReceived":
            # Parse as message webhook
            webhook = GreenAPIMessageWebhook(**webhook_data)
            return await _handle_incoming_message(webhook, operation_start)

        if webhook_type == "stateInstanceChanged":
            # Parse as state change webhook
            state_webhook = GreenAPIStateWebhook(**webhook_data)
            logger.info(
                "WhatsApp instance state changed",
                state=state_webhook.stateInstance,
                timestamp=state_webhook.timestamp,
            )
            metrics.increment_counter(
                "whatsapp_state_changes_total",
                {"state": state_webhook.stateInstance},
            )
            return {
                "status": "acknowledged",
                "webhook_type": webhook_type,
                "state": state_webhook.stateInstance,
            }

        elif webhook_type == "outgoingMessageStatus":
            # Handle message status updates
            logger.info(
                "Received message status update",
                webhook_type=webhook_type,
            )
            return {
                "status": "acknowledged",
                "webhook_type": webhook_type,
            }

        else:
            # Unknown webhook type - log and acknowledge
            logger.warning(
                "Received unknown webhook type",
                webhook_type=webhook_type,
            )
            metrics.increment_counter("whatsapp_unknown_webhooks_total", {})
            return {
                "status": "acknowledged",
                "webhook_type": webhook_type,
                "message": "Unknown webhook type",
            }

    except ValidationError as e:
        logger.error(
            "Pydantic validation error",
            error=str(e),
            webhook_data=webhook_data,
        )
        metrics.increment_counter("whatsapp_webhook_errors_total", {"type": "validation"})
        raise HTTPException(status_code=422, detail=f"Webhook validation failed: {str(e)}") from e

    except ValidationException as e:
        logger.error(
            "Webhook validation error",
            error=str(e),
            webhook_data=webhook_data,
        )
        metrics.increment_counter("whatsapp_webhook_errors_total", {"type": "validation"})
        raise HTTPException(status_code=422, detail=str(e)) from e

    except WhatsAppException as e:
        logger.error(
            "WhatsApp processing error",
            error=str(e),
        )
        metrics.increment_counter("whatsapp_webhook_errors_total", {"type": "whatsapp"})
        raise HTTPException(status_code=422, detail=str(e)) from e

    except Exception as e:
        logger.error(
            "Unexpected error processing WhatsApp webhook",
            error=str(e),
        )
        metrics.increment_counter("whatsapp_webhook_errors_total", {"type": "unexpected"})
        raise HTTPException(status_code=500, detail="Internal processing error") from e


async def _handle_incoming_message(
    webhook: GreenAPIMessageWebhook,
    operation_start: datetime,
) -> dict[str, str]:
    """Handle incoming WhatsApp message webhook."""
    try:
        # Check for GREEN-API error codes before processing
        error_response = _handle_green_api_errors(webhook)
        if error_response:
            return error_response

        # Log message processing start
        _log_message_processing_start(webhook)

        # Process message based on type (group vs individual)
        action = await _process_message_by_type(webhook)

        # Record metrics and completion
        operation_duration = _record_processing_metrics(action, operation_start)
        _log_processing_completion(webhook, action)

        return {
            "status": "processed",
            "action": action,
            "processing_time_ms": str(round(operation_duration * 1000, 2)),
        }

    except WhatsAppException as e:
        logger.error(
            "WhatsApp processing error",
            chat_id=_mask_chat_id(webhook.chatId),
            error=str(e),
        )
        metrics.increment_counter("whatsapp_webhook_errors_total", {"type": "whatsapp"})
        raise HTTPException(status_code=422, detail=str(e)) from e

    except Exception as e:
        logger.error(
            "Unexpected error processing WhatsApp webhook",
            chat_id=_mask_chat_id(webhook.chatId),
            error=str(e),
        )
        metrics.increment_counter("whatsapp_webhook_errors_total", {"type": "unexpected"})
        raise HTTPException(status_code=500, detail="Internal processing error") from e


def _log_message_processing_start(webhook: GreenAPIMessageWebhook) -> None:
    """Log the start of message processing with content details."""
    message_content, content_length = _extract_message_content(webhook)

    logger.info(
        "Processing WhatsApp message",
        chat_id=_mask_chat_id(webhook.chatId),
        sender_name=webhook.senderName,
        message_type=webhook.messageData.typeMessage,
        content_preview=message_content,
        content_length=content_length,
        timestamp=webhook.timestamp,
    )


def _extract_message_content(webhook: GreenAPIMessageWebhook) -> tuple[str, int]:
    """Extract message content and length for logging."""
    if webhook.isContactMessage and webhook.contactMessage:
        message_content = f"Contact: {webhook.contactMessage.displayName}"
        content_length = len(webhook.contactMessage.vcard)
    elif webhook.isContactsArrayMessage and webhook.contactsArrayMessage:
        contact_count = len(webhook.contactsArrayMessage.contacts)
        message_content = f"Contacts Array: {contact_count} contacts"
        content_length = sum(len(c.vcard) for c in webhook.contactsArrayMessage.contacts)
    else:
        text = webhook.textMessage
        message_content = text[:50] + "..." if len(text) > 50 else text
        content_length = len(webhook.textMessage)

    return message_content, content_length


async def _process_message_by_type(webhook: GreenAPIMessageWebhook) -> str:
    """Process message based on whether it's from a group or individual chat."""
    is_group_message = webhook.chatId.endswith("@g.us")

    if is_group_message:
        return await _process_group_message(webhook)
    else:
        _log_individual_message_skipped(webhook)
        return "skipped_individual_message"


async def _process_group_message(webhook: GreenAPIMessageWebhook) -> str:
    """Process a group message for endorsements."""
    try:
        group_id = GroupID(value=webhook.chatId)

        if webhook.isAnyContactMessage:
            await _process_group_contact_message(
                group_id=group_id,
                sender_name=webhook.senderName,
                webhook=webhook,
                timestamp=webhook.timestamp,
            )
            return "processed_group_contact_endorsement"
        else:
            await _process_group_endorsement_message(
                group_id=group_id,
                sender_name=webhook.senderName,
                message_text=webhook.textMessage,
                timestamp=webhook.timestamp,
            )
            return "processed_group_endorsement"

    except ValidationException as e:
        logger.warning(
            "Invalid group ID format",
            chat_id=webhook.chatId,
            error=str(e),
        )
        return "skipped_invalid_group"


def _log_individual_message_skipped(webhook: GreenAPIMessageWebhook) -> None:
    """Log that an individual message was skipped."""
    logger.info(
        "Skipping individual message processing",
        chat_id=_mask_chat_id(webhook.chatId),
    )


def _record_processing_metrics(action: str, operation_start: datetime) -> float:
    """Record processing metrics and return operation duration."""
    operation_duration = (datetime.now(UTC) - operation_start).total_seconds()

    metrics.increment_counter("whatsapp_webhooks_processed_total", {"action": action})
    metrics.record_histogram(
        "whatsapp_webhook_processing_duration_seconds",
        operation_duration,
        {},
    )

    return operation_duration


def _log_processing_completion(webhook: GreenAPIMessageWebhook, action: str) -> None:
    """Log successful processing completion."""
    logger.info(
        "WhatsApp webhook processed successfully",
        chat_id=_mask_chat_id(webhook.chatId),
        action=action,
    )


async def _process_group_endorsement_message(
    group_id: GroupID,
    sender_name: str,
    message_text: str,
    timestamp: int,
) -> None:
    """
    Process a group message for potential endorsements.

    Args:
        group_id: WhatsApp group identifier
        sender_name: Name of message sender
        message_text: Message content
        timestamp: Unix timestamp of message
    """
    try:
        # Step 1: Classify message to check if it contains endorsements
        classifier = MessageClassifier()
        classification = classifier.classify(message_text)

        logger.info(
            "Message classified",
            group_id=group_id.value,
            message_type=classification.message_type.value,
            confidence=classification.confidence,
        )

        if classification.message_type != MessageType.RECOMMENDATION:
            logger.debug(
                "Message does not contain endorsement, skipping further processing",
                group_id=group_id.value,
            )
            return

        # Steps 2-4: Process endorsement message through MessageProcessor pipeline
        try:
            # Initialize repositories for provider persistence
            from src.infrastructure.persistence.repositories import (
                firestore_endorsement_repository as endorsement_repo,
            )
            from src.infrastructure.persistence.repositories import (
                firestore_provider_repository as provider_repo,
            )
            from src.infrastructure.service_registry import get_service_registry

            service_registry = get_service_registry()
            firestore_client = service_registry.get_firestore_client()
            provider_repository = provider_repo.FirestoreProviderRepository(
                firestore_client,
            )
            endorsement_repository = endorsement_repo.FirestoreEndorsementRepository(
                firestore_client,
            )

            processor = MessageProcessor(
                provider_repository=provider_repository,
                endorsement_repository=endorsement_repository,
            )
            result = await processor.process_endorsement_message(
                group_id=group_id,
                sender_name=sender_name,
                message_text=message_text,
                timestamp=timestamp,
                classification=classification,
            )

            logger.info(
                "Group endorsement processing completed",
                group_id=group_id.value,
                classification_confidence=classification.confidence,
                endorsements_created=len(result.endorsements_created),
                processing_duration=result.processing_duration_seconds,
                success=result.success,
            )

        except Exception as e:
            logger.error(
                "Failed to process endorsement through MessageProcessor",
                group_id=group_id.value,
                error=str(e),
            )
            # Continue processing rather than failing the entire webhook
            # This ensures webhook reliability even if endorsement processing fails

    except Exception as e:
        logger.error(
            "Failed to process group endorsement message",
            group_id=group_id.value,
            error=str(e),
        )
        raise


async def _process_group_contact_message(
    group_id: GroupID,
    sender_name: str,
    webhook: GreenAPIMessageWebhook,
    timestamp: int,
) -> None:
    """
    Process a group contact message for provider endorsements.

    Contact messages are treated as high-confidence endorsements since sharing
    a contact card is a deliberate action that represents strong recommendation.

    Args:
        group_id: WhatsApp group identifier
        sender_name: Name of message sender
        webhook: Complete webhook with contact data
        timestamp: Unix timestamp of message
    """
    try:
        contacts_to_process = []

        # Extract contacts based on message type
        if webhook.isContactMessage and webhook.contactMessage:
            contacts_to_process = [webhook.contactMessage]
        elif webhook.isContactsArrayMessage and webhook.contactsArrayMessage:
            contacts_to_process = webhook.contactsArrayMessage.contacts

        if not contacts_to_process:
            logger.warning(
                "Contact message received but no contact data found",
                group_id=group_id.value,
            )
            return

        logger.info(
            "Processing contact message",
            group_id=group_id.value,
            sender_name=sender_name,
            contact_count=len(contacts_to_process),
            timestamp=timestamp,
        )

        # Parse contact cards and convert to mentions for endorsement processing
        contact_parser = ContactParser()
        all_mentions = []

        for contact_data in contacts_to_process:
            try:
                # Parse the vCard data
                parsed_contact = contact_parser.parse_vcard(
                    vcard_data=contact_data.vcard,
                    display_name=contact_data.displayName,
                )

                # Convert to mentions with high confidence (contact sharing = strong endorsement)
                mentions = contact_parser.contact_to_mentions(parsed_contact, confidence=0.95)
                all_mentions.extend(mentions)

                logger.info(
                    "Contact parsed and converted to mentions",
                    group_id=group_id.value,
                    contact_name=contact_data.displayName,
                    phone_count=len(parsed_contact.phone_numbers),
                    mentions_count=len(mentions),
                    sender=sender_name,
                )

            except Exception as e:
                logger.error(
                    "Failed to parse contact card",
                    group_id=group_id.value,
                    contact_name=contact_data.displayName,
                    error=str(e),
                )
                continue

        if all_mentions:
            logger.info(
                "Contact endorsements ready for processing",
                group_id=group_id.value,
                total_mentions=len(all_mentions),
                contact_count=len(contacts_to_process),
            )

            # Process contact mentions through endorsement pipeline
            try:
                # Create a contact-based message classification with high confidence

                contact_classification = ClassificationResult(
                    message_type=MessageType.RECOMMENDATION,
                    confidence=0.95,  # High confidence for contact sharing
                    keywords=["contact_card_shared"],
                    rule_matches=["contact_endorsement_signal"],
                )

                # Create synthetic message text for MessageProcessor compatibility
                contact_names = [
                    mention.text
                    for mention in all_mentions
                    if mention.extraction_type == "contact_display_name"
                ]
                synthetic_message = f"Contact shared: {', '.join(contact_names)}"

                # Initialize repositories for provider persistence
                from src.infrastructure.persistence.repositories import (
                    firestore_endorsement_repository as endorsement_repo,
                )
                from src.infrastructure.persistence.repositories import (
                    firestore_provider_repository as provider_repo,
                )
                from src.infrastructure.service_registry import get_service_registry

                service_registry = get_service_registry()
                firestore_client = service_registry.get_firestore_client()
                provider_repository = provider_repo.FirestoreProviderRepository(
                    firestore_client,
                )
                endorsement_repository = endorsement_repo.FirestoreEndorsementRepository(
                    firestore_client,
                )

                processor = MessageProcessor(
                    provider_repository=provider_repository,
                    endorsement_repository=endorsement_repository,
                )
                result = await processor.process_structured_mentions(
                    group_id=group_id,
                    sender_name=sender_name,
                    message_text=synthetic_message,
                    timestamp=timestamp,
                    classification=contact_classification,
                    extracted_mentions=all_mentions,
                )

                logger.info(
                    "Contact endorsement processing completed",
                    group_id=group_id.value,
                    contact_count=len(contacts_to_process),
                    mentions_processed=len(all_mentions),
                    endorsements_created=len(result.endorsements_created),
                    processing_duration=result.processing_duration_seconds,
                    success=result.success,
                )

            except Exception as e:
                logger.error(
                    "Failed to process contact endorsements through MessageProcessor",
                    group_id=group_id.value,
                    contact_count=len(contacts_to_process),
                    mentions_count=len(all_mentions),
                    error=str(e),
                )
                # Continue processing rather than failing the entire webhook
                # This ensures webhook reliability even if endorsement processing fails

    except Exception as e:
        logger.error(
            "Failed to process group contact message",
            group_id=group_id.value,
            error=str(e),
        )
        raise


def _mask_chat_id(chat_id: str) -> str:
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


def _is_simplified_webhook_format(webhook_data: dict[str, Any]) -> bool:
    """
    Check if webhook data is in simplified test format.

    Simplified format has chatId and senderName at top level,
    while full GREEN-API format has nested senderData and messageData.
    """
    return (
        "chatId" in webhook_data
        and "senderName" in webhook_data
        and "senderData" not in webhook_data
        and "messageData" not in webhook_data
    )


def _convert_simplified_to_full_format(webhook_data: dict[str, Any]) -> dict[str, Any]:
    """
    Convert simplified test webhook format to full GREEN-API format.

    Args:
        webhook_data: Simplified webhook data from tests

    Returns:
        Full GREEN-API format webhook data
    """
    # Default instance data for test compatibility
    default_instance_data = {
        "idInstance": 1234567890,
        "wid": "test_instance@c.us",
        "typeInstance": "whatsapp",
    }

    # Extract values from simplified format
    chat_id = webhook_data.get("chatId", "")
    sender_id = webhook_data.get("senderId", "")
    sender_name = webhook_data.get("senderName", "")
    text_message = webhook_data.get("textMessage", "")
    timestamp = webhook_data.get("timestamp", 0)
    type_webhook = webhook_data.get("typeWebhook", "incomingMessageReceived")

    # Build full format
    return {
        "typeWebhook": type_webhook,
        "instanceData": default_instance_data,
        "timestamp": timestamp,
        "idMessage": f"test_message_{timestamp}",
        "senderData": {
            "chatId": chat_id,
            "sender": sender_id or f"{sender_name.replace(' ', '_').lower()}@c.us",
            "senderName": sender_name,
            "chatName": "Test Group" if chat_id.endswith("@g.us") else None,
        },
        "messageData": {
            "typeMessage": "textMessage",
            "textMessageData": {
                "textMessage": text_message,
                "isTemplateMessage": False,
            },
        },
    }


@router.post("/message-webhook")
async def whatsapp_message_webhook() -> dict[str, str]:
    """Simple GREEN-API message webhook endpoint."""
    return {"webhook": "message", "status": "received"}


@router.post("/status")
async def whatsapp_status_webhook() -> dict[str, str]:
    """GREEN-API message delivery status webhook."""
    return {"webhook": "status", "status": "received"}


@router.post("/notification")
async def whatsapp_notification_webhook() -> dict[str, str]:
    """GREEN-API system notification webhook."""
    return {"webhook": "notification", "status": "received"}


def _handle_green_api_errors(webhook: GreenAPIMessageWebhook) -> dict[str, str] | None:
    """
    Handle GREEN-API specific error codes in webhook messages.

    GREEN-API sends specific error markers in textMessage when WhatsApp
    infrastructure encounters issues. These should be handled gracefully
    rather than processed as normal endorsement content.

    Args:
        webhook: Parsed webhook data

    Returns:
        Error response dict if SWE error detected, None if message is valid
    """
    text_message = webhook.textMessage
    if not text_message:
        return None

    # GREEN-API error code patterns
    swe_error_patterns = {
        "{{SWE001}}": {
            "description": "First incoming message error on additional devices",
            "action": "request_message_resend",
            "severity": "info",
        },
        "{{SWE002}}": {
            "description": "Large file download error (>100MB)",
            "action": "check_message_on_phone",
            "severity": "warning",
        },
        "{{SWE003}}": {
            "description": "Message decryption error - authorization keys lost",
            "action": "reauthorize_device",
            "severity": "error",
        },
        "{{SWE004}}": {
            "description": "Group chat error - exceeds 1024 members",
            "action": "reduce_group_size",
            "severity": "error",
        },
        "{{SWE999}}": {
            "description": "Incoming message without encryption keys",
            "action": "request_message_resend",
            "severity": "warning",
        },
    }

    # Check for SWE error markers
    for error_code, error_info in swe_error_patterns.items():
        if error_code in text_message:
            logger.warning(
                "GREEN-API webhook error detected",
                error_code=error_code,
                description=error_info["description"],
                action=error_info["action"],
                chat_id=_mask_chat_id(webhook.chatId),
                sender_name=webhook.senderName,
                message_preview=text_message[:100],
            )

            metrics.increment_counter(
                "whatsapp_greenapi_errors_total",
                {
                    "error_code": error_code.strip("{}"),
                    "severity": error_info["severity"],
                    "action": error_info["action"],
                },
            )

            return {
                "status": "acknowledged_with_error",
                "error_code": error_code,
                "error_description": error_info["description"],
                "recommended_action": error_info["action"],
                "message": f"GREEN-API error detected: {error_info['description']}",
            }

    return None
