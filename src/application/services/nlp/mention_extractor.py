"""Mention extractor for identifying provider mentions in messages."""

import re
import time
from difflib import SequenceMatcher
from typing import Any

import yaml

from config.settings import MentionExtractionSettings, Settings
from src.domain.models import ExtractedMention
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import MentionExtractionError


class MentionExtractor:
    """
    Extract provider mentions from messages using multiple strategies.

    Strategies include:
    - Name pattern extraction (business names, possessive forms)
    - Phone number pattern extraction
    - Service keyword extraction
    - Location pattern extraction
    """

    def __init__(self, settings: MentionExtractionSettings | None = None) -> None:
        """Initialize mention extractor with settings and configuration."""
        self._logger = get_logger(__name__)
        self._metrics = get_metrics_collector()

        # Load settings
        if settings is None:
            from config.settings import get_settings

            app_settings: Settings = get_settings()
            settings = app_settings.mention_extraction

        self.settings: MentionExtractionSettings = settings

        # Load configuration files
        self._name_patterns: dict[str, Any] = {}
        self._service_keywords: dict[str, Any] = {}
        self._location_patterns: dict[str, Any] = {}
        self._blacklisted_terms: list[str] = []

        try:
            self._load_configuration_files()
            self._logger.info(
                "MentionExtractor initialized successfully",
                name_patterns_count=len(self._name_patterns),
                service_keywords_count=len(self._service_keywords),
                location_patterns_count=len(self._location_patterns),
                blacklisted_terms_count=len(self._blacklisted_terms),
            )
        except Exception as e:
            self._logger.error(
                "Failed to initialize MentionExtractor configuration",
                error=str(e),
            )
            self._metrics.increment_counter(
                "mention_extractor_initialization_errors_total",
                {"error_type": "configuration_loading"},
            )
            raise MentionExtractionError(
                f"Failed to initialize mention extractor: {str(e)}",
            ) from e

    def _load_configuration_files(self) -> None:
        """Load YAML configuration files."""
        try:
            # Load name patterns
            if self.settings.name_pattern_extraction_enabled:
                with open(
                    self.settings.name_patterns_config_file,
                    encoding="utf-8",
                ) as f:
                    self._name_patterns = yaml.safe_load(f) or {}

            # Load service keywords
            if self.settings.service_keyword_extraction_enabled:
                with open(
                    self.settings.service_keywords_config_file,
                    encoding="utf-8",
                ) as f:
                    self._service_keywords = yaml.safe_load(f) or {}

            # Load location patterns
            if self.settings.location_extraction_enabled:
                with open(
                    self.settings.location_patterns_config_file,
                    encoding="utf-8",
                ) as f:
                    self._location_patterns = yaml.safe_load(f) or {}

            # Load blacklisted terms
            with open(
                self.settings.blacklisted_terms_config_file,
                encoding="utf-8",
            ) as f:
                blacklist_data = yaml.safe_load(f) or {}
                # Flatten all blacklisted terms into a single list
                self._blacklisted_terms = []
                for category in blacklist_data.values():
                    if isinstance(category, list):
                        self._blacklisted_terms.extend(category)

        except FileNotFoundError as e:
            raise MentionExtractionError(
                f"Configuration file not found: {e.filename}",
            ) from e
        except yaml.YAMLError as e:
            raise MentionExtractionError(
                f"Invalid YAML configuration: {str(e)}",
            ) from e

    def extract_mentions(self, message: str) -> list[ExtractedMention]:
        """
        Extract provider mentions from a message using multiple strategies.

        Args:
            message: The message text to extract mentions from

        Returns:
            List of ExtractedMention objects sorted by confidence score

        Raises:
            MentionExtractionError: If message is empty or extraction fails
        """
        if not message or not message.strip():
            raise MentionExtractionError("Message cannot be empty")

        self._logger.info(
            "Starting mention extraction",
            message_length=len(message),
        )

        start_time = time.time()
        extracted_mentions: list[ExtractedMention] = []

        try:
            # Apply all enabled extraction strategies
            if self.settings.name_pattern_extraction_enabled:
                name_mentions = self._extract_name_patterns(message)
                extracted_mentions.extend(name_mentions)

            if self.settings.phone_pattern_extraction_enabled:
                phone_mentions = self._extract_phone_patterns(message)
                extracted_mentions.extend(phone_mentions)

            if self.settings.service_keyword_extraction_enabled:
                service_mentions = self._extract_service_keywords(message)
                extracted_mentions.extend(service_mentions)

            if self.settings.location_extraction_enabled:
                location_mentions = self._extract_location_patterns(message)
                extracted_mentions.extend(location_mentions)

            # Filter and process mentions
            filtered_mentions = self._filter_mentions(extracted_mentions)
            final_mentions = self._post_process_mentions(filtered_mentions)

            # Record metrics
            extraction_time = time.time() - start_time
            self._metrics.record_histogram(
                "mention_extraction_duration_seconds",
                extraction_time,
                {
                    "message_length_bucket": self._get_message_length_bucket(
                        len(message),
                    ),
                },
            )

            self._metrics.increment_counter(
                "mention_extraction_attempts_total",
                {"status": "success"},
            )

            for mention in final_mentions:
                self._metrics.increment_counter(
                    "mentions_extracted_total",
                    {"extraction_type": mention.extraction_type},
                )

            self._logger.info(
                "Mention extraction completed",
                mentions_found=len(final_mentions),
                extraction_time_seconds=extraction_time,
            )

            return final_mentions

        except Exception as e:
            self._metrics.increment_counter(
                "mention_extraction_attempts_total",
                {"status": "error"},
            )
            self._logger.error(
                "Mention extraction failed",
                error=str(e),
                message_length=len(message),
            )
            raise MentionExtractionError(
                f"Failed to extract mentions: {str(e)}",
            ) from e

    def _extract_name_patterns(self, message: str) -> list[ExtractedMention]:
        """Extract business names using regex patterns."""
        mentions: list[ExtractedMention] = []

        if not self._name_patterns.get("business_name_patterns"):
            return mentions

        business_patterns = self._name_patterns["business_name_patterns"]

        # Extract from business suffix patterns
        suffix_patterns = business_patterns.get("business_suffix_patterns", [])
        for pattern_config in suffix_patterns:
            pattern = pattern_config.get("pattern", "")
            confidence_weight = pattern_config.get("confidence_weight", 0.5)

            try:
                matches = re.finditer(pattern, message, re.IGNORECASE)
                for match in matches:
                    mention_text = match.group(1) + " " + match.group(2)
                    mentions.append(
                        ExtractedMention(
                            text=mention_text.strip(),
                            confidence=confidence_weight,
                            extraction_type="name_pattern",
                            start_position=match.start(),
                            end_position=match.end(),
                        ),
                    )
            except re.error:
                self._logger.warning(f"Invalid regex pattern: {pattern}")

        return mentions

    def _extract_phone_patterns(self, message: str) -> list[ExtractedMention]:
        """Extract phone numbers using regex patterns."""
        mentions: list[ExtractedMention] = []

        # South African phone number patterns
        patterns = [
            (r"\+27\d{9}", 0.95),  # +27821234567
            (r"0\d{9}", 0.85),  # 0821234567
            (r"\b\d{3}[-\s]?\d{3}[-\s]?\d{4}\b", 0.80),  # 082 123 4567
        ]

        for pattern, confidence in patterns:
            try:
                matches = re.finditer(pattern, message)
                for match in matches:
                    mentions.append(
                        ExtractedMention(
                            text=match.group().strip(),
                            confidence=confidence * self.settings.phone_pattern_confidence_weight,
                            extraction_type="phone_pattern",
                            start_position=match.start(),
                            end_position=match.end(),
                        ),
                    )
            except re.error:
                self._logger.warning(f"Invalid phone regex pattern: {pattern}")

        return mentions

    def _extract_service_keywords(self, message: str) -> list[ExtractedMention]:
        """Extract service-related keywords."""
        mentions: list[ExtractedMention] = []

        message_words = re.findall(r"\b\w+\b", message.lower())

        for _category, keywords in self._service_keywords.items():
            if isinstance(keywords, dict):
                for keyword, base_confidence in keywords.items():
                    if keyword.lower() in message_words:
                        # Find position of keyword in original message
                        pattern = r"\b" + re.escape(keyword) + r"\b"
                        match = re.search(pattern, message, re.IGNORECASE)
                        if match:
                            mentions.append(
                                ExtractedMention(
                                    text=keyword,
                                    confidence=base_confidence
                                    * self.settings.service_keyword_confidence_weight,
                                    extraction_type="service_keyword",
                                    start_position=match.start(),
                                    end_position=match.end(),
                                ),
                            )

        return mentions

    def _extract_location_patterns(self, message: str) -> list[ExtractedMention]:
        """Extract location references using patterns."""
        mentions: list[ExtractedMention] = []

        if not self._location_patterns:
            return mentions

        # Extract major cities
        major_cities = self._location_patterns.get("major_cities", {})
        for _city_group, city_patterns in major_cities.items():
            for pattern_config in city_patterns:
                pattern = pattern_config.get("pattern", "")
                confidence_weight = pattern_config.get("confidence_weight", 0.5)

                try:
                    matches = re.finditer(pattern, message, re.IGNORECASE)
                    for match in matches:
                        mentions.append(
                            ExtractedMention(
                                text=match.group().strip(),
                                confidence=confidence_weight
                                * self.settings.location_confidence_weight,
                                extraction_type="location_pattern",
                                start_position=match.start(),
                                end_position=match.end(),
                            ),
                        )
                except re.error:
                    self._logger.warning(f"Invalid location regex pattern: {pattern}")

        return mentions

    def _filter_mentions(
        self,
        mentions: list[ExtractedMention],
    ) -> list[ExtractedMention]:
        """Filter mentions based on various criteria."""
        filtered: list[ExtractedMention] = []

        for mention in mentions:
            # Filter by confidence threshold
            if mention.confidence < self.settings.minimum_confidence_threshold:
                continue

            # Filter by length
            if (
                len(mention.text) < self.settings.minimum_mention_length
                or len(mention.text) > self.settings.maximum_mention_length
            ):
                continue

            # Filter blacklisted terms
            if mention.text.lower() in [term.lower() for term in self._blacklisted_terms]:
                continue

            filtered.append(mention)

        return filtered

    def _post_process_mentions(
        self,
        mentions: list[ExtractedMention],
    ) -> list[ExtractedMention]:
        """Post-process mentions (deduplication, sorting, limits)."""
        processed_mentions = mentions.copy()

        # Deduplicate similar mentions if enabled
        if self.settings.deduplicate_similar_mentions:
            processed_mentions = self._deduplicate_mentions(processed_mentions)

        # Sort by confidence (highest first)
        processed_mentions.sort(key=lambda x: x.confidence, reverse=True)

        # Limit to maximum mentions per message
        if len(processed_mentions) > self.settings.maximum_mentions_per_message:
            processed_mentions = processed_mentions[: self.settings.maximum_mentions_per_message]

        return processed_mentions

    def _deduplicate_mentions(
        self,
        mentions: list[ExtractedMention],
    ) -> list[ExtractedMention]:
        """Remove similar/duplicate mentions."""
        if not mentions:
            return mentions

        deduplicated: list[ExtractedMention] = []
        threshold = self.settings.similarity_threshold_for_deduplication

        for mention in mentions:
            is_duplicate = False
            replace_index = -1

            for i, existing in enumerate(deduplicated):
                similarity = SequenceMatcher(
                    None,
                    mention.text.lower(),
                    existing.text.lower(),
                ).ratio()
                if similarity >= threshold:
                    is_duplicate = True
                    # Keep the one with higher confidence
                    if mention.confidence > existing.confidence:
                        replace_index = i
                    break

            if is_duplicate and replace_index >= 0:
                deduplicated[replace_index] = mention
            elif not is_duplicate:
                deduplicated.append(mention)

        return deduplicated

    def _get_message_length_bucket(self, length: int) -> str:
        """Get message length bucket for metrics."""
        if length < 50:
            return "short"
        elif length < 200:
            return "medium"
        elif length < 500:
            return "long"
        else:
            return "very_long"

    def health_check(self) -> dict[str, Any]:
        """Check health status of mention extractor."""
        try:
            # Test with a simple message containing various mention types
            test_message = (
                "Contact Davies Electrical Services on +27821234567 "
                "in Cape Town for emergency repairs"
            )
            test_mentions = self.extract_mentions(test_message)

            extraction_strategies = {
                "name_pattern": self.settings.name_pattern_extraction_enabled,
                "phone_pattern": self.settings.phone_pattern_extraction_enabled,
                "service_keyword": self.settings.service_keyword_extraction_enabled,
                "location_extraction": self.settings.location_extraction_enabled,
            }

            health_status = {
                "status": "healthy",
                "extraction_strategies": extraction_strategies,
                "configuration_loaded": {
                    "name_patterns": len(self._name_patterns) > 0,
                    "service_keywords": len(self._service_keywords) > 0,
                    "location_patterns": len(self._location_patterns) > 0,
                    "blacklisted_terms": len(self._blacklisted_terms) > 0,
                },
                "test_extraction": {
                    "mentions_found": len(test_mentions),
                    "extraction_types": [*{m.extraction_type for m in test_mentions}],
                },
            }

            self._metrics.record_gauge("mention_extractor_health_status", 1, {})
            return health_status

        except Exception as e:
            self._logger.error("MentionExtractor health check failed", error=str(e))
            self._metrics.record_gauge("mention_extractor_health_status", 0, {})
            self._metrics.increment_counter(
                "mention_extractor_health_check_failures_total",
                {"error_type": "health_check_failed"},
            )

            return {
                "status": "unhealthy",
                "error": str(e),
                "extraction_strategies": {},
            }
