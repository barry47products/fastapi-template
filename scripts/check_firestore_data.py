#!/usr/bin/env python3
"""Quick script to check what data is in the Firestore emulator."""

import os

from google.cloud import firestore

# Set up environment for emulator
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
os.environ["GOOGLE_CLOUD_PROJECT"] = "neighbour-approved-dev"

# Initialize Firestore client
db = firestore.Client(project="neighbour-approved-dev")

print("🔍 Checking Firestore emulator data...")
print("=" * 50)

# Check providers collection
print("\n📊 PROVIDERS COLLECTION:")
providers_ref = db.collection("providers")
providers = list(providers_ref.stream())
print(f"Total providers: {len(providers)}")

for i, provider in enumerate(providers, 1):
    data = provider.to_dict()
    print(f"\n{i}. Provider ID: {provider.id}")
    print(f"   Name: {data.get('name', 'N/A')}")
    print(f"   Phone: {data.get('phone', 'N/A')}")
    print(f"   Category: {data.get('category', 'N/A')}")
    print(f"   Endorsements: {data.get('endorsement_count', 0)}")
    print(f"   Created: {data.get('created_at', 'N/A')}")

# Check endorsements collection
print("\n📊 ENDORSEMENTS COLLECTION:")
endorsements_ref = db.collection("endorsements")
endorsements = list(endorsements_ref.stream())
print(f"Total endorsements: {len(endorsements)}")

for i, endorsement in enumerate(endorsements, 1):
    data = endorsement.to_dict()
    print(f"\n{i}. Endorsement ID: {endorsement.id}")
    print(f"   Group ID: {data.get('group_id', 'N/A')}")
    print(f"   Provider ID: {data.get('provider_id', 'N/A')}")
    print(f"   Confidence: {data.get('confidence', 'N/A')}")
    print(f"   Mention: {data.get('mention_text', 'N/A')}")
    print(f"   Created: {data.get('created_at', 'N/A')}")

print("\n" + "=" * 50)
print("✅ Firestore data check complete!")
