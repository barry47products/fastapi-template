# Frequently Asked Questions

Common questions and practical solutions for using the FastAPI template.

## Database Selection

### Q: When should I use PostgreSQL vs Firestore vs Redis?

**PostgreSQL** - Best for:

- Complex relational data with foreign keys
- ACID transactions and data consistency
- SQL queries and reporting
- Traditional web applications
- Team familiar with relational databases

**Firestore** - Best for:

- Document-based data structures
- Real-time synchronization needs
- Global scalability requirements
- Mobile/web app backends
- Offline-first applications

**Redis** - Best for:

- Simple key-value storage
- High-performance caching
- Session management
- Real-time analytics
- Temporary data storage

### Q: Can I use multiple databases simultaneously?

Yes! The template supports multi-database configurations:

```env
# Primary database
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:pass@localhost:5432/myapp

# Enable additional databases via feature flags
ENABLE_REDIS_CACHE=true
REDIS_URL=redis://localhost:6379

ENABLE_FIRESTORE=true
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

Use different repositories for different data types:

- PostgreSQL for transactional data (users, orders)
- Redis for caching and sessions
- Firestore for real-time features

### Q: How do I handle database migrations?

The template includes a migration system:

```python
# Create a migration
from src.infrastructure.persistence.migrations import BaseMigration

class AddProductCategoryMigration(BaseMigration):
    version = "2024_01_15_001"
    description = "Add category field to products"

    async def up(self):
        # Migration logic here
        pass

    async def down(self):
        # Rollback logic here
        pass
```

Run migrations:

```bash
make migrate-up    # Apply pending migrations
make migrate-down  # Rollback last migration
```

## Testing Strategy

### Q: How do I achieve 100% test coverage effectively?

**Structure your tests by domain, not coverage:**

```python
# ✅ Good: Domain-focused test class
class TestUserRegistration:
    def test_valid_user_registration_succeeds(self):
        # Test the happy path

    def test_duplicate_email_registration_fails(self):
        # Test business rule validation

    def test_invalid_email_format_rejected(self):
        # Test input validation

# ❌ Avoid: Coverage-focused test class
class TestUserModel:
    def test_line_47(self):  # Tests specific code line
    def test_branch_coverage_case_3(self):  # Tests coverage metric
```

**Use the testing pyramid:**

- **Unit tests (70%)**: Fast, isolated, test business logic
- **Integration tests (20%)**: Test component interactions
- **E2E tests (10%)**: Test complete user flows

**Mock external dependencies only:**

```python
# ✅ Mock external services
@patch('src.infrastructure.email.EmailService')
def test_user_registration_sends_welcome_email(mock_email):
    # Test that email is sent, not email service internals

# ❌ Don't mock your own domain logic
@patch('src.domain.models.User.validate_email')  # Bad!
```

### Q: How do I test async code effectively?

Use pytest-asyncio and proper async test patterns:

```python
import pytest

@pytest.mark.asyncio
async def test_async_endpoint():
    # Use AsyncClient for FastAPI testing
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/users", json=user_data)
        assert response.status_code == 201

@pytest.mark.asyncio
async def test_async_repository():
    # Test async repository methods
    user = await user_repo.save(test_user)
    found_user = await user_repo.find_by_id(user.id)
    assert found_user == user
```

### Q: How do I handle slow tests?

Use test markers and selective running:

```python
# Mark slow tests
@pytest.mark.slow
def test_database_integration():
    # Database-heavy test

@pytest.mark.integration
def test_external_api_integration():
    # External service test
```

Run different test suites:

```bash
make test-fast        # Skip slow and integration tests
make test-integration # Only integration tests
make test-slow        # Only slow tests
make test            # All tests
```

## Development Workflow

### Q: How do I organize my code following clean architecture?

**Layer responsibilities:**

```python
# Domain layer - Pure business logic
# src/domain/models/order.py
class Order:
    def calculate_total(self) -> Money:
        # Pure business logic, no dependencies

