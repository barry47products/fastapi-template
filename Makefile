# FastAPI Template - Modern Development Makefile
# Using Ruff + MyPy for all quality checks

.PHONY: help install format lint typecheck test test-watch test-cov test-fast test-unit test-integration test-behaviour test-security test-smoke quality quick fix clean pr run run-test run-prod

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
RED := \033[0;31m
RESET := \033[0m

help: ## Show this help message
	@echo "$(CYAN)Available commands:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-15s$(RESET) %s\n", $$1, $$2}'

install: ## Install dependencies with Poetry
	@echo "$(CYAN)Installing dependencies...$(RESET)"
	poetry install --with dev
	poetry run pre-commit install
	@echo "$(GREEN)✓ Dependencies installed$(RESET)"

# Formatting and Linting
format: ## Format code with Ruff (auto-fix)
	@echo "$(CYAN)Formatting code...$(RESET)"
	poetry run ruff format .
	poetry run ruff check --fix .
	@echo "$(GREEN)✓ Code formatted$(RESET)"

lint: ## Check code with Ruff (no auto-fix)
	@echo "$(CYAN)Linting code...$(RESET)"
	poetry run ruff format --check .
	poetry run ruff check .
	@echo "$(GREEN)✓ Linting passed$(RESET)"

typecheck: ## Type check with MyPy
	@echo "$(CYAN)Type checking...$(RESET)"
	poetry run mypy .
	@echo "$(GREEN)✓ Type checking passed$(RESET)"

# Testing
test: ## Run tests (fast, no coverage)
	@echo "$(CYAN)Running tests...$(RESET)"
	poetry run pytest -xvs
	@echo "$(GREEN)✓ Tests passed$(RESET)"

test-watch: ## Run tests in watch mode (auto-rerun on file changes)
	@echo "$(CYAN)Starting test watcher...$(RESET)"
	@echo "$(GREEN)Tests will auto-run when files change. Press Ctrl+C to stop.$(RESET)"
	poetry run ptw tests src --runner "poetry run pytest --tb=short -v"

test-cov: ## Run tests with coverage report
	@echo "$(CYAN)Running tests with coverage...$(RESET)"
	poetry run pytest --cov=src --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✓ Coverage report generated$(RESET)"

test-fast: ## Run fast tests only (excludes slow markers)
	@echo "$(CYAN)Running fast tests...$(RESET)"
	poetry run pytest -m "fast and not slow" -xvs
	@echo "$(GREEN)✓ Fast tests passed$(RESET)"

test-unit: ## Run unit tests only
	@echo "$(CYAN)Running unit tests...$(RESET)"
	poetry run pytest -m "unit" -xvs
	@echo "$(GREEN)✓ Unit tests passed$(RESET)"

test-integration: ## Run integration tests only
	@echo "$(CYAN)Running integration tests...$(RESET)"
	poetry run pytest -m "integration" -xvs
	@echo "$(GREEN)✓ Integration tests passed$(RESET)"

test-behaviour: ## Run behaviour-driven tests
	@echo "$(CYAN)Running behaviour tests...$(RESET)"
	poetry run pytest -m "behaviour" -xvs
	@echo "$(GREEN)✓ Behaviour tests passed$(RESET)"

test-security: ## Run security tests
	@echo "$(CYAN)Running security tests...$(RESET)"
	poetry run pytest -m "security" -xvs
	@echo "$(GREEN)✓ Security tests passed$(RESET)"

test-smoke: ## Run smoke tests only
	@echo "$(CYAN)Running smoke tests...$(RESET)"
	poetry run pytest -m "smoke" -xvs
	@echo "$(GREEN)✓ Smoke tests passed$(RESET)"

# Combined commands
quality: ## Run all quality checks (lint + typecheck + test)
	@echo "$(CYAN)Running all quality checks...$(RESET)"
	@$(MAKE) lint
	@$(MAKE) typecheck
	@$(MAKE) test
	@echo "$(GREEN)✓ All quality checks passed$(RESET)"

quick: ## Quick quality check (format + fast test)
	@echo "$(CYAN)Quick check...$(RESET)"
	@$(MAKE) format
	@$(MAKE) test-fast
	@echo "$(GREEN)✓ Quick check complete$(RESET)"

fix: ## Fix all auto-fixable issues
	@echo "$(CYAN)Fixing issues...$(RESET)"
	poetry run ruff format .
	poetry run ruff check --fix --unsafe-fixes .
	@echo "$(GREEN)✓ Fixed all auto-fixable issues$(RESET)"

pr: ## Prepare for pull request (format + quality)
	@echo "$(CYAN)Preparing for PR...$(RESET)"
	@$(MAKE) format
	@$(MAKE) quality
	@echo "$(GREEN)✓ Ready for pull request$(RESET)"

# Application
run: ## Start development server with local config
	ENV_FILE=.env.local poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

run-test: ## Start development server with test config
	ENV_FILE=.env.test poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8001

run-prod: ## Start production server (no reload)
	poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000

# Utility commands
clean: ## Clean up generated files
	@echo "$(CYAN)Cleaning up...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	@echo "$(GREEN)✓ Cleanup complete$(RESET)"

watch: ## Watch for changes and run tests
	poetry run ptw -- -xvs