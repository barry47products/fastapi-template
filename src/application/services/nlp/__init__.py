"""NLP module for message classification, mention extraction, and summary generation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mention_extractor import MentionExtractor  # noqa: F401
    from .message_classifier import MessageClassifier  # noqa: F401
    from .provider_matcher import ProviderMatcher, ProviderMatchResult  # noqa: F401
    from .summary_generator import GroupSummaryGenerator  # noqa: F401
else:
    # Runtime placeholder imports to satisfy Pylint
    try:
        # pylint: disable-next=import-outside-toplevel
        from .mention_extractor import MentionExtractor

        # pylint: disable-next=import-outside-toplevel
        from .message_classifier import MessageClassifier

        # pylint: disable-next=import-outside-toplevel
        from .provider_matcher import ProviderMatcher, ProviderMatchResult

        # pylint: disable-next=import-outside-toplevel
        from .summary_generator import GroupSummaryGenerator
    except ImportError:
        # Fallback to lazy loading if imports fail due to circular dependencies
        def __getattr__(name: str) -> type:
            """Lazy import NLP classes to avoid circular dependencies."""
            if name == "MentionExtractor":
                # pylint: disable-next=import-outside-toplevel
                from .mention_extractor import MentionExtractor

                return MentionExtractor
            if name == "MessageClassifier":
                # pylint: disable-next=import-outside-toplevel
                from .message_classifier import MessageClassifier

                return MessageClassifier
            if name == "ProviderMatcher":
                # pylint: disable-next=import-outside-toplevel
                from .provider_matcher import ProviderMatcher

                return ProviderMatcher
            if name == "ProviderMatchResult":
                # pylint: disable-next=import-outside-toplevel
                from .provider_matcher import ProviderMatchResult

                return ProviderMatchResult
            if name == "GroupSummaryGenerator":
                # pylint: disable-next=import-outside-toplevel
                from .summary_generator import GroupSummaryGenerator

                return GroupSummaryGenerator
            raise AttributeError(f"module {__name__} has no attribute {name}")

        # Define placeholders for __all__ - these should not interfere with __getattr__
        # They're only used for type checking and __all__ definition


__all__ = [
    "MessageClassifier",
    "MentionExtractor",
    "ProviderMatcher",
    "ProviderMatchResult",
    "GroupSummaryGenerator",
]
