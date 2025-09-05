# Neighbour Approved: Technical Considerations

## Core Technical Architecture

### Integration Layer: GREEN-API

#### **Why GREEN-API**

- Direct WhatsApp Business API access without Meta's complex approval process
- Webhook-based message reception enabling real-time processing
- Support for both group and private messaging
- Ability to read message history for context
- Emoji reaction detection capabilities

#### **Critical GREEN-API Considerations**

- Rate limiting: Must respect WhatsApp's anti-spam policies
- Message templates: Private messages may require pre-approved templates
- Webhook reliability: Need redundancy and retry logic
- Cost per message: Factor into unit economics
- API stability: Build abstraction layer for potential provider switching

### Architecture: Python Backend with FastAPI

#### **Chosen Architecture: Python Backend (Container-based)**

We're building with a Python backend for better control, easier debugging, and simpler local development.

_Architecture Advantages:_

- Familiar development environment with full debugging capabilities
- Easier local testing without cloud emulation
- Stateful processing capabilities for complex flows
- Complete control over message processing pipeline
- Better suited for complex NLP requirements
- Simpler dependency injection and testing

_Technical Stack:_

- **FastAPI**: Modern, fast, async Python web framework
- **Uvicorn**: ASGI server for production
- **Pydantic**: Data validation and settings management
- **Poetry**: Dependency management
- **Docker**: Containerisation (for later deployment)

_Recommended Architecture:_

```bash
WhatsApp → GREEN-API → Webhook Endpoint (FastAPI)
                      ↓
                 Message Router
                      ↓
        Processing Pipeline (Async)
        (mention detection, endorsement processing,
         summary generation, emoji handler)
                      ↓
                 PostgreSQL DB
                      ↓
              Response Sender
```

**Local Development Setup:**

```python
# src/main.py
from fastapi import FastAPI
from src.interfaces.api.routers import webhooks, health
from src.infrastructure.observability import configure_logging

app = FastAPI(title="Neighbour Approved")

# Configure logging
configure_logging()

# Add routers
app.include_router(webhooks.router)
app.include_router(health.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

**Production Deployment (Future):**

- Containerised with Docker
- Deployed to Cloud Run or Kubernetes
- Auto-scaling based on load
- Health checks and graceful shutdown
- Zero-downtime deployments

---

## Message Processing Pipeline

### FastAPI Application Structure

**Main Application Entry Point:**

```python
# src/interfaces/api/app.py
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from src.infrastructure.observability import logger, metrics
from src.infrastructure.feature_flags import feature_flags
from config.settings import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Neighbour Approved API")
    feature_flags.initialise(settings)
    yield
    # Shutdown
    logger.info("Shutting down Neighbour Approved API")

app = FastAPI(
    title="Neighbour Approved",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
)
```

**Webhook Handler:**

```python
# src/interfaces/api/routers/webhooks.py
from fastapi import APIRouter, Depends, Request, HTTPException
from src.application.commands import ProcessMessageCommand
from src.infrastructure.security import verify_webhook_signature

router = APIRouter(prefix="/webhook", tags=["webhooks"])

@router.post("/whatsapp")
async def handle_whatsapp_webhook(
    request: Request,
    verified: bool = Depends(verify_webhook_signature)
):
    if not verified:
        raise HTTPException(status_code=403, detail="Invalid signature")

    body = await request.json()
    command = ProcessMessageCommand()
    result = await command.execute(body)

    return {"status": "processed", "message_id": result.message_id}
