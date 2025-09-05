# Neighbour Approved: Deployment, Feature Flags & Module System

## Python Module System & `__init__.py` Patterns

### Understanding `__init__.py`

The `__init__.py` file serves three critical purposes:

1. **Marks a directory as a Python package** (can be imported)
2. **Controls what's exposed** when someone imports the package
3. **Provides a clean public API** hiding internal implementation

### Module Structure Example

```python
# ❌ WITHOUT proper __init__.py (Bad)
# To use phone_number, you'd need:
from src.domain.value_objects.phone_number import PhoneNumber, validate_phone, normalise_phone

# ✅ WITH proper __init__.py (Good)
# You can simply:
from src.domain.value_objects import PhoneNumber, validate_phone
```

### Layered `__init__.py` Pattern

```python
# src/__init__.py
"""
Root package for Neighbour Approved.
This exposes only the version for package metadata.
"""
__version__ = "0.1.0"

# We don't expose anything else at root level to force explicit imports


# src/domain/__init__.py
"""
Domain layer containing business logic and models.
This re-exports commonly used domain objects for convenience.
"""
from src.domain.models import Provider, Endorsement, Group, Message
from src.domain.value_objects import PhoneNumber, GroupId, ProviderId

# This allows: from src.domain import Provider, PhoneNumber
__all__ = [
    "Provider",
    "Endorsement",
    "Group",
    "Message",
    "PhoneNumber",
    "GroupId",
    "ProviderId",
]


# src/domain/models/__init__.py
"""
Domain models package.
Exports all Pydantic models for the domain.
"""
from src.domain.models.provider import Provider
from src.domain.models.endorsement import Endorsement
from src.domain.models.group import Group
from src.domain.models.message import Message

__all__ = ["Provider", "Endorsement", "Group", "Message"]


# src/domain/value_objects/__init__.py
"""
Value objects for domain-driven design.
These are immutable objects that represent domain concepts.
"""
from src.domain.value_objects.phone_number import PhoneNumber, PhoneNumberStr
from src.domain.value_objects.group_id import GroupId
from src.domain.value_objects.provider_id import ProviderId

# By listing in __all__, we make it explicit what's public
__all__ = [
    "PhoneNumber",
    "PhoneNumberStr",
    "GroupId",
    "ProviderId",
]


# src/infrastructure/__init__.py
"""
Infrastructure layer.
We DON'T re-export here because infrastructure should be injected, not imported directly.
"""
# Empty on purpose - force explicit imports of infrastructure components


# src/infrastructure/observability/__init__.py
"""
Observability components.
These are singleton instances that should be imported and used throughout the app.
"""
from src.infrastructure.observability.structured_logger import get_logger
from src.infrastructure.observability.metrics_collector import metrics
from src.infrastructure.observability.tracer import tracer

# These are singletons, so we export the instances
logger = get_logger()

__all__ = ["logger", "metrics", "tracer"]


# src/shared/__init__.py
"""
Shared utilities and types.
These are cross-cutting concerns used throughout the application.
"""
from src.shared.exceptions import (
    NeighbourApprovedException,
    ValidationException,
    NotFoundException,
    RateLimitException,
)
from src.shared.types import JsonDict, ISODateTime

__all__ = [
    "NeighbourApprovedException",
    "ValidationException",
    "NotFoundException",
    "RateLimitException",
    "JsonDict",
    "ISODateTime",
]
```

### Import Best Practices

```python
# ✅ GOOD: Import from package level
from src.domain import Provider, PhoneNumber
from src.infrastructure.observability import logger, metrics

# ❌ BAD: Deep imports that expose internals
from src.domain.models.provider import Provider
from src.infrastructure.observability.structured_logger import StructuredLogger

# ✅ GOOD: Explicit infrastructure imports when needed
from src.infrastructure.persistence.repositories import ProviderRepository

# ❌ BAD: Wildcard imports
from src.domain import *
```

---

## Core Components Build Order - Flow-Based

### WIP Limit 1 - Build Sequentially

**No timelines, no deadlines. Complete each component fully before moving to the next.**

### Component Flow (Build in THIS Order)

