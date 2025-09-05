# Neighbour Approved - behaviour-Driven Testing Makefile
# Streamlined commands for behaviour-focused development

.PHONY: help install test test-cov test-fast lint run firestore-up firestore-down clean

# Default target
help: ## Show available make targets
	@echo "Neighbour Approved - Development Commands"
	@echo "========================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development Setup
install: ## Install dependencies with Poetry
	poetry install

# Testing - Behaviour Focused
test: ## Run behaviour tests (fast, no coverage)
	poetry run pytest

test-cov: ## Run tests with coverage when needed
	poetry run pytest --cov=src --cov-report=term-missing

test-fast: ## Run non-slow tests only
	poetry run pytest -m "not slow"

# Code Quality
lint: ## Check and fix code with ruff
	poetry run ruff check --fix src/ config/ tests/
	poetry run ruff format src/ config/ tests/

typecheck: ## Type check with mypy
	poetry run mypy src/ config/

# Application
run: ## Start development server with local config
	ENV_FILE=.env.local poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

run-test: ## Start development server with test config
	ENV_FILE=.env.test poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8001

run-prod: ## Start production server (no reload)
	poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000

# Firestore Emulator (Essential for testing)
firestore-up: ## Start Firestore emulator
	@echo "Starting Firestore emulator..."
	docker-compose -f docker-compose.dev.yml up -d firestore-emulator
	@echo "Waiting for Firestore emulator to be ready..."
	@timeout 60 bash -c 'until curl -s http://localhost:8080 > /dev/null; do sleep 2; done' || echo "Warning: Emulator may not be ready yet"
	@echo "✅ Firestore emulator running at http://localhost:8080"

firestore-down: ## Stop Firestore emulator
	docker-compose -f docker-compose.dev.yml down

# Cleanup
clean: ## Clean up build artifacts and cache
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	@echo "✅ Cleanup complete"