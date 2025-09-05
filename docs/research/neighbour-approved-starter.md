# Neighbour Approved: Project Starter Template

## Development Environment Setup (MacBook Pro)

```bash
# 1. Install Python 3.13
brew install python@3.13

# 2. Install Poetry (latest)
curl -sSL https://install.python-poetry.org | python3 -

# 3. Install VSCode
brew install --cask visual-studio-code

# 4. Create project
mkdir neighbour-approved && cd neighbour-approved

# 5. Initialise poetry with Python 3.13
poetry init --name neighbour-approved --python "^3.13"
poetry env use python3.13

# 6. Create directory structure
mkdir -p src/{domain,application,infrastructure,interfaces,shared}
mkdir -p src/domain/{models,rules,value_objects}
mkdir -p src/infrastructure/{observability,persistence,security,feature_flags}
mkdir -p src/interfaces/{api,events}
mkdir -p tests/{unit,integration,e2e}
mkdir -p .vscode
mkdir config

# 7. Initialise git
git init
```

## Essential First Files

### 1. `pyproject.toml` (Latest Package Versions)

```toml
[tool.poetry]
name = "neighbour-approved"
version = "0.1.0"
description = "WhatsApp-based local service endorsement platform"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include = "src"}]

[tool.poetry.dependencies]
python = "^3.13"
fastapi = "^0.115.0"
uvicorn = "^0.32.0"
pydantic = "^2.10.0"
pydantic-settings = "^2.6.0"
structlog = "^24.4.0"
prometheus-client = "^0.21.0"
httpx = "^0.28.0"
green-api = "^2.0.0"  # Check latest version
asyncpg = "^0.29.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
pytest-cov = "^6.0.0"
black = "^24.10.0"
ruff = "^0.8.0"
mypy = "^1.13.0"
pre-commit = "^4.0.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 88
target-version = ['py313']

[tool.ruff]
line-length = 88
target-version = "py313"
select = ["E", "F", "W", "C90", "I", "N", "UP", "S", "B", "A", "COM", "C4"]

[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
fail_under = 100
show_missing = true
```

### 2. `.vscode/settings.json`

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": [
    "tests",
    "-v",
    "--cov=src",
    "--cov-report=term-missing"
  ],
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": "explicit",
    "source.fixAll": "explicit"
  },
  "[python]": {
    "editor.rulers": [88],
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".pytest_cache": true,
    ".coverage": true,
    ".mypy_cache": true,
    ".ruff_cache": true
  },
  "terminal.integrated.env.osx": {
    "PYTHONDONTWRITEBYTECODE": "1"
  }
}
```

### 3. `.vscode/extensions.json`

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "tamasfe.even-better-toml",
    "streetsidesoftware.code-spell-checker",
    "eamodio.gitlens",
    "usernamehw.errorlens",
    "ms-vscode.makefile-tools"
  ]
}
```

### 4. `.vscode/launch.json`

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.main:app", "--reload", "--port", "8000"],
      "jinja": true,
      "env": {
        "ENVIRONMENT": "development",
        "DEBUG": "true"
      }
    },
    {
      "name": "Python: Current File",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Test Current File",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"]
    }
  ]
}
```

### 2. `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.10.0
    hooks:
      - id: black
        language_version: python3.13

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
        args: [--strict]
```

### 3. `config/settings.py`

```python
"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from enum import Enum


class Environment(str, Enum):
    """Application environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    No hardcoded values - everything comes from environment or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = Field(default="neighbour-approved")
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    version: str = Field(default="0.1.0")

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_key_header: str = Field(default="X-API-Key")

    # Observability
    log_level: str = Field(default="INFO")
    metrics_enabled: bool = Field(default=True)
    metrics_port: int = Field(default=9090)

    # Feature Flags
    feature_flags_enabled: bool = Field(default=True)
    feature_flags_file: str = Field(default="feature_flags.json")


# Singleton instance
settings = Settings()
```

### 4. `src/__init__.py`

```python
"""Neighbour Approved - WhatsApp-based service endorsement platform."""

__version__ = "0.1.0"

# We don't export anything at the root level
# This forces explicit imports and prevents accidental coupling
```

### 5. `src/shared/__init__.py`

```python
"""Shared utilities and types used across the application."""
from src.shared.exceptions import (
    NeighbourApprovedException,
    ValidationException,
    NotFoundException,
)
from src.shared.types import JsonDict

__all__ = [
    "NeighbourApprovedException",
    "ValidationException",
    "NotFoundException",
    "JsonDict",
]
```

### 6. `src/shared/exceptions.py`

```python
"""Custom exception hierarchy for the application."""
from typing import Optional, Dict, Any


class NeighbourApprovedException(Exception):
    """
    Base exception for all application exceptions.

    All exceptions should inherit from this to enable consistent handling.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ValidationException(NeighbourApprovedException):
    """Raised when input validation fails."""

    pass


class NotFoundException(NeighbourApprovedException):
    """Raised when a requested resource cannot be found."""

    pass
```

### 7. `src/shared/types.py`

```python
"""Common type definitions used throughout the application."""
from typing import Dict, Any, TypeAlias

