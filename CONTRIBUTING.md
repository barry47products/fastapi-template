# Contributing to FastAPI Template

Thank you for your interest in contributing to FastAPI Template! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Development Workflow](#development-workflow)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Poetry for dependency management
- Git for version control
- Basic understanding of FastAPI, async Python, and clean architecture

### Development Setup

1. **Fork and clone the repository**:

   ```bash
   git clone https://github.com/your-username/fastapi-template.git
   cd fastapi-template
   ```

2. **Install dependencies**:

   ```bash
   poetry install
   poetry shell
   ```

3. **Set up pre-commit hooks**:

   ```bash
   pre-commit install
   ```

4. **Run tests to verify setup**:

   ```bash
   make test
   ```

## Code Style

This project uses strict code quality standards:

### Formatting and Linting

- **Ruff**: Used for both linting and formatting
- **MyPy**: Strict type checking required
- **Line length**: Maximum 100 characters
- **Import sorting**: Handled by Ruff

### Code Standards

- **100% test coverage**: No exceptions - all new code must be covered
- **Full type annotations**: Use Python 3.11+ syntax, no `Any` types unless absolutely necessary
- **No comments**: Code should be self-documenting
- **Immutable models**: Use Pydantic with `frozen=True`
- **Specific exceptions**: Never raise generic `Exception`
- **Pure functions**: Where possible, avoid side effects
- **British English**: Use British spelling in all user-facing content

### Architecture Principles

- **Clean Architecture**: Maintain clear separation between layers
- **Domain-driven design**: Keep business logic in the domain layer
- **Dependency injection**: Use FastAPI's DI system
- **Single responsibility**: Each class/function should have one reason to change

## Testing Requirements

### Test Categories

Tests are organised by purpose and execution speed:

```bash
# Run specific test categories
make test-unit          # Domain and business logic
make test-integration   # Infrastructure components
make test-behaviour     # End-to-end scenarios
make test-security      # Security validations
make test-fast          # Quick feedback for TDD
```

### Test Standards

- **100% coverage**: Both line and branch coverage required
- **Behaviour-focused**: Test what the code does, not how it does it
- **Domain-focused classes**: Organise tests around business concepts
- **Clear test names**: Should describe the expected behaviour
- **Minimal mocking**: Mock external dependencies only

### Test Structure

```python
class TestUserRegistrationWorkflow:
    """Tests for user registration business rules."""

    def test_creates_pending_account_for_new_user(self) -> None:
        """Should create pending account when user registers with valid details."""
        # Given
        registration_data = UserRegistrationRequest(...)

        # When
        result = register_user(registration_data)

        # Then
        assert result.status == UserStatus.PENDING
```

## Pull Request Process

### Before Submitting

1. **Create a feature branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Run quality checks**:

   ```bash
   make quality  # Runs lint, typecheck, and all tests
   ```

3. **Update documentation** if needed

4. **Add tests** for any new functionality

### PR Requirements

- **Descriptive title**: Clearly describe what the PR does
- **Detailed description**: Explain the motivation and approach
- **Link issues**: Reference any related issues
- **Small scope**: Keep PRs focused and reviewable
- **All checks pass**: CI must be green

### PR Template

```markdown
## Description

Brief description of changes and motivation.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Refactoring

## Testing

- [ ] Added tests for new functionality
- [ ] All existing tests pass
- [ ] Test coverage remains at 100%

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or justified)
```

## Issue Guidelines

### Bug Reports

Include:

- **Environment**: Python version, OS, relevant package versions
- **Steps to reproduce**: Clear, minimal reproduction steps
- **Expected behaviour**: What should happen
- **Actual behaviour**: What actually happens
- **Error messages**: Full stack traces if applicable

### Feature Requests

Include:

- **Problem**: What problem does this solve?
- **Solution**: Describe the desired solution
- **Alternatives**: What alternatives have you considered?
- **Additional context**: Any other relevant information

### Good First Issues

Look for issues labelled `good-first-issue` if you're new to the project.

## Development Workflow

### TDD Approach

This project follows Test-Driven Development:

1. **Red**: Write a failing test
2. **Green**: Write minimal code to make it pass
3. **Refactor**: Improve the code while keeping tests green

### Quality Gates

All changes must pass:

- **Formatting**: `make format`
- **Linting**: `make lint`
- **Type checking**: `make typecheck`
- **Tests**: `make test`
- **Coverage**: Must maintain 100%

### Commit Messages

Follow conventional commit format:

```bash
feat: add user registration endpoint

Implements user registration with email verification.
Includes validation, rate limiting, and audit logging.
```

### Branch Protection

The `main` branch is protected and requires:

- Pull request reviews
- Status checks to pass
- Up-to-date branches

## Environment Configuration

Create `.env` file for local development:

```bash
# Copy example configuration
cp .env.example .env

# Edit with your local settings
vim .env
```

Never commit `.env` files or secrets to the repository.

## Getting Help

- **Documentation**: Check the `docs/` directory
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Code Review**: Don't hesitate to ask questions during review

## Release Process

Releases are managed by maintainers:

1. Version bumping follows semantic versioning
2. Releases are tagged and include changelog
3. Breaking changes require major version bump
4. Deprecations include migration guides

## Recognition

Contributors are recognised in:

- README.md contributors section
- Release notes for significant contributions
- GitHub's contribution graph

---

Thank you for contributing to FastAPI Template! Your efforts help make this template better for the entire Python community.
