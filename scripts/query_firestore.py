#!/usr/bin/env python3
"""
Simple script to query your Firestore emulator.
This acts as a basic "IDE" for browsing Firestore data.
"""

import os

from google.cloud import firestore

# Set emulator host
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"


def main():
    """Interactive Firestore browser."""
    # Initialize client
    db = firestore.Client(project="neighbour-approved-dev")

    print("🔥 Firestore Emulator Browser")
    print("=" * 40)

    # List collections
    print("\n📁 Available Collections:")
    collections = ["endorsements", "providers", "_health_checks"]

    for i, collection_name in enumerate(collections, 1):
        try:
            collection_ref = db.collection(collection_name)
            docs = list(collection_ref.limit(5).stream())
            count = len(docs)
            print(f"  {i}. {collection_name} ({count} documents shown)")
        except Exception as e:
            print(f"  {i}. {collection_name} (error: {e})")

    # Interactive query
    while True:
        print("\n🔍 Query Options:")
        print("  1. Browse endorsements")
        print("  2. Browse providers")
        print("  3. Browse health checks")
        print("  4. Custom query")
        print("  5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == "1":
            browse_collection(db, "endorsements")
        elif choice == "2":
            browse_collection(db, "providers")
        elif choice == "3":
            browse_collection(db, "_health_checks")
        elif choice == "4":
            custom_query(db)
        elif choice == "5":
            break
        else:
            print("Invalid choice!")


def browse_collection(db, collection_name):
    """Browse documents in a collection."""
    print(f"\n📄 Browsing {collection_name}:")
    print("-" * 40)

    try:
        collection_ref = db.collection(collection_name)
        docs = collection_ref.limit(10).stream()

        for i, doc in enumerate(docs, 1):
            print(f"\n{i}. Document ID: {doc.id}")
            data = doc.to_dict()
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                print(f"   {key}: {value}")

    except Exception as e:
        print(f"Error browsing collection: {e}")


def custom_query(db):
    """Run custom queries."""
    collection_name = input("Enter collection name: ").strip()
    field_name = input("Enter field name to filter by (or press Enter to skip): ").strip()

    try:
        collection_ref = db.collection(collection_name)

        if field_name:
            field_value = input(f"Enter value for {field_name}: ").strip()
            query = collection_ref.where(field_name, "==", field_value)
        else:
            query = collection_ref

        docs = query.limit(5).stream()

        print("\n📄 Query Results:")
        print("-" * 40)

        for i, doc in enumerate(docs, 1):
            print(f"\n{i}. Document ID: {doc.id}")
            data = doc.to_dict()
            for key, value in data.items():
                print(f"   {key}: {value}")

    except Exception as e:
        print(f"Error running query: {e}")


if __name__ == "__main__":
    main()
