# Neighbour Approved: Security & Monitoring Strategy

## Security Architecture Overview

### Defence in Depth Strategy

```bash
Internet → WAF → Load Balancer → API Gateway → Application → Database
              ↓         ↓              ↓            ↓           ↓
         [Monitoring at Every Layer with Prometheus & Logs]
```

### Security Principles

1. **Zero Trust**: Verify everything, trust nothing
2. **Least Privilege**: Minimal permissions for all components
3. **Defence in Depth**: Multiple security layers
4. **Fail Secure**: Default to denying access
5. **Security by Design**: Built-in, not bolted-on

---

## API Security Implementation

### Multi-Layer Authentication

```python
# src/infrastructure/security/auth_layers.py
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException, Header, Depends

class AuthenticationLayers:
    """Multiple authentication mechanisms for different use cases."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._api_keys = set(settings.internal_api_keys.get_secret_value().split(','))
        self._jwt_secret = settings.jwt_secret.get_secret_value()

    async def verify_api_key(
        self,
        x_api_key: str = Header(..., description="API Key")
    ) -> str:
        """For webhook endpoints - simple API key."""
        if x_api_key not in self._api_keys:
            raise HTTPException(status_code=403, detail="Invalid API key")
        return x_api_key

    async def verify_jwt_token(
        self,
        authorization: str = Header(..., description="Bearer token")
    ) -> Dict[str, Any]:
        """For provider dashboard - JWT tokens."""
        try:
            token = authorization.replace("Bearer ", "")
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    async def verify_webhook_signature(
        self,
        x_webhook_signature: str = Header(...),
        body: bytes = Depends(get_body)
    ) -> bool:
        """For GREEN-API webhooks - HMAC signature."""
        expected = hmac.new(
            self._settings.webhook_secret.get_secret_value().encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(x_webhook_signature, expected):
            raise HTTPException(status_code=403, detail="Invalid signature")
        return True
```

### Request Validation & Sanitisation

```python
# src/infrastructure/security/request_validator.py
from typing import Any, Dict
import re
import bleach
from src.shared.exceptions import ValidationException

class RequestValidator:
    """Validates and sanitises all incoming data."""

    # Patterns that might indicate injection attempts
    SUSPICIOUS_PATTERNS = [
        r'<script',
        r'javascript:',
        r'on\w+\s*=',  # Event handlers
        r'union\s+select',  # SQL injection
        r'exec\s*\(',  # Command injection
        r'\$\{.*\}',  # Template injection
    ]

    def sanitise_text(self, text: str) -> str:
        """Remove any potentially harmful content."""
        # Check for suspicious patterns
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValidationException(f"Suspicious content detected")

        # Clean HTML/script tags
        cleaned = bleach.clean(text, tags=[], strip=True)

        # Limit length to prevent DoS
        if len(cleaned) > 1000:
            raise ValidationException("Text too long")

        return cleaned

    def validate_phone_number(self, phone: str) -> str:
        """Strict phone number validation."""
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)

        # Must be between 10 and 15 digits
        if not 10 <= len(digits) <= 15:
            raise ValidationException("Invalid phone number length")

        # Must not start with 0
        if digits.startswith('0'):
            raise ValidationException("Invalid phone number format")

        return f"+{digits}"

    def validate_group_id(self, group_id: str) -> str:
        """WhatsApp group ID validation."""
        pattern = r'^[\w-]+@g\.us$'
        if not re.match(pattern, group_id):
            raise ValidationException("Invalid group ID format")
        return group_id
```

---

## Threat Modelling & Mitigation

### Identified Threats

| Threat                 | Impact | Likelihood | Mitigation                                              |
| ---------------------- | ------ | ---------- | ------------------------------------------------------- |
| API Key Compromise     | High   | Medium     | Rotate keys regularly, monitor usage patterns           |
| WhatsApp Account Ban   | High   | Low        | Strict rate limiting, compliance with WhatsApp policies |
| Fake Endorsements      | Medium | Medium     | Velocity checks, group member verification              |
| Data Breach            | High   | Low        | Encryption at rest, minimal data storage                |
| DDoS Attack            | Medium | Medium     | Rate limiting, CDN, auto-scaling                        |
| Injection Attacks      | High   | Low        | Input validation, parameterised queries                 |
| Provider Impersonation | Medium | Medium     | Phone number verification, claim process                |

### Security Controls

