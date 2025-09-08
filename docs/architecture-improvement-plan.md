# Architecture Improvement Plan

**Created**: 9 September 2025  
**Objective**: Transform the FastAPI template from an architecture showcase into a production-ready, pragmatic starting point for teams.

## Executive Summary

This plan addresses the architectural evaluation findings, focusing on simplification, pragmatism, and production readiness. The improvements are organised into four phases, each building upon the previous to ensure a smooth transition without breaking existing functionality.

## Phase 1: Simplification & Pattern Reduction (Week 1)

### 1.1 Replace Service Registry with FastAPI Dependency Injection

**Problem**: 160+ lines of boilerplate for managing 8 services  
**Solution**: Use FastAPI's native dependency injection system

**Implementation Steps**:

```python
# Instead of ServiceRegistry pattern:
# OLD: registry.get_metrics_collector()
# NEW: FastAPI dependencies

# src/infrastructure/dependencies.py
from functools import lru_cache
from typing import Annotated
from fastapi import Depends

@lru_cache
def get_metrics_collector() -> MetricsCollector:
    """Singleton metrics collector via FastAPI DI."""
    return MetricsCollector()

@lru_cache
def get_health_checker() -> HealthChecker:
    """Singleton health checker via FastAPI DI."""
    return HealthChecker(timeout=30)

# Usage in routes:
async def endpoint(
    metrics: Annotated[MetricsCollector, Depends(get_metrics_collector)]
):
    metrics.increment_counter("endpoint_calls")
```

**Tasks**:

1. Create `src/infrastructure/dependencies.py` with all service providers
2. Remove `ServiceRegistry` class entirely
3. Update all service access to use `Depends()` pattern
4. Remove dual singleton/registry pattern from health checker
5. Update tests to use dependency overrides

### 1.2 Simplify Repository Factory

**Problem**: Tightly coupled to specific repository types  
**Solution**: Generic repository provider with type registration

**Implementation**:

```python
# src/infrastructure/persistence/repository_provider.py
from typing import Protocol, Type, TypeVar

T = TypeVar('T', bound=Repository)

class RepositoryProvider:
    """Simple, extensible repository provider."""

    def __init__(self, database_url: str, db_type: DatabaseType):
        self.database_url = database_url
        self.db_type = db_type
        self._repositories: dict[Type, Repository] = {}

    def get[T](self, repository_type: Type[T]) -> T:
        """Get or create repository instance."""
        if repository_type not in self._repositories:
            self._repositories[repository_type] = self._create_repository(repository_type)
        return self._repositories[repository_type]

    def _create_repository(self, repo_type: Type[Repository]) -> Repository:
        """Factory method for creating repositories based on db_type."""
        # Implementation based on feature flags
```

### 1.3 Reduce Pattern Complexity

**Actions**:

1. Remove unnecessary factory patterns where simple functions suffice
2. Consolidate event handling into a single subscriber pattern
3. Replace abstract base classes with Protocols where appropriate
4. Remove `ObservabilityEventPublisher` complexity - use simple event handlers

## Phase 2: Testing Improvements (Week 1-2)

### 2.1 Fix Test Theatre (Mock Testing)

**Problem**: Tests that test the mocks rather than behaviour  
**Solution**: Focus on integration tests with real implementations

**Implementation**:

```python
# Mark test categories for different audiences
import pytest

@pytest.mark.unit
@pytest.mark.domain
class TestUserBusinessRules:
    """Domain logic tests - for developers."""

@pytest.mark.integration
@pytest.mark.infrastructure
class TestPersistenceLayer:
    """Infrastructure tests - for DevOps/SRE."""

@pytest.mark.e2e
@pytest.mark.api
class TestAPIEndpoints:
    """End-to-end tests - for QA/Full-stack engineers."""
```

**Tasks**:

1. Audit all tests for mock-testing-mock scenarios
2. Replace with actual behaviour tests
3. Add pytest markers for categorisation:
   - `@pytest.mark.unit` - Pure logic tests
   - `@pytest.mark.integration` - Component interaction tests
   - `@pytest.mark.infrastructure` - External service tests
   - `@pytest.mark.performance` - Performance benchmarks
   - `@pytest.mark.security` - Security validation
4. Update test running commands in Makefile

### 2.2 Improve Test Documentation

**Actions**:

1. Add test strategy document explaining the markers
2. Create test matrix showing what each role should care about
3. Add examples of good vs bad tests

## Phase 3: Infrastructure Enhancements (Week 2)

### 3.1 Multi-Database Support with Feature Flags

**Implementation**:

```python
# src/infrastructure/persistence/database_config.py
from enum import Enum
from pydantic import BaseModel

class DatabaseType(str, Enum):
    FIRESTORE = "firestore"
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    IN_MEMORY = "in_memory"  # For testing

class DatabaseConfig(BaseModel):
    primary_db: DatabaseType = DatabaseType.IN_MEMORY
    cache_db: DatabaseType | None = None
    feature_flags: dict[str, bool] = {
        "enable_firestore": False,
        "enable_postgresql": False,
        "enable_redis_cache": False,
    }

# Repository implementations
class FirestoreRepository:
    """Google Firestore implementation."""

class PostgreSQLRepository:
    """PostgreSQL implementation with SQLAlchemy."""

class RedisCache:
    """Redis caching layer."""

class InMemoryRepository:
    """In-memory implementation for testing."""
```

**Tasks**:

1. Create database configuration with feature flags
2. Implement basic repository for each database type
3. Add database selection logic based on configuration
4. Create migration utilities for each database type
5. Add connection pooling and retry logic

### 3.2 Improve Observability Naming

**Problem**: Generic metric and health check names  
**Solution**: Semantic naming that provides context in external tools

