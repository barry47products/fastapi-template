# ChatterBridge Functional Specification

## Executive Summary

ChatterBridge is a bidirectional messaging bridge between WhatsApp groups and Slack channels/threads, utilizing a publish-subscribe architecture with Redis as the message broker. The application enables seamless communication between teams using different platforms while maintaining message context, user identity, and thread organization.

## System Overview

### Purpose

ChatterBridge serves as an integration layer that:

- Relays messages between WhatsApp groups and Slack channels in real-time
- Maintains persistent thread associations for organized conversations
- Supports multiple workspace installations through OAuth 2.0
- Provides secure, scalable message routing with deduplication

### Architecture Pattern

The system implements a **Publish-Subscribe (Pub-Sub) architecture** with the following characteristics:

- **Decoupled Components**: Services communicate through Redis channels, not direct calls
- **Asynchronous Processing**: Non-blocking message handling for high throughput
- **Event-Driven**: Components react to message events published to Redis
- **Scalable**: Components can be scaled independently based on load

## Core Components

### 1. Webhook Service (`webhooks.py`)

**Purpose**: Entry point for WhatsApp messages via GREEN-API webhooks

**Functionality**:

- Receives HTTP POST webhooks from GREEN-API (WhatsApp Business API)
- Validates and sanitizes incoming message data
- Detects onboarding link codes in messages
- Publishes processed messages to Redis channel `whatsapp:messages`
- Handles webhook types:
  - `incomingMessageReceived`: New WhatsApp messages
  - `outgoingMessageStatus`: Delivery status updates
  - `stateInstanceChanged`: WhatsApp instance state changes

**Security Features**:

- Request size validation (max payload limits)
- JSON payload validation
- Optional authentication header validation
- Input sanitization to prevent injection attacks

### 2. Slack Events Service (`slack_events.py`)

**Purpose**: Entry point for Slack messages via Events API

**Functionality**:

- Receives Slack Events API webhooks
- Verifies request signatures using SLACK_SIGNING_SECRET
- Handles event types:
  - `message`: Regular messages in threads
  - `app_mention`: Bot mentions for onboarding
  - `member_joined_channel`: Bot joining channels
  - `url_verification`: Slack endpoint verification
- Routes messages from managed threads to WhatsApp
- Publishes to Redis channel `slack:messages`

**Multi-Workspace Support**:

- Maintains workspace-specific Slack clients
- Uses OAuth tokens stored per workspace
- Extracts team_id from events for workspace identification

### 3. Message Worker (`worker.py`)

**Purpose**: Core message processing and routing engine

**Functionality**:

- Subscribes to Redis pub/sub channels:
  - `whatsapp:messages`: Messages from WhatsApp
  - `slack:messages`: Messages from Slack
- Routes messages between platforms with formatting
- Manages Slack thread lifecycle:
  - Creates new threads for WhatsApp groups
  - Maintains thread persistence in Redis
  - Handles thread timeout and channel broadcasting
- Implements message deduplication
- Tracks activity timestamps for timeout logic

**Key Responsibilities**:

- Platform-specific message formatting
- User name resolution
- Thread management and persistence
- Metrics collection and health monitoring

### 4. Application Factory (`app_factory.py`)

**Purpose**: Unified FastAPI application creation and configuration

**Functionality**:

- Creates FastAPI instances with consistent configuration
- Registers all endpoints (webhooks, health, monitoring, dashboard)
- Applies middleware stack:
  - Request logging
  - Security (rate limiting, IP intelligence)
  - Compression
- Manages static file serving with caching
- Handles lead generation forms for landing page

### 5. Services Layer (`services.py`)

#### WhatsAppService

- Sends messages to WhatsApp via GREEN-API
- Implements circuit breaker pattern for fault tolerance
- Handles retry logic with exponential backoff
- Validates and formats WhatsApp messages

#### SlackService

- Posts messages to Slack channels/threads
- Manages Block Kit formatting
- Handles user mentions and rich text
- Implements workspace-specific client management

#### RedisService

- Manages Redis operations for caching
- Handles pub/sub operations
- Implements connection pooling
- Provides atomic operations for thread management

## Message Flow Architecture

### WhatsApp to Slack Flow

