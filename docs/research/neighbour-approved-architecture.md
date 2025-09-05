# Neighbour Approved: Software Architecture

## Core Architecture Principles

Following your rules strictly, this architecture emphasises:

- **Immutability**: Data flows through pure functions
- **Single Responsibility**: Each module does ONE thing
- **Testability**: Every function is independently testable
- **Configuration**: Zero hardcoded values
- **Type Safety**: Full type annotations with Pydantic models

---

## Security Architecture

### API Authentication

```python
# src/infrastructure/security/api_key_validator.py
from typing import Optional, Set
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from src.infrastructure.observability.metrics_collector import metrics
from config.settings import Settings

class ApiKeyValidator:
    def __init__(self, settings: Settings):
        self._valid_keys: Set[str] = set(
            settings.internal_api_keys.get_secret_value().split(',')
        )
        self._header = APIKeyHeader(name=settings.api_key_header_name)

    async def validate(self, api_key: str = Security(APIKeyHeader)) -> str:
        metrics.increment("api.auth.attempts")

        if api_key not in self._valid_keys:
            metrics.increment("api.auth.failures")
            raise HTTPException(
                status_code=403,
                detail="Invalid API key"
            )

        metrics.increment("api.auth.successes")
        return api_key
```

### Webhook Verification

```python
# src/infrastructure/security/webhook_verifier.py
import hmac
import hashlib
from typing import Dict, Any
from src.shared.exceptions import WebhookVerificationException

class WebhookVerifier:
    def __init__(self, secret: str):
        self._secret = secret.encode()

    def verify_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        expected = hmac.new(
            self._secret,
            payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            raise WebhookVerificationException(
                "Invalid webhook signature"
            )

        return True
```

### Rate Limiting

```python
# src/infrastructure/security/rate_limiter.py
from typing import Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from src.shared.exceptions import RateLimitExceededException

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self._max_requests = max_requests
        self._window = timedelta(seconds=window_seconds)
        self._requests: Dict[str, list[datetime]] = defaultdict(list)

    def check_limit(self, identifier: str) -> Tuple[bool, int]:
        now = datetime.utcnow()
        cutoff = now - self._window

        # Clean old requests
        self._requests[identifier] = [
            req_time for req_time in self._requests[identifier]
            if req_time > cutoff
        ]

        current_count = len(self._requests[identifier])

        if current_count >= self._max_requests:
            raise RateLimitExceededException(
                f"Rate limit exceeded: {current_count}/{self._max_requests}"
            )

        self._requests[identifier].append(now)
        return True, self._max_requests - current_count - 1
```

### Data Encryption

```python
# src/infrastructure/security/encryption_service.py
from cryptography.fernet import Fernet
from typing import Optional

class EncryptionService:
    """Encrypts sensitive data at rest."""

    def __init__(self, key: str):
        self._fernet = Fernet(key.encode())

    def encrypt_phone_number(self, phone: str) -> str:
        return self._fernet.encrypt(phone.encode()).decode()

    def decrypt_phone_number(self, encrypted: str) -> str:
        return self._fernet.decrypt(encrypted.encode()).decode()
```

---

## Observability & Monitoring

### Metrics Collection

```python
# src/infrastructure/observability/metrics_collector.py
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from typing import Dict, Any
import time
from functools import wraps

class MetricsCollector:
    def __init__(self):
        self.registry = CollectorRegistry()

        # Business metrics
        self.messages_processed = Counter(
            'messages_processed_total',
            'Total messages processed',
            ['message_type', 'group_id'],
            registry=self.registry
        )

        self.endorsements_created = Counter(
            'endorsements_created_total',
            'Total endorsements created',
            ['provider_category'],
            registry=self.registry
        )

        self.summaries_sent = Counter(
            'summaries_sent_total',
            'Total summaries sent to groups',
            ['group_id'],
            registry=self.registry
        )

        # Performance metrics
        self.processing_duration = Histogram(
            'message_processing_duration_seconds',
            'Time spent processing messages',
            ['operation'],
            registry=self.registry
        )

        self.api_request_duration = Histogram(
            'api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )

        # System metrics
        self.active_groups = Gauge(
            'active_groups',
            'Number of active WhatsApp groups',
            registry=self.registry
        )

        self.providers_total = Gauge(
            'providers_total',
            'Total number of providers',
            ['status'],
            registry=self.registry
        )

    def track_processing(self, operation: str):
        """Decorator to track processing duration."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                with self.processing_duration.labels(operation).time():
                    return await func(*args, **kwargs)
            return wrapper
        return decorator

metrics = MetricsCollector()
```

