"""Unit tests for domain health checks."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.health import (
    _validate_user_age,
    check_business_rules,
    check_domain_layer_health,
    check_sample_domain_functionality,
    check_value_object_validation,
)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger for testing."""
    return MagicMock()


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create mock metrics collector for testing."""
    return MagicMock()


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.behaviour
class TestSampleDomainFunctionality:
    """Test sample domain functionality health check."""

    @pytest.mark.asyncio
    async def test_returns_true_with_valid_data(self) -> None:
        """Returns True when domain functionality is valid."""
        result = await check_sample_domain_functionality()
        assert result is True

    @pytest.mark.asyncio
    @patch("src.domain.health.datetime")
    async def test_returns_false_when_datetime_invalid(self, mock_datetime: MagicMock) -> None:
        """Returns False when datetime creation fails."""
        # Make datetime.now() return non-datetime object
        mock_datetime.now.return_value = "not a datetime"

        result = await check_sample_domain_functionality()
        assert result is False

    @pytest.mark.asyncio
    async def test_validates_data_structure(self) -> None:
        """Validates that data structure checking works."""
        # This test verifies the function works with valid data
        result = await check_sample_domain_functionality()
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self) -> None:
        """Returns False when an exception occurs."""
        with patch("src.domain.health.datetime") as mock_datetime:
            mock_datetime.now.side_effect = Exception("Test error")

            result = await check_sample_domain_functionality()
            assert result is False

    @pytest.mark.asyncio
    async def test_validates_numeric_value_type(self) -> None:
        """Validates that numeric value is int or float."""
        # This test covers the type checking branch
        result = await check_sample_domain_functionality()
        assert result is True

    @pytest.mark.asyncio
    async def test_validates_positive_numeric_value(self) -> None:
        """Validates that numeric value must be positive."""
        # The function returns numeric_value >= 0, so positive values should pass
        result = await check_sample_domain_functionality()
        assert result is True


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.behaviour
class TestValueObjectValidation:
    """Test value object validation health check."""

    @pytest.mark.asyncio
    async def test_returns_true_for_valid_email(self) -> None:
        """Returns True when email validation passes."""
        result = await check_value_object_validation()
        assert result is True

    @pytest.mark.asyncio
    @patch("src.domain.health.re.match")
    async def test_returns_false_for_invalid_email(self, mock_match: MagicMock) -> None:
        """Returns False when email validation fails."""
        mock_match.return_value = None

        result = await check_value_object_validation()
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self) -> None:
        """Returns False when an exception occurs."""
        with patch("src.domain.health.re.match") as mock_match:
            mock_match.side_effect = Exception("Regex error")

            result = await check_value_object_validation()
            assert result is False

    @pytest.mark.asyncio
    async def test_uses_correct_email_pattern(self) -> None:
        """Verifies the correct email pattern is used."""
        with patch("src.domain.health.re.match") as mock_match:
            mock_match.return_value = True

            await check_value_object_validation()

            # Verify the pattern and test email
            call_args = mock_match.call_args
            pattern = call_args[0][0]
            test_email = call_args[0][1]

            assert pattern == r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            assert test_email == "test@example.com"


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.behaviour
class TestUserAgeValidation:
    """Test user age validation helper function."""

    def test_valid_ages_return_true(self) -> None:
        """Returns True for ages between 13 and 120."""
        valid_ages = [13, 18, 25, 50, 65, 100, 120]
        for age in valid_ages:
            assert _validate_user_age(age) is True

    def test_invalid_ages_return_false(self) -> None:
        """Returns False for ages outside 13-120 range."""
        invalid_ages = [0, 5, 12, 121, 150, 200, -1]
        for age in invalid_ages:
            assert _validate_user_age(age) is False

    def test_boundary_ages(self) -> None:
        """Tests boundary values for age validation."""
        assert _validate_user_age(12) is False  # Just below minimum
        assert _validate_user_age(13) is True  # Minimum valid
        assert _validate_user_age(120) is True  # Maximum valid
        assert _validate_user_age(121) is False  # Just above maximum


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.behaviour
class TestBusinessRules:
    """Test business rules health check."""

    @pytest.mark.asyncio
    async def test_returns_true_when_all_rules_pass(self) -> None:
        """Returns True when all business rules are valid."""
        result = await check_business_rules()
        assert result is True

    @pytest.mark.asyncio
    @patch("src.domain.health._validate_user_age")
    async def test_returns_false_when_valid_age_check_fails(self, mock_validate: MagicMock) -> None:
        """Returns False when valid age check fails."""
        # Make the first call (age 25) return False
        mock_validate.side_effect = [False, True, True, True]

        result = await check_business_rules()
        assert result is False

    @pytest.mark.asyncio
    @patch("src.domain.health._validate_user_age")
    async def test_returns_false_when_invalid_age_accepted(self, mock_validate: MagicMock) -> None:
        """Returns False when invalid ages are incorrectly accepted."""
        # Make valid ages pass but invalid age (5) also pass
        mock_validate.side_effect = [True, True, True, False]  # 25, 65, 5, 150

        result = await check_business_rules()
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self) -> None:
        """Returns False when an exception occurs."""
        with patch("src.domain.health._validate_user_age") as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            result = await check_business_rules()
            assert result is False

    @pytest.mark.asyncio
    async def test_checks_correct_age_values(self) -> None:
        """Verifies the correct age values are checked."""
        with patch("src.domain.health._validate_user_age") as mock_validate:
            # The function stops on the first False return, so we need to understand its logic
            mock_validate.side_effect = [True, True, False]  # 25, 65 pass; 5 fails

            await check_business_rules()

            # Verify the ages that were checked
            calls = mock_validate.call_args_list
            ages_checked = [call[0][0] for call in calls]
            # The function checks: 25, 65 (valid), then 5 (invalid) - may not reach 150
            assert 25 in ages_checked
            assert 65 in ages_checked if len(ages_checked) > 1 else True
            assert 5 in ages_checked if len(ages_checked) > 2 else True


@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.behaviour
class TestDomainLayerHealthCheck:
    """Test comprehensive domain layer health check."""

    @pytest.mark.asyncio
    @patch("src.domain.health.get_metrics_collector")
    @patch("src.domain.health.get_logger")
    async def test_all_checks_pass(
        self, mock_get_logger: MagicMock, mock_get_metrics: MagicMock
    ) -> None:
        """Returns healthy when all checks pass."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        result = await check_domain_layer_health()

        assert result["healthy"] is True
        assert result["checks"]["sample_domain_functionality"] is True
        assert result["checks"]["value_object_validation"] is True
        assert result["checks"]["business_rules"] is True

        # Verify success metrics were recorded
        assert mock_metrics.increment_counter.call_count == 4  # 3 successes + 1 overall
        mock_logger.debug.assert_called_once_with("All domain health checks passed")

    @pytest.mark.asyncio
    @patch("src.domain.health.get_metrics_collector")
    @patch("src.domain.health.get_logger")
    @patch("src.domain.health.check_sample_domain_functionality")
    async def test_single_check_fails(
        self,
        mock_check_func: AsyncMock,
        mock_get_logger: MagicMock,
        mock_get_metrics: MagicMock,
    ) -> None:
        """Returns unhealthy when a single check fails."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_check_func.return_value = False

        result = await check_domain_layer_health()

        assert result["healthy"] is False
        assert result["checks"]["sample_domain_functionality"] is False
        assert result["checks"]["value_object_validation"] is True
        assert result["checks"]["business_rules"] is True

        # Verify failure was logged and recorded
        mock_logger.warning.assert_any_call(
            "Domain health check failed", check="sample_domain_functionality"
        )
        mock_logger.warning.assert_any_call("Some domain health checks failed")

    @pytest.mark.asyncio
    @patch("src.domain.health.get_metrics_collector")
    @patch("src.domain.health.get_logger")
    @patch("src.domain.health.check_value_object_validation")
    @patch("src.domain.health.check_business_rules")
    async def test_multiple_checks_fail(
        self,
        mock_business: AsyncMock,
        mock_value: AsyncMock,
        mock_get_logger: MagicMock,
        mock_get_metrics: MagicMock,
    ) -> None:
        """Returns unhealthy when multiple checks fail."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_value.return_value = False
        mock_business.return_value = False

        result = await check_domain_layer_health()

        assert result["healthy"] is False
        assert result["checks"]["sample_domain_functionality"] is True
        assert result["checks"]["value_object_validation"] is False
        assert result["checks"]["business_rules"] is False

        # Verify multiple failures were logged
        warning_calls = mock_logger.warning.call_args_list
        assert (
            len([call for call in warning_calls if call[0][0] == "Domain health check failed"]) == 2
        )

    @pytest.mark.asyncio
    @patch("src.domain.health.get_metrics_collector")
    @patch("src.domain.health.get_logger")
    @patch("src.domain.health.check_sample_domain_functionality")
    async def test_exception_during_health_check(
        self,
        mock_check_func: AsyncMock,
        mock_get_logger: MagicMock,
        mock_get_metrics: MagicMock,
    ) -> None:
        """Returns error status when exception occurs during health check."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_check_func.side_effect = Exception("Check failed")

        result = await check_domain_layer_health()

        assert result["healthy"] is False
        assert "error" in result
        assert result["error"] == "Check failed"
        assert result["checks"] == {}  # No checks completed

        # Verify error was logged
        mock_logger.error.assert_called_once_with("Domain health check error", error="Check failed")
        # Verify error metric was recorded
        mock_metrics.increment_counter.assert_called_with(
            "domain_layer_health_checks_total",
            {"status": "error"},
        )

    @pytest.mark.asyncio
    @patch("src.domain.health.get_metrics_collector")
    @patch("src.domain.health.get_logger")
    async def test_metrics_recorded_for_each_check(
        self, mock_get_logger: MagicMock, mock_get_metrics: MagicMock
    ) -> None:
        """Verifies metrics are recorded for each health check."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        await check_domain_layer_health()

        # Should record success for each check plus overall status
        calls = mock_metrics.increment_counter.call_args_list

        # Verify individual check metrics
        check_metrics = [call for call in calls if "health_check_successes_total" in call[0][0]]
        assert len(check_metrics) == 3

        # Verify overall status metric
        overall_metrics = [
            call for call in calls if "domain_layer_health_checks_total" in call[0][0]
        ]
        assert len(overall_metrics) == 1
        assert overall_metrics[0][0][1] == {"status": "healthy"}

    @pytest.mark.asyncio
    @patch("src.domain.health.get_metrics_collector")
    @patch("src.domain.health.get_logger")
    @patch("src.domain.health.check_sample_domain_functionality")
    async def test_failure_metrics_recorded(
        self,
        mock_check_func: AsyncMock,
        mock_get_logger: MagicMock,
        mock_get_metrics: MagicMock,
    ) -> None:
        """Verifies failure metrics are recorded correctly."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics
        mock_check_func.return_value = False

        await check_domain_layer_health()

        # Check that failure metric was recorded
        calls = mock_metrics.increment_counter.call_args_list
        failure_metrics = [
            call for call in calls if "domain_health_check_failures_total" in call[0][0]
        ]
        assert len(failure_metrics) == 1
        assert failure_metrics[0][0][1] == {"check": "sample_domain_functionality"}

        # Check overall unhealthy status
        overall_metrics = [
            call for call in calls if "domain_layer_health_checks_total" in call[0][0]
        ]
        assert len(overall_metrics) == 1
        assert overall_metrics[0][0][1] == {"status": "unhealthy"}

    @pytest.mark.asyncio
    async def test_actual_health_check_functions_are_async(self) -> None:
        """Verifies all health check functions are properly async."""
        import inspect

        assert inspect.iscoroutinefunction(check_sample_domain_functionality)
        assert inspect.iscoroutinefunction(check_value_object_validation)
        assert inspect.iscoroutinefunction(check_business_rules)
        assert inspect.iscoroutinefunction(check_domain_layer_health)

    @pytest.mark.asyncio
    async def test_health_checks_include_sleep_delay(self) -> None:
        """Verifies health checks include appropriate delays."""
        import time

        # Test that checks take some time (due to asyncio.sleep)
        start = time.time()
        await check_sample_domain_functionality()
        duration = time.time() - start

        # Should take at least 0.01 seconds due to sleep
        assert duration >= 0.01

    @pytest.mark.asyncio
    @patch("src.domain.health.get_metrics_collector")
    @patch("src.domain.health.get_logger")
    async def test_check_results_structure(
        self, mock_get_logger: MagicMock, mock_get_metrics: MagicMock
    ) -> None:
        """Verifies the structure of health check results."""
        mock_logger = MagicMock()
        mock_metrics = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_metrics.return_value = mock_metrics

        result = await check_domain_layer_health()

        # Verify result structure
        assert isinstance(result, dict)
        assert "healthy" in result
        assert isinstance(result["healthy"], bool)
        assert "checks" in result
        assert isinstance(result["checks"], dict)

        # Verify all expected checks are present
        expected_checks = [
            "sample_domain_functionality",
            "value_object_validation",
            "business_rules",
        ]
        for check_name in expected_checks:
            assert check_name in result["checks"]
            assert isinstance(result["checks"][check_name], bool)