```text
1. WhatsApp User sends message in group
2. GREEN-API receives message and triggers webhook
3. Webhook Service (webhooks.py) receives POST request
4. Service validates and processes message:
   - Extracts group_id, sender, text, timestamp
   - Checks for onboarding link codes
   - Sanitizes content
5. Publishes to Redis channel "whatsapp:messages"
6. Message Worker subscribes and receives message
7. Worker checks group mapping in Redis
8. If mapped:
   - Retrieves or creates Slack thread for group
   - Formats message with WhatsApp sender info
   - Posts to Slack thread via SlackService
9. Updates activity timestamp and metrics
```

### Slack to WhatsApp Flow

```text
1. Slack User posts message in managed thread
2. Slack Events API sends webhook
3. Slack Events Service receives and verifies request
4. Service processes message event:
   - Validates it's from a managed thread
   - Extracts user info and text
   - Identifies target WhatsApp group
5. Publishes to Redis channel "slack:messages"
6. Message Worker receives message
7. Worker formats message with Slack sender info
8. Sends to WhatsApp group via GREEN-API
9. Updates metrics and activity tracking
```

## Onboarding and Integration Process

### 1. Slack App Installation

**OAuth 2.0 Flow**:

1. User visits `/slack/install` endpoint
2. System generates OAuth URL with:
   - Client ID
   - Required scopes
   - CSRF state token
   - Redirect URI
3. User authorizes app in Slack
4. Slack redirects to callback with auth code
5. System exchanges code for access token
6. Token stored in Redis with workspace metadata

### 2. WhatsApp Group Linking

#### **Step 1: Initiate from Slack**

1. User mentions bot in Slack channel: `@bot link whatsapp group`
2. Bot generates unique link code: `workspace-name#channel-name`
3. Creates pending link entry in Redis (10-minute expiration)
4. Responds with instructions to send code from WhatsApp

#### **Step 2: Complete from WhatsApp**

1. User sends link code to WhatsApp group with bot
2. Webhook service detects link code pattern
3. LinkEstablishmentService validates:
   - Code format is correct
   - Pending link exists and not expired
   - Group not already linked
4. Creates bidirectional mapping in Redis
5. Sends confirmation to both platforms

### 3. Link Code System

**Format**: `workspace-name#channel-name`

**Normalization Rules**:

- Convert to lowercase
- Replace spaces/special chars with dashes
- Remove leading/trailing dashes
- Collapse multiple dashes to single

**Detection**:

- LinkCodeDetector scans incoming WhatsApp messages
- Extracts potential codes using regex patterns
- Validates against pending links

## Data Storage and Persistence

### Redis Schema

**Group Mappings**:

```bash
mapping:group:{whatsapp_group_id}
  - slack_channel_id
  - slack_channel_name
  - whatsapp_group_name
  - slack_team_id
  - slack_team_name
  - timeout (seconds)
  - created_at
  - created_by
```

**Thread Management**:

```bash
group:thread:{whatsapp_group_id}
  - Slack thread timestamp

group:last_activity:{whatsapp_group_id}
  - Unix timestamp of last message
```

**Deduplication**:

```bash
message:sent:{message_id}
  - Flag with TTL to prevent duplicates
```

**OAuth Tokens**:

```bash
oauth:token:{team_id}
  - Access token
  - Bot user ID
  - Team name
  - Installation metadata
```

**Pending Links**:

```bash
onboarding:pending:{link_code}
  - channel_id
  - team_id
  - user_id
  - expires_at
```

## Security Features

### 1. Authentication & Authorization

- Slack request signature verification
- Optional GREEN-API authentication headers
- OAuth 2.0 for Slack workspace access
- State parameter for CSRF protection

### 2. Rate Limiting

- Per-IP rate limits for webhook endpoints
- Circuit breaker for external API calls
- Request size validation
- Timeout controls for long-running operations

### 3. Input Validation

- Message text sanitization
- SQL injection prevention
- XSS protection in web dashboard
- Path traversal prevention

### 4. IP Intelligence (Optional)

- Geographic location tracking
- VPN/proxy detection
- Threat intelligence integration
- Configurable blocking rules

## Multi-Workspace Support

### Architecture

- **Per-Workspace Tokens**: Each Slack workspace has its own OAuth token
- **Token Manager**: Centralized service for token storage/retrieval
- **Workspace Identification**: Extract team_id from Slack events
- **Client Caching**: Maintains workspace-specific Slack clients

### Installation Flow