```

### Inbound Message Classification

**Challenge**: Accurately identifying request vs recommendation vs noise

#### **Solution: Multi-stage Classification**

1. **Keyword Detection** (Fast, rule-based)
   - "recommend", "anyone know", "need a", "looking for"
   - Language variations and common misspellings
2. **Context Analysis** (NLP-based when needed)
   - Question mark detection
   - Sentence structure analysis
   - Previous message context (if replying)
3. **Entity Extraction**
   - Service type identification (plumber, electrician, etc.)
   - Provider name extraction from recommendations
   - Temporal markers ("urgent", "tomorrow", "ASAP")

**Technical Stack**:

- spaCy for NLP (lightweight, fast) - added when needed
- Regex patterns for common cases - start with this
- Cloud Natural Language API for complex cases (future)

### Provider Matching & Deduplication

**Challenge**: Same provider, different mentions, complex tag assignment

- "Davies Electrical" vs "Davies" vs "John from Davies"
- Phone number variations: "+44 7700 900123" vs "07700900123"
- **Tag inference**: "need emergency electrician" → tags: `{"Electrician": ["Emergency"], "Emergency": ["24/7"]}`

#### **Solution: PostgreSQL-Powered Matching Pipeline**

**Fuzzy Phone Matching** with PostgreSQL `pg_trgm`:

```sql
-- Find similar phone numbers
SELECT * FROM providers 
WHERE phone_normalized % %s  -- trigram similarity
ORDER BY similarity(phone_normalized, %s) DESC
LIMIT 1;
```

**Tag-Based Provider Discovery**:

```sql
-- Find providers by tag capabilities
SELECT * FROM providers 
WHERE tags->'Electrician' ? 'Geysers'  -- JSONB containment
AND endorsement_count >= 2;
```

```python
# src/domain/rules/provider_matcher.py
from dataclasses import dataclass
from typing import Optional
import re
from difflib import SequenceMatcher

@dataclass(frozen=True)
class MatchResult:
    is_match: bool
    confidence: float
    matched_provider: Optional[Provider]

class ProviderMatcher:
    def match(self, mention: str, existing: List[Provider]) -> MatchResult:
        normalised_mention = self._normalise(mention)

        for provider in existing:
            # Check phone number first (most reliable)
            if provider.phone and self._extract_phone(mention):
                if self._phones_match(
                    self._extract_phone(mention),
                    provider.phone
                ):
                    return MatchResult(True, 0.95, provider)

            # Check name similarity
            similarity = SequenceMatcher(
                None,
                normalised_mention,
                self._normalise(provider.name)
            ).ratio()

            if similarity > 0.85:
                return MatchResult(True, similarity, provider)

        return MatchResult(False, 0.0, None)

    def _normalise(self, text: str) -> str:
        """Normalise text for comparison."""
        return re.sub(r'[^\w\s]', '', text.lower()).strip()

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text."""
        pattern = r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}'
        match = re.search(pattern, text)
        return match.group(0) if match else None
```

### Async Processing Benefits

**Why Async Python Backend**:

FastAPI with async/await provides excellent concurrency for I/O-bound operations:

```python
# src/application/commands/process_message.py
from typing import List
import asyncio

class ProcessMessageCommand:
    """Processes WhatsApp messages asynchronously."""

    async def execute(self, message: Message) -> ProcessResult:
        # Parallel processing of independent tasks
        async with asyncio.TaskGroup() as tg:
            classification_task = tg.create_task(
                self._classify_message(message)
            )
            entity_task = tg.create_task(
                self._extract_entities(message)
            )

        classification = classification_task.result()
        entities = entity_task.result()

        # Process based on classification
        if classification.is_request:
            await self._handle_request(message, entities)
        elif classification.is_recommendation:
            await self._handle_recommendation(message, entities)

        return ProcessResult(success=True)

    async def _classify_message(self, message: Message) -> Classification:
        """Classify message type asynchronously."""
        # Can make async API calls if needed
        return await self._classifier.classify(message)

    async def _extract_entities(self, message: Message) -> List[Entity]:
        """Extract entities asynchronously."""
        # Can run NLP models asynchronously
        return await self._extractor.extract(message)
```

**Concurrency Advantages**:

- Handle multiple webhooks simultaneously
- Process database operations in parallel
- Non-blocking I/O for external API calls
- Efficient resource utilisation
- Better response times under load

### State Management

**Application State Strategy**:

In-memory state for active sessions:

```python
# src/infrastructure/state/session_manager.py
from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass(frozen=True)
class Session:
    group_id: str
    last_summary: datetime
    pending_followups: list[str]
    active_reactions: dict[str, datetime]

class SessionManager:
    """Manages in-memory session state."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def get_session(self, group_id: str) -> Optional[Session]:
        return self._sessions.get(group_id)

    def update_session(self, session: Session) -> None:
        self._sessions[session.group_id] = session

    def cleanup_expired(self) -> None:
        """Remove sessions older than 24 hours."""
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self._sessions = {
            k: v for k, v in self._sessions.items()
            if v.last_summary > cutoff
        }
