"""Persistence layer infrastructure components."""

from .repositories import InMemoryProductRepository, InMemoryUserRepository
from .repository_provider import (
    configure_repository_provider,
    get_product_repository,
    get_repository_provider,
    get_user_repository,
    RepositoryProvider,
)

__all__ = [
    "InMemoryProductRepository",
    "InMemoryUserRepository",
    "RepositoryProvider",
    "configure_repository_provider",
    "get_product_repository",
    "get_repository_provider",
    "get_user_repository",
]
