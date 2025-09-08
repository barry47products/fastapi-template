# Testing Strategy

**Created**: 8 September 2025  
**Purpose**: Guide developers, DevOps engineers, and QA teams on effective testing practices using pytest markers and behaviour-focused testing.

## Overview

This template uses a comprehensive testing strategy that eliminates test theatre anti-patterns while providing targeted test execution for different development scenarios. Tests are categorised using pytest markers to enable role-specific test execution.

## Test Categories and Markers

### Primary Test Types

| Marker                     | Purpose                     | Target Audience | Command                 |
| -------------------------- | --------------------------- | --------------- | ----------------------- |
| `@pytest.mark.unit`        | Isolated component tests    | Developers      | `make test-unit`        |
| `@pytest.mark.integration` | Component interaction tests | DevOps/SRE      | `make test-integration` |
| `@pytest.mark.contract`    | API/Interface validation    | QA Engineers    | `pytest -m contract`    |
| `@pytest.mark.e2e`         | End-to-end system tests     | QA/Full-stack   | `pytest -m e2e`         |

### Test Speed Categories

| Marker              | Purpose                  | Execution Time | Usage                 |
| ------------------- | ------------------------ | -------------- | --------------------- |
| `@pytest.mark.fast` | Quick feedback tests     | < 100ms        | TDD development cycle |
| `@pytest.mark.slow` | Resource-intensive tests | > 1s           | CI/CD only            |

### Test Purpose Categories

| Marker                    | Purpose                   | Focus Area       | Example             |
| ------------------------- | ------------------------- | ---------------- | ------------------- |
| `@pytest.mark.behaviour`  | Business logic validation | Domain rules     | User age validation |
| `@pytest.mark.resilience` | Error handling            | Edge cases       | Network timeouts    |
| `@pytest.mark.security`   | Security validation       | Auth/permissions | API key validation  |
| `@pytest.mark.smoke`      | Basic functionality       | Critical paths   | Application startup |

### Infrastructure Categories

| Marker                    | Purpose               | Dependencies    | Usage            |
| ------------------------- | --------------------- | --------------- | ---------------- |
| `@pytest.mark.database`   | Database interactions | DB connection   | Repository tests |
| `@pytest.mark.network`    | External API calls    | Internet access | Webhook tests    |
| `@pytest.mark.filesystem` | File operations       | Disk access     | Config loading   |

## Test Execution Matrix

### Developer Workflow

```bash
# TDD cycle - fast feedback
make test-fast              # Quick unit tests during development

# Feature completion
make test-behaviour         # Verify business logic
make test-unit             # Full unit test suite

# Before commit
make test-security         # Security validation
```

### CI/CD Pipeline

```bash
# Stage 1: Fast validation
pytest -m "fast and unit"

# Stage 2: Integration testing
pytest -m "integration and not slow"

# Stage 3: Full validation
pytest -m "not e2e"        # Everything except end-to-end

# Stage 4: End-to-end (optional)
pytest -m "e2e"           # Full system tests
```

### Role-Specific Testing

#### Developers (Feature Development)

- **Primary**: `@pytest.mark.unit` + `@pytest.mark.behaviour`
- **Secondary**: `@pytest.mark.fast` for TDD
- **Focus**: Domain logic, business rules, component isolation

#### DevOps/SRE (Infrastructure)

- **Primary**: `@pytest.mark.integration` + `@pytest.mark.resilience`
- **Secondary**: `@pytest.mark.database` + `@pytest.mark.network`
- **Focus**: Component interactions, error handling, infrastructure

#### QA Engineers (Quality Assurance)

- **Primary**: `@pytest.mark.contract` + `@pytest.mark.e2e`
- **Secondary**: `@pytest.mark.security` + `@pytest.mark.smoke`
- **Focus**: API contracts, full system validation, security

## Good vs Bad Test Examples

### ✅ Good: Behaviour-Focused Testing

```python
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.behaviour
class TestUserAgeValidation:
    """Test user age validation business rules."""

    def test_valid_ages_are_accepted(self) -> None:
        """Should accept ages within valid range."""
        assert validate_user_age(18) is True
        assert validate_user_age(65) is True

    def test_invalid_ages_are_rejected(self) -> None:
        """Should reject ages outside valid range."""
        assert validate_user_age(12) is False
        assert validate_user_age(150) is False
```

**Why it's good**:

- Tests actual behaviour, not implementation
- Clear business rule validation
- No mocking of the method under test
- Focused on domain logic

### ❌ Bad: Mock-Testing-Mock Anti-Pattern

```python
# DON'T DO THIS
def test_logger_info_called(self) -> None:
    """Bad: Tests mock call instead of behaviour."""
    logger = get_logger("test")

    with patch.object(logger, "info") as mock_info:
        logger.info("Test message", key="value")

        # Testing the mock, not the behaviour
        mock_info.assert_called_once_with("Test message", key="value")
```

**Why it's bad**:

- Tests mock interaction, not actual functionality
- Doesn't verify logging actually works
- Brittle - breaks when implementation changes
- Provides false confidence

### ✅ Good: External Dependency Mocking

```python
@pytest.mark.unit
@pytest.mark.fast
class TestWebhookVerification:
    """Test webhook verification with external dependency mocking."""

    @patch("requests.post")  # Mock external HTTP call
    def test_successful_webhook_sends_notification(self, mock_post):
        """Should send notification when webhook verification succeeds."""
        mock_post.return_value.status_code = 200

        result = process_webhook(valid_webhook_data)

        assert result.success is True
        mock_post.assert_called_once()  # Verify external call made
```

**Why it's good**:

- Mocks external dependency (requests), not component under test
- Tests the actual webhook processing behaviour
- Verifies integration with external service
- Focuses on component functionality

### ✅ Good: Integration Testing

```python
@pytest.mark.integration
@pytest.mark.database
class TestUserRepository:
    """Test user repository with real database interactions."""

    def test_user_creation_and_retrieval(self):
        """Should create and retrieve user from database."""
        # Using real database connection (test DB)
        repo = UserRepository()

        user = User(name="Test User", email="test@example.com")
        created_user = repo.create(user)

        retrieved_user = repo.get_by_id(created_user.id)

        assert retrieved_user.name == "Test User"
        assert retrieved_user.email == "test@example.com"
```

**Why it's good**:

- Tests real database interactions
- Validates data persistence and retrieval
- Appropriate use of integration testing
- No mocking of core functionality

## Testing Anti-Patterns to Avoid

### 1. Mock-Testing-Mock

```python
# DON'T DO THIS
def test_method_called_with_correct_args(self):
    with patch.object(service, 'method') as mock_method:
        service.method(arg1, arg2)
        mock_method.assert_called_once_with(arg1, arg2)  # Testing mock!
```

### 2. Over-Mocking

```python
# DON'T DO THIS - Too many mocks
@patch('module.dependency_1')
@patch('module.dependency_2')
@patch('module.dependency_3')
@patch('module.dependency_4')
def test_business_logic(self, mock1, mock2, mock3, mock4):
    # If you need this many mocks, reconsider your design
```

### 3. Implementation Testing

```python
# DON'T DO THIS - Testing implementation details
def test_uses_specific_algorithm(self):
    assert "quicksort" in str(sort_function.__code__)  # Implementation detail!
```

### 4. Magic Number Testing

```python
# DON'T DO THIS - Unclear business meaning
def test_user_validation(self):
    assert validate_user(42, "xyz", 99.5) is True  # What do these numbers mean?
```

## Test Organisation Guidelines

### Directory Structure

```bash
tests/
├── unit/                  # @pytest.mark.unit tests
│   ├── domain/           # Business logic tests
│   ├── application/      # Use case tests
│   └── infrastructure/   # Component tests
├── integration/          # @pytest.mark.integration tests
│   └── infrastructure/   # Component interaction tests
└── contracts/            # @pytest.mark.contract tests
    └── api/              # API interface tests
```

### Test Class Naming

```python
# Good: Domain-focused naming
@pytest.mark.unit
@pytest.mark.behaviour
class TestUserAgeValidation:
    """Test user age validation business rules."""

# Good: Component-focused naming
@pytest.mark.unit
@pytest.mark.fast
class TestMetricsCollector:
    """Test metrics collection functionality."""

# Avoid: Coverage-focused naming
class TestUserServiceAllMethods:  # DON'T DO THIS
```

### Test Method Naming

```python
# Good: Behaviour description
def test_should_reject_users_under_minimum_age(self):
def test_returns_error_when_database_unavailable(self):
def test_increments_counter_with_correct_labels(self):

# Avoid: Implementation description
def test_calls_validate_method(self):      # DON'T DO THIS
def test_mock_returns_true(self):          # DON'T DO THIS
```

## Running Tests

### Development Commands

```bash
# Fast TDD cycle
make test-fast              # Quick unit tests

# Feature validation
make test-behaviour         # Business logic tests
make test-unit             # Full unit suite
make test-integration      # Component interactions

# Pre-commit validation
make test-security         # Security tests
make quality              # Full quality gate
```

### CI/CD Integration

```bash
# Parallel execution
pytest -m "unit and fast" --numprocesses=4
pytest -m "integration" --numprocesses=2
pytest -m "contract" --numprocesses=1
```

### Coverage Requirements

- **Unit tests**: 100% line and branch coverage
- **Integration tests**: Focus on critical paths
- **Contract tests**: All API endpoints and responses

## Conclusion

This testing strategy emphasises behaviour verification over implementation testing, uses clear categorisation for role-specific execution, and eliminates test theatre anti-patterns. The marker system enables targeted testing while maintaining comprehensive coverage across all system components.

**Key Principles**:

1. Test behaviour, not implementation
2. Mock external dependencies, not components under test
3. Use markers for targeted execution
4. Focus on business value and domain rules
5. Maintain clear separation between test types
