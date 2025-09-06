"""
Domain models module.

This package contains sample domain entities that demonstrate:
- Rich domain models with behavior
- Business rule enforcement
- Domain event publishing  
- Immutability with controlled mutations
- Value object usage
- Self-validation

Domain entities are objects with identity that encapsulate business logic.
They should contain the core business rules and behavior of your application.

Replace these with your actual business domain entities.
"""

from .user import User, UserStatus

__all__ = [
    "User",
    "UserStatus",
]
