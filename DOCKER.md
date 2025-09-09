# Docker Deployment Guide

This FastAPI template includes comprehensive Docker support for both development and production deployments.

## Quick Start

### Development with Docker Compose

```bash
# Start all services (API, PostgreSQL, Redis, Firestore)
docker-compose up

# Start with optional tools (pgAdmin, Redis Commander)
docker-compose --profile tools up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Production Docker Build

```bash
# Build production image
docker build -t fastapi-template .

# Run production container
docker run -p 8000:8000 \
  -e APP_NAME=fastapi-template \
  -e ENVIRONMENT=production \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  fastapi-template
```

## Docker Architecture

### Multi-Stage Dockerfile

Our production Dockerfile uses a multi-stage build for optimal security and image size:

- **Builder Stage**: Installs Poetry and dependencies in a virtual environment
- **Runtime Stage**: Minimal production image with only runtime dependencies
- **Security**: Non-root user, minimal attack surface
- **Health Checks**: Built-in health monitoring for container orchestration

### Image Optimization Features

- ✅ **Multi-stage build** - Reduces final image size by ~60%
- ✅ **Layer caching** - Dependencies installed before code copy
- ✅ **Non-root user** - Security best practices
- ✅ **Health checks** - Container orchestration support
- ✅ **Optimized runtime** - uvloop for better performance

## Development Environment

The `docker-compose.yml` provides a complete development environment:

### Services Included

| Service | Port | Description |
|---------|------|-------------|
| **api** | 8000 | FastAPI application with hot reload |
| **postgres** | 5432 | PostgreSQL 17 database |
| **redis** | 6379 | Redis cache |
| **firestore** | 8080 | Google Firestore emulator |
| **pgadmin** | 5050 | PostgreSQL admin interface (optional) |
| **redis-commander** | 8081 | Redis admin interface (optional) |

### Environment Variables

```bash
# Application
APP_NAME=fastapi-template
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000

# Database  
DATABASE_URL=postgresql://fastapi_user:fastapi_pass@postgres:5432/fastapi_db
DATABASE_TYPE=postgresql

# Cache
REDIS_URL=redis://redis:6379/0

# Security (change in production!)
INTERNAL_API_KEYS=dev-key-12345
WEBHOOK_SECRET=dev-webhook-secret-67890
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

## Production Deployment

### Environment-Specific Builds

```bash
# Development build with debugging
docker build --target runtime --build-arg POETRY_VERSION=1.8.3 -t fastapi-template:dev .

# Production build (default)
docker build -t fastapi-template:latest .
```

### Container Orchestration

The Docker image is ready for deployment to:

- **Kubernetes** - Includes health checks and graceful shutdown
- **Docker Swarm** - Supports service scaling and rolling updates
- **AWS ECS/Fargate** - Optimized for cloud container services
- **Google Cloud Run** - Compatible with serverless containers
- **Azure Container Instances** - Ready for Azure deployment

### Production Example

```yaml
# docker-compose.prod.yml
version: '3.9'
services:
  api:
    image: fastapi-template:latest
    ports:
      - "80:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - INTERNAL_API_KEYS=${API_KEYS}
      - WEBHOOK_SECRET=${WEBHOOK_SECRET}
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Advanced Usage

### Custom Commands

```bash
# Run tests in container
docker run --rm -v $(pwd):/app fastapi-template:dev poetry run pytest

# Interactive shell
docker run --rm -it -v $(pwd):/app fastapi-template:dev bash

# Database migrations (when implemented)
docker run --rm --env-file .env fastapi-template:latest python -m alembic upgrade head
```

### Performance Tuning

#### Production Optimization

```bash
# Multi-worker deployment
docker run -p 8000:8000 \
  -e WEB_CONCURRENCY=4 \
  -e MAX_WORKERS=4 \
  fastapi-template:latest \
  gunicorn src.main:app -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 --workers 4
```

#### Memory and CPU Limits

```yaml
services:
  api:
    image: fastapi-template:latest
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

## Troubleshooting

### Common Issues

**Build fails with Poetry errors:**

```bash
# Clear Docker build cache
docker builder prune

# Build with verbose output
docker build --progress=plain --no-cache .
```

**Container exits immediately:**

```bash
# Check logs
docker logs fastapi-template-api

# Run with interactive shell
docker run --rm -it fastapi-template:latest bash
```

**Health check fails:**

```bash
# Check if health endpoint is accessible
docker exec fastapi-template-api curl -f http://localhost:8000/health/

# Verify environment variables
docker exec fastapi-template-api env | grep API
```

**Database connection issues:**

```bash
# Check PostgreSQL connection
docker exec fastapi-template-api pg_isready -h postgres -p 5432

# Verify network connectivity
docker network inspect fastapi-template_default
```

### Development Tips

```bash
# Hot reload development
docker-compose up api  # Only start API with hot reload

# Run specific services
docker-compose up postgres redis  # Only databases

# Clean restart
docker-compose down -v  # Remove volumes
docker-compose up --build  # Rebuild images
```

## Security Considerations

### Production Checklist

- [ ] Change default database passwords
- [ ] Use secure API keys and webhook secrets
- [ ] Enable TLS/HTTPS termination
- [ ] Configure proper CORS origins
- [ ] Set up log aggregation
- [ ] Monitor resource usage
- [ ] Regular security updates

### Secrets Management

```bash
# Use Docker secrets (Swarm) or Kubernetes secrets
echo "super-secure-api-key" | docker secret create api_key -

# Or use external secret management
export DATABASE_URL=$(vault kv get -field=url secret/database)
```

This Docker setup provides a production-ready foundation for deploying your FastAPI application anywhere containers are supported.