```bash
1. Configuration Management (settings.py)
   ↓ DONE →
2. Exception Hierarchy (exceptions.py)
   ↓ DONE →
3. Logging System (logger.py)
   ↓ DONE →
4. Metrics Collection (metrics.py)
   ↓ DONE →
5. Feature Flags (feature_flags.py)
   ↓ DONE →
6. Security Layer (api_key_validator.py)
   ↓ DONE →
7. First Value Object (phone_number.py)
   ↓ DONE →
8. First Domain Model (provider.py)
   ↓ DONE →
[Continue one at a time...]
```

### Module Development Flow

For EACH module (WIP = 1):

```python
# Step 1: Create test file
tests/unit/domain/value_objects/test_phone_number.py

# Step 2: Write comprehensive tests (RED)
# Step 3: Create implementation file
src/domain/value_objects/phone_number.py

# Step 4: Implement until tests pass (GREEN)
# Step 5: Update __init__.py to expose
src/domain/value_objects/__init__.py

# Step 6: Run all checks
poetry run pytest tests/ --cov=src --cov-fail-under=100
poetry run black src tests
poetry run ruff src tests
poetry run mypy src

# Step 7: Commit
git add .
git commit -m "feat: implement PhoneNumber value object"

# Module COMPLETE - Move to next
```

---

## Feature Flags Strategy

### Configuration File

```json
// feature_flags.json (for local development)
{
  "enable_nlp_processing": {
    "enabled": false,
    "description": "Use NLP for message classification"
  },
  "enable_automatic_endorsements": {
    "enabled": true,
    "percentage": 50,
    "description": "Automatically create endorsements from mentions"
  },
  "enable_emoji_reactions": {
    "enabled": true,
    "description": "Allow emoji reactions for contact details"
  },
  "enable_keyword_bidding": {
    "enabled": false,
    "description": "Allow providers to bid on keywords"
  },
  "new_summary_format": {
    "enabled": true,
    "percentage": 10,
    "description": "A/B test new summary message format"
  }
}
```

### Using Feature Flags in Code

```python
# src/application/commands/process_message.py
from src.infrastructure.feature_flags import feature_flags
from src.infrastructure.observability import logger, metrics

class ProcessMessageCommand:
    async def execute(self, message: Message) -> ProcessMessageResult:
        # Feature flag for NLP processing
        if await feature_flags.is_enabled(
            "enable_nlp_processing",
            {"group_id": message.group_id}
        ):
            mentions = await self._nlp_extractor.extract(message)
            logger.info("Used NLP extraction", mentions_count=len(mentions))
            metrics.nlp_usage.inc()
        else:
            mentions = self._regex_extractor.extract(message)
            logger.info("Used regex extraction", mentions_count=len(mentions))

        # Feature flag for automatic endorsements
        if await feature_flags.is_enabled(
            "enable_automatic_endorsements",
            {"group_id": message.group_id}
        ):
            await self._create_automatic_endorsements(mentions)

        return ProcessMessageResult(mentions=mentions)
```

---

## Deployment Architecture

### Container Strategy (For Later Testing)

```dockerfile
# Dockerfile - FOR FUTURE USE (not needed initially)
FROM python:3.13-slim as base

# Security: Don't run as root
RUN useradd -m -u 1000 appuser

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry==1.7.1

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Multi-stage build for smaller final image
FROM python:3.13-slim

RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy installed packages from base
COPY --from=base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser config ./config

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health/live')"

# Run with gunicorn for production
CMD ["gunicorn", "src.interfaces.api.app:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

### Local Development Setup (MacBook Pro)

```bash
# 1. Install Python 3.13 using homebrew
brew install python@3.13

# 2. Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# 3. Configure poetry to use Python 3.13
poetry env use python3.13

# 4. Install VSCode
brew install --cask visual-studio-code

# 5. Install Claude Code
# Download from Anthropic website

# 6. Install Docker Desktop (for later)
brew install --cask docker

