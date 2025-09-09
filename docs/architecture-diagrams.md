# Architecture Diagrams

Visual guide to the FastAPI template's architecture, request flows, and deployment patterns.

> **Note**: All diagrams are also available as individual Mermaid files in the [`docs/diagrams/`](./diagrams/) directory for easy integration into presentations, documentation tools, and IDEs that support Mermaid rendering.

## System Overview

```mermaid
--8<-- "docs/diagrams/system-overview.mmd"
```

[📄 View Source: system-overview.mmd](./diagrams/system-overview.mmd)

**Key Principles:**

- **Domain Layer**: Pure business logic, no dependencies
- **Application Layer**: Orchestration and use cases
- **Infrastructure Layer**: External concerns (DB, APIs, metrics)
- **Interface Layer**: HTTP handling and serialization

## Request Flow Architecture

```mermaid
--8<-- "docs/diagrams/request-flow.mmd"
```

[📄 View Source: request-flow.mmd](./diagrams/request-flow.mmd)

**Flow Highlights:**

1. **Authentication** happens at the API boundary
2. **Business logic** is pure and testable in the domain
3. **Domain events** handle cross-cutting concerns
4. **Repository pattern** abstracts data persistence
5. **Structured responses** maintain API consistency

## Database Architecture Options

### PostgreSQL Configuration

```mermaid
--8<-- "docs/diagrams/database-postgresql.mmd"
```

[📄 View Source: database-postgresql.mmd](./diagrams/database-postgresql.mmd)

### Firestore Configuration

```mermaid
--8<-- "docs/diagrams/database-firestore.mmd"
```

[📄 View Source: database-firestore.mmd](./diagrams/database-firestore.mmd)

### Multi-Database Setup

```mermaid
--8<-- "docs/diagrams/database-multi.mmd"
```

[📄 View Source: database-multi.mmd](./diagrams/database-multi.mmd)

## Clean Architecture Layers

```mermaid
--8<-- "docs/diagrams/clean-architecture.mmd"
```

[📄 View Source: clean-architecture.mmd](./diagrams/clean-architecture.mmd)

**Dependency Rules:**

- **Inward pointing**: Outer layers depend on inner layers
- **Interface segregation**: Each layer defines its own interfaces
- **Dependency inversion**: Concrete implementations injected from outside

## Deployment Architecture

### Development Environment

```mermaid
--8<-- "docs/diagrams/deployment-development.mmd"
```

[📄 View Source: deployment-development.mmd](./diagrams/deployment-development.mmd)

### Production Deployment

```mermaid
--8<-- "docs/diagrams/deployment-production.mmd"
```

[📄 View Source: deployment-production.mmd](./diagrams/deployment-production.mmd)

### Container Architecture

```mermaid
--8<-- "docs/diagrams/container-architecture.mmd"
```

[📄 View Source: container-architecture.mmd](./diagrams/container-architecture.mmd)

## Event-Driven Architecture

```mermaid
--8<-- "docs/diagrams/event-driven-architecture.mmd"
```

[📄 View Source: event-driven-architecture.mmd](./diagrams/event-driven-architecture.mmd)

**Benefits:**

- **Decoupling**: Domain logic separated from infrastructure concerns
- **Extensibility**: Easy to add new event handlers
- **Testing**: Events can be captured and verified in tests
- **Observability**: Automatic metrics and logging through events

## Security Architecture

```mermaid
--8<-- "docs/diagrams/security-architecture.mmd"
```

[📄 View Source: security-architecture.mmd](./diagrams/security-architecture.mmd)

**Security Features:**

- **API Key Authentication**: Multiple key support with different permissions
- **Rate Limiting**: Configurable per-endpoint limits
- **Input Validation**: Pydantic model validation
- **CORS Configuration**: Controlled cross-origin access
- **Security Headers**: HSTS, CSP, X-Frame-Options
- **Request Sanitization**: SQL injection and XSS prevention

## Testing Architecture

```mermaid
--8<-- "docs/diagrams/testing-architecture.mmd"
```

[📄 View Source: testing-architecture.mmd](./diagrams/testing-architecture.mmd)

**Testing Strategy:**

- **Unit Tests**: Fast, isolated, no external dependencies
- **Integration Tests**: Real database and service interactions
- **Contract Tests**: API specification compliance
- **Behaviour Tests**: End-to-end user scenarios

## Monitoring & Observability

```mermaid
--8<-- "docs/diagrams/monitoring-observability.mmd"
```

[📄 View Source: monitoring-observability.mmd](./diagrams/monitoring-observability.mmd)

**Observability Stack:**

- **Metrics**: Prometheus-compatible metrics with business KPIs
- **Logging**: Structured JSON logs with correlation IDs
- **Health Checks**: Liveness and readiness probes
- **Tracing**: Request correlation and performance tracking

## Using These Diagrams

### In Documentation Tools

Most documentation tools support including Mermaid files directly:

**MkDocs Material:**

```markdown
```mermaid
--8<-- "docs/diagrams/system-overview.mmd"
```

**GitBook:**

```markdown
{% embed url="./diagrams/system-overview.mmd" %}
```

**Notion:**
Import the `.mmd` files directly into Notion pages.

### In IDEs and Editors

**VS Code:** Install the "Mermaid Preview" extension to render diagrams inline.

**JetBrains IDEs:** Use the "Mermaid" plugin for syntax highlighting and preview.

**GitHub/GitLab:** Mermaid diagrams render automatically in markdown files.

### In Presentations

**Marp:** Include diagrams directly in slide presentations.

**Reveal.js:** Use the Mermaid plugin to embed interactive diagrams.

**PowerPoint/Keynote:** Export diagrams as SVG or PNG from Mermaid Live Editor.

---

These diagrams provide a comprehensive view of the template's architecture. Use them to understand the system design, plan your customizations, and communicate architecture decisions with your team.
