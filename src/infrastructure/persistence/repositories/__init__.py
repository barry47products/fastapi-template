"""Sample repository implementations for template demonstration."""

from .sample_product_repository import InMemoryProductRepository
from .sample_user_repository import InMemoryUserRepository

__all__ = [
    "InMemoryProductRepository",
    "InMemoryUserRepository",
]
