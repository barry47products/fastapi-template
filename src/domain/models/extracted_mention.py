"""ExtractedMention domain model representing a provider mention found in messages."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExtractedMention(BaseModel):
    """
    Immutable domain model representing an extracted mention from a message.

    Represents a provider mention identified in WhatsApp group messages through
    various extraction strategies (name patterns, phone numbers, service keywords,
    location references). Contains position information and confidence scoring
    for downstream processing and validation.
    """

    model_config = ConfigDict(frozen=True)

    text: str = Field(description="The extracted mention text")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for this extraction",
    )
    extraction_type: str = Field(description="Type of extraction strategy used")
    start_position: int = Field(ge=0, description="Start position in original message")
    end_position: int = Field(ge=0, description="End position in original message")

    @model_validator(mode="after")
    def validate_positions(self) -> "ExtractedMention":
        """Validate position consistency."""
        if self.end_position <= self.start_position:
            raise ValueError("end_position must be greater than start_position")
        return self

    def __str__(self) -> str:
        """Return string representation of ExtractedMention."""
        return f"{self.extraction_type}: '{self.text}' (confidence: {self.confidence:.2f})"

    def __repr__(self) -> str:
        """Return detailed string representation of ExtractedMention."""
        return (
            f"ExtractedMention(text='{self.text}', "
            f"confidence={self.confidence}, type='{self.extraction_type}')"
        )

    def __hash__(self) -> int:
        """Return hash based on text, position, and extraction type."""
        return hash(
            (self.text, self.start_position, self.end_position, self.extraction_type),
        )

    def __eq__(self, other: object) -> bool:
        """Compare mentions based on text, position, and extraction type."""
        if not isinstance(other, ExtractedMention):
            return False
        return (
            self.text == other.text
            and self.start_position == other.start_position
            and self.end_position == other.end_position
            and self.extraction_type == other.extraction_type
        )

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if mention has high confidence score."""
        return self.confidence >= threshold

    def get_length(self) -> int:
        """Get the character length of the extracted text."""
        return len(self.text)

    def get_position_span(self) -> int:
        """Get the character span of the mention in the original message."""
        return self.end_position - self.start_position

    def overlaps_with(self, other: "ExtractedMention") -> bool:
        """Check if this mention overlaps with another mention positionally."""
        return not (
            self.end_position <= other.start_position or other.end_position <= self.start_position
        )