```python
# src/infrastructure/security/threat_monitor.py
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

class ThreatMonitor:
    """Monitors for suspicious patterns and potential attacks."""

    def __init__(self, alerting_service: AlertingService):
        self._alerting = alerting_service
        self._endorsement_velocity: Dict[str, List[datetime]] = defaultdict(list)
        self._failed_auth_attempts: Dict[str, int] = defaultdict(int)

    async def check_endorsement_velocity(
        self,
        provider_id: str,
        group_id: str
    ) -> bool:
        """Detect abnormal endorsement patterns."""
        now = datetime.utcnow()
        key = f"{provider_id}:{group_id}"

        # Track endorsements in sliding window
        self._endorsement_velocity[key].append(now)

        # Keep only last hour
        cutoff = now - timedelta(hours=1)
        self._endorsement_velocity[key] = [
            t for t in self._endorsement_velocity[key] if t > cutoff
        ]

        # Alert if more than 5 endorsements per hour from same group
        if len(self._endorsement_velocity[key]) > 5:
            await self._alerting.send_alert(
                severity="HIGH",
                title="Suspicious endorsement velocity",
                details={
                    "provider_id": provider_id,
                    "group_id": group_id,
                    "count": len(self._endorsement_velocity[key])
                }
            )
            return False

        return True

    async def track_failed_auth(self, identifier: str) -> None:
        """Track failed authentication attempts."""
        self._failed_auth_attempts[identifier] += 1

        # Alert after 5 failed attempts
        if self._failed_auth_attempts[identifier] >= 5:
            await self._alerting.send_alert(
                severity="MEDIUM",
                title="Multiple failed auth attempts",
                details={"identifier": identifier}
            )
```

---

## Monitoring & Observability

### Metrics Architecture

```python
# src/infrastructure/observability/metrics_registry.py
from prometheus_client import Counter, Histogram, Gauge, Summary
from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class MetricDefinition:
    name: str
    description: str
    metric_type: str
    labels: tuple

class MetricsRegistry:
    """Central registry for all application metrics."""

    # Business Metrics
    MESSAGES_PROCESSED = MetricDefinition(
        name="messages_processed_total",
        description="Total WhatsApp messages processed",
        metric_type="counter",
        labels=("group_id", "message_type", "status")
    )

    ENDORSEMENTS_CREATED = MetricDefinition(
        name="endorsements_created_total",
        description="Total endorsements created",
        metric_type="counter",
        labels=("provider_category", "source")
    )

    SUMMARIES_SENT = MetricDefinition(
        name="summaries_sent_total",
        description="Summaries sent to groups",
        metric_type="counter",
        labels=("group_id", "provider_count")
    )

    EMOJI_REACTIONS = MetricDefinition(
        name="emoji_reactions_total",
        description="Emoji reactions received",
        metric_type="counter",
        labels=("group_id", "emoji_type")
    )

    # Performance Metrics
    API_LATENCY = MetricDefinition(
        name="api_request_duration_seconds",
        description="API request latency",
        metric_type="histogram",
        labels=("method", "endpoint", "status_code")
    )

    MESSAGE_PROCESSING_TIME = MetricDefinition(
        name="message_processing_duration_seconds",
        description="Time to process WhatsApp messages",
        metric_type="histogram",
        labels=("operation", "status")
    )

    DATABASE_QUERY_TIME = MetricDefinition(
        name="database_query_duration_seconds",
        description="Database query execution time",
        metric_type="histogram",
        labels=("operation", "collection")
    )

    # System Metrics
    ACTIVE_GROUPS = MetricDefinition(
        name="active_groups_total",
        description="Number of active WhatsApp groups",
        metric_type="gauge",
        labels=()
    )

    PROVIDERS_BY_STATUS = MetricDefinition(
        name="providers_total",
        description="Total providers by endorsement status",
        metric_type="gauge",
        labels=("status",)  # unendorsed, endorsed, legend
    )

    # Error Metrics
    ERRORS = MetricDefinition(
        name="errors_total",
        description="Total errors by type",
        metric_type="counter",
        labels=("error_type", "severity")
    )

    # Security Metrics
    AUTH_ATTEMPTS = MetricDefinition(
        name="auth_attempts_total",
        description="Authentication attempts",
        metric_type="counter",
        labels=("result", "method")
    )

    RATE_LIMIT_HITS = MetricDefinition(
        name="rate_limit_exceeded_total",
        description="Rate limit exceeded events",
        metric_type="counter",
        labels=("limit_type", "identifier")
    )
```

