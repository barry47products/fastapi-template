#!/usr/bin/env python3
"""Demo queries to show Firestore capabilities with your live data."""

import os

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Set emulator host
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"


def demo_queries() -> None:
    """Demonstrate various Firestore query patterns."""
    db = firestore.Client(project="neighbour-approved-dev")

    print("🔍 Firestore Query Demonstrations")
    print("=" * 50)

    # 1. Simple collection query
    print("\n1️⃣ All Providers:")
    print("-" * 20)
    providers = db.collection("providers").limit(5).stream()
    for provider in providers:
        data = provider.to_dict()
        print(f"  📋 {data.get('category', 'Unknown')} - {data.get('phone', 'No phone')}")

    # 2. Filter by category
    print("\n2️⃣ Filter: Plumbers Only:")
    print("-" * 25)
    plumbers = (
        db.collection("providers").where(filter=FieldFilter("category", "==", "plumber")).stream()
    )
    for plumber in plumbers:
        data = plumber.to_dict()
        tags = data.get("tags", {})
        emergency = tags.get("emergency", "unknown")
        print(f"  🔧 {data.get('phone')} (Emergency: {emergency})")

    # 3. Filter endorsements by status
    print("\n3️⃣ Filter: Active Endorsements:")
    print("-" * 28)
    active_endorsements = (
        db.collection("endorsements").where(filter=FieldFilter("status", "==", "ACTIVE")).stream()
    )
    for endorsement in active_endorsements:
        data = endorsement.to_dict()
        confidence = data.get("confidence_score", 0)
        etype = data.get("endorsement_type", "Unknown")
        print(f"  ⭐ {etype} endorsement (confidence: {confidence})")

    # 4. Range query - high confidence endorsements
    print("\n4️⃣ Range Query: High Confidence (>0.8):")
    print("-" * 35)
    high_confidence = (
        db.collection("endorsements")
        .where(filter=FieldFilter("confidence_score", ">=", 0.8))
        .stream()
    )
    for endorsement in high_confidence:
        data = endorsement.to_dict()
        confidence = data.get("confidence_score", 0)
        message = data.get("message_context", "")[:40] + "..."
        print(f"  🎯 {confidence} - {message}")

    # 5. Complex tag query
    print("\n5️⃣ Tag Query: Licensed Providers:")
    print("-" * 32)
    licensed = (
        db.collection("providers").where(filter=FieldFilter("tags.licensed", "==", "yes")).stream()
    )
    for provider in licensed:
        data = provider.to_dict()
        category = data.get("category", "Unknown")
        phone = data.get("phone", "No phone")
        print(f"  ✅ Licensed {category}: {phone}")

    # 6. Count documents (manual)
    print("\n6️⃣ Document Counts:")
    print("-" * 18)
    collections = ["providers", "endorsements", "_health_checks"]
    for collection_name in collections:
        docs = list(db.collection(collection_name).stream())
        print(f"  📊 {collection_name}: {len(docs)} documents")

    print("\n🌐 All queries ran against: localhost:8080")
    print("📋 Project: neighbour-approved-dev")


if __name__ == "__main__":
    demo_queries()
