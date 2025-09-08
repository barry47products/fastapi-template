"""Feature flags management system."""

from functools import lru_cache
from typing import Optional


class _FeatureFlagManagerSingleton:
    """Singleton holder for the feature flag manager."""

    _instance: Optional["FeatureFlagManager"] = None

    @classmethod
    def get_instance(cls) -> "FeatureFlagManager":
        """Get or create the singleton feature flag manager instance."""
        if cls._instance is None:
            cls._instance = FeatureFlagManager()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "FeatureFlagManager") -> None:
        """Set the singleton feature flag manager instance."""
        cls._instance = instance


class FeatureFlagManager:
    """Feature flags management system for runtime configuration."""

    def __init__(self, flags: dict[str, bool] | None = None) -> None:
        """Initialize feature flag manager.

        Args:
            flags: Initial flags dictionary, defaults to empty dict
        """
        self._flags: dict[str, bool] = flags.copy() if flags else {}

    def is_enabled(self, flag_name: str, default: bool = False) -> bool:
        """Check if a feature flag is enabled.

        Args:
            flag_name: Name of the feature flag
            default: Default value if flag doesn't exist

        Returns:
            Boolean indicating if flag is enabled
        """
        return self._flags.get(flag_name, default)

    def set_flag(self, flag_name: str, value: bool) -> None:
        """Set a feature flag value.

        Args:
            flag_name: Name of the feature flag
            value: Boolean value to set
        """
        self._flags[flag_name] = value

    def get_all_flags(self) -> dict[str, bool]:
        """Get all feature flags as a dictionary.

        Returns:
            Copy of all flags dictionary
        """
        return self._flags.copy()

    def toggle_flag(self, flag_name: str) -> None:
        """Toggle a feature flag value.

        Args:
            flag_name: Name of the feature flag to toggle
        """
        current_value = self._flags.get(flag_name, False)
        self._flags[flag_name] = not current_value

    def remove_flag(self, flag_name: str) -> None:
        """Remove a feature flag.

        Args:
            flag_name: Name of the feature flag to remove
        """
        self._flags.pop(flag_name, None)

    def load_from_dict(self, flags: dict[str, bool]) -> None:
        """Load flags from a dictionary, replacing all existing flags.

        Args:
            flags: Dictionary of flags to load
        """
        self._flags = flags.copy()


def configure_feature_flags(flags: dict[str, bool] | None = None) -> None:
    """Configure feature flags system.

    This function is kept for backward compatibility during initialization.
    With dependency injection, configuration is handled via get_feature_flag_manager().

    Args:
        flags: Dictionary of flags to initialize with
    """
    # For backward compatibility, set the singleton instance
    manager = FeatureFlagManager(flags)
    _FeatureFlagManagerSingleton.set_instance(manager)


@lru_cache
def get_feature_flag_manager() -> FeatureFlagManager:
    """Get a feature flag manager instance via dependency injection.

    Returns:
        FeatureFlagManager instance (cached)

    Creates a default manager with empty flags for dependency injection.
    """
    return FeatureFlagManager()
