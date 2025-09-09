"""Money value object for financial calculations."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import BaseModel, field_validator

from src.shared.exceptions import ValidationException


class Money(BaseModel):
    """
    Money value object for precise financial calculations.

    Demonstrates value object patterns for financial data:
    - Decimal precision for currency
    - Currency code validation
    - Arithmetic operations
    - Formatting for display
    - Immutability
    """

    model_config = {"frozen": True}

    amount: Decimal
    currency: str = "USD"

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Any) -> Decimal:
        """Validate and normalize amount."""
        if v is None:
            raise ValidationException("Amount cannot be null", field="amount")

        try:
            # Convert to Decimal for precision
            if isinstance(v, int | float | str):
                decimal_amount = Decimal(str(v))
            elif isinstance(v, Decimal):
                decimal_amount = v
            else:
                raise ValueError("Invalid amount type")

            # Round to 2 decimal places for currency
            decimal_amount = decimal_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            if decimal_amount < 0:
                raise ValidationException("Amount cannot be negative", field="amount")

            return decimal_amount

        except (ValueError, TypeError) as e:
            raise ValidationException(f"Invalid amount format: {e!s}", field="amount") from e

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code."""
        if not v or not isinstance(v, str):
            raise ValidationException("Currency code cannot be empty", field="currency")

        currency = v.strip().upper()

        # Validate currency code format (ISO 4217)
        if len(currency) != 3:
            raise ValidationException("Currency code must be 3 characters", field="currency")

        if not currency.isalpha():
            raise ValidationException("Currency code must contain only letters", field="currency")

        # Common currency codes validation
        valid_currencies = {
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
        }

        if currency not in valid_currencies:
            raise ValidationException(f"Unsupported currency code: {currency}", field="currency")

        return currency

    def __str__(self) -> str:
        """Return formatted money string."""
        return f"{self.currency} {self.amount:.2f}"

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"Money(amount={self.amount}, currency='{self.currency}')"

    def __hash__(self) -> int:
        """Return hash for set/dict usage."""
        return hash((self.amount, self.currency))

    def __eq__(self, other: Any) -> bool:
        """Compare money values."""
        if isinstance(other, Money):
            return self.amount == other.amount and self.currency == other.currency
        return False

    def __add__(self, other: "Money") -> "Money":
        """Add two Money values."""
        self._validate_same_currency(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        """Subtract two Money values."""
        self._validate_same_currency(other)
        result_amount = self.amount - other.amount
        if result_amount < 0:
            raise ValidationException("Result cannot be negative", field="amount")
        return Money(amount=result_amount, currency=self.currency)

    def __mul__(self, multiplier: float | int | Decimal) -> "Money":
        """Multiply money by a number."""
        if not isinstance(multiplier, int | float | Decimal):
            raise ValidationException("Multiplier must be a number", field="multiplier")

        if multiplier < 0:
            raise ValidationException("Multiplier cannot be negative", field="multiplier")

        new_amount = self.amount * Decimal(str(multiplier))
        return Money(amount=new_amount, currency=self.currency)

    def __truediv__(self, divisor: float | int | Decimal) -> "Money":
        """Divide money by a number."""
        if not isinstance(divisor, int | float | Decimal):
            raise ValidationException("Divisor must be a number", field="divisor")

        if divisor <= 0:
            raise ValidationException("Divisor must be positive", field="divisor")

        new_amount = self.amount / Decimal(str(divisor))
        return Money(amount=new_amount, currency=self.currency)

    def _validate_same_currency(self, other: "Money") -> None:
        """Validate that two Money objects have the same currency."""
        if self.currency != other.currency:
            raise ValidationException(
                f"Cannot operate on different currencies: {self.currency} vs {other.currency}",
                field="currency",
            )

    def to_cents(self) -> int:
        """Convert to cents/smallest currency unit."""
        return int(self.amount * 100)

    def format_display(self, include_symbol: bool = True) -> str:
        """Format money for display with currency symbols."""
        symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CAD": "C$",
            "AUD": "A$",
            "CHF": "CHF",
            "CNY": "¥",
        }

        if include_symbol and self.currency in symbols:
            symbol = symbols[self.currency]
            return f"{symbol}{self.amount:.2f}"
        return f"{self.amount:.2f} {self.currency}"

    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self.amount == 0

    def is_positive(self) -> bool:
        """Check if amount is positive."""
        return self.amount > 0

    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        """Create zero money value."""
        return cls(amount=Decimal("0.00"), currency=currency)

    @classmethod
    def from_cents(cls, cents: int, currency: str = "USD") -> "Money":
        """Create Money from cents/smallest currency unit."""
        amount = Decimal(cents) / 100
        return cls(amount=amount, currency=currency)