# 7. VSCode settings.json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "[python]": {
        "editor.rulers": [88]
    }
}
```

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: gcr.io
  IMAGE_NAME: neighbour-approved
  GCP_PROJECT: ${{ secrets.GCP_PROJECT }}

jobs:
  test:
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

      - name: Run tests with coverage
        run: |
          poetry run pytest tests/ \
            --cov=src \
            --cov-report=xml \
            --cov-report=term \
            --cov-fail-under=100

      - name: Run linting
        run: |
          poetry run black --check src tests
          poetry run ruff src tests
          poetry run mypy src

      - name: Run security checks
        run: |
          poetry run bandit -r src/
          poetry run safety check

      - name: SonarQube analysis
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        run: |
          sonar-scanner \
            -Dsonar.projectKey=neighbour-approved \
            -Dsonar.python.coverage.reportPaths=coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Configure Docker for GCR
        run: gcloud auth configure-docker

      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.GCP_PROJECT }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ env.GCP_PROJECT }}/${{ env.IMAGE_NAME }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ${{ env.REGISTRY }}/${{ env.GCP_PROJECT }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          format: cyclonedx-json

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - uses: actions/checkout@v3

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Deploy to Cloud Run (Staging)
        run: |
          gcloud run deploy neighbour-approved-staging \
            --image ${{ env.REGISTRY }}/${{ env.GCP_PROJECT }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            --platform managed \
            --region europe-west2 \
            --allow-unauthenticated \
            --set-env-vars="ENVIRONMENT=staging" \
            --set-secrets="GREEN_API_TOKEN=green-api-token:latest" \
            --min-instances=1 \
            --max-instances=10 \
            --memory=512Mi \
            --cpu=1

      - name: Run smoke tests
        run: |
          STAGING_URL=$(gcloud run services describe neighbour-approved-staging \
            --platform managed \
            --region europe-west2 \
            --format 'value(status.url)')

          poetry run pytest tests/smoke/ --base-url=$STAGING_URL

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Blue-Green Deployment
        run: |
          # Deploy to green environment
          gcloud run deploy neighbour-approved-green \
            --image ${{ env.REGISTRY }}/${{ env.GCP_PROJECT }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            --platform managed \
            --region europe-west2 \
            --no-traffic \
            --set-env-vars="ENVIRONMENT=production" \
            --set-secrets="GREEN_API_TOKEN=green-api-token:latest" \
            --min-instances=2 \
            --max-instances=100 \
            --memory=1Gi \
            --cpu=2

          # Run health checks
          GREEN_URL=$(gcloud run services describe neighbour-approved-green \
            --platform managed \
            --region europe-west2 \
            --format 'value(status.url)')

          curl -f $GREEN_URL/health/ready || exit 1

          # Gradual traffic shift
          gcloud run services update-traffic neighbour-approved \
            --to-tags=green=10 \
            --platform managed \
            --region europe-west2

          # Monitor for 5 minutes
          sleep 300

          # Check error rate (this would check actual metrics)
          # If good, continue rollout

          gcloud run services update-traffic neighbour-approved \
            --to-tags=green=50 \
            --platform managed \
            --region europe-west2

          sleep 300

          # Full cutover
          gcloud run services update-traffic neighbour-approved \
            --to-latest \
            --platform managed \
            --region europe-west2

      - name: Notify deployment
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: "Production deployment ${{ job.status }}"
        if: always()
```

### Infrastructure as Code

```terraform
# terraform/main.tf
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "neighbour-approved-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud Run Service
resource "google_cloud_run_service" "app" {
  name     = "neighbour-approved"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/neighbour-approved:latest"

        resources {
          limits = {
            cpu    = "2"
            memory = "1Gi"
          }
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name = "GREEN_API_TOKEN"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.green_api_token.secret_id
              key  = "latest"
            }
          }
        }
      }

      service_account_name = google_service_account.app.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "2"
        "autoscaling.knative.dev/maxScale" = "100"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Cloud SQL PostgreSQL Database
resource "google_sql_database_instance" "postgres" {
  project          = var.project_id
  name             = "neighbour-approved-postgres"
  database_version = "POSTGRES_15"
  region           = var.region
  
  settings {
    tier                        = "db-f1-micro"
    availability_type           = "REGIONAL"
    disk_size                  = 20
    disk_type                  = "PD_SSD"
    disk_autoresize           = true
    disk_autoresize_limit     = 100
    backup_configuration {
      enabled                             = true
      start_time                         = "03:00"
      location                           = var.region
      point_in_time_recovery_enabled     = true
      transaction_log_retention_days     = 7
    }
    ip_configuration {
      ipv4_enabled    = true
      private_network = google_compute_network.vpc.self_link
      require_ssl     = true
    }
  }
  
  deletion_protection = true
}

resource "google_sql_database" "database" {
  project  = var.project_id
  name     = "neighbour_approved"
  instance = google_sql_database_instance.postgres.name
}

# Monitoring Dashboard
resource "google_monitoring_dashboard" "main" {
  dashboard_json = jsonencode({
    displayName = "Neighbour Approved Operations"
    dashboardFilters = []
    gridLayout = {
      widgets = [
        {
          title = "Request Rate"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                prometheusQuery = "rate(requests_total[5m])"
              }
            }]
          }
        }
      ]
    }
  })
}
```