1. Each workspace installs app independently
2. OAuth flow generates workspace-specific token
3. Token stored with workspace metadata
4. Bot user ID cached per workspace
5. All operations use workspace-specific credentials

## Configuration Management

### Environment Variables

**Required**:

- `GREEN_API_INSTANCE`: WhatsApp API instance ID
- `GREEN_API_TOKEN`: WhatsApp API authentication
- `SLACK_CLIENT_ID`: Slack OAuth client ID
- `SLACK_CLIENT_SECRET`: Slack OAuth client secret
- `SLACK_SIGNING_SECRET`: Request signature verification
- `REDIS_URL`: Redis connection string

**Optional**:

- `BROADCAST_TIMEOUT`: Seconds before broadcasting to channel (default: 1800)
- `SSL_ENABLED`: Enable HTTPS (default: true)
- `DASHBOARD_ENABLED`: Enable web dashboard (default: true)
- `APP_PORT`: Application port (default: 8000)

### Message Formatting

- Configurable prefixes for platform identification
- Template support for thread starters
- Unicode emoji support
- Mention preservation and formatting

## Operational Features

### 1. Health Monitoring

**Endpoints**:

- `/health`: Overall system health
- `/health/webhook`: Webhook service status
- `/health/slack`: Slack Events service status
- `/health/worker`: Message Worker status

**Checks**:

- Redis connectivity
- GREEN-API availability
- Slack API responsiveness
- Worker processing status

### 2. Metrics Collection

**Tracked Metrics**:

- Messages processed (by direction)
- Processing latency
- Error rates by type
- Active threads/groups
- API call success rates

**Endpoints**:

- `/metrics`: Prometheus-compatible metrics
- `/monitoring/status`: Detailed status page
- `/api/metrics`: JSON metrics API

### 3. Dashboard

**Features**:

- Real-time message statistics
- Active group/thread monitoring
- Error log visualization
- System health indicators
- Configuration display

## Error Handling

### Retry Strategies

1. **Exponential Backoff**: For transient API failures
2. **Circuit Breaker**: Prevents cascade failures
3. **Dead Letter Queue**: For persistent failures
4. **Graceful Degradation**: Continues operation with reduced functionality

### Error Types

- **Retryable**: Network timeouts, rate limits, temporary API errors
- **Non-Retryable**: Invalid credentials, malformed data, permission errors
- **Critical**: Redis connection loss, configuration errors

## Performance Characteristics

### Scalability

- **Horizontal Scaling**: Components can run multiple instances
- **Async Processing**: Non-blocking I/O for high concurrency
- **Connection Pooling**: Efficient resource utilization
- **Message Batching**: Bulk operations where supported

### Optimization

- **Redis Pub/Sub**: Minimal latency message routing
- **Caching**: User names, channel info, thread associations
- **Compression**: Gzip middleware for HTTP responses
- **Static File Caching**: Long-term caching for assets

## Deployment Architecture

### Unified Deployment (Recommended)

```bash
./start.sh  # or python run_unified.py
```

Starts all services in single process:

- Webhook handler (port 8000)
- Slack Events handler
- Message Worker (background task)
- Dashboard (if enabled)

### Component Separation (Legacy)

Individual services can run separately for scaling:

- Webhook Service: High availability for incoming messages
- Worker: Scale based on message volume
- Slack Events: Dedicated instance for Slack traffic

## Future Enhancements

### Planned Features

1. **Media Support**: Images, documents, videos
2. **Message Editing**: Sync edits between platforms
3. **Message Deletion**: Bidirectional deletion sync
4. **User Profiles**: Rich user information display
5. **Message Search**: Historical message search
6. **Analytics Dashboard**: Advanced metrics and insights

### Architecture Evolution

1. **Message Queue**: Consider RabbitMQ/Kafka for larger scale
2. **Database**: PostgreSQL for message history
3. **Caching Layer**: Dedicated Redis cluster
4. **Load Balancing**: HAProxy/NGINX for distribution
5. **Container Orchestration**: Kubernetes deployment

## Conclusion

ChatterBridge provides a robust, scalable solution for bridirectional messaging between WhatsApp and Slack. The pub-sub architecture ensures loose coupling and high availability, while the comprehensive onboarding system makes integration straightforward for end users. Security features, monitoring capabilities, and multi-workspace support make it suitable for enterprise deployment.
