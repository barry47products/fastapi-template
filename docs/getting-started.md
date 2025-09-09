# Getting Started Guide

Complete walkthrough to get your FastAPI application running from template to production deployment.

## Prerequisites

- **Python 3.13+** (recommended via [pyenv](https://github.com/pyenv/pyenv))
- **Poetry** for dependency management
- **Docker** (optional, for containerized development)
- **Git** for version control

## Quick Setup (5 minutes)

### 1. Create Your Project

```bash
# Clone the template
git clone https://github.com/your-username/fastapi-template.git your-project-name
cd your-project-name

# Remove template git history and start fresh
rm -rf .git
git init
git add .
git commit -m "Initial commit from FastAPI template"
```

### 2. Install Dependencies

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
poetry shell
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit your environment variables
vim .env  # or your preferred editor
```

**Essential environment variables:**

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_TITLE="Your API Name"

# Security
INTERNAL_API_KEYS=your-secret-api-key-here
WEBHOOK_SECRET=your-webhook-secret

# Database (choose one)
DATABASE_TYPE=postgresql  # postgresql|firestore|redis|in_memory
DATABASE_URL=postgresql://user:password@localhost:5432/your_db

# Development settings
ENVIRONMENT=development
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

### 4. Start Development Server

```bash
# Run with hot reload
make run

# Alternative: direct uvicorn command
poetry run uvicorn src.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` to see your API documentation!

## Your First Endpoint (10 minutes)

### 1. Create a Domain Model

```python
# src/domain/models/product.py
from pydantic import BaseModel

class Product(BaseModel):
    id: str
    name: str
    description: str
    price: float
    category: str

    class Config:
        frozen = True  # Immutable model
```

### 2. Add Application Logic

```python
# src/application/commands/create_product.py
from src.domain.models.product import Product
from src.shared.types import Result

class CreateProductCommand:
    def __init__(self, name: str, description: str, price: float, category: str):
        self.name = name
        self.description = description
        self.price = price
        self.category = category

def handle_create_product(command: CreateProductCommand) -> Result[Product]:
    # Business logic here
    product = Product(
        id=generate_id(),
        name=command.name,
        description=command.description,
        price=command.price,
        category=command.category
    )
    return Result.success(product)
```

### 3. Create API Endpoint

```python
# src/interfaces/api/routers/products.py
from fastapi import APIRouter, HTTPStatus
from src.application.commands.create_product import CreateProductCommand, handle_create_product

router = APIRouter(prefix="/products", tags=["products"])

@router.post("/", status_code=HTTPStatus.CREATED)
async def create_product(command: CreateProductCommand):
    result = handle_create_product(command)

    if result.is_success():
        return result.value
    else:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=result.error
        )
```

### 4. Register Your Router

```python
# src/interfaces/api/main.py
from src.interfaces.api.routers import products

# Add to your app setup
app.include_router(products.router, prefix="/api/v1")
```

## Testing Your API (5 minutes)

### 1. Write a Simple Test

```python
# tests/unit/application/commands/test_create_product.py
import pytest
from src.application.commands.create_product import CreateProductCommand, handle_create_product

def test_create_product_success():
    # Given
    command = CreateProductCommand(
        name="Test Product",
        description="A test product",
        price=19.99,
        category="test"
    )

    # When
    result = handle_create_product(command)

    # Then
    assert result.is_success()
    assert result.value.name == "Test Product"
    assert result.value.price == 19.99
```

### 2. Run Tests

```bash
# Run all tests
make test

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run fast tests only (TDD mode)
make test-fast

# Watch mode for continuous testing
make watch
```

### 3. Check Code Quality

```bash
# Format code
make format

# Check linting
make lint

# Type checking
make typecheck

# All quality checks
make quality
```

## Database Integration (10 minutes)

### 1. Choose Your Database

The template supports multiple databases with feature flags:

```env
# PostgreSQL (Production recommended)
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb

# Firestore (NoSQL option)
DATABASE_TYPE=firestore
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Redis (Cache/simple storage)
DATABASE_TYPE=redis
DATABASE_URL=redis://localhost:6379

# In-memory (Testing only)
DATABASE_TYPE=in_memory
```

### 2. Create a Repository

```python
# src/infrastructure/persistence/product_repository.py
from typing import Optional
from src.domain.models.product import Product
from src.infrastructure.persistence.base import BaseRepository

class ProductRepository(BaseRepository[Product]):
    async def save(self, product: Product) -> None:
        # Implementation based on your DATABASE_TYPE
        await self._save_entity(product)

    async def find_by_id(self, product_id: str) -> Optional[Product]:
        return await self._find_by_id(Product, product_id)

    async def find_by_category(self, category: str) -> list[Product]:
        return await self._find_by_field(Product, "category", category)
```

### 3. Use Dependency Injection

```python
# src/interfaces/api/routers/products.py
from fastapi import Depends
from src.infrastructure.dependencies import get_product_repository

@router.post("/")
async def create_product(
    command: CreateProductCommand,
    repo: ProductRepository = Depends(get_product_repository)
):
    # Use repository in your endpoint
    result = handle_create_product(command, repo)
    return result.value
```

## Deployment Options

### Local Development

```bash
# Docker Compose (recommended)
docker-compose up -d

# Manual setup
make run
```

### Production Deployment

```bash
# Build Docker image
docker build -t your-api:latest .

# Run with environment variables
docker run -p 8000:8000 --env-file .env.prod your-api:latest

# Or use the deployment script
./scripts/deployment/deploy-prod.sh
```

### Cloud Deployment

The template includes configurations for:

- **GitHub Actions**: Automated CI/CD pipelines
- **Docker**: Production-ready containers
- **Health Checks**: Kubernetes/cloud platform ready
- **Observability**: Metrics and logging integration

## Essential Commands Reference

```bash
# Development
make run                # Start development server
make test               # Run all tests with coverage
make test-fast          # Fast tests for TDD
make watch              # Continuous testing
make quality            # Full quality check (lint + type + test)

# Code Quality
make format             # Auto-format code
make lint               # Check code style
make typecheck          # Static type checking

# Database
make migrate-up         # Apply database migrations
make migrate-down       # Rollback migrations

# Docker
make docker-build       # Build production image
make docker-run         # Run containerized app
```

## Next Steps

### Immediate Actions

1. **Customize the template**: Update API_TITLE, add your business logic
2. **Configure your database**: Choose PostgreSQL, Firestore, or Redis
3. **Set up authentication**: Extend the API key system or add OAuth
4. **Add your first real endpoint**: Follow the patterns shown above

### Production Readiness

1. **Environment secrets**: Use proper secret management
2. **Database setup**: Configure connection pooling and migrations
3. **Monitoring**: Enable metrics collection and alerting
4. **CI/CD**: Customize GitHub Actions workflows
5. **Documentation**: Update API docs and add business-specific guides

### Advanced Features

1. **Background tasks**: Add Celery or similar for async processing
2. **Caching**: Implement Redis caching strategies
3. **Rate limiting**: Configure advanced rate limiting rules
4. **WebSocket support**: Add real-time capabilities
5. **Multi-tenancy**: Extend for multiple client support

## Common Issues & Solutions

### Port Already in Use

```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

### Poetry Lock Issues

```bash
# Reset poetry lock file
rm poetry.lock
poetry install
```

### Database Connection Errors

```bash
# Check database is running
docker-compose ps
# View logs
docker-compose logs postgres
```

### Import Errors

```bash
# Ensure you're in poetry shell
poetry shell
# Or run with poetry prefix
poetry run python -m pytest
```

---

**🎉 Congratulations!** You now have a production-ready FastAPI application. Check out the [Architecture Guide](architecture-principles.md) to understand the design patterns, and the [FAQ](faq.md) for common questions.

**Need help?** Open an issue in the repository or check the extensive test suite for usage examples.