### Structured Logging

```python
# src/infrastructure/observability/structured_logger.py
import structlog
from typing import Dict, Any
from contextvars import ContextVar

# Context variables for request tracing
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')

def configure_logging(log_level: str, environment: str) -> structlog.BoundLogger:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            ),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer() if environment == "production"
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()

class LoggerAdapter:
    def __init__(self, logger: structlog.BoundLogger):
        self._logger = logger

    def log_message_received(self, message: Dict[str, Any]) -> None:
        self._logger.info(
            "message_received",
            message_id=message.get('id'),
            group_id=message.get('group_id'),
            message_type=message.get('type')
        )

    def log_endorsement_created(
        self,
        provider_id: str,
        endorser_id: str,
        group_id: str
    ) -> None:
        self._logger.info(
            "endorsement_created",
            provider_id=provider_id,
            endorser_id=endorser_id,
            group_id=group_id
        )

    def log_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        self._logger.error(
            "error_occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            **context
        )
```

### Distributed Tracing

```python
# src/infrastructure/observability/tracer.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from contextlib import contextmanager
from typing import Dict, Any

def configure_tracing(service_name: str, endpoint: str) -> trace.Tracer:
    provider = TracerProvider()
    processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint=endpoint)
    )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    return trace.get_tracer(service_name)

class Tracer:
    def __init__(self, tracer: trace.Tracer):
        self._tracer = tracer

    @contextmanager
    def span(self, name: str, attributes: Dict[str, Any] = None):
        with self._tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span
```

### Health Checks

```python
# src/infrastructure/observability/health_checker.py
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass(frozen=True)
class ComponentHealth:
    name: str
    status: HealthStatus
    message: str
    metadata: Dict[str, Any]

class HealthChecker:
    def __init__(self):
        self._checks: List[callable] = []

    def register_check(self, check: callable) -> None:
        self._checks.append(check)

    async def check_health(self) -> Dict[str, Any]:
        results = []
        overall_status = HealthStatus.HEALTHY

        for check in self._checks:
            result = await check()
            results.append(result)

            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status,
            "components": [
                {
                    "name": r.name,
                    "status": r.status,
                    "message": r.message,
                    "metadata": r.metadata
                }
                for r in results
            ]
        }

# Example health check
async def check_postgres_health() -> ComponentHealth:
    try:
        # Attempt database connection with simple query
        # SELECT 1
        return ComponentHealth(
            name="postgresql",
            status=HealthStatus.HEALTHY,
            message="PostgreSQL is responsive",
            metadata={"response_time_ms": 5}
        )
    except Exception as e:
        return ComponentHealth(
            name="postgresql",
            status=HealthStatus.UNHEALTHY,
            message=f"PostgreSQL connection failed: {str(e)}",
            metadata={}
        )
```

---

## Code Quality Enforcement

### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
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
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-all]
        args: [--strict, --ignore-missing-imports]

  - repo: https://github.com/pycqa/isort
    rev: 5.13.0
    hooks:
      - id: isort
        args: [--profile, black]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.0
    hooks:
      - id: bandit
        args: [-r, src/]
        exclude: ^tests/

  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: poetry run pytest tests/unit -v --cov=src --cov-report=term-missing --cov-fail-under=100
        language: system
        pass_filenames: false
        always_run: true
```

### Pyproject.toml Configuration

```toml
# pyproject.toml
[tool.poetry]
name = "neighbour-approved"
version = "0.1.0"
description = "WhatsApp-based local service endorsement platform"

[tool.poetry.dependencies]
python = "^3.13"
fastapi = "^0.115.0"
pydantic = "^2.10.0"
pydantic-settings = "^2.6.0"
green-api = "^2.0.0"
asyncpg = "^0.29.0"
structlog = "^24.4.0"
prometheus-client = "^0.21.0"
opentelemetry-api = "^1.29.0"
opentelemetry-sdk = "^1.29.0"
opentelemetry-instrumentation-fastapi = "^0.50b0"
cryptography = "^44.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
pytest-cov = "^6.0.0"
black = "^24.10.0"
ruff = "^0.8.0"
mypy = "^1.13.0"
isort = "^5.13.0"
bandit = "^1.8.0"
pre-commit = "^4.0.0"

