"""Unit tests for Money value object."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.domain.value_objects.money import Money
from src.shared.exceptions import ValidationException


class TestMoneyValidation:
    """Test money amount and currency validation."""

    def test_valid_amount_types(self) -> None:
        """Accepts valid amount types and converts to Decimal."""
        valid_amounts = [
            (100, Decimal("100.00")),
            (99.99, Decimal("99.99")),
            ("50.50", Decimal("50.50")),
            (Decimal("25.25"), Decimal("25.25")),
            (0, Decimal("0.00")),
        ]

        for input_amount, expected_decimal in valid_amounts:
            money = Money(amount=input_amount)  # type: ignore[arg-type]
            assert money.amount == expected_decimal
            assert isinstance(money.amount, Decimal)

    def test_amount_rounding_to_two_decimal_places(self) -> None:
        """Rounds amounts to 2 decimal places using ROUND_HALF_UP."""
        test_cases = [
            (99.999, Decimal("100.00")),
            (99.995, Decimal("100.00")),
            (99.994, Decimal("99.99")),
            (50.555, Decimal("50.56")),
            (50.554, Decimal("50.55")),
        ]

        for input_amount, expected_amount in test_cases:
            money = Money(amount=input_amount)  # type: ignore[arg-type]
            assert money.amount == expected_amount

    def test_none_amount_raises_validation_error(self) -> None:
        """Raises ValidationException for None amount."""
        import pydantic_core

        with pytest.raises((pydantic_core.ValidationError, Exception)) as exc_info:
            Money(amount=None)  # type: ignore[arg-type]

        # Pydantic will raise ValidationError before our custom validator runs
        assert "Decimal input should be" in str(exc_info.value)

    def test_negative_amount_raises_validation_error(self) -> None:
        """Raises ValidationException for negative amounts."""
        with pytest.raises(ValidationException) as exc_info:
            Money(amount=-10.50)  # type: ignore[arg-type]

        assert "Amount cannot be negative" in str(exc_info.value)
        assert exc_info.value.field == "amount"

    def test_invalid_amount_type_raises_validation_error(self) -> None:
        """Raises ValidationException for invalid amount types."""
        invalid_amounts = [[], {}, object(), lambda x: x]

        for invalid_amount in invalid_amounts:
            import pydantic_core

            with pytest.raises((pydantic_core.ValidationError, Exception)) as exc_info:
                Money(amount=invalid_amount)  # type: ignore[arg-type]

            # Pydantic will raise ValidationError before our custom validator runs
            assert "Decimal input should be" in str(exc_info.value)

    def test_valid_currency_codes(self) -> None:
        """Accepts valid ISO 4217 currency codes."""
        valid_currencies = [
            "USD",
            "EUR",
            "GBP",
            "JPY",
            "CAD",
            "AUD",
            "CHF",
            "CNY",
            "SEK",
            "NZD",
            "MXN",
            "SGD",
            "HKD",
            "NOK",
            "TRY",
            "ZAR",
            "BRL",
            "INR",
            "KRW",
            "PLN",
            "TWD",
            "THB",
        ]

        for currency in valid_currencies:
            money = Money(amount=100, currency=currency)  # type: ignore[arg-type]
            assert money.currency == currency

    def test_currency_normalization(self) -> None:
        """Normalizes currency by converting to uppercase and trimming."""
        money = Money(amount=100, currency="  usd  ")  # type: ignore[arg-type]
        assert money.currency == "USD"

    def test_default_currency_is_usd(self) -> None:
        """Uses USD as default currency."""
        money = Money(amount=100)  # type: ignore[arg-type]
        assert money.currency == "USD"

    def test_empty_currency_raises_validation_error(self) -> None:
        """Raises ValidationException for empty currency."""
        with pytest.raises(ValidationException) as exc_info:
            Money(amount=100, currency="")  # type: ignore[arg-type]

        assert "Currency code cannot be empty" in str(exc_info.value)
        assert exc_info.value.field == "currency"

    def test_none_currency_raises_validation_error(self) -> None:
        """Raises ValidationException for None currency."""
        import pydantic_core

        with pytest.raises((pydantic_core.ValidationError, Exception)) as exc_info:
            Money(amount=100, currency=None)  # type: ignore[arg-type]

        # Pydantic will raise ValidationError before our custom validator runs
        assert "Input should be a valid string" in str(exc_info.value)

    def test_invalid_currency_length_raises_validation_error(self) -> None:
        """Raises ValidationException for currency codes not 3 characters."""
        invalid_currencies = ["US", "USDX", "A", ""]

        for invalid_currency in invalid_currencies:
            with pytest.raises(ValidationException) as exc_info:
                Money(amount=100, currency=invalid_currency)  # type: ignore[arg-type]

            if invalid_currency == "":
                assert "Currency code cannot be empty" in str(exc_info.value)
            else:
                assert "Currency code must be 3 characters" in str(exc_info.value)
            assert exc_info.value.field == "currency"

    def test_non_alpha_currency_raises_validation_error(self) -> None:
        """Raises ValidationException for currency codes with non-letters."""
        invalid_currencies = ["US1", "U$D", "12D"]

        for invalid_currency in invalid_currencies:
            with pytest.raises(ValidationException) as exc_info:
                Money(amount=100, currency=invalid_currency)  # type: ignore[arg-type]

            assert "Currency code must contain only letters" in str(exc_info.value)
            assert exc_info.value.field == "currency"

    def test_unsupported_currency_raises_validation_error(self) -> None:
        """Raises ValidationException for unsupported currency codes."""
        with pytest.raises(ValidationException) as exc_info:
            Money(amount=100, currency="XYZ")  # type: ignore[arg-type]

        assert "Unsupported currency code: XYZ" in str(exc_info.value)
        assert exc_info.value.field == "currency"


class TestMoneyStringMethods:
    """Test string representation and comparison methods."""

    def test_str_returns_formatted_money_string(self) -> None:
        """Returns formatted money string."""
        money = Money(amount=Decimal("100.50"), currency="USD")
        assert str(money) == "USD 100.50"

    def test_repr_returns_detailed_representation(self) -> None:
        """Returns detailed representation."""
        money = Money(amount=Decimal("100.50"), currency="USD")
        assert repr(money) == "Money(amount=100.50, currency='USD')"

    def test_hash_returns_consistent_value(self) -> None:
        """Returns consistent hash for same money value."""
        money1 = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        money2 = Money(amount=100, currency="USD")  # type: ignore[arg-type]

        assert hash(money1) == hash(money2)

    def test_hash_differs_for_different_amounts(self) -> None:
        """Returns different hash for different amounts."""
        money1 = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        money2 = Money(amount=200, currency="USD")  # type: ignore[arg-type]

        assert hash(money1) != hash(money2)

    def test_hash_differs_for_different_currencies(self) -> None:
        """Returns different hash for different currencies."""
        money1 = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        money2 = Money(amount=100, currency="EUR")  # type: ignore[arg-type]

        assert hash(money1) != hash(money2)

    def test_equality_with_same_money_object(self) -> None:
        """Returns True when comparing same Money objects."""
        money1 = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        money2 = Money(amount=100, currency="USD")  # type: ignore[arg-type]

        assert money1 == money2

    def test_equality_with_different_amounts(self) -> None:
        """Returns False when comparing different amounts."""
        money1 = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        money2 = Money(amount=200, currency="USD")  # type: ignore[arg-type]

        assert money1 != money2

    def test_equality_with_different_currencies(self) -> None:
        """Returns False when comparing different currencies."""
        money1 = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        money2 = Money(amount=100, currency="EUR")  # type: ignore[arg-type]

        assert money1 != money2

    def test_equality_with_different_type_returns_false(self) -> None:
        """Returns False when comparing with different types."""
        money = Money(amount=100, currency="USD")  # type: ignore[arg-type]

        assert money != "USD 100.00"
        assert money != 100
        assert money is not None


class TestMoneyArithmeticOperations:
    """Test arithmetic operations."""

    def test_addition_same_currency(self) -> None:
        """Adds two Money values with same currency."""
        money1 = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        money2 = Money(amount=50, currency="USD")  # type: ignore[arg-type]
        result = money1 + money2

        assert result.amount == Decimal("150.00")
        assert result.currency == "USD"
        assert isinstance(result, Money)

    def test_addition_different_currency_raises_error(self) -> None:
        """Raises ValidationException when adding different currencies."""
        money1 = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        money2 = Money(amount=50, currency="EUR")  # type: ignore[arg-type]

        with pytest.raises(ValidationException) as exc_info:
            money1 + money2

        assert "Cannot operate on different currencies: USD vs EUR" in str(exc_info.value)
        assert exc_info.value.field == "currency"

    def test_subtraction_same_currency(self) -> None:
        """Subtracts two Money values with same currency."""
        money1 = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        money2 = Money(amount=30, currency="USD")  # type: ignore[arg-type]
        result = money1 - money2

        assert result.amount == Decimal("70.00")
        assert result.currency == "USD"
        assert isinstance(result, Money)

    def test_subtraction_different_currency_raises_error(self) -> None:
        """Raises ValidationException when subtracting different currencies."""
        money1 = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        money2 = Money(amount=30, currency="EUR")  # type: ignore[arg-type]

        with pytest.raises(ValidationException) as exc_info:
            money1 - money2

        assert "Cannot operate on different currencies: USD vs EUR" in str(exc_info.value)
        assert exc_info.value.field == "currency"

    def test_subtraction_resulting_negative_raises_error(self) -> None:
        """Raises ValidationException when subtraction results in negative."""
        money1 = Money(amount=50, currency="USD")  # type: ignore[arg-type]
        money2 = Money(amount=100, currency="USD")  # type: ignore[arg-type]

        with pytest.raises(ValidationException) as exc_info:
            money1 - money2

        assert "Result cannot be negative" in str(exc_info.value)
        assert exc_info.value.field == "amount"

    def test_multiplication_by_integer(self) -> None:
        """Multiplies money by integer."""
        money = Money(amount=25, currency="USD")  # type: ignore[arg-type]
        result = money * 4

        assert result.amount == Decimal("100.00")
        assert result.currency == "USD"
        assert isinstance(result, Money)

    def test_multiplication_by_float(self) -> None:
        """Multiplies money by float."""
        money = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        result = money * 1.5

        assert result.amount == Decimal("150.00")
        assert result.currency == "USD"

    def test_multiplication_by_decimal(self) -> None:
        """Multiplies money by Decimal."""
        money = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        result = money * Decimal("2.25")

        assert result.amount == Decimal("225.00")
        assert result.currency == "USD"

    def test_multiplication_by_invalid_type_raises_error(self) -> None:
        """Raises ValidationException when multiplying by invalid type."""
        money = Money(amount=100, currency="USD")  # type: ignore[arg-type]

        with pytest.raises(ValidationException) as exc_info:
            money * "invalid"  # type: ignore[operator]

        assert "Multiplier must be a number" in str(exc_info.value)
        assert exc_info.value.field == "multiplier"

    def test_multiplication_by_negative_raises_error(self) -> None:
        """Raises ValidationException when multiplying by negative number."""
        money = Money(amount=100, currency="USD")  # type: ignore[arg-type]

        with pytest.raises(ValidationException) as exc_info:
            money * -2

        assert "Multiplier cannot be negative" in str(exc_info.value)
        assert exc_info.value.field == "multiplier"

    def test_division_by_integer(self) -> None:
        """Divides money by integer."""
        money = Money(amount=100, currency="USD")  # type: ignore[arg-type]
        result = money / 4

        assert result.amount == Decimal("25.00")
        assert result.currency == "USD"
        assert isinstance(result, Money)

    def test_division_by_float(self) -> None:
        """Divides money by float."""
        money = Money(amount=150, currency="USD")  # type: ignore[arg-type]
        result = money / 1.5

        assert result.amount == Decimal("100.00")
        assert result.currency == "USD"

    def test_division_by_decimal(self) -> None:
        """Divides money by Decimal."""
        money = Money(amount=225, currency="USD")  # type: ignore[arg-type]
        result = money / Decimal("2.25")

        assert result.amount == Decimal("100.00")
        assert result.currency == "USD"

    def test_division_by_invalid_type_raises_error(self) -> None:
        """Raises ValidationException when dividing by invalid type."""
        money = Money(amount=100, currency="USD")  # type: ignore[arg-type]

        with pytest.raises(ValidationException) as exc_info:
            money / "invalid"  # type: ignore[operator]

        assert "Divisor must be a number" in str(exc_info.value)
        assert exc_info.value.field == "divisor"

    def test_division_by_zero_raises_error(self) -> None:
        """Raises ValidationException when dividing by zero."""
        money = Money(amount=100, currency="USD")  # type: ignore[arg-type]

        with pytest.raises(ValidationException) as exc_info:
            money / 0

        assert "Divisor must be positive" in str(exc_info.value)
        assert exc_info.value.field == "divisor"

    def test_division_by_negative_raises_error(self) -> None:
        """Raises ValidationException when dividing by negative number."""
        money = Money(amount=100, currency="USD")  # type: ignore[arg-type]

        with pytest.raises(ValidationException) as exc_info:
            money / -2

        assert "Divisor must be positive" in str(exc_info.value)
        assert exc_info.value.field == "divisor"


class TestMoneyUtilityMethods:
    """Test utility methods."""

    def test_to_cents_conversion(self) -> None:
        """Converts money to cents."""
        money = Money(amount=Decimal("100.50"), currency="USD")
        assert money.to_cents() == 10050

    def test_to_cents_zero_amount(self) -> None:
        """Converts zero money to cents."""
        money = Money(amount=Decimal("0.00"), currency="USD")
        assert money.to_cents() == 0

    def test_to_cents_fractional_cents(self) -> None:
        """Converts money with fractional cents."""
        money = Money(amount=Decimal("99.99"), currency="USD")
        assert money.to_cents() == 9999

    def test_format_display_with_symbols(self) -> None:
        """Formats money with currency symbols."""
        test_cases = [
            ("USD", "$100.50"),
            ("EUR", "€100.50"),
            ("GBP", "£100.50"),
            ("JPY", "¥100.50"),
            ("CAD", "C$100.50"),
            ("AUD", "A$100.50"),
            ("CHF", "CHF100.50"),
            ("CNY", "¥100.50"),
        ]

        for currency, expected_format in test_cases:
            money = Money(amount=Decimal("100.50"), currency=currency)
            assert money.format_display() == expected_format

    def test_format_display_without_symbols(self) -> None:
        """Formats money without currency symbols."""
        money = Money(amount=Decimal("100.50"), currency="USD")
        assert money.format_display(include_symbol=False) == "100.50 USD"

    def test_format_display_unsupported_currency(self) -> None:
        """Formats money with unsupported currency without symbol."""
        money = Money(amount=Decimal("100.50"), currency="SEK")
        assert money.format_display() == "100.50 SEK"

    def test_is_zero_true(self) -> None:
        """Returns True for zero amount."""
        money = Money(amount=Decimal("0.00"), currency="USD")
        assert money.is_zero() is True

    def test_is_zero_false(self) -> None:
        """Returns False for non-zero amount."""
        money = Money(amount=Decimal("0.01"), currency="USD")
        assert money.is_zero() is False

    def test_is_positive_true(self) -> None:
        """Returns True for positive amount."""
        money = Money(amount=Decimal("100.00"), currency="USD")
        assert money.is_positive() is True

    def test_is_positive_false_for_zero(self) -> None:
        """Returns False for zero amount."""
        money = Money(amount=Decimal("0.00"), currency="USD")
        assert money.is_positive() is False


class TestMoneyClassMethods:
    """Test class factory methods."""

    def test_zero_factory_method_default_currency(self) -> None:
        """Creates zero money with default USD currency."""
        money = Money.zero()

        assert money.amount == Decimal("0.00")
        assert money.currency == "USD"
        assert money.is_zero() is True

    def test_zero_factory_method_specific_currency(self) -> None:
        """Creates zero money with specific currency."""
        money = Money.zero(currency="EUR")

        assert money.amount == Decimal("0.00")
        assert money.currency == "EUR"
        assert money.is_zero() is True

    def test_from_cents_factory_method_default_currency(self) -> None:
        """Creates money from cents with default USD currency."""
        money = Money.from_cents(12345)

        assert money.amount == Decimal("123.45")
        assert money.currency == "USD"

    def test_from_cents_factory_method_specific_currency(self) -> None:
        """Creates money from cents with specific currency."""
        money = Money.from_cents(5000, currency="EUR")

        assert money.amount == Decimal("50.00")
        assert money.currency == "EUR"

    def test_from_cents_zero_amount(self) -> None:
        """Creates money from zero cents."""
        money = Money.from_cents(0)

        assert money.amount == Decimal("0.00")
        assert money.currency == "USD"
        assert money.is_zero() is True


class TestMoneyImmutability:
    """Test money immutability."""

    def test_money_is_frozen(self) -> None:
        """Money objects are immutable (frozen)."""
        money = Money(amount=100, currency="USD")  # type: ignore[arg-type]

        import pydantic_core

        with pytest.raises((pydantic_core.ValidationError, TypeError)):
            money.amount = Decimal("200.00")  # type: ignore[misc]

    def test_money_model_config_frozen(self) -> None:
        """Money model configuration has frozen=True."""
        assert Money.model_config["frozen"] is True


class TestMoneyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_amounts(self) -> None:
        """Handles very small amounts correctly."""
        money = Money(amount=Decimal("0.01"), currency="USD")
        assert money.amount == Decimal("0.01")
        assert money.to_cents() == 1

    def test_large_amounts(self) -> None:
        """Handles large amounts correctly."""
        money = Money(amount=Decimal("999999999.99"), currency="USD")
        assert money.amount == Decimal("999999999.99")
        assert money.to_cents() == 99999999999

    def test_precise_decimal_calculations(self) -> None:
        """Maintains precision in decimal calculations."""
        money1 = Money(amount=Decimal("10.01"), currency="USD")
        money2 = Money(amount=Decimal("20.02"), currency="USD")
        result = money1 + money2

        assert result.amount == Decimal("30.03")

    def test_rounding_edge_cases(self) -> None:
        """Handles rounding edge cases correctly."""
        test_cases = [
            ("0.005", Decimal("0.01")),  # Round half up
            ("0.004", Decimal("0.00")),  # Round down
            ("1.115", Decimal("1.12")),  # Round half up
            ("1.114", Decimal("1.11")),  # Round down
        ]

        for input_str, expected in test_cases:
            money = Money(amount=Decimal(input_str), currency="USD")
            assert money.amount == expected