```

**Persistent State in PostgreSQL**:

- **Provider profiles with hierarchical tags** (JSONB for tag structure)
  - Basic info: name, phone, category, endorsement_count
  - **Tags field**: `{"Electrician": ["Geysers", "Wiring"], "Emergency": ["24/7"]}`
  - **Revenue model**: Tags enable provider keyword bidding and category specialization
- **Endorsement records** with provider and group relationships
- **Group metadata** and settings
- **Historical message data** for analytics
- **Audit logs** for compliance

**State Management Best Practices**:

- Keep sessions ephemeral (in-memory)
- Persist business data immediately
- Use transactions for consistency
- Implement graceful recovery

---

## Privacy & Compliance Architecture

### Data Minimisation Principle

**What We Store**:

- Provider names and phone numbers (public info)
- Endorsement counts (aggregated)
- Group IDs (not member details)
- Timestamp of interactions

**What We DON'T Store**:

- Message content beyond extractions
- User phone numbers (except providers)
- Personal conversations
- Media files or documents

### GDPR Compliance

**Technical Implementation**:

- Opt-out webhook that triggers immediate data deletion
- 30-day automatic purge of interaction logs
- No data transfer outside region
- Encryption at rest and in transit

**Right to be Forgotten**:

```python
def handle_optout(phone_number):
    # Remove from active sessions
    redis.delete(f"session:{phone_number}")
    # Add to permanent opt-out list
    db.execute("""
        INSERT INTO optouts (phone_hash, timestamp) 
        VALUES (%s, %s)
    """, [hash(phone_number), datetime.now()])
    # Don't delete endorsements (they're anonymised)
```

### WhatsApp Compliance

**Critical Rules**:

- No promotional messages without user-initiated contact
- 24-hour window for responses to user messages
- Clear opt-out in every message
- No automatic group joining or manipulation

---

## Scaling Considerations

### Python Backend Scaling Strategy

**Expected Growth Pattern**:

- One group success → 5-10 adjacent groups (neighbourhood network)
- Exponential within city (local Facebook groups cross-pollination)
- Platform growth: 10x monthly during viral phase

**Technical Preparation**:

1. **Application Architecture**:

   ```python
   # Async processing for high concurrency
   async def process_message(message: Message) -> None:
       async with asyncio.TaskGroup() as tg:
           tg.create_task(classify_message(message))
           tg.create_task(extract_entities(message))
   ```

2. **Database Connection Pooling**:

   ```python
   # src/infrastructure/persistence/postgres_pool.py
   import asyncpg
   from asyncpg import Pool

   class PostgreSQLPool:
       def __init__(self, database_url: str, max_connections: int = 10):
           self._database_url = database_url
           self._max_connections = max_connections
           self._pool: Pool = None

       async def initialize(self):
           self._pool = await asyncpg.create_pool(
               self._database_url, 
               max_size=self._max_connections
           )
   ```

3. **Caching Strategy**:

   - In-memory cache for hot data (provider profiles)
   - Redis for distributed cache (future)
   - Cache group summaries (regenerate hourly)

4. **Horizontal Scaling**:
   - Multiple FastAPI instances behind load balancer
   - Stateless design enables easy scaling
   - Health checks for automatic instance management

### Performance Targets

**MVP Phase (Current Focus)**:

- Handle 100 groups (5,000 members)
- Process 1,000 messages/day
- Sub-second API response time
- Single instance on local machine

**Growth Phase (Future)**:

- Handle 10,000 groups (500,000 members)
- Process 100,000 messages/day
- Multiple instances with load balancing
- Redis for session management

**Scale Phase (Future)**:

- Handle 1M groups (50M members)
- Process 10M messages/day
- Kubernetes deployment
- Multi-region architecture

---

## Natural Language Processing Pipeline

### Service Category Taxonomy

**Challenge**: "Plumber" vs "plumbing" vs "fix leak" vs "boiler repair"

#### **Solution: Hierarchical Category System**

```bash
Home Repair
├── Plumbing
│   ├── Keywords: plumber, leak, pipe, boiler, tap
│   ├── Phrases: "fix leak", "burst pipe", "no hot water"
│   └── Aliases: plumber → plumbing → waterworks
├── Electrical
│   ├── Keywords: electrician, wiring, lights, fuse
│   └── Phrases: "power out", "tripping switch"
```

### Recommendation Extraction

**Pattern Recognition**:

```python
RECOMMENDATION_PATTERNS = [
    r"(?:I |we )?(?:use|used|recommend|try) (\w+ \w+)",
    r"(\w+ \w+) (?:is|are|were) (?:great|good|brilliant)",
    r"(?:call|contact|try) (\w+ \w+)",
    r"(\w+) (?:did|sorted|fixed) (?:mine|ours)",
]
```

### Sentiment Filtering

**Avoid False Positives**:

- "DON'T use Davies" → No endorsement
- "Davies was okay I guess" → No automatic endorsement
- "Davies if you're desperate" → No endorsement

---

## Testing & Quality Assurance

### Test Environment Setup

**Local Development Testing**:

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from src.interfaces.api.app import app

@pytest.fixture
def test_client():
    """Test client for FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_green_api():
    """Mock GREEN-API client for testing."""
    mock = Mock()
    mock.send_message.return_value = {"messageId": "test-123"}
    return mock
```

