#!/usr/bin/env python3
"""Seed Firestore emulator with test data for IDE exploration."""

import os
import uuid
from datetime import datetime, UTC

from google.cloud import firestore

# Set emulator host
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"


def main() -> None:
    """Seed Firestore with test data."""
    db = firestore.Client(project="neighbour-approved-dev")

    print("🌱 Seeding Firestore Emulator with Test Data")
    print("=" * 50)

    # Create test providers
    providers_data = [
        {
            "_id": str(uuid.uuid4()),
            "phone": "+12345678901",
            "category": "plumber",
            "tags": {"emergency": "true", "licensed": "yes", "experience": "5years"},
            "created_at": datetime.now(UTC).isoformat(),
        },
        {
            "_id": str(uuid.uuid4()),
            "phone": "+12345678902",
            "category": "electrician",
            "tags": {"licensed": "yes", "emergency": "false", "residential": "true"},
            "created_at": datetime.now(UTC).isoformat(),
        },
        {
            "_id": str(uuid.uuid4()),
            "phone": "+12345678903",
            "category": "cleaner",
            "tags": {"eco_friendly": "true", "weekly": "available"},
            "created_at": datetime.now(UTC).isoformat(),
        },
    ]

    # Create test endorsements
    endorsements_data = [
        {
            "_id": str(uuid.uuid4()),
            "provider_id": providers_data[0]["_id"],
            "endorser_phone": "+19876543210",
            "group_id": "1234567890@g.us",
            "endorsement_type": "MANUAL",
            "status": "ACTIVE",
            "confidence_score": 0.95,
            "message_context": "Excellent plumber, fixed our leak quickly!",
            "created_at": datetime.now(UTC).isoformat(),
        },
        {
            "_id": str(uuid.uuid4()),
            "provider_id": providers_data[1]["_id"],
            "endorser_phone": "+19876543211",
            "group_id": "1234567890@g.us",
            "endorsement_type": "AUTOMATIC",
            "status": "ACTIVE",
            "confidence_score": 0.85,
            "message_context": "Great electrician work in my house",
            "created_at": datetime.now(UTC).isoformat(),
        },
        {
            "_id": str(uuid.uuid4()),
            "provider_id": providers_data[0]["_id"],
            "endorser_phone": "+19876543212",
            "group_id": "0987654321@g.us",
            "endorsement_type": "MANUAL",
            "status": "PENDING",
            "confidence_score": 0.78,
            "message_context": "Used this plumber before, good service",
            "created_at": datetime.now(UTC).isoformat(),
        },
    ]

    # Health check data
    health_data = [
        {
            "_id": str(uuid.uuid4()),
            "service": "firestore",
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "details": {"connection": "active", "latency_ms": 45},
        },
    ]

    # Seed providers
    print("\n📁 Seeding providers collection...")
    providers_ref = db.collection("providers")
    for provider in providers_data:
        doc_ref = providers_ref.document(provider["_id"])
        doc_ref.set(provider)
        print(f"  ✅ Created provider: {provider['category']} ({provider['phone']})")

    # Seed endorsements
    print("\n📁 Seeding endorsements collection...")
    endorsements_ref = db.collection("endorsements")
    for endorsement in endorsements_data:
        doc_ref = endorsements_ref.document(endorsement["_id"])
        doc_ref.set(endorsement)
        print(
            f"  ✅ Created endorsement: {endorsement['endorsement_type']} (confidence: {endorsement['confidence_score']})",
        )

    # Seed health checks
    print("\n📁 Seeding _health_checks collection...")
    health_ref = db.collection("_health_checks")
    for health in health_data:
        doc_ref = health_ref.document(health["_id"])
        doc_ref.set(health)
        print(f"  ✅ Created health check: {health['service']}")

    print("\n🎉 Seeding Complete!")
    print("Created:")
    print(f"  - {len(providers_data)} providers")
    print(f"  - {len(endorsements_data)} endorsements")
    print(f"  - {len(health_data)} health checks")
    print("\n🔍 View data with: make firestore-browse")


if __name__ == "__main__":
    main()
