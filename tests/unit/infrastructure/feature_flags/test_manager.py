"""Unit tests for feature flags manager."""

from __future__ import annotations

from src.infrastructure.feature_flags.manager import (
    FeatureFlagManager,
    _FeatureFlagManagerSingleton,
    configure_feature_flags,
    get_feature_flag_manager,
)


class TestFeatureFlagManager:
    """Test FeatureFlagManager class functionality."""

    def test_initializes_with_empty_flags_by_default(self) -> None:
        """Manager initializes with empty flags dictionary by default."""
        manager = FeatureFlagManager()

        assert manager.get_all_flags() == {}

    def test_initializes_with_provided_flags(self) -> None:
        """Manager initializes with provided flags dictionary."""
        initial_flags = {"feature_a": True, "feature_b": False}
        manager = FeatureFlagManager(flags=initial_flags)

        assert manager.get_all_flags() == initial_flags

    def test_initializes_with_copy_of_flags(self) -> None:
        """Manager creates copy of provided flags to avoid mutation."""
        initial_flags = {"feature_a": True}
        manager = FeatureFlagManager(flags=initial_flags)

        # Modify original flags
        initial_flags["feature_b"] = False

        # Manager should not be affected
        assert manager.get_all_flags() == {"feature_a": True}

    def test_is_enabled_returns_flag_value(self) -> None:
        """is_enabled returns correct flag value when flag exists."""
        manager = FeatureFlagManager({"feature_a": True, "feature_b": False})

        assert manager.is_enabled("feature_a") is True
        assert manager.is_enabled("feature_b") is False

    def test_is_enabled_returns_default_for_nonexistent_flag(self) -> None:
        """is_enabled returns default value when flag doesn't exist."""
        manager = FeatureFlagManager()

        assert manager.is_enabled("nonexistent") is False  # Default is False
        assert manager.is_enabled("nonexistent", default=True) is True

    def test_set_flag_creates_new_flag(self) -> None:
        """set_flag creates new flag with specified value."""
        manager = FeatureFlagManager()

        manager.set_flag("new_feature", True)

        assert manager.is_enabled("new_feature") is True
        assert manager.get_all_flags() == {"new_feature": True}

    def test_set_flag_updates_existing_flag(self) -> None:
        """set_flag updates existing flag value."""
        manager = FeatureFlagManager({"existing_feature": False})

        manager.set_flag("existing_feature", True)

        assert manager.is_enabled("existing_feature") is True

    def test_get_all_flags_returns_copy(self) -> None:
        """get_all_flags returns copy to prevent external mutation."""
        manager = FeatureFlagManager({"feature_a": True})

        flags_copy = manager.get_all_flags()
        flags_copy["feature_b"] = False  # Modify the copy

        # Original manager should be unaffected
        assert manager.get_all_flags() == {"feature_a": True}

    def test_toggle_flag_creates_flag_as_true_when_nonexistent(self) -> None:
        """toggle_flag creates new flag as True when it doesn't exist."""
        manager = FeatureFlagManager()

        manager.toggle_flag("new_feature")

        assert manager.is_enabled("new_feature") is True

    def test_toggle_flag_flips_existing_flag_values(self) -> None:
        """toggle_flag flips existing flag values correctly."""
        manager = FeatureFlagManager({"enabled_feature": True, "disabled_feature": False})

        manager.toggle_flag("enabled_feature")
        manager.toggle_flag("disabled_feature")

        assert manager.is_enabled("enabled_feature") is False
        assert manager.is_enabled("disabled_feature") is True

    def test_remove_flag_deletes_existing_flag(self) -> None:
        """remove_flag deletes existing flag from manager."""
        manager = FeatureFlagManager({"feature_to_remove": True, "feature_to_keep": False})

        manager.remove_flag("feature_to_remove")

        assert manager.get_all_flags() == {"feature_to_keep": False}
        assert manager.is_enabled("feature_to_remove") is False  # Default behavior

    def test_remove_flag_ignores_nonexistent_flag(self) -> None:
        """remove_flag safely ignores nonexistent flags."""
        manager = FeatureFlagManager({"existing_feature": True})

        # Should not raise exception
        manager.remove_flag("nonexistent_feature")

        assert manager.get_all_flags() == {"existing_feature": True}

    def test_load_from_dict_replaces_all_flags(self) -> None:
        """load_from_dict replaces all existing flags with new dictionary."""
        manager = FeatureFlagManager({"old_feature": True, "another_old": False})
        new_flags = {"new_feature": True, "different_feature": False}

        manager.load_from_dict(new_flags)

        assert manager.get_all_flags() == new_flags
        assert manager.is_enabled("old_feature") is False  # No longer exists

    def test_load_from_dict_creates_copy(self) -> None:
        """load_from_dict creates copy of provided flags to avoid mutation."""
        manager = FeatureFlagManager()
        flags_to_load = {"feature_a": True}

        manager.load_from_dict(flags_to_load)

        # Modify original dictionary
        flags_to_load["feature_b"] = False

        # Manager should not be affected
        assert manager.get_all_flags() == {"feature_a": True}


