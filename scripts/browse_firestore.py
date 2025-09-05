#!/usr/bin/env python3
"""Simple Firestore browser for your emulator."""

import os
import sys

from google.cloud import firestore

# Set emulator host
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"


def main() -> None:
    """Browse Firestore emulator data."""
    try:
        # Initialize client
        db = firestore.Client(project="neighbour-approved-dev")

        print("🔥 Firestore Emulator Data Browser")
        print("=" * 50)

        # List collections with document counts
        collections = ["endorsements", "providers", "_health_checks"]

        for collection_name in collections:
            print(f"\n📁 Collection: {collection_name}")
            print("-" * 30)

            try:
                collection_ref = db.collection(collection_name)
                docs = list(collection_ref.limit(10).stream())

                if docs:
                    print(f"Found {len(docs)} documents:")
                    for i, doc in enumerate(docs, 1):
                        print(f"\n  {i}. Document ID: {doc.id}")
                        data = doc.to_dict()
                        for key, value in list(data.items())[:3]:  # Show first 3 fields
                            if isinstance(value, str) and len(value) > 40:
                                value = value[:40] + "..."
                            print(f"     {key}: {value}")
                        if len(data) > 3:
                            print(f"     ... and {len(data) - 3} more fields")
                else:
                    print("  (no documents found)")

            except Exception as e:
                print(f"  Error: {e}")

        print("\n🌐 Emulator running at: localhost:8080")
        print("📊 Project: neighbour-approved-dev")

    except Exception as e:
        print(f"❌ Failed to connect to Firestore emulator: {e}")
        print("Make sure the emulator is running: make firestore-up")
        sys.exit(1)


if __name__ == "__main__":
    main()