# Type aliases for clarity
JsonDict: TypeAlias = Dict[str, Any]
ISODateTime: TypeAlias = str  # ISO 8601 formatted datetime string
```

### 8. `src/infrastructure/observability/__init__.py`

```python
"""Observability components - logging, metrics, tracing."""
from src.infrastructure.observability.logger import get_logger, configure_logging
from src.infrastructure.observability.metrics import Metrics

# Singleton instances
logger = get_logger(__name__)
metrics = Metrics()

__all__ = ["logger", "metrics", "configure_logging"]
```

### 9. `src/infrastructure/observability/logger.py`

```python
"""Structured logging configuration."""
import structlog
from typing import Optional
from config.settings import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.environment == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name or __name__)
```

### 10. `src/infrastructure/observability/metrics.py`

```python
"""Metrics collection using Prometheus."""
from prometheus_client import Counter, Histogram, Gauge
from typing import Optional
from functools import wraps
import time
import asyncio


class Metrics:
    """Singleton metrics collector."""

    def __init__(self) -> None:
        # Business metrics
        self.messages_processed = Counter(
            "messages_processed_total",
            "Total messages processed",
            ["message_type", "status"],
        )

        # Performance metrics
        self.request_duration = Histogram(
            "request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
        )

    def track_time(self, operation: str):
        """Decorator to track execution time."""
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    start = time.time()
                    try:
                        return await func(*args, **kwargs)
                    finally:
                        duration = time.time() - start
                        self.request_duration.labels(
                            method=operation,
                            endpoint=func.__name__,
                        ).observe(duration)
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    start = time.time()
                    try:
                        return func(*args, **kwargs)
                    finally:
                        duration = time.time() - start
                        self.request_duration.labels(
                            method=operation,
                            endpoint=func.__name__,
                        ).observe(duration)
                return sync_wrapper
        return decorator
```

### 11. `src/infrastructure/feature_flags/__init__.py`

```python
"""Feature flag management."""
from src.infrastructure.feature_flags.manager import FeatureFlags

# Singleton instance
feature_flags = FeatureFlags()

__all__ = ["feature_flags"]
```

### 12. `src/infrastructure/feature_flags/manager.py`

```python
"""Feature flag manager implementation."""
import json
from typing import Dict, Any, Optional
from pathlib import Path
from config.settings import settings