class TestFeatureFlagManagerSingleton:
    """Test singleton pattern for feature flag manager."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _FeatureFlagManagerSingleton._instance = None

    def test_get_instance_creates_new_manager_when_none_exists(self) -> None:
        """get_instance creates new FeatureFlagManager when none exists."""
        manager = _FeatureFlagManagerSingleton.get_instance()

        assert isinstance(manager, FeatureFlagManager)
        assert manager.get_all_flags() == {}

    def test_get_instance_returns_same_instance_on_subsequent_calls(self) -> None:
        """get_instance returns same instance on subsequent calls."""
        manager1 = _FeatureFlagManagerSingleton.get_instance()
        manager2 = _FeatureFlagManagerSingleton.get_instance()

        assert manager1 is manager2

    def test_set_instance_replaces_singleton_instance(self) -> None:
        """set_instance replaces the singleton instance."""
        # Get initial instance
        original_manager = _FeatureFlagManagerSingleton.get_instance()

        # Set new instance
        new_manager = FeatureFlagManager({"test_flag": True})
        _FeatureFlagManagerSingleton.set_instance(new_manager)

        # Verify new instance is returned
        retrieved_manager = _FeatureFlagManagerSingleton.get_instance()
        assert retrieved_manager is new_manager
        assert retrieved_manager is not original_manager
        assert retrieved_manager.is_enabled("test_flag") is True


class TestConfigureFeatureFlags:
    """Test configure_feature_flags function."""

    def setup_method(self) -> None:
        """Reset singleton state before each test."""
        _FeatureFlagManagerSingleton._instance = None

    def test_configures_feature_flags_for_backward_compatibility(self) -> None:
        """Configuration function maintained for backward compatibility."""
        flags = {"test_feature": True}

        # Should not raise any exceptions
        configure_feature_flags(flags)

    def test_sets_singleton_for_backward_compatibility(self) -> None:
        """Sets singleton manager for backward compatibility."""
        flags = {"fallback_test": False}

        configure_feature_flags(flags)

        singleton_manager = _FeatureFlagManagerSingleton.get_instance()
        assert singleton_manager.is_enabled("fallback_test") is False

    def test_configures_empty_flags_by_default(self) -> None:
        """Configures with empty flags when no flags provided to configure function."""
        configure_feature_flags()

        singleton_manager = _FeatureFlagManagerSingleton.get_instance()
        assert singleton_manager.get_all_flags() == {}

    def test_configures_with_none_flags(self) -> None:
        """Configures feature flags with None flags argument."""
        configure_feature_flags(flags=None)

        singleton_manager = _FeatureFlagManagerSingleton.get_instance()
        assert singleton_manager.get_all_flags() == {}

    def test_configures_with_empty_flags(self) -> None:
        """Configures feature flags with empty flags dictionary."""
        configure_feature_flags(flags={})

        singleton_manager = _FeatureFlagManagerSingleton.get_instance()
        assert singleton_manager.get_all_flags() == {}


class TestGetFeatureFlagManager:
    """Test get_feature_flag_manager function."""

    def setup_method(self) -> None:
        """Reset state before each test."""
        # Clear the lru_cache to ensure fresh instance
        get_feature_flag_manager.cache_clear()
        _FeatureFlagManagerSingleton._instance = None

    def test_returns_feature_flag_manager_instance(self) -> None:
        """Returns a FeatureFlagManager instance."""
        manager = get_feature_flag_manager()

        assert isinstance(manager, FeatureFlagManager)
        assert manager.get_all_flags() == {}

    def test_returns_same_instance_on_subsequent_calls(self) -> None:
        """Returns same cached instance on subsequent calls due to lru_cache."""
        manager1 = get_feature_flag_manager()
        manager2 = get_feature_flag_manager()

        assert manager1 is manager2

    def test_can_modify_returned_manager(self) -> None:
        """Can modify the returned manager instance."""
        manager = get_feature_flag_manager()

        # Set a flag
        manager.set_flag("test_feature", True)

        # Verify it persists in the cached instance
        manager2 = get_feature_flag_manager()
        assert manager2.is_enabled("test_feature") is True

    def test_creates_new_singleton_when_none_exists(self) -> None:
        """Creates new manager instance."""
        manager = get_feature_flag_manager()

        assert isinstance(manager, FeatureFlagManager)
        assert manager.get_all_flags() == {}

    def test_integration_with_configure_and_get(self) -> None:
        """Integration test: configure flags sets the singleton, get returns fresh instance."""
        flags = {"integration_test": True, "another_flag": False}

        # Configure flags (sets singleton)
        configure_feature_flags(flags)

        # Get manager returns a fresh instance (not the singleton)
        manager = get_feature_flag_manager()

        # The dependency injection version returns empty flags by default
        assert manager.get_all_flags() == {}

        # But the singleton is still configured
        singleton = _FeatureFlagManagerSingleton.get_instance()
        assert singleton.is_enabled("integration_test") is True
        assert singleton.is_enabled("another_flag") is False


class TestFeatureFlagManagerWorkflows:
    """Test complete feature flag workflows and use cases."""

    def test_typical_feature_flag_lifecycle(self) -> None:
        """Test complete lifecycle of a feature flag."""
        manager = FeatureFlagManager()

        # Feature starts disabled (default)
        assert manager.is_enabled("new_experimental_feature") is False

        # Enable feature for testing
        manager.set_flag("new_experimental_feature", True)
        assert manager.is_enabled("new_experimental_feature") is True

        # Toggle for A/B testing
        manager.toggle_flag("new_experimental_feature")
        assert manager.is_enabled("new_experimental_feature") is False

        # Re-enable after successful test
        manager.toggle_flag("new_experimental_feature")
        assert manager.is_enabled("new_experimental_feature") is True

        # Remove after full rollout
        manager.remove_flag("new_experimental_feature")
        assert manager.is_enabled("new_experimental_feature") is False

    def test_bulk_flag_management(self) -> None:
        """Test managing multiple flags at once."""
        manager = FeatureFlagManager()

        # Load initial configuration
        initial_config = {
            "user_dashboard_v2": True,
            "advanced_search": False,
            "beta_notifications": True,
            "experimental_ui": False,
        }
        manager.load_from_dict(initial_config)

        assert len(manager.get_all_flags()) == 4
        assert manager.is_enabled("user_dashboard_v2") is True
        assert manager.is_enabled("advanced_search") is False

        # Update configuration (simulating config reload)
        updated_config = {
            "user_dashboard_v2": True,  # Keep enabled
            "advanced_search": True,  # Enable
            "new_analytics": True,  # Add new flag
            # beta_notifications and experimental_ui removed
        }
        manager.load_from_dict(updated_config)

        assert len(manager.get_all_flags()) == 3
        assert manager.is_enabled("advanced_search") is True
        assert manager.is_enabled("new_analytics") is True
        assert manager.is_enabled("beta_notifications") is False  # Removed, default False

    def test_flag_isolation_between_managers(self) -> None:
        """Test that separate manager instances maintain flag isolation."""
        manager1 = FeatureFlagManager({"shared_name": True})
        manager2 = FeatureFlagManager({"shared_name": False})

        # Managers should have independent flag values
        assert manager1.is_enabled("shared_name") is True
        assert manager2.is_enabled("shared_name") is False

        # Modifying one should not affect the other
        manager1.set_flag("shared_name", False)
        assert manager1.is_enabled("shared_name") is False
        assert manager2.is_enabled("shared_name") is False  # Still independent

        manager2.set_flag("unique_to_manager2", True)
        assert manager1.is_enabled("unique_to_manager2") is False
        assert manager2.is_enabled("unique_to_manager2") is True

    def test_default_value_behavior_in_workflows(self) -> None:
        """Test default value behavior in real-world scenarios."""
        manager = FeatureFlagManager()

        # Check multiple flags with different defaults
        features_to_check = [
            ("conservative_feature", False),  # Default to disabled for safety
            ("progressive_feature", True),  # Default to enabled for adoption
            ("experimental_feature", False),  # Default to disabled for stability
        ]

        for feature_name, expected_default in features_to_check:
            assert manager.is_enabled(feature_name, default=expected_default) == expected_default

        # Enable one feature and verify others maintain defaults
        manager.set_flag("conservative_feature", True)

        assert manager.is_enabled("conservative_feature") is True
        assert manager.is_enabled("progressive_feature", default=True) is True
        assert manager.is_enabled("experimental_feature", default=False) is False
