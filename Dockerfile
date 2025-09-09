# FastAPI Template - Single-stage Docker build for development and production
# Optimized for reliability and ease of use

FROM python:3.13-slim

# Set build arguments
ARG POETRY_VERSION=1.8.3

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Poetry with specific version for reproducibility
RUN pip install --no-cache-dir poetry==$POETRY_VERSION

# Configure Poetry for container environment
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml poetry.lock ./

# Install dependencies and create virtual environment
RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true && \
    poetry install --only=main --no-root && \
    rm -rf $POETRY_CACHE_DIR

# Copy application source code
COPY . .

# Create non-root user for security
RUN groupadd -r fastapi && useradd -r -g fastapi fastapi \
    && chown -R fastapi:fastapi /app

# Switch to non-root user
USER fastapi

# Add health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose application port
EXPOSE 8000

# Production command with optimized settings
CMD ["python", "-m", "uvicorn", "src.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--access-log", \
     "--loop", "uvloop"]
