#!/bin/bash
# Test GitHub Environments Setup
# Validates that environments are properly configured

set -euo pipefail

# Colors for output
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

# Test GitHub CLI availability
test_gh_cli() {
    log_info "Checking GitHub CLI availability..."

    if ! command -v gh >/dev/null 2>&1; then
        log_error "GitHub CLI (gh) is not installed"
        log_info "Install with: brew install gh"
        exit 1
    fi

    if ! gh auth status >/dev/null 2>&1; then
        log_error "GitHub CLI is not authenticated"
        log_info "Run: gh auth login"
        exit 1
    fi

    log_success "GitHub CLI is available and authenticated"
}

# Test repository access
test_repo_access() {
    log_info "Testing repository access..."

    if gh repo view >/dev/null 2>&1; then
        repo_name=$(gh repo view --json nameWithOwner -q .nameWithOwner)
        log_success "Repository access confirmed: $repo_name"
    else
        log_error "Cannot access repository"
        exit 1
    fi
}

# Test environment creation
test_environments() {
    log_info "Testing environment setup..."

    # Note: GitHub CLI doesn't have direct environment commands yet
    # We'll test by trying to run a workflow that uses environments

    log_warning "Environment testing requires manual verification"
    log_info "Please check the following in GitHub web interface:"
    echo "  1. Go to Settings → Environments"
    echo "  2. Verify 'staging' environment exists"
    echo "  3. Verify 'production' environment exists"
    echo "  4. Check that secrets are configured in each environment"
}

# Test workflow files
test_workflows() {
    log_info "Testing workflow configuration..."

    local workflows=(
        ".github/workflows/ci.yml"
        ".github/workflows/deploy.yml"
        ".github/workflows/environment-setup.yml"
        ".github/workflows/monitoring.yml"
        ".github/workflows/security-scan.yml"
    )

    for workflow in "${workflows[@]}"; do
        if [[ -f "$workflow" ]]; then
            log_success "Workflow exists: $workflow"
        else
            log_warning "Workflow missing: $workflow"
        fi
    done
}

# Test Docker configuration
test_docker_config() {
    log_info "Testing Docker configuration..."

    local docker_files=(
        "deployment/Dockerfile"
        "deployment/docker-compose.yml"
        "deployment/docker-compose.prod.yml"
        "deployment/docker-compose.staging.yml"
        "deployment/dockerignore"
    )

    for file in "${docker_files[@]}"; do
        if [[ -f "$file" ]]; then
            log_success "Docker file exists: $file"
        else
            log_warning "Docker file missing: $file"
        fi
    done

    # Test docker-compose syntax
    if command -v docker-compose >/dev/null 2>&1; then
        if docker-compose -f deployment/docker-compose.yml config >/dev/null 2>&1; then
            log_success "Docker Compose configuration is valid"
        else
            log_error "Docker Compose configuration has errors"
        fi
    else
        log_warning "Docker Compose not available for testing"
    fi
}

# Generate setup summary
generate_summary() {
    log_info "Environment Setup Summary"
    echo ""
    echo "✅ Next Steps:"
    echo "  1. Create GitHub environments (staging, production)"
    echo "  2. Add required secrets to each environment"
    echo "  3. Configure deployment protection rules"
    echo "  4. Test deployment workflow"
    echo ""
    echo "🔗 Useful Links:"
    echo "  - Repository Settings: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/settings"
    echo "  - Environments: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/settings/environments"
    echo "  - Actions: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/actions"
    echo ""
    echo "📚 Documentation:"
    echo "  - Deployment Setup: docs/deployment-setup.md"
    echo "  - Docker Guide: DOCKER.md"
}

# Main test execution
main() {
    log_info "Starting GitHub environment setup test"
    echo ""

    test_gh_cli
    test_repo_access
    test_workflows
    test_docker_config
    test_environments

    echo ""
    generate_summary

    log_success "Environment setup test completed!"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
