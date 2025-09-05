# Neighbour Approved

**The Gratitude Engine for Local Services** - A WhatsApp-based service endorsement platform where good work gets recognised, remembered, and rewarded.

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/poetry-managed-blueviolet.svg)](https://python-poetry.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063.svg)](https://docs.pydantic.dev/)
[![Uvicorn](https://img.shields.io/badge/Uvicorn-0.35.0-2196F3.svg)](https://www.uvicorn.org/)

[![pytest](https://img.shields.io/badge/pytest-8.3.0-orange.svg)](https://pytest.org/)
[![Code Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://pytest.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/badge/linting-ruff-FCC624.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)

[![structlog](https://img.shields.io/badge/logging-structlog-orange.svg)](https://www.structlog.org/)
[![Prometheus](https://img.shields.io/badge/metrics-prometheus-E6522C.svg)](https://prometheus.io/)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen.svg)](https://pre-commit.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

WhatsApp-based local service endorsement platform that captures and organises community recommendations.

## Overview

Neighbour Approved transforms WhatsApp neighbourhood groups into intelligent recommendation engines. When neighbours mention service providers, we capture these as endorsements, creating a permanent, searchable record of community trust.

## Development Approach

- **Test-Driven Development (TDD)**: Red-Green-Refactor cycle
- **Flow-Based Development**: WIP limit of 1 - complete one module entirely before starting the next
- **100% Test Coverage**: No exceptions
- **Type Safety**: Full type annotations with Python 3.13

## Tech Stack

- Python 3.13
- FastAPI
- Pydantic
- Poetry for dependency management
- Firestore for persistence
- GREEN-API for WhatsApp integration

## Getting Started

### Prerequisites

- Python 3.13+
- Poetry package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/neighbour-approved.git
cd neighbour-approved

# Install dependencies
poetry install
```

### VSCode Setup

After installation, configure VSCode to use the Poetry environment:

1. **Find your Poetry environment path**:

   ```bash
   poetry env info --path
   ```

2. **Select Python Interpreter in VSCode**:
   - Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
   - Type "Python: Select Interpreter"
   - Choose the Poetry environment path from step 1

3. **Reload VSCode** if needed:
   - Press `Cmd+Shift+P` / `Ctrl+Shift+P`
   - Type "Developer: Reload Window"

### Running the Application

```bash
# Start development server
poetry run uvicorn src.main:app --reload

# Or use the built-in development server
poetry run python -m src.main

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=src --cov-report=term-missing