**Implementation**:

```python
# Better metric naming
metrics.increment_counter(
    "api_request_total",
    labels={
        "method": "POST",
        "endpoint": "/users",
        "status": "success",
        "service": "user_service"
    }
)

# Better health check naming
health_checker.register_check(
    "database_postgresql_primary",
    check_postgresql_connection
)
health_checker.register_check(
    "cache_redis_availability",
    check_redis_connection
)
health_checker.register_check(
    "external_api_greenapi_whatsapp",
    check_whatsapp_api
)
```

## Phase 4: Documentation & Deployment (Week 2-3)

### 4.1 Simplify Ruff Configuration

**Current**: 200+ lines of rules  
**Target**: 50 lines focusing on critical checks

```toml
[tool.ruff.lint]
select = [
    "F",     # Pyflakes (critical errors)
    "E",     # Pycodestyle errors
    "I",     # Import sorting
    "N",     # Naming conventions
    "UP",    # Python version upgrades
    "S",     # Security
    "B",     # Bugbear (common bugs)
    "SIM",   # Simplification
    "RUF",   # Ruff-specific
]
ignore = [
    "E501",  # Line length (let formatter handle)
    "S101",  # Assert usage (needed for tests)
]
```

### 4.2 Enhanced API Documentation

**Implementation**:

```python
# src/interfaces/api/documentation.py
def create_api_documentation(app: FastAPI):
    """Enhanced API documentation with examples."""

    app.openapi_tags = [
        {"name": "users", "description": "User management operations"},
        {"name": "health", "description": "System health monitoring"},
    ]

    # Add request/response examples
    # Add authentication documentation
    # Add error response schemas
    # Add rate limiting information
```

**Documentation Deliverables**:

1. `docs/api/` - Detailed API guides with curl examples
2. `docs/architecture/` - Architecture decisions and patterns
3. `docs/deployment/` - Production deployment guides
4. `docs/development/` - Developer onboarding (not CLAUDE.md)

### 4.3 Deployment Infrastructure

**Deliverables**:

1. **Dockerfile** - Multi-stage build with security scanning
2. **docker-compose.yml** - Full local development environment
3. \*\*kubernetes/` - Basic manifests and Helm chart
4. **.github/workflows/** - CI/CD pipelines
5. **scripts/** - Deployment and maintenance scripts

## Phase 5: Open Source Preparation (Week 3)

### 5.1 Repository Setup

**Tasks**:

1. Create comprehensive README.md with:
   - Clear value proposition
   - Quick start guide
   - Architecture overview
   - Contributing guidelines
2. Add LICENSE file (MIT suggested)
3. Create CONTRIBUTING.md with:
   - Code style guide
   - PR process
   - Testing requirements
4. Add CODE_OF_CONDUCT.md
5. Create issue templates
6. Set up GitHub Actions for:
   - Automated testing
   - Code quality checks
   - Security scanning
   - Dependency updates

### 5.2 Documentation Polish

**Tasks**:

1. Remove all references to "Neighbour Approved" specific business
2. Genericise examples to be broadly applicable
3. Create getting started video/tutorial
4. Add architecture diagrams
5. Create FAQ section

### 5.3 Example Implementations

**Create Three Example Domains**:

1. **E-commerce** - Product catalog, orders, inventory
2. **Blog Platform** - Posts, comments, users
3. **Task Management** - Projects, tasks, teams

Each demonstrating the patterns without constraining users.

## Implementation Priority Matrix

| Priority | Phase                 | Effort | Impact   | Dependencies |
| -------- | --------------------- | ------ | -------- | ------------ |
| **P0**   | 1.1 FastAPI DI        | High   | High     | None         |
| **P0**   | 2.1 Fix Test Theatre  | Medium | High     | None         |
| **P0**   | 4.3 Deployment        | High   | Critical | None         |
| **P1**   | 3.1 Multi-DB Support  | High   | Medium   | 1.1          |
| **P1**   | 1.3 Pattern Reduction | Medium | Medium   | 1.1          |
| **P1**   | 4.1 Simplify Ruff     | Low    | Medium   | None         |
| **P2**   | 3.2 Better Naming     | Low    | Low      | None         |
| **P2**   | 4.2 API Docs          | Medium | Medium   | None         |
| **P2**   | 5.1-5.3 Open Source   | Medium | High     | All above    |

## Success Metrics

1. **Code Complexity**: Reduce total LOC by 30%
2. **Setup Time**: New developer productive in < 30 minutes
3. **Test Clarity**: 100% of tests clearly indicate what they validate
4. **Deployment**: One-command deployment to any environment
5. **Documentation**: All patterns explained with examples

## Migration Strategy

### Week 1

- Implement FastAPI DI (breaking change - major version bump)
- Fix test theatre issues
- Start Dockerfile creation

### Week 2

- Complete infrastructure improvements
- Implement multi-database support
- Simplify configurations

### Week 3

- Polish documentation
- Prepare for open source
- Create example implementations
- Final testing and validation

## Risk Mitigation

1. **Breaking Changes**: Version bump to 1.0.0, maintain 0.x branch
2. **Performance**: Benchmark before/after each phase
3. **Compatibility**: Test with Python 3.11+ (not just 3.13)
4. **Migration Path**: Provide automated migration scripts

## Conclusion

This plan transforms the template from an architectural demonstration into a practical, production-ready foundation. The focus shifts from pattern purity to developer productivity whilst maintaining the excellent testing and domain separation already achieved.

The end result will be a template that:

- Can be deployed immediately
- Is understood quickly
- Scales with the team's needs
- Maintains architectural integrity without complexity

**Next Step**: Begin Phase 1.1 - Replace Service Registry with FastAPI DI
