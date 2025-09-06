"""
Value objects for domain layer.

This package contains sample value objects that demonstrate:
- Immutable value types
- Self-validation
- Rich behavior methods
- Equality by value
- Domain-specific constraints

Value objects represent concepts that are identified by their value rather
than by identity. Common examples include Money, Email, Address, etc.

Replace these with your actual domain value objects.
"""

from .email import Email
from .money import Money
from .phone_number import PhoneNumber

__all__ = ["Email", "Money", "PhoneNumber"]
