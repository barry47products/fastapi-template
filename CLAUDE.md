# FastAPI Template - Claude Code Configuration

## Project Overview

Clean architecture FastAPI template with comprehensive testing, observability, and multiple database support. Uses Python/FastAPI with clean architecture and flow-based development (WIP = 1).

## Tech Stack

- **Python 3.13** + **FastAPI** + **Poetry** + **VSCode** + **Claude Code**
- **Database**: Google Firestore (NoSQL)
- **WhatsApp**: GREEN-API integration
- **Platform**: MacBook Pro (Apple Silicon)

## Architecture

```bash
src/
├── domain/              # Pure business logic (frozen Pydantic models)
├── application/         # Commands & queries
├── infrastructure/      # External integrations (WhatsApp, DB, security, observability)
├── interfaces/api/      # FastAPI routes
└── shared/             # Utilities & exceptions
```

**Principles**: Functional core + imperative shell, immutability, full typing, single responsibility, explicit dependencies, environment configuration.

## Development Workflow

**WIP = 1**: Work on ONE roadmap item at a time. Complete 100% before moving to next.

**TDD Cycle**: RED (failing test) → GREEN (minimal code) → REFACTOR (clean up) → Infrastructure integration (config, logging, metrics, health)

**Completion**: Update roadmap → commit → move to next item

## Key Commands

```bash
# Setup
poetry install && poetry shell

# Development
make run                # uvicorn src.main:app --reload --port 8000
make test               # pytest with 100% coverage requirement
make test-fast          # TDD fast tests (no slow markers)
make watch              # TDD watch mode with ptw

# Code Quality (Modern Ruff + MyPy)
make format             # ruff format + ruff check --fix (auto-fix)
make lint               # ruff format --check + ruff check (no fixes)
make typecheck          # mypy strict type checking

# Combined Workflows
make quality            # lint + typecheck + test (full quality check)
make quick              # format + test-fast (rapid development)
make pr                 # format + quality (prepare for PR)
make fix                # ruff --unsafe-fixes (aggressive auto-fix)
```

## Code Standards

- **100% test coverage** (line + branch) - no exceptions
- **Full type annotations** - Python 3.13 syntax, strict typing
- **No comments** - self-documenting code
- **Immutable models** - Pydantic with `frozen=True`
- **Specific exceptions** - never generic `Exception`
- **Pure functions** where possible
- **Environment config** - zero hardcoded values
- **Always use British English in output.**
- **Formatting** - No Blank lines with whitespace.
- **Formatting** - No lines longer than 100 characters.
- **Formatting** - 1 empty line at the end of modules.
- **Formatting** - No trailing whitespace.

## Infrastructure Integration (MANDATORY)

Every new module must integrate with foundation:

```python
from src.infrastructure.observability import get_logger, get_metrics_collector
from src.shared.exceptions import DomainSpecificError

logger = get_logger(__name__)
metrics = get_metrics_collector()

def business_function(input_value: str) -> Result:
    if not input_value:
        logger.warning("Validation failed", input=input_value)
        metrics.increment_counter("validation_errors_total")
        raise DomainSpecificError("Input required")

    logger.info("Processing completed", length=len(input_value))
    metrics.increment_counter("processing_total")
    return Result(value=input_value)
```

**Import Rules**: Use module-level imports only

- ✅ `from src.domain.models import Provider`
- ❌ `from src.domain.models.provider import Provider`

## Testing Strategy

- **Unit tests**: `tests/unit/` - mirror src structure, mock external dependencies
- **Integration tests**: `tests/integration/` - test real component interactions
- **TDD approach**: Write failing test first, then minimal implementation
- **Placement**: `src/domain/models/provider.py` → `tests/unit/domain/test_models/test_provider.py`
- **Test Focus**: Test classes should be domain focused. Do not use coverage focussed test classes.

## Environment Variables

Create `.env` for local development (never commit):

```env
APP_NAME=fastapi-template
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000
METRICS_ENABLED=true
METRICS_PORT=9090
LOG_LEVEL=INFO
INTERNAL_API_KEYS=your_api_key
WEBHOOK_SECRET=your_secret
```

## Git Workflow

**Format**:

```bash
type: one-line summary under 72 characters

Optional body explaining WHY (not what - diff shows that).
Focus on business context and reasoning.
```

**Good Examples**:

```bash
feat: add mention extractor for WhatsApp messages

Extracts provider references using patterns and phone numbers.
Part of automated endorsement capture pipeline.
```

**Avoid**:

- ❌ 50+ bullet points listing files
- ❌ Test counts ("Added 17 tests")
- ❌ Coverage metrics ("99.93% coverage")
- ❌ Implementation details
- ❌ Status tracking ("✅ COMPLETE")

**Focus On**:

- ✅ Business value and context
- ✅ Why the change was made
- ✅ Future developer understanding

## Common Linting Fixes

1. **Float comparisons**: Use `abs(result - 0.8) < 0.001` instead of `result == 0.8`
2. **Exception types**: Use specific exceptions, not generic `Exception`
3. **Type annotations**: Add explicit types to fix Pylint no-member issues
4. **Line length**: Break long lines or use intermediate variables (100 char limit)
5. **Never disable linting** - fix the underlying issue

## Quality Requirements

- **Black** 100 chars) + **Ruff** + **MyPy** - all must pass
- **100% coverage** - both line and branch
- **Strict typing** - no `Any` unless absolutely required
- **TDD approach** - tests before implementation
- **Infrastructure integration** - logging, metrics, health, exceptions