# Application layer - Orchestration
# src/application/commands/place_order.py
def handle_place_order(command: PlaceOrderCommand) -> Result[Order]:
    # Orchestrate domain objects and infrastructure

# Infrastructure layer - External concerns
# src/infrastructure/persistence/order_repository.py
class OrderRepository:
    # Database access, external APIs

# Interface layer - HTTP concerns
# src/interfaces/api/routers/orders.py
@router.post("/orders")
async def place_order(command: PlaceOrderCommand):
    # HTTP handling, serialization
```

**Dependency direction:** Interface → Application → Domain ← Infrastructure

### Q: What's the best way to handle errors and exceptions?

Use domain-specific exceptions with error codes:

```python
# Define specific exceptions
class InvalidEmailError(ValidationError):
    code = "INVALID_EMAIL"
    message = "Email format is invalid"

class UserNotFoundError(NotFoundError):
    code = "USER_NOT_FOUND"
    message = "User does not exist"

# Use in business logic
def register_user(email: str) -> Result[User]:
    if not Email.is_valid(email):
        return Result.failure(InvalidEmailError())

    # Business logic here
    return Result.success(user)

# Handle in API layer
@router.post("/users")
async def create_user(request: CreateUserRequest):
    result = register_user(request.email)

    if result.is_failure():
        raise HTTPException(
            status_code=get_http_status(result.error),
            detail=result.error.to_dict()
        )
```

### Q: How do I implement proper logging and observability?

Use structured logging with context:

```python
from src.infrastructure.observability import get_logger, get_metrics_collector

logger = get_logger(__name__)
metrics = get_metrics_collector()

def process_payment(payment: Payment) -> Result[PaymentResult]:
    logger.info(
        "Processing payment",
        payment_id=payment.id,
        amount=str(payment.amount),
        currency=payment.currency
    )

    try:
        # Process payment
        result = payment_processor.charge(payment)

        metrics.increment_counter("payments_processed_total")
        metrics.record_histogram("payment_amount", payment.amount.value)

        logger.info(
            "Payment processed successfully",
            payment_id=payment.id,
            transaction_id=result.transaction_id
        )

        return Result.success(result)

    except PaymentProcessorError as e:
        metrics.increment_counter("payment_errors_total")

        logger.error(
            "Payment processing failed",
            payment_id=payment.id,
            error_code=e.code,
            error_message=str(e)
        )

        return Result.failure(PaymentProcessingError(str(e)))
```

## Deployment Options

### Q: What's the difference between Docker deployment options?

**Development (docker-compose.yml):**

- Hot reload enabled
- Debug logging
- Development databases
- All services exposed

**Production (docker-compose.prod.yml):**

- Optimized images
- Health checks
- Secrets management
- Load balancing ready
- Security hardening

**Single container:**

```bash
# Build production image
docker build -t myapi:latest .

