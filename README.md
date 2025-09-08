# FastAPI Template

> **Production-ready FastAPI template with clean architecture, comprehensive testing, and modern Python practices**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Poetry](https://img.shields.io/badge/Poetry-package%20manager-blue)](https://python-poetry.org)
[![Ruff](https://img.shields.io/badge/Code%20style-Ruff-black)](https://github.com/astral-sh/ruff)
[![MyPy](https://img.shields.io/badge/Type%20checker-MyPy-blue)](https://mypy.readthedocs.io)
[![Test Coverage](https://img.shields.io/badge/Coverage-100%25-brightgreen)](https://pytest.org)

## Why This Template?

**Stop spending weeks setting up infrastructure.** This template provides everything you need to build production-ready APIs from day one.

- 🚀 **Zero-to-API in minutes** - Complete setup with authentication, validation, and monitoring
- 🏗️ **Clean Architecture** - Domain-driven design with clear separation of concerns
- 🔒 **Production Security** - API key authentication, rate limiting, and input validation
- 📊 **Built-in Observability** - Structured logging, metrics, and health checks
- 🧪 **100% Test Coverage** - Comprehensive test suite with behavioural testing
- 🐳 **Docker Ready** - Multi-stage builds with development and production configurations
- 🗄️ **Multi-Database Support** - PostgreSQL, Firestore, Redis with feature flags
- ⚡ **Developer Experience** - Hot reload, type safety, and modern Python tooling

## Quick Start

### 1. Create Your Project

```bash
# Clone the template
git clone https://github.com/barry47products/fastapi-template.git your-project-name
cd your-project-name

# Install dependencies
poetry install && poetry shell

# Set up development environment
cp .env.example .env
```

### 2. Start Development

```bash
# Run with hot reload
make run

# Run tests
make test

# Check code quality
make quality
```

### 3. Your API is Ready

Visit `http://localhost:8000/docs` to explore your API documentation.

## What's Included

### 🏗️ Architecture

- **Domain Layer**: Pure business logic with immutable models
- **Application Layer**: Commands, queries, and orchestration
- **Infrastructure Layer**: Database, external APIs, security
- **Interface Layer**: FastAPI routes and schemas

### 🛠️ Development Tools

- **Poetry**: Dependency management and virtual environments
- **Ruff**: Lightning-fast linting and formatting
- **MyPy**: Static type checking with strict mode
- **Pytest**: Testing framework with high coverage requirement
- **Pre-commit**: Automated code quality checks

### 📦 Infrastructure

- **Authentication**: API key validation with multiple formats
- **Rate Limiting**: Configurable request throttling
- **Validation**: Pydantic models with comprehensive error handling
- **Observability**: Structured logging with metrics collection
- **Health Checks**: Kubernetes-ready liveness and readiness probes
- **Error Handling**: Domain-specific exceptions with proper HTTP responses

### 🗄️ Database Support

- **PostgreSQL**: Production async implementation with connection pooling
- **Firestore**: NoSQL document store with caching
- **Redis**: High-performance caching layer
- **Feature Flags**: Enable/disable databases via configuration

## Configuration

All configuration is handled via environment variables:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_TITLE="Your API"

# Security
INTERNAL_API_KEYS=your-secret-key-here
WEBHOOK_SECRET=webhook-secret

# Database (choose one)
DATABASE_TYPE=postgresql  # postgresql|firestore|redis|in_memory
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Observability
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

## Available Commands

```bash
# Development
make run                # Start development server
make test               # Run all tests
make test-fast          # Run fast tests only (excludes slow markers)
make watch              # Run tests in watch mode

# Code Quality
make format             # Format code with Ruff
make lint               # Check code style
make typecheck          # Run MyPy type checking
make quality            # Run all quality checks
make pr                 # Prepare for pull request

# Database
make migrate-up         # Apply database migrations
make migrate-down       # Rollback last migration

# Docker
make docker-build       # Build Docker image
make docker-run         # Run in container
```

## Testing Strategy

This template follows behaviour-driven testing principles:

- **Unit Tests**: Domain logic and pure functions
- **Integration Tests**: Component interactions
- **Contract Tests**: API endpoint behaviour
- **Behaviour Tests**: User story validation

```bash
# Run specific test categories
make test-unit          # Domain and business logic
make test-integration   # Infrastructure components
make test-behaviour     # End-to-end scenarios
make test-security      # Security validations
```

## Deployment

### Docker

```dockerfile
# Multi-stage build included
docker build -t your-api .
docker run -p 8000:8000 your-api
```

### Kubernetes

```yaml
# Kubernetes manifests provided
kubectl apply -f kubernetes/
```

### Environment Variables

Production-ready configuration with validation:

```python
# All settings are typed and validated
class Settings(BaseModel):
    api: APISettings
    database: DatabaseSettings
    security: SecuritySettings
    observability: ObservabilitySettings
```

## Architecture Decisions

### Why Clean Architecture?

- **Testability**: Business logic isolated from infrastructure
- **Flexibility**: Easy to swap databases or external services
- **Maintainability**: Clear boundaries and responsibilities

### Why These Tools?

- **FastAPI**: Best-in-class API framework with automatic docs
- **Ruff**: 10-100x faster than alternatives with same results
- **Poetry**: Reliable dependency management with lock files
- **Pydantic**: Runtime validation with excellent error messages

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure all tests pass: `make quality`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/barry47products/fastapi-template/issues)
- 💬 [Discussions](https://github.com/barry47products/fastapi-template/discussions)

---

## **Built with ❤️ for the Python community**
