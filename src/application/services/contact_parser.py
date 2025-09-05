"""vCard contact parser for extracting provider information from contact messages."""

import re
from dataclasses import dataclass

from src.domain.models import ExtractedMention
from src.domain.value_objects import PhoneNumber
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import ContactParsingException, PhoneNumberValidationError


@dataclass
class ParsedContact:
    """Parsed contact information from vCard data."""

    display_name: str
    phone_numbers: list[PhoneNumber]
    organization: str | None = None
    email: str | None = None
    raw_vcard: str = ""


class ContactParser:
    """
    vCard parser for extracting provider information from WhatsApp contact messages.

    Follows existing architecture patterns with domain events for observability
    and integration with the mention extraction pipeline.
    """

    def __init__(self) -> None:
        """Initialize ContactParser with dependencies."""
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()

    def parse_vcard(self, vcard_data: str, display_name: str) -> ParsedContact:
        """
        Parse vCard data to extract provider information.

        Args:
            vcard_data: Raw vCard formatted contact data
            display_name: Display name from GREEN-API webhook

        Returns:
            ParsedContact with extracted information

        Raises:
            ContactParsingException: If vCard parsing fails
        """
        try:
            self.logger.info(
                "Parsing vCard data",
                display_name=display_name,
                vcard_length=len(vcard_data),
            )

            phone_numbers = self._extract_phone_numbers(vcard_data)
            organization = self._extract_organization(vcard_data)
            email = self._extract_email(vcard_data)

            if not phone_numbers:
                self.logger.warning(
                    "No valid phone numbers found in vCard",
                    display_name=display_name,
                )

            parsed_contact = ParsedContact(
                display_name=display_name,
                phone_numbers=phone_numbers,
                organization=organization,
                email=email,
                raw_vcard=vcard_data,
            )

            self.metrics.increment_counter("contact_parsing_success_total", {})
            self.logger.info(
                "vCard parsed successfully",
                display_name=display_name,
                phone_count=len(phone_numbers),
                has_organization=organization is not None,
            )

            return parsed_contact

        except Exception as e:
            self.metrics.increment_counter("contact_parsing_errors_total", {})
            self.logger.error(
                "Failed to parse vCard data",
                display_name=display_name,
                error=str(e),
            )
            raise ContactParsingException(f"vCard parsing failed: {e}") from e

    def contact_to_mentions(
        self,
        contact: ParsedContact,
        confidence: float = 0.9,
    ) -> list[ExtractedMention]:
        """
        Convert parsed contact to ExtractedMention objects for endorsement processing.

        Args:
            contact: Parsed contact information
            confidence: Confidence score for contact-based mentions (default 0.9)

        Returns:
            List of ExtractedMention objects for mention processing pipeline
        """
        try:
            mentions = []

            # Create mention for display name
            if contact.display_name.strip():
                mentions.append(
                    ExtractedMention(
                        text=contact.display_name.strip(),
                        confidence=confidence,
                        extraction_type="contact_display_name",
                        start_position=0,
                        end_position=len(contact.display_name.strip()),
                    ),
                )

            # Create mentions for phone numbers
            for phone in contact.phone_numbers:
                mentions.append(
                    ExtractedMention(
                        text=phone.normalized,
                        confidence=confidence,
                        extraction_type="contact_phone_number",
                        start_position=0,
                        end_position=len(phone.normalized),
                    ),
                )

            # Create mention for organization if available
            if contact.organization and contact.organization.strip():
                mentions.append(
                    ExtractedMention(
                        text=contact.organization.strip(),
                        confidence=confidence,
                        extraction_type="contact_organization",
                        start_position=0,
                        end_position=len(contact.organization.strip()),
                    ),
                )

            self.logger.info(
                "Contact converted to mentions",
                display_name=contact.display_name,
                mention_count=len(mentions),
                confidence=confidence,
            )

            return mentions

        except Exception as e:
            self.logger.error(
                "Failed to convert contact to mentions",
                display_name=contact.display_name,
                error=str(e),
            )
            raise ContactParsingException(f"Contact mention conversion failed: {e}") from e

    def _extract_phone_numbers(self, vcard_data: str) -> list[PhoneNumber]:
        """Extract and validate phone numbers from vCard data."""
        phone_numbers = []

        # vCard phone number patterns (TEL field with various formats)
        tel_patterns = [
            r"TEL[^:]*:([^\r\n]+)",  # TEL field with phone number
            r"TEL;[^:]*:([^\r\n]+)",  # TEL with attributes
        ]

        for pattern in tel_patterns:
            matches = re.findall(pattern, vcard_data, re.IGNORECASE)
            for match in matches:
                cleaned_number = re.sub(r"[^\d+]", "", match.strip())
                if cleaned_number:
                    try:
                        phone = PhoneNumber(value=cleaned_number)
                        if phone not in phone_numbers:
                            phone_numbers.append(phone)
                    except PhoneNumberValidationError:
                        self.logger.debug(
                            "Invalid phone number in vCard",
                            raw_number=match,
                            cleaned=cleaned_number,
                        )
                        continue

        return phone_numbers

    def _extract_organization(self, vcard_data: str) -> str | None:
        """Extract organization name from vCard data."""
        # vCard organization patterns (ORG field)
        org_patterns = [
            r"ORG:([^\n\r]+)",  # ORG field
            r"ORG;[^:]*:([^\n\r]+)",  # ORG with attributes
        ]

        for pattern in org_patterns:
            match = re.search(pattern, vcard_data, re.IGNORECASE)
            if match:
                org = match.group(1).strip()
                if org:
                    return org

        return None

    def _extract_email(self, vcard_data: str) -> str | None:
        """Extract email address from vCard data."""
        # vCard email patterns (EMAIL field)
        email_patterns = [
            r"EMAIL:([^\n\r]+)",  # EMAIL field
            r"EMAIL;[^:]*:([^\n\r]+)",  # EMAIL with attributes
        ]

        for pattern in email_patterns:
            match = re.search(pattern, vcard_data, re.IGNORECASE)
            if match:
                email = match.group(1).strip()
                # Basic email validation
                if "@" in email and "." in email:
                    return email

        return None