[tool.ruff]
line-length = 88
target-version = "py313"
select = ["E", "F", "W", "C90", "I", "N", "UP", "S", "B", "A", "COM", "C4", "DTZ", "T10", "EM", "EXE", "ISC", "ICN", "G", "INP", "PIE", "PYI", "PT", "Q", "RET", "SLF", "SIM", "TID", "TCH", "ARG", "PTH", "ERA", "PD", "PGH", "PL", "TRY", "NPY", "RUF"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_unimported = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
check_untyped_defs = true

[tool.coverage.run]
branch = true
source = ["src"]

[tool.coverage.report]
fail_under = 100
show_missing = true
skip_covered = false
```

### Code Quality Configuration

```bash
# quality-check.sh - Local code quality checks
#!/bin/bash

echo "🔍 Running code quality checks..."

# Format checking
echo "📝 Checking code formatting..."
poetry run black --check src tests

# Linting
echo "🔧 Running linter..."
poetry run ruff check src tests

# Type checking
echo "🔍 Type checking..."
poetry run mypy src --strict

# Complexity check
echo "📊 Checking complexity..."
poetry run ruff check src tests --select C90

# Security check
echo "🔒 Security scanning..."
poetry run bandit -r src/

# Test coverage
echo "🧪 Running tests with coverage..."
poetry run pytest tests/ --cov=src --cov-fail-under=100

echo "✅ All quality checks passed!"
```

### VSCode Tasks Configuration

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Tests",
      "type": "shell",
      "command": "poetry run pytest tests/ -v",
      "group": {
        "kind": "test",
        "isDefault": true
      },
      "problemMatcher": []
    },
    {
      "label": "Format Code",
      "type": "shell",
      "command": "poetry run black src tests",
      "group": "build",
      "problemMatcher": []
    },
    {
      "label": "Lint Code",
      "type": "shell",
      "command": "poetry run ruff check src tests --fix",
      "group": "build",
      "problemMatcher": []
    },
    {
      "label": "Type Check",
      "type": "shell",
      "command": "poetry run mypy src",
      "group": "build",
      "problemMatcher": []
    },
    {
      "label": "Quality Check",
      "type": "shell",
      "command": "./quality-check.sh",
      "group": "build",
      "problemMatcher": []
    }
  ]
}
```

---

## API Security Implementation

```python
# src/interfaces/api/app.py
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from src.infrastructure.security.api_key_validator import ApiKeyValidator
from src.infrastructure.observability.metrics_collector import metrics
from src.infrastructure.observability.structured_logger import request_id_var
import uuid
import time

app = FastAPI(
    title="Neighbour Approved API",
    docs_url=None,  # Disable in production
    redoc_url=None  # Disable in production
)

# Security Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*.neighbour-approved.com", "localhost"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # No CORS in production
    allow_credentials=False,
    allow_methods=["POST"],  # Only POST for webhooks
    allow_headers=["X-API-Key"],
)

class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        metrics.api_request_duration.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).observe(duration)

        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestTracingMiddleware)

# Dependency injection for API key validation
api_key_validator = ApiKeyValidator(settings)

@app.post("/webhook/whatsapp", dependencies=[Depends(api_key_validator.validate)])
async def whatsapp_webhook(request: Request):
    # Webhook processing with full observability
    pass
```

---

## Project Structure

```bash
neighbour-approved/
├── pyproject.toml
├── poetry.lock
├── .env.example
├── .pre-commit-config.yaml         # Linting and code quality
├── sonar-project.properties        # SonarQube configuration
├── docker-compose.yml              # Local development services
├── config/
│   ├── __init__.py
│   └── settings.py                 # Pydantic settings management
│
├── src/
│   ├── __init__.py
│   │
│   ├── domain/                     # Core business logic (pure functions)
│   │   ├── __init__.py
│   │   ├── models/                 # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── provider.py         # Provider data model
│   │   │   ├── endorsement.py      # Endorsement data model
│   │   │   ├── group.py            # WhatsApp group model
│   │   │   ├── message.py          # Message models
│   │   │   └── request.py          # Service request model
│   │   │
│   │   ├── rules/                  # Business rules (pure functions)
│   │   │   ├── __init__.py
│   │   │   ├── endorsement_calculator.py
│   │   │   ├── provider_matcher.py
│   │   │   ├── mention_validator.py
│   │   │   └── summary_composer.py
│   │   │
│   │   └── value_objects/          # Immutable value objects
│   │       ├── __init__.py
│   │       ├── phone_number.py
│   │       ├── group_id.py
│   │       └── provider_name.py
│   │
│   ├── application/                # Application services (orchestration)
│   │   ├── __init__.py
│   │   ├── commands/               # Command handlers
│   │   │   ├── __init__.py
│   │   │   ├── process_message.py
│   │   │   ├── generate_summary.py
│   │   │   ├── handle_reaction.py
│   │   │   └── send_followup.py
│   │   │
│   │   └── queries/                # Query handlers
│   │       ├── __init__.py
│   │       ├── get_endorsed_providers.py
│   │       ├── get_pending_followups.py
│   │       └── get_group_statistics.py
│   │
│   ├── infrastructure/             # External integrations
│   │   ├── __init__.py
│   │   ├── whatsapp/
│   │   │   ├── __init__.py
│   │   │   ├── green_api_client.py
│   │   │   └── message_sender.py
│   │   │
│   │   ├── persistence/
│   │   │   ├── __init__.py
│   │   │   ├── repositories/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── provider_repository.py
│   │   │   │   ├── endorsement_repository.py
│   │   │   │   └── group_repository.py
│   │   │   │
│   │   │   └── postgres/
│   │   │       ├── __init__.py
│   │   │       └── postgres_adapter.py
│   │   │
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── api_key_validator.py
│   │   │   ├── rate_limiter.py
│   │   │   ├── webhook_verifier.py
│   │   │   └── encryption_service.py
│   │   │
│   │   ├── observability/
│   │   │   ├── __init__.py
│   │   │   ├── metrics_collector.py
│   │   │   ├── structured_logger.py
│   │   │   ├── tracer.py
│   │   │   └── health_checker.py
│   │   │
│   │   └── nlp/
│   │       ├── __init__.py
│   │       ├── request_classifier.py
│   │       ├── mention_extractor.py
│   │       └── service_categoriser.py
│   │
│   ├── interfaces/                 # API/External interfaces
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── app.py             # FastAPI app
│   │   │   ├── dependencies.py    # Dependency injection
│   │   │   └── routers/
│   │   │       ├── __init__.py
│   │   │       ├── webhooks.py
│   │   │       ├── providers.py
│   │   │       └── health.py
│   │   │
│   │   └── events/                # Event handlers
│   │       ├── __init__.py
│   │       └── whatsapp_webhook.py
│   │
│   └── shared/                    # Shared utilities
│       ├── __init__.py
│       ├── types.py               # Type definitions
│       ├── exceptions.py          # Custom exceptions
│       └── validators.py          # Shared validators
│
└── tests/
    ├── __init__.py
    ├── conftest.py                # pytest fixtures
    ├── unit/                      # Mirrors src structure
    │   ├── domain/
    │   ├── application/
    │   ├── infrastructure/
    │   └── interfaces/
    ├── integration/               # Integration tests
    └── e2e/                       # End-to-end tests
```

---

## Key Design Patterns

### 1. Functional Core, Imperative Shell

**Functional Core** (Pure Functions):

```python
# src/domain/rules/endorsement_calculator.py
from typing import FrozenSet
from src.domain.models.endorsement import Endorsement
from src.domain.models.provider import Provider

def calculate_endorsement_count(
    provider: Provider,
    endorsements: FrozenSet[Endorsement]
) -> int:
    """Pure function: no side effects, deterministic."""
    return len([e for e in endorsements if e.provider_id == provider.id])
```

**Imperative Shell** (Side Effects):

```python
# src/application/commands/process_message.py
from src.domain.rules.mention_validator import is_valid_mention
from src.infrastructure.persistence.repositories.provider_repository import ProviderRepository

async def process_message_command(
    message: Message,
    provider_repo: ProviderRepository
) -> ProcessMessageResult:
    """Orchestrates pure functions and side effects."""
    if is_valid_mention(message):  # Pure function
        provider = await provider_repo.save(...)  # Side effect
        return ProcessMessageResult(success=True)
```

### 2. Dependency Injection with FastAPI

```python
# src/interfaces/api/dependencies.py
from functools import lru_cache
from src.infrastructure.whatsapp.green_api_client import GreenApiClient
from config.settings import Settings

@lru_cache
def get_settings() -> Settings:
    return Settings()  # Loads from environment

def get_whatsapp_client(settings: Settings = Depends(get_settings)) -> GreenApiClient:
    return GreenApiClient(
        instance_id=settings.green_api_instance_id,
        token=settings.green_api_token
    )
```

### 3. Repository Pattern

```python
# src/infrastructure/persistence/repositories/provider_repository.py
from abc import ABC, abstractmethod
from typing import Optional
from src.domain.models.provider import Provider
from src.domain.value_objects.phone_number import PhoneNumber

class ProviderRepository(ABC):
    @abstractmethod
    async def find_by_phone(self, phone: PhoneNumber) -> Optional[Provider]:
        ...

    @abstractmethod
    async def save(self, provider: Provider) -> Provider:
        ...
```

---

## Module Examples

### Single-Purpose Module: Phone Number Validator

```python
# src/domain/value_objects/phone_number.py
from typing import NewType
from pydantic import BaseModel, validator
import re

PhoneNumberStr = NewType('PhoneNumberStr', str)

class PhoneNumber(BaseModel):
    """Immutable value object for phone numbers."""
    value: str

    class Config:
        frozen = True

    @validator('value')
    def validate_phone(cls, v: str) -> str:
        pattern = r'^\+?[1-9]\d{1,14}$'
        if not re.match(pattern, v):
            raise ValueError(f"Invalid phone number format: {v}")
        return v

    def normalise(self) -> PhoneNumberStr:
        """Returns normalised phone number."""
        digits_only = re.sub(r'\D', '', self.value)
        return PhoneNumberStr(f"+{digits_only}")
```

### Single-Purpose Module: Mention Extractor

```python
# src/infrastructure/nlp/mention_extractor.py
from typing import FrozenSet
from src.domain.models.message import Message
from src.domain.models.provider import ProviderMention

def extract_mentions(message: Message) -> FrozenSet[ProviderMention]:
    """Extracts provider mentions from a message."""
    mentions = set()
    patterns = [
        r"(?:use|used|try|recommend) (\w+ \w+)",
        r"(\w+ \w+) (?:is|are|were) (?:great|good|brilliant)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, message.text, re.IGNORECASE)
        for match in matches:
            mentions.add(ProviderMention(name=match, confidence=0.8))

    return frozenset(mentions)
```

---

## Configuration Management

```python
# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Optional
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    """All configuration via environment variables."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Application
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    service_name: str = Field(default="neighbour-approved")

    # Security
    api_key_header_name: str = Field(default="X-API-Key")
    internal_api_keys: SecretStr = Field(..., description="Comma-separated API keys")
    webhook_secret: SecretStr = Field(..., description="GREEN-API webhook secret")
    encryption_key: SecretStr = Field(..., description="Fernet encryption key")

    # GREEN-API
    green_api_instance_id: str = Field(..., description="GREEN-API instance ID")
    green_api_token: SecretStr = Field(..., description="GREEN-API token")
    green_api_webhook_url: str = Field(..., description="Webhook URL")

    # Database
    database_url: SecretStr = Field(..., description="PostgreSQL connection URL")
    database_pool_size: int = Field(default=10, description="Max database connections")

    # Message Processing
    summary_frequency_hours: int = Field(default=24)
    followup_delay_days: int = Field(default=7)
    endorsement_threshold: int = Field(default=2)

    # Rate Limiting
    max_messages_per_group_per_hour: int = Field(default=5)
    max_emoji_reactions_per_summary: int = Field(default=20)
    max_requests_per_minute: int = Field(default=60)

    # Observability
    metrics_enabled: bool = Field(default=True)
    metrics_port: int = Field(default=9090)
    log_level: str = Field(default="INFO")
    trace_sample_rate: float = Field(default=0.1)
```

---

## Testing Strategy

### TDD Example: Provider Matcher

```python
# tests/unit/domain/rules/test_provider_matcher.py
import pytest
from src.application.services.nlp.provider_matcher import match_providers
from src.domain.models.provider import Provider
from src.domain.value_objects.provider_name import ProviderName

class TestProviderMatcher:
    def test_exact_name_match_returns_same_provider(self):
        # Given
        existing = Provider(name=ProviderName("Davies Electrical"))
        mention = ProviderName("Davies Electrical")

        # When
        result = match_providers(existing, mention)

        # Then
        assert result.is_match is True
        assert result.confidence == 1.0

    def test_similar_name_returns_high_confidence(self):
        # Given
        existing = Provider(name=ProviderName("Davies Electrical"))
        mention = ProviderName("Davies Electric")

        # When
        result = match_providers(existing, mention)

        # Then
        assert result.is_match is True
        assert result.confidence > 0.8

    def test_completely_different_name_returns_no_match(self):
        # Given
        existing = Provider(name=ProviderName("Davies Electrical"))
        mention = ProviderName("Smith Plumbing")

        # When
        result = match_providers(existing, mention)

        # Then
        assert result.is_match is False
```

---

## Exception Handling

```python
# src/shared/exceptions.py
class NeighbourApprovedException(Exception):
    """Base exception for all custom exceptions."""
    pass

class WhatsAppDeliveryException(NeighbourApprovedException):
    """Raised when message delivery fails."""
    pass

class ProviderNotFoundException(NeighbourApprovedException):
    """Raised when provider cannot be found."""
    pass

class RateLimitExceededException(NeighbourApprovedException):
    """Raised when rate limit is exceeded."""
    pass

class InvalidPhoneNumberException(NeighbourApprovedException):
    """Raised when phone number format is invalid."""
    pass
```

---

## Key Architectural Decisions

### 1. Immutability Everywhere

- All domain models are Pydantic models with `frozen=True`
- Use `FrozenSet` instead of `Set` for collections
- Return new objects instead of mutating existing ones

### 2. Type Safety

- Every function has type annotations
- Use `NewType` for domain-specific types
- Pydantic for runtime validation

### 3. Testability First

- Pure functions for business logic
- Dependency injection for side effects
- Repository pattern for data access

### 4. No Hidden Dependencies

- All dependencies explicit in function signatures
- Configuration via environment variables only
- No global state

### 5. Error Handling

- Specific exceptions for each failure mode
- Let exceptions bubble up to handlers
- Log at boundaries, not in domain logic

---

## Maintainability Practices

### Error Handling with Context

```python
# src/application/commands/process_message.py
from src.infrastructure.observability.structured_logger import LoggerAdapter
from src.infrastructure.observability.metrics_collector import metrics
from src.infrastructure.observability.tracer import Tracer

class ProcessMessageCommand:
    def __init__(
        self,
        logger: LoggerAdapter,
        tracer: Tracer,
        provider_repo: ProviderRepository
    ):
        self._logger = logger
        self._tracer = tracer
        self._provider_repo = provider_repo

    @metrics.track_processing("process_message")
    async def execute(self, message: Message) -> ProcessMessageResult:
        with self._tracer.span(
            "process_message",
            {"message_id": message.id, "group_id": message.group_id}
        ):
            try:
                self._logger.log_message_received(message.dict())

                # Process with full observability
                mentions = extract_mentions(message)

                for mention in mentions:
                    provider = await self._provider_repo.find_or_create(mention)
                    metrics.endorsements_created.labels(
                        provider_category=provider.category
                    ).inc()

                return ProcessMessageResult(success=True)

            except ProviderNotFoundException as e:
                self._logger.log_error(e, {"message_id": message.id})
                metrics.increment("errors.provider_not_found")
                raise
            except Exception as e:
                self._logger.log_error(e, {"message_id": message.id})
                metrics.increment("errors.unexpected")
                raise
```

### Deployment Health Verification

```python
# src/interfaces/api/routers/health.py
from fastapi import APIRouter, Depends
from src.infrastructure.observability.health_checker import HealthChecker

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/live")
async def liveness():
    """Kubernetes liveness probe - is the service running?"""
    return {"status": "alive"}

@router.get("/ready")
async def readiness(health_checker: HealthChecker = Depends()):
    """Kubernetes readiness probe - can the service handle traffic?"""
    result = await health_checker.check_health()

    if result["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=result)

    return result

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")
```

### Graceful Shutdown

```python
# src/interfaces/api/app.py
import signal
import asyncio
from contextlib import asynccontextmanager

shutdown_event = asyncio.Event()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Neighbour Approved API")

    # Register health checks
    health_checker.register_check(check_postgres_health)
    health_checker.register_check(check_whatsapp_health)

    # Start background tasks
    task = asyncio.create_task(process_pending_summaries())

    yield

    # Shutdown
    logger.info("Shutting down Neighbour Approved API")
    shutdown_event.set()
    await task
    await close_postgres_connections()

app = FastAPI(lifespan=lifespan)

def handle_sigterm(signum, frame):
    shutdown_event.set()

signal.signal(signal.SIGTERM, handle_sigterm)
```

---

## Development Workflow - Flow-Based Approach

### Work In Progress (WIP) Limit: 1

**Core Principle**: Complete one module entirely before starting the next. No multitasking, no parallel work.

### Flow for Each Module (TDD)

```mermaid
graph LR
    A[Pick One Module] --> B[Write Failing Test]
    B --> C[Red: Test Fails]
    C --> D[Write Minimal Code]
    D --> E[Green: Test Passes]
    E --> F[Refactor if Needed]
    F --> G[Add Observability]
    G --> H[Integration Test]
    H --> I[Module Complete]
    I --> A
```

1. **Pick ONE module** from backlog
2. **Write failing test** for the behaviour
3. **RED** - Verify test fails
4. **Write minimal code** to pass test
5. **GREEN** - Test passes
6. **Refactor** if needed (tests still pass)
7. **Add observability** (metrics, logging)
8. **Integration test** if external dependency
9. **Module DONE** - Pick next module

### Development Environment

**Local Setup (MacBook Pro)**:

- Python 3.13 (latest)
- VSCode with Python extensions
- Claude Code for AI assistance
- Poetry for dependency management
- Docker Desktop (for later pipeline testing)

**VSCode Extensions Required**:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "tamasfe.even-better-toml",
    "streetsidesoftware.code-spell-checker",
    "eamodio.gitlens"
  ]
}
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: poetry install

      - name: Run linting
        run: |
          poetry run black --check src tests
          poetry run ruff src tests
          poetry run mypy src
          poetry run isort --check-only src tests

      - name: Security scan
        run: poetry run bandit -r src/

      - name: Run tests with coverage
        run: poetry run pytest tests/ -v --cov=src --cov-report=xml --cov-fail-under=100

      - name: SonarQube scan
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        run: sonar-scanner

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

