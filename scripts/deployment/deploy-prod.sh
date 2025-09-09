#!/bin/bash
# Production Deployment Script for FastAPI Template
# Handles Docker secrets, image pull, and service orchestration

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"
ENV_FILE="${PROJECT_ROOT}/.env.prod"

# Colours for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check environment file
    if [[ ! -f "${ENV_FILE}" ]]; then
        log_error "Production environment file not found: ${ENV_FILE}"
        log_info "Create ${ENV_FILE} based on .env.example"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Create Docker secrets
create_secrets() {
    log_info "Creating Docker secrets..."

    # Load environment variables
    set -a
    source "${ENV_FILE}"
    set +a

    # Create secrets if they don't exist
    secrets=(
        "database_url:postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-fastapi_prod}"
        "redis_url:redis://:${REDIS_PASSWORD}@redis:6379"
        "redis_password:${REDIS_PASSWORD}"
        "postgres_user:postgres"
        "postgres_password:${POSTGRES_PASSWORD}"
        "api_keys:${INTERNAL_API_KEYS}"
        "webhook_secret:${WEBHOOK_SECRET}"
        "grafana_user:admin"
        "grafana_password:${GRAFANA_PASSWORD:-admin123}"
    )

    for secret in "${secrets[@]}"; do
        secret_name="${secret%%:*}"
        secret_value="${secret#*:}"

        if ! docker secret inspect "${secret_name}" >/dev/null 2>&1; then
            echo -n "${secret_value}" | docker secret create "${secret_name}" -
            log_success "Created secret: ${secret_name}"
        else
            log_warning "Secret already exists: ${secret_name}"
        fi
    done
}

# Pull latest images
pull_images() {
    log_info "Pulling latest Docker images..."

    cd "${PROJECT_ROOT}"
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" pull

    log_success "Images pulled successfully"
}

# Deploy services
deploy_services() {
    log_info "Deploying services..."

    cd "${PROJECT_ROOT}"

    # Deploy with production configuration
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d

    log_success "Services deployed successfully"
}

# Health check
health_check() {
    log_info "Performing health checks..."

    local max_attempts=30
    local attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f -s "http://localhost:8000/status" >/dev/null 2>&1; then
            log_success "FastAPI service is healthy"
            return 0
        fi

        attempt=$((attempt + 1))
        log_info "Health check attempt ${attempt}/${max_attempts}..."
        sleep 10
    done

    log_error "Health check failed after ${max_attempts} attempts"
    return 1
}

# Show deployment status
show_status() {
    log_info "Deployment status:"

    cd "${PROJECT_ROOT}"
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps

    echo ""
    log_info "Service URLs:"
    echo "  FastAPI:    http://localhost:8000"
    echo "  Prometheus: http://localhost:9091"
    echo "  Grafana:    http://localhost:3000 (if enabled)"
}

# Main deployment flow
main() {
    log_info "Starting production deployment..."

    check_prerequisites
    create_secrets
    pull_images
    deploy_services

    if health_check; then
        show_status
        log_success "Production deployment completed successfully!"
    else
        log_error "Deployment completed but health check failed"
        exit 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
