#!/bin/bash

# Start Docker services for development

set -e

echo "Starting Docker services..."
docker-compose up -d postgres redis firestore

echo "Waiting for services to be ready..."
sleep 5

# Check service health
docker-compose ps

echo ""
echo "Services are starting up. They will be available at:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - Firestore Emulator: localhost:8080"
echo ""
echo "To view logs: docker-compose logs -f [service_name]"
echo "To stop services: docker-compose down"