**WhatsApp Test Setup**:

- Dedicated test WhatsApp groups with team members
- GREEN-API sandbox environment for development
- Mock webhook payloads for unit testing

**Integration Testing**:

```python
# tests/integration/test_webhook_flow.py
async def test_full_message_flow(test_client, mock_green_api):
    # Test complete flow from webhook to response
    payload = {
        "messageData": {
            "body": "Can anyone recommend a plumber?",
            "from": "447700900123@c.us",
            "chatId": "120363123456789@g.us"
        }
    }

    response = test_client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200
    assert mock_green_api.send_message.called
```

### Monitoring & Observability

**Application Metrics**:

```python
# src/infrastructure/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps

class Metrics:
    def __init__(self):
        # Business metrics
        self.messages_processed = Counter(
            'messages_processed_total',
            'Total messages processed',
            ['message_type', 'status']
        )

        # Performance metrics
        self.request_duration = Histogram(
            'request_duration_seconds',
            'Request duration',
            ['method', 'endpoint']
        )

    def track_time(self, operation: str):
        """Decorator to track execution time."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    return await func(*args, **kwargs)
                finally:
                    duration = time.time() - start
                    self.request_duration.labels(
                        method=operation,
                        endpoint=func.__name__
                    ).observe(duration)
            return wrapper
        return decorator
```

**Local Monitoring Dashboard**:

- Prometheus running locally via Docker
- Grafana for visualisation
- Custom dashboard for key metrics

---

## Security Considerations

### Potential Attack Vectors

**Spam/Manipulation**:

- Fake endorsements from bot accounts
- Providers gaming the system
- Malicious group takeover attempts

**Mitigation**:

- Rate limiting per phone number
- Endorsement velocity checks
- Manual review triggers for anomalies
- Require minimum group age/size

### API Security

```python
# Webhook validation
def validate_webhook(request):
    signature = request.headers.get('X-GREEN-API-Signature')
    payload = request.body
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

---

## Cost Optimisation

### Per-Message Economics

**GREEN-API Costs**:

- Inbound message: ~£0.005
- Outbound message: ~£0.01
- Media message: ~£0.02

**Optimisation Strategies**:

1. Batch summaries (one message vs many)
2. Emoji reactions are free (use for interaction)
3. Cache responses for common queries
4. Progressive detail (summary → details on request)

### Infrastructure Cost Management

**Python Backend Optimisation**:

- Start with single instance locally (zero cost)
- Use async processing for higher concurrency
- Implement connection pooling for database
- Cache frequently accessed data in memory

**Future Production Costs**:

- Cloud Run: Pay per request (scales to zero)
- PostgreSQL: Fixed instance cost (Cloud SQL or managed service)
- Monitoring: Free tier sufficient for MVP

**Cost Control Measures**:

```python
# Rate limiting to control API costs
from src.infrastructure.security.rate_limiter import RateLimiter

rate_limiter = RateLimiter(
    max_requests_per_group_per_hour=5,
    max_summaries_per_day=1
)

@router.post("/webhook/whatsapp")
async def handle_webhook(request: Request):
    group_id = extract_group_id(request)

    if not rate_limiter.check_limit(group_id):
        logger.warning(f"Rate limit exceeded for group {group_id}")
        return {"status": "rate_limited"}

    # Process message