---

## Application Bootstrap

```python
# src/main.py
"""
Application entry point that initialises all core components.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from config.settings import Settings
from src.infrastructure.observability import configure_logging, metrics
from src.infrastructure.feature_flags import feature_flags
from src.infrastructure.persistence import init_postgres
from src.interfaces.api import create_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = Settings()

    # Initialise core components (ORDER MATTERS!)
    configure_logging(settings)
    feature_flags.initialise(settings)
    await init_postgres(settings)

    logger = get_logger(__name__)
    logger.info(
        "Application started",
        environment=settings.environment,
        version=__version__
    )

    yield

    # Shutdown
    logger.info("Application shutting down")
    await cleanup_resources()

def create_application() -> FastAPI:
    """Factory function to create the FastAPI application."""
    return create_app(lifespan=lifespan)

# For Gunicorn
app = create_application()

if __name__ == "__main__":
    # For local development
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # Use our structured logging
    )
```

---

## Development Workflow with Feature Flags

### Flow-Based Feature Development (WIP = 1)

```python
# 1. Add feature flag to configuration (while working on module)
{
  "enable_smart_categorisation": {
    "enabled": false,
    "description": "Use ML for service categorisation"
  }
}

# 2. Write test for feature flag check
def test_categorisation_uses_flag():
    # Test that flag controls behaviour
    pass

# 3. Implement feature behind flag
async def categorise_service(message: str) -> ServiceCategory:
    if await feature_flags.is_enabled("enable_smart_categorisation"):
        return await ml_categoriser.categorise(message)
    else:
        return regex_categoriser.categorise(message)

# 4. Complete module with flag disabled
# 5. Commit completed module
# 6. Later: Enable flag in test environment
# 7. Later: Gradually roll out to production
# 8. Eventually: Remove flag once stable
```

### Module Completion Criteria

A module is ONLY complete when:

1. ✅ Tests written and passing (100% coverage)
2. ✅ Type annotations complete
3. ✅ All linting checks pass
4. ✅ Feature flag controls behaviour (if applicable)
5. ✅ Module exposed in `__init__.py`
6. ✅ Documentation/docstrings added
7. ✅ Code committed to git

#### **Then and only then: Pick next module from backlog**

---

## Module Import Cheat Sheet

```python
# ✅ CORRECT PATTERNS

# Import from package level when exposed
from src.domain import Provider
from src.shared import ValidationException

# Import from specific module when needed
from src.infrastructure.persistence.repositories import ProviderRepository

# Import singleton instances
from src.infrastructure.observability import logger, metrics

# ❌ INCORRECT PATTERNS

# Don't bypass package API
from src.domain.models.provider import Provider  # Use src.domain instead

# Don't use wildcards
from src.domain import *

# Don't import implementation details
from src.infrastructure.observability.structured_logger import StructuredLogger

# 📁 WHEN TO USE __init__.py EXPORTS

# YES: Domain models (frequently used together)
from src.domain import Provider, Endorsement, Group

# YES: Exceptions (need consistent handling)
from src.shared import ValidationException, NotFoundException

# YES: Singleton instances
from src.infrastructure.observability import logger, metrics

# NO: Infrastructure implementations (should be injected)
# NO: Internal utilities (keep them private)
# NO: Test fixtures (only for tests)
```

## Remember: Flow-Based Development

1. **One Module at a Time** - WIP = 1
2. **Test First** - Red, Green, Refactor
3. **Complete Before Moving** - No parallel work
4. **Clean Commits** - One module per commit
5. **No Skipping Ahead** - Follow the backlog order

This architecture ensures:

1. **Clean deployments** through future CI/CD
2. **Safe feature rollouts** with feature flags from day one
3. **Proper module organisation** with clear public APIs
4. **Core components** built in the right order
5. **Clear import patterns** that prevent coupling
6. **Flow-based development** with WIP limit of 1