# Run with environment file
docker run -p 8000:8000 --env-file .env.prod myapi:latest
```

### Q: How do I deploy to cloud platforms?

**AWS ECS:**

```bash
# Build and push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-west-2.amazonaws.com
docker build -t myapi .
docker tag myapi:latest 123456789.dkr.ecr.us-west-2.amazonaws.com/myapi:latest
docker push 123456789.dkr.ecr.us-west-2.amazonaws.com/myapi:latest
```

**Google Cloud Run:**

```bash
# Deploy directly from source
gcloud run deploy myapi --source . --region us-central1
```

**Azure Container Apps:**

```bash
az containerapp up --name myapi --source . --resource-group mygroup
```

### Q: How do I handle secrets in production?

**Never put secrets in environment files committed to git.**

**Use platform secret management:**

```python
# src/config/settings.py
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Load from environment or secret manager
    database_url: str = Field(..., env="DATABASE_URL")
    api_key: str = Field(..., env="API_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = False
```

**Platform-specific secrets:**

- **AWS**: Use AWS Systems Manager Parameter Store or Secrets Manager
- **Google Cloud**: Use Secret Manager
- **Azure**: Use Key Vault
- **Kubernetes**: Use Kubernetes Secrets
- **Docker**: Use Docker Secrets (Swarm mode)

## Performance Tuning

### Q: How do I optimize database performance?

**Connection pooling (already configured):**

```python
# src/infrastructure/persistence/postgresql.py
engine = create_async_engine(
    database_url,
    pool_size=20,           # Concurrent connections
    max_overflow=30,        # Additional connections when busy
    pool_pre_ping=True,     # Verify connections before use
    pool_recycle=3600       # Recycle connections hourly
)
```

**Query optimization:**

```python
# Use indexes for common queries
class User:
    email: str = Field(..., index=True)  # Index frequently queried fields

# Use bulk operations for multiple records
async def bulk_update_users(users: list[User]):
    await repository.bulk_update(users)  # More efficient than individual updates
```

**Caching strategies:**

```python
# Cache expensive computations
@lru_cache(maxsize=100)
def calculate_shipping_cost(weight: float, distance: float) -> Money:
    # Expensive calculation cached in memory

# Use Redis for shared caching
async def get_user_preferences(user_id: str) -> UserPreferences:
    cached = await redis_client.get(f"user_prefs:{user_id}")
    if cached:
        return UserPreferences.parse_raw(cached)

    prefs = await user_repo.get_preferences(user_id)
    await redis_client.setex(f"user_prefs:{user_id}", 3600, prefs.json())
    return prefs
```

### Q: How do I monitor application performance?

**Built-in metrics collection:**

```python
# Metrics automatically collected for:
# - Request duration and count
# - Error rates by endpoint
# - Database query performance
# - Cache hit/miss rates
```

**Custom business metrics:**

```python
from src.infrastructure.observability import get_metrics_collector

metrics = get_metrics_collector()

def process_order(order: Order):
    # Increment business counters
    metrics.increment_counter("orders_processed_total")
    metrics.increment_counter(f"orders_by_category_{order.category}")

    # Record business histograms
    metrics.record_histogram("order_value", order.total.amount)
    metrics.record_histogram("order_items_count", len(order.items))
```

**Health check endpoints:**

- `/status` - Basic health check
- `/health` - Detailed health with dependencies
- `/metrics` - Prometheus metrics (restrict in production)

## Common Issues

### Q: Why am I getting import errors?

**Most common causes:**

1. **Not in Poetry shell:**

    ```bash
    poetry shell  # Activate virtual environment
    # or
    poetry run python your_script.py
    ```

2. **Incorrect Python path:**

    ```bash
    # Add to your IDE/editor configuration
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    ```

3. **Circular imports:**

    ```python
    # ❌ Avoid circular imports between modules
    # Instead, move shared dependencies to a common module
    ```

### Q: How do I debug failing tests?

**Run specific tests with verbose output:**

```bash
# Single test with full output
poetry run pytest tests/unit/test_user_registration.py::test_valid_registration -vvv

# Debug with pdb
poetry run pytest --pdb tests/unit/test_user_registration.py

# Show all print statements
poetry run pytest -s tests/unit/test_user_registration.py
```

**Common test failures:**

- **Async/await issues**: Ensure all async functions are properly awaited
- **Database state**: Use database fixtures or reset between tests
- **Mock configuration**: Verify mocks are patching the correct import path

### Q: My API is running slowly. How do I investigate?

**Check the metrics endpoint:**

```bash
curl http://localhost:8000/metrics | grep -E "(request_duration|db_query_duration)"
```

**Enable debug logging:**

```env
LOG_LEVEL=DEBUG
```

**Profile specific endpoints:**

```python
import cProfile
import pstats

def profile_endpoint():
    profiler = cProfile.Profile()
    profiler.enable()

    # Your endpoint logic here
    result = process_request()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative').print_stats(20)

    return result
```

---

**Still have questions?** Check the [Architecture Guide](architecture-principles.md) for design patterns, or open an issue in the repository for specific problems.