```

---

## Deployment Strategy

### Local Development (Current)

- Python 3.13 with Poetry
- FastAPI with auto-reload
- Local PostgreSQL (Docker or native)
- ngrok for webhook testing

### Staging Environment (Next)

- Docker container on Cloud Run
- Staging PostgreSQL database (Cloud SQL)
- Separate GREEN-API instance
- Basic monitoring with Cloud Logging

### Production Deployment (Future)

- Multi-region Cloud Run deployment
- Production PostgreSQL with backups (Cloud SQL HA)
- Full monitoring stack (Prometheus, Grafana)
- Zero-downtime blue-green deployments

**Docker Configuration** (for future use):

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy dependencies
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

# Copy application
COPY src ./src
COPY config ./config

# Run with Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Technical Roadmap - Flow-Based

### Current Module: [Active Work - WIP = 1]

Focus on ONE module until complete.

### Completed Modules: ✅

(Track completed work here)

### Module Backlog (In Priority Order)

#### Foundation Modules (Do First)

1. **Settings Configuration** - All configuration via environment
2. **Exception Hierarchy** - Base exceptions for error handling
3. **Structured Logger** - Logging infrastructure
4. **Metrics Collector** - Prometheus metrics
5. **Feature Flags Manager** - Control feature rollout

#### Core Domain (Do Next)

1. **Phone Number Value Object** - Phone validation and normalisation
2. **Group ID Value Object** - WhatsApp group identifier
3. **Provider ID Value Object** - Unique provider identifier
4. **Provider Model** - Provider domain model
5. **Endorsement Model** - Endorsement domain model

#### Infrastructure (Then)

1. **API Key Validator** - Security layer
2. **Rate Limiter** - Request throttling
3. **Webhook Verifier** - GREEN-API signature validation
4. **Health Checker** - Liveness/readiness probes

#### Message Processing (Then)

1. **Message Classifier** - Identify request vs recommendation
2. **Provider Matcher** - Fuzzy matching for providers
3. **Mention Extractor** - Extract provider mentions
4. **Summary Generator** - Create group summaries

#### API Layer (Finally)

1. **FastAPI App** - Main application
2. **Webhook Handler** - GREEN-API webhook endpoint
3. **Health Endpoints** - Health check routes
4. **Metrics Endpoint** - Prometheus metrics route

### Decision Gates

**After Foundation**: System can log, track metrics, and handle errors ✓
**After Core Domain**: Business logic is defined and tested ✓  
**After Infrastructure**: System is secure and observable ✓
**After Message Processing**: Can handle WhatsApp messages ✓
**After API Layer**: Ready for integration testing ✓

### Remember: Complete Current Module Before Starting Next

No parallel work. No jumping ahead. One module at a time.

---

## Risk Mitigation

### Technical Risks

**WhatsApp Policy Changes**:

- Mitigation: Abstract GREEN-API integration
- Backup: Direct WhatsApp Business API

**Message Misclassification**:

- Mitigation: Start with simple regex, add NLP gradually
- Backup: Manual review queue for edge cases

**Scaling Bottlenecks**:

- Mitigation: Async processing from day one
- Backup: Horizontal scaling with multiple instances

**Data Loss**:

- Mitigation: Regular PostgreSQL backups and WAL archiving
- Backup: Point-in-time recovery with transaction logs

### Python Backend Specific Risks

**Memory Leaks**:

- Mitigation: Proper async context management
- Monitoring: Memory usage metrics

**Connection Pool Exhaustion**:

- Mitigation: Connection pooling with limits
- Monitoring: Active connection metrics

**Webhook Timeout**:

- Mitigation: Fast acknowledgment, async processing
- Backup: Retry mechanism for failed messages

---

## Development Principles

1. **Flow-Based Development**: WIP limit of 1 - complete one module entirely before starting next
2. **Test-Driven**: No code without failing test first (Red-Green-Refactor)
3. **Start Simple**: Regex before NLP, single process before distributed
4. **Fail Gracefully**: Never break the WhatsApp experience
5. **Measure Everything**: You can't improve what you don't measure
6. **Privacy First**: Collect minimum data, delete aggressively
7. **Type Safety**: Python 3.13 with full type annotations
8. **Document Decisions**: Future you will thank present you

## Development Environment

- **Python**: 3.13 (latest)
- **Framework**: FastAPI with Uvicorn
- **IDE**: VSCode with Claude Code
- **Platform**: MacBook Pro (Apple Silicon)
- **Package Manager**: Poetry (latest)
- **Container**: Docker Desktop (for future testing only)
- **Database**: PostgreSQL (relational, JSONB for tags)
- **Monitoring**: Prometheus + Grafana (local)
