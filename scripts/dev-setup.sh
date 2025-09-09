#!/bin/bash

# FastAPI Template - Development Environment Setup Script
# This script sets up the complete development environment with Docker services

set -e  # Exit on error

# Colours for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}FastAPI Template - Development Setup${NC}"
echo "======================================"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command_exists docker; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command_exists poetry; then
    echo -e "${RED}Poetry is not installed. Please install Poetry first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "\n${YELLOW}Creating .env file from .env.development...${NC}"
    cp .env.development .env
    echo -e "${GREEN}✓ .env file created${NC}"
else
    echo -e "\n${YELLOW}.env file already exists, skipping...${NC}"
fi

# Install Python dependencies
echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
poetry install --with postgres --with redis --with firestore
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Start Docker services
echo -e "\n${YELLOW}Starting Docker services...${NC}"
docker-compose up -d postgres redis firestore
echo -e "${GREEN}✓ Docker services started${NC}"

# Wait for services to be healthy
echo -e "\n${YELLOW}Waiting for services to be healthy...${NC}"
sleep 5

# Check PostgreSQL
until docker-compose exec -T postgres pg_isready -U fastapi_user -d fastapi_db > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}✓ PostgreSQL is ready${NC}"

# Check Redis
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "${GREEN}✓ Redis is ready${NC}"

# Check Firestore Emulator
until curl -f http://localhost:8080 > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "${GREEN}✓ Firestore Emulator is ready${NC}"

# Run tests to verify setup
echo -e "\n${YELLOW}Running tests to verify setup...${NC}"
poetry run pytest tests/unit/infrastructure/persistence/ -q --tb=no

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Development environment setup complete!${NC}"
    echo -e "\n${YELLOW}Services running:${NC}"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo "  - Firestore Emulator: localhost:8080"
    echo ""
    echo -e "${YELLOW}Optional management tools:${NC}"
    echo "  - pgAdmin: docker-compose --profile tools up pgadmin (http://localhost:5050)"
    echo "  - Redis Commander: docker-compose --profile tools up redis-commander (http://localhost:8081)"
    echo ""
    echo -e "${YELLOW}To start the FastAPI application:${NC}"
    echo "  make run"
    echo ""
    echo -e "${YELLOW}To stop Docker services:${NC}"
    echo "  docker-compose down"
else
    echo -e "\n${RED}⚠️  Some tests failed. Please check the output above.${NC}"
fi
