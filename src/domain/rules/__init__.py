"""Domain rules package."""

# ProviderMatcher has been moved to application services
# Import from the new location for backward compatibility
from src.application.services.nlp import ProviderMatcher, ProviderMatchResult

__all__ = ["ProviderMatcher", "ProviderMatchResult"]