### Module Creation Checklist (WIP = 1)

**Current Module: **********\_\_************

- [ ] Single purpose defined
- [ ] Name describes the purpose
- [ ] Test file created first
- [ ] Tests written (RED phase)
- [ ] Tests fail as expected
- [ ] Implementation started
- [ ] 100% type annotated
- [ ] Pure function (if possible)
- [ ] Pydantic models for data
- [ ] No hardcoded values
- [ ] Specific exceptions only
- [ ] No mutation of inputs
- [ ] Self-documenting code
- [ ] Tests pass (GREEN phase)
- [ ] Refactored if needed
- [ ] 100% test coverage
- [ ] All linting passing
- [ ] Module exported in **init**.py
- [ ] Committed to git

#### **✅ Module COMPLETE - Pick next from backlog**

---

## Production Readiness Checklist

### Security

- [ ] All endpoints require API key authentication
- [ ] Webhook signatures verified
- [ ] Rate limiting implemented
- [ ] Sensitive data encrypted at rest
- [ ] No secrets in code or logs
- [ ] Security headers configured
- [ ] OWASP Top 10 addressed

### Observability

- [ ] Metrics exposed for Prometheus
- [ ] Structured logging to stdout
- [ ] Distributed tracing configured
- [ ] Health checks implemented
- [ ] Error tracking configured
- [ ] Performance monitoring
- [ ] Alerting rules defined

### Code Quality

- [ ] 100% test coverage
- [ ] All linting passing
- [ ] Type checking passing
- [ ] No security vulnerabilities
- [ ] Documentation complete
- [ ] API spec up to date

### Reliability

- [ ] Graceful shutdown handling
- [ ] Circuit breakers for external services
- [ ] Retry logic with backoff
- [ ] Timeout configurations
- [ ] Database connection pooling
- [ ] Memory leak prevention
- [ ] Resource cleanup
