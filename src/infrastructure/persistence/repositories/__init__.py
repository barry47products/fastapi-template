"""Multi-database repository implementations."""

from __future__ import annotations

from .base import (
    BaseRepository,
    CacheableRepository,
    ConnectionPoolMixin,
    Repository,
    RetryMixin,
    TransactionalRepository,
)
from .sample_product_repository import InMemoryProductRepository
from .sample_user_repository import InMemoryUserRepository

# Database-specific implementations (imported conditionally)
try:
    from .firestore import FirestoreRepository
except ImportError:
    FirestoreRepository = None  # type: ignore[misc,assignment]

try:
    from .postgresql import PostgreSQLRepository
except ImportError:
    PostgreSQLRepository = None  # type: ignore[misc,assignment]

try:
    from .redis_cache import RedisCacheRepository
except ImportError:
    RedisCacheRepository = None  # type: ignore[misc,assignment]

__all__ = [
    "BaseRepository",
    "CacheableRepository",
    "ConnectionPoolMixin",
    "FirestoreRepository",
    "InMemoryProductRepository",
    "InMemoryUserRepository",
    "PostgreSQLRepository",
    "RedisCacheRepository",
    "Repository",
    "RetryMixin",
    "TransactionalRepository",
]