### Alerting Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: neighbour_approved_alerts
    interval: 30s
    rules:
      # Business Alerts
      - alert: LowEndorsementRate
        expr: rate(endorsements_created_total[1h]) < 0.1
        for: 2h
        labels:
          severity: warning
        annotations:
          summary: "Low endorsement creation rate"
          description: "Less than 0.1 endorsements per hour for 2 hours"

      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate above 5% for 5 minutes"

      # Performance Alerts
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, api_request_duration_seconds) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency"
          description: "95th percentile latency above 2 seconds"

      - alert: DatabaseSlowQueries
        expr: histogram_quantile(0.95, database_query_duration_seconds) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow database queries"
          description: "95th percentile query time above 1 second"

      # Security Alerts
      - alert: HighFailedAuthRate
        expr: rate(auth_attempts_total{result="failed"}[5m]) > 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High authentication failure rate"
          description: "More than 10 failed auth attempts per minute"

      - alert: RateLimitBreaches
        expr: rate(rate_limit_exceeded_total[5m]) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Frequent rate limit breaches"
          description: "Rate limits being hit frequently"

      # System Alerts
      - alert: WhatsAppWebhookDown
        expr: up{job="whatsapp_webhook"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "WhatsApp webhook endpoint down"
          description: "Webhook endpoint has been down for 1 minute"

      - alert: MemoryUsageHigh
        expr: process_resident_memory_bytes / 1024 / 1024 > 500
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Process using more than 500MB RAM"
```

### Logging Strategy

```python
# src/infrastructure/observability/logging_config.py
import structlog
from pythonjsonlogger import jsonlogger
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": jsonlogger.JsonFormatter,
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "rename_fields": {"asctime": "timestamp"},
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": "/var/log/neighbour-approved/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": "ERROR",
        }
    },
    "loggers": {
        "neighbour_approved": {
            "handlers": ["console", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["console"],
            "level": "INFO",
        }
    }
}

def configure_structured_logging(environment: str) -> structlog.BoundLogger:
    """Configure structured logging with appropriate processors."""

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    if environment == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()
```

### Dashboard Configuration

```python
# grafana/dashboards/neighbour_approved.json
{
  "dashboard": {
    "title": "Neighbour Approved Operations",
    "panels": [
      {
        "title": "Messages Processed",
        "targets": [{
          "expr": "rate(messages_processed_total[5m])"
        }]
      },
      {
        "title": "Endorsement Rate",
        "targets": [{
          "expr": "rate(endorsements_created_total[1h])"
        }]
      },
      {
        "title": "API Latency (p50, p95, p99)",
        "targets": [
          {"expr": "histogram_quantile(0.5, api_request_duration_seconds)"},
          {"expr": "histogram_quantile(0.95, api_request_duration_seconds)"},
          {"expr": "histogram_quantile(0.99, api_request_duration_seconds)"}
        ]
      },
      {
        "title": "Active Groups",
        "targets": [{
          "expr": "active_groups_total"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(errors_total[5m])"
        }]
      },
      {
        "title": "Provider Distribution",
        "targets": [{
          "expr": "providers_total"
        }]
      }
    ]
  }
}
```

---

## Incident Response Plan

### Severity Levels

| Level         | Response Time | Examples                                |
| ------------- | ------------- | --------------------------------------- |
| P1 - Critical | 15 minutes    | Service down, data breach, WhatsApp ban |
| P2 - High     | 1 hour        | Authentication broken, high error rate  |
| P3 - Medium   | 4 hours       | Performance degradation, feature broken |
| P4 - Low      | 24 hours      | Minor bugs, cosmetic issues             |

### Runbooks

```python
# src/infrastructure/observability/runbooks.py
from enum import Enum
from typing import Dict, List

class IncidentType(str, Enum):
    HIGH_ERROR_RATE = "high_error_rate"
    WHATSAPP_BAN = "whatsapp_ban"
    DATABASE_DOWN = "database_down"
    SECURITY_BREACH = "security_breach"

