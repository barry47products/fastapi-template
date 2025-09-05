"""Message classification domain models for WhatsApp message processing."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MessageType(str, Enum):
    """
    Classification types for WhatsApp group messages.

    REQUEST: Messages asking for service provider recommendations
    RECOMMENDATION: Messages recommending or endorsing service providers
    UNKNOWN: Messages that don't fit classification patterns
    """

    REQUEST = "request"
    RECOMMENDATION = "recommendation"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        """Return the enum value as string."""
        return self.value

    def is_actionable(self) -> bool:
        """Check if message type requires system action."""
        return self in {MessageType.REQUEST, MessageType.RECOMMENDATION}

    def requires_mention_extraction(self) -> bool:
        """Check if message type should trigger mention extraction."""
        return self == MessageType.RECOMMENDATION


class ClassificationResult(BaseModel):
    """
    Immutable domain model representing message classification results.

    Contains the classification outcome, confidence metrics, and supporting
    evidence (keywords, rule matches) for downstream processing and validation.
    Used to determine appropriate system responses and mention extraction triggers.
    """

    model_config = ConfigDict(frozen=True)

    message_type: MessageType = Field(description="Classified message type")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Classification confidence score",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords that influenced classification",
    )
    rule_matches: list[str] = Field(
        default_factory=list,
        description="Rule patterns that matched during classification",
    )

    def __str__(self) -> str:
        """Return string representation of ClassificationResult."""
        return f"{self.message_type.value.title()} (confidence: {self.confidence:.2f})"

    def __repr__(self) -> str:
        """Return detailed string representation of ClassificationResult."""
        return (
            f"ClassificationResult(type={self.message_type.value}, "
            f"confidence={self.confidence}, keywords={len(self.keywords)})"
        )

    def __hash__(self) -> int:
        """Return hash based on message type and confidence."""
        return hash((self.message_type, round(self.confidence, 2)))

    def __eq__(self, other: object) -> bool:
        """Compare classification results based on type and confidence."""
        if not isinstance(other, ClassificationResult):
            return False
        return (
            self.message_type == other.message_type
            and abs(self.confidence - other.confidence) < 0.01
        )

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if classification has high confidence score."""
        return self.confidence >= threshold

    def is_actionable(self) -> bool:
        """Check if classified message requires system action."""
        return self.message_type.is_actionable()

    def should_extract_mentions(self) -> bool:
        """Check if classified message should trigger mention extraction."""
        return self.message_type.requires_mention_extraction()

    def get_supporting_evidence_count(self) -> int:
        """Get total count of supporting evidence (keywords + rule matches)."""
        return len(self.keywords) + len(self.rule_matches)

    def has_keyword_evidence(self, keyword: str) -> bool:
        """Check if specific keyword was part of classification evidence."""
        return keyword.lower() in [k.lower() for k in self.keywords]

    def has_rule_evidence(self, rule_pattern: str) -> bool:
        """Check if specific rule pattern was part of classification evidence."""
        return rule_pattern in self.rule_matches

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_type": self.message_type.value,
            "confidence": self.confidence,
            "keywords": self.keywords,
            "rule_matches": self.rule_matches,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassificationResult":
        """Create ClassificationResult from dictionary data."""
        return cls(
            message_type=MessageType(data["message_type"]),
            confidence=data["confidence"],
            keywords=data.get("keywords", []),
            rule_matches=data.get("rule_matches", []),
        )