class FeatureFlags:
    """Simple local feature flag manager."""

    def __init__(self) -> None:
        self._flags: Dict[str, Any] = {}
        self._load_flags()

    def _load_flags(self) -> None:
        """Load feature flags from JSON file."""
        if not settings.feature_flags_enabled:
            return

        flags_file = Path(settings.feature_flags_file)
        if flags_file.exists():
            with open(flags_file) as f:
                self._flags = json.load(f)

    async def is_enabled(
        self,
        flag_key: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if a feature flag is enabled."""
        if not settings.feature_flags_enabled:
            return False

        flag = self._flags.get(flag_key, {})
        return flag.get("enabled", False)
```

### 13. `feature_flags.json`

```json
{
  "enable_whatsapp_integration": {
    "enabled": false,
    "description": "Enable live WhatsApp integration"
  },
  "enable_automatic_endorsements": {
    "enabled": false,
    "description": "Create endorsements from second mentions"
  }
}
```

### 14. `tests/conftest.py`

```python
"""Pytest configuration and fixtures."""
import pytest
from typing import AsyncGenerator
from fastapi.testclient import TestClient

from src.interfaces.api.app import create_app


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator:
    """Create an async test client."""
    from httpx import AsyncClient

    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### 15. `tests/unit/test_example.py`

```python
"""Example test file demonstrating TDD approach."""
import pytest
from src.shared.exceptions import ValidationException


class TestExample:
    """Example test class."""

    def test_always_passes(self) -> None:
        """Sanity check that tests are running."""
        assert True

    def test_exception_includes_error_code(self) -> None:
        """Test that our custom exceptions include error codes."""
        exc = ValidationException("Invalid input")
        assert exc.error_code == "ValidationException"
        assert exc.message == "Invalid input"
```

### 16. `.env.example`

```env
# Application
ENVIRONMENT=development
DEBUG=true

# API
API_HOST=0.0.0.0
API_PORT=8000

# Observability
LOG_LEVEL=INFO
METRICS_ENABLED=true

# Feature Flags
FEATURE_FLAGS_ENABLED=true
FEATURE_FLAGS_FILE=feature_flags.json
```

### 17. `Makefile`

```makefile
.PHONY: help install test lint format run clean module-start module-test module-done

help: ## Show this help message
    @grep -E '^[a-zA-Z_-]+:.*?## .*$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $1, $2}'

install: ## Install dependencies
    poetry install

test: ## Run tests with coverage
    poetry run pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=100

test-watch: ## Run tests in watch mode
    poetry run pytest-watch tests/ -- -v

lint: ## Run linting
    poetry run black --check src tests
    poetry run ruff check src tests
    poetry run mypy src

format: ## Format code
    poetry run black src tests
    poetry run ruff check --fix src tests

run: ## Run the application locally
    poetry run uvicorn src.main:app --reload --port 8000

clean: ## Clean up generated files
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    rm -rf .coverage .pytest_cache .mypy_cache .ruff_cache

# Flow-based development commands
module-start: ## Start working on a new module (WIP=1)
    @echo "📝 Starting new module. Remember: WIP limit = 1"
    @echo "1. Write failing test first (RED)"
    @echo "2. Implement minimal code (GREEN)"
    @echo "3. Refactor if needed"
    @echo "4. Run 'make module-test' to verify"

module-test: ## Test current module thoroughly
    @echo "🧪 Testing current module..."
    poetry run pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=100
    poetry run black --check src tests
    poetry run ruff check src tests
    poetry run mypy src
    @echo "✅ All checks passed!"

module-done: ## Complete current module and prepare for next
    @echo "✅ Module complete! Running final checks..."
    make module-test
    @echo "📦 Ready to commit. Next: git add . && git commit -m 'feat: ...'"
    @echo "Then pick next module from backlog (WIP=1)"
```

## Flow-Based Development Workflow

### Working on ONE Module at a Time (WIP = 1)

```bash
# STEP 1: Start new module
make module-start

# STEP 2: Create test file (RED phase)
touch tests/unit/domain/value_objects/test_phone_number.py

# STEP 3: Write comprehensive tests
# Edit test file in VSCode with Claude Code assistance

# STEP 4: Run tests - should FAIL
make test
# ❌ RED - Good! Tests fail as expected

# STEP 5: Create implementation
touch src/domain/value_objects/phone_number.py

# STEP 6: Implement minimal code to pass tests
# Edit implementation in VSCode

# STEP 7: Run tests - should PASS
make test
# ✅ GREEN - Tests pass!

# STEP 8: Update __init__.py to expose module
# Edit src/domain/value_objects/__init__.py

# STEP 9: Verify everything
make module-test

# STEP 10: Complete module
make module-done

# STEP 11: Commit
git add .
git commit -m "feat: implement PhoneNumber value object"

# STEP 12: Pick NEXT module (only one!)
# Repeat from STEP 1
```

### Module Development Checklist

```markdown
## Current Module: [Module Name]

### Pre-Implementation

- [ ] Module purpose clearly defined
- [ ] Test file created
- [ ] Comprehensive tests written
- [ ] Tests fail as expected (RED)

### Implementation

- [ ] Minimal code to pass tests
- [ ] Tests pass (GREEN)
- [ ] Type annotations complete
- [ ] No hardcoded values
- [ ] Specific exceptions only

### Quality Checks

- [ ] 100% test coverage
- [ ] Black formatting passes
- [ ] Ruff linting passes
- [ ] MyPy type checking passes
- [ ] Module exposed in **init**.py

### Documentation

- [ ] Docstrings added where needed
- [ ] Complex logic explained
- [ ] Public API clear

### Complete

- [ ] All checks pass
- [ ] Code committed
- [ ] Ready for next module

**Remember: WIP = 1. Do not start next module until this is DONE.**
```

## Module Build Order (Complete Sequentially)

1. **Settings Configuration** (`config/settings.py`)
2. **Base Exception** (`src/shared/exceptions.py`)
3. **Logger Setup** (`src/infrastructure/observability/logger.py`)
4. **Metrics Collection** (`src/infrastructure/observability/metrics.py`)
5. **Feature Flags** (`src/infrastructure/feature_flags/manager.py`)
6. **Phone Number Value Object** (`src/domain/value_objects/phone_number.py`)
7. **Group ID Value Object** (`src/domain/value_objects/group_id.py`)
8. **Provider ID Value Object** (`src/domain/value_objects/provider_id.py`)
9. **Provider Model** (`src/domain/models/provider.py`)
10. **Endorsement Model** (`src/domain/models/endorsement.py`)
11. Continue one at a time...

## VSCode Shortcuts for Flow-Based Development

```json
// Add to keybindings.json
{
    "key": "cmd+shift+t",
    "command": "python.runtests",
    "when": "editorTextFocus && editorLangId == python"
},
{
    "key": "cmd+shift+f",
    "command": "editor.action.formatDocument",
    "when": "editorTextFocus && editorLangId == python"
},
{
    "key": "cmd+shift+l",
    "command": "ruff.executeAutofix",
    "when": "editorTextFocus && editorLangId == python"
}
```

## Claude Code Integration Tips

1. **Test First**: Ask Claude Code to write comprehensive tests before implementation
2. **Single Purpose**: Each request should be for ONE module only
3. **Type Safety**: Always request full type annotations
4. **No Comments**: Request self-documenting code
5. **Functional Style**: Request immutable, functional implementations

Example prompt for Claude Code:

```text
Write comprehensive pytest tests for a PhoneNumber value object that:
- Validates phone number format
- Normalises to E.164 format
- Is immutable (frozen Pydantic model)
- Raises ValidationException for invalid inputs
- Has 100% test coverage
No implementation yet, just tests.
```