RUNBOOKS: Dict[IncidentType, List[str]] = {
    IncidentType.HIGH_ERROR_RATE: [
        "1. Check error logs for patterns",
        "2. Identify failing component",
        "3. Check recent deployments",
        "4. Consider rollback if deployment-related",
        "5. Scale up if load-related",
        "6. Apply hotfix if bug identified"
    ],
    IncidentType.WHATSAPP_BAN: [
        "1. Verify ban in GREEN-API dashboard",
        "2. Check for policy violations in recent messages",
        "3. Contact GREEN-API support",
        "4. Switch to backup WhatsApp number if available",
        "5. Notify affected groups via email",
        "6. Submit appeal to WhatsApp"
    ],
    IncidentType.DATABASE_DOWN: [
        "1. Check Firestore status page",
        "2. Verify network connectivity",
        "3. Check service account permissions",
        "4. Switch to backup region if configured",
        "5. Enable read-only mode",
        "6. Queue writes for replay"
    ],
    IncidentType.SECURITY_BREACH: [
        "1. Isolate affected components",
        "2. Rotate all API keys and secrets",
        "3. Audit recent access logs",
        "4. Identify breach vector",
        "5. Patch vulnerability",
        "6. Notify affected users per GDPR"
    ]
}
```

---

## Compliance & Audit

### Audit Logging

```python
# src/infrastructure/observability/audit_logger.py
from typing import Dict, Any, Optional
from datetime import datetime
import json

class AuditLogger:
    """Logs all security-relevant events for compliance."""

    def __init__(self, logger: structlog.BoundLogger):
        self._logger = logger.bind(log_type="audit")

    def log_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        result: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self._logger.info(
            "access_audit",
            user_id=user_id,
            resource=resource,
            action=action,
            result=result,
            metadata=metadata or {},
            timestamp=datetime.utcnow().isoformat()
        )

    def log_data_change(
        self,
        entity_type: str,
        entity_id: str,
        operation: str,
        old_value: Optional[Dict[str, Any]],
        new_value: Optional[Dict[str, Any]],
        changed_by: str
    ) -> None:
        self._logger.info(
            "data_audit",
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            timestamp=datetime.utcnow().isoformat()
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any]
    ) -> None:
        self._logger.warning(
            "security_audit",
            event_type=event_type,
            severity=severity,
            details=details,
            timestamp=datetime.utcnow().isoformat()
        )
```

### GDPR Compliance Monitoring

```python
# src/infrastructure/compliance/gdpr_monitor.py
class GDPRComplianceMonitor:
    """Ensures GDPR compliance for data operations."""

    def __init__(self, audit_logger: AuditLogger):
        self._audit = audit_logger
        self._consent_records: Dict[str, datetime] = {}

    async def record_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool
    ) -> None:
        """Record user consent for data processing."""
        self._audit.log_data_change(
            entity_type="consent",
            entity_id=user_id,
            operation="update",
            old_value={"granted": not granted},
            new_value={"granted": granted, "type": consent_type},
            changed_by=user_id
        )

        if granted:
            self._consent_records[f"{user_id}:{consent_type}"] = datetime.utcnow()

    async def handle_data_request(
        self,
        user_id: str,
        request_type: str  # "access", "portability", "deletion"
    ) -> Dict[str, Any]:
        """Handle GDPR data subject requests."""
        self._audit.log_access(
            user_id=user_id,
            resource="personal_data",
            action=request_type,
            result="initiated"
        )

        # Implementation depends on request type
        # Must complete within 30 days per GDPR

        return {
            "request_id": str(uuid.uuid4()),
            "status": "processing",
            "estimated_completion": datetime.utcnow() + timedelta(days=7)
        }
```

---

## Continuous Security Improvement

### Security Testing in CI/CD (Future Implementation)

```yaml
# .github/workflows/security.yml
# To be implemented after core modules are complete
name: Security Scanning

on:
  push:
    branches: [main, develop]
  schedule:
    - cron: "0 2 * * *" # Daily at 2 AM

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: "fs"
          scan-ref: "."
          format: "sarif"
          output: "trivy-results.sarif"

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: "trivy-results.sarif"

      - name: Run Bandit security linter
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit-report.json

      - name: OWASP Dependency Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: "neighbour-approved"
          path: "."
          format: "JSON"
```

### Local Security Testing (Use Now)

```bash
#!/bin/bash
# security-check.sh - Run security checks locally

echo "🔒 Running security checks..."

# Bandit for Python security issues
poetry run bandit -r src/

# Check for known vulnerabilities in dependencies
poetry run pip-audit

echo "✅ Security checks complete"
```

### Security Metrics Dashboard

Track security posture over time:

- Vulnerabilities by severity
- Time to patch metrics
- Authentication success/failure rates
- API key rotation frequency
- Compliance audit results
- Security training completion

---

## Notes

This comprehensive security and monitoring strategy ensures:

- **Complete visibility** into system behaviour
- **Proactive alerting** for issues
- **Security by design** at every layer
- **Compliance readiness** for GDPR and other regulations
- **Continuous improvement** through metrics and testing

Every action is logged, every metric is tracked, and every security control has monitoring in place. This allows you to detect, respond to, and prevent issues before they impact users.
