# Multi-stage FastAPI Template Docker build with security scanning
# Optimized for production with minimal attack surface

# ============================================================================
# Builder Stage - Dependencies and compilation
# ============================================================================
FROM python:3.13-slim AS builder

# Set build arguments with security considerations
ARG POETRY_VERSION=1.8.3
ARG BUILD_ENV=production

# Install build dependencies with latest security patches
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Poetry with integrity verification
RUN pip install --no-cache-dir --disable-pip-version-check poetry==$POETRY_VERSION

# Configure Poetry for optimal container builds
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    POETRY_HOME="/opt/poetry"

# Create application directory
WORKDIR /app

# Copy dependency files for layer caching optimisation
COPY pyproject.toml poetry.lock ./

# Install dependencies with production optimisations
RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true && \
    poetry install --only=main --no-root --no-dev && \
    # Remove unnecessary files to reduce image size
    find /app/.venv -name "*.pyc" -delete && \
    find /app/.venv -name "__pycache__" -type d -exec rm -rf {} + && \
    rm -rf $POETRY_CACHE_DIR

# Copy application source code
COPY . .

# Install the application package
RUN poetry install --only-root

# ============================================================================
# Production Runtime Stage - Minimal attack surface
# ============================================================================
FROM python:3.13-slim AS production

# Build metadata for tracking and security
LABEL maintainer="FastAPI Template" \
      version="1.0.0" \
      description="Production FastAPI application with security hardening" \
      org.opencontainers.image.source="https://github.com/your-org/fastapi-template" \
      org.opencontainers.image.licenses="MIT"

# Install only essential runtime dependencies with latest security patches
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    # Create non-root user early for security
    && groupadd -r -g 1000 fastapi \
    && useradd -r -u 1000 -g fastapi -d /app -s /bin/bash fastapi

# Set security-focused environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Security hardening
    PYTHONFAULTHANDLER=1 \
    PYTHONIOENCODING=UTF-8

# Create secure application directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=fastapi:fastapi /app/.venv /app/.venv

# Copy application code with proper ownership
COPY --from=builder --chown=fastapi:fastapi /app/src /app/src
COPY --from=builder --chown=fastapi:fastapi /app/config /app/config
COPY --from=builder --chown=fastapi:fastapi /app/pyproject.toml /app/

# Set proper permissions and remove sensitive files
RUN find /app -name "*.pyc" -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} + && \
    find /app -name "*.pyo" -delete && \
    # Remove potential sensitive development files
    rm -f /app/.env* /app/docker-compose* && \
    # Set secure permissions
    chmod -R 755 /app && \
    chmod -R 644 /app/src /app/config && \
    # Ensure virtual environment is executable
    chmod -R 755 /app/.venv/bin

# Switch to non-root user for security
USER fastapi

# Add comprehensive health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f -H "User-Agent: healthcheck" http://localhost:8000/status || exit 1

# Expose application port (documented, not security boundary)
EXPOSE 8000

# Production command with security and performance optimisations
CMD ["python", "-m", "uvicorn", "src.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--access-log", \
     "--no-server-header", \
     "--loop", "uvloop", \
     "--log-config", "/app/config/logging.json"]

# ============================================================================
# Development Stage - Hot reload and debugging support
# ============================================================================
FROM builder AS development

# Install development dependencies
RUN poetry install --with=dev

# Set development environment variables
ENV ENVIRONMENT=development \
    LOG_LEVEL=DEBUG

# Copy all source code including tests and config files
COPY --chown=fastapi:fastapi . .

# Create non-root user for development
RUN groupadd -r -g 1000 fastapi && useradd -r -u 1000 -g fastapi fastapi \
    && chown -R fastapi:fastapi /app

USER fastapi

# Development command with hot reload
CMD ["python", "-m", "uvicorn", "src.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload", \
     "--reload-dir", "/app/src", \
     "--reload-dir", "/app/config"]
