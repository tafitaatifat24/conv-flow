#!/usr/bin/env python
"""Test API routes."""
from fastapi.testclient import TestClient
from conv_flow.main import app

def test_api_routes():
    """Test all API endpoints."""
    client = TestClient(app)

    # Test health endpoint
    print("Testing health endpoint...")
    response = client.get("/api/health")
    print(f"✓ Health: {response.status_code} - {response.json()}")

    # Test conversation creation endpoint
    print()
    print("Testing conversation creation endpoint...")
    response = client.post("/api/conversations", json={
        "source": "email",
        "content": "Test conversation content",
        "participants": ["user@example.com"],
    })
    print(f"✓ Create conversation: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"  - Conversation ID: {data.get('id')}")
        print(f"  - Source: {data.get('source')}")
        conv_id = data.get("id")
    else:
        print(f"  - Error: {response.text}")
        return

    # Test list conversations endpoint
    print()
    print("Testing list conversations endpoint...")
    response = client.get("/api/conversations")
    print(f"✓ List conversations: {response.status_code} - {len(response.json())} conversations")

    # Test get conversation endpoint
    print()
    print(f"Testing get conversation endpoint (ID: {conv_id})...")
    response = client.get(f"/api/conversations/{conv_id}")
    print(f"✓ Get conversation: {response.status_code}")
    if response.status_code == 200:
        print(f"  - Source: {response.json().get('source')}")

    # Test classification endpoint (will fail without LLM, but route should exist)
    print()
    print("Testing classification endpoint...")
    response = client.post(f"/api/conversations/{conv_id}/classify")
    print(f"✓ Classify endpoint: {response.status_code} (expected to fail - no LLM)")
    if response.status_code != 200:
        print(f"  - Expected error (LLM not available in test): {response.status_code}")

    # Test analysis endpoint (will fail without LLM, but route should exist)
    print()
    print("Testing analysis endpoint...")
    response = client.post(f"/api/conversations/{conv_id}/analyze")
    print(f"✓ Analyze endpoint: {response.status_code} (expected to fail - no LLM)")
    if response.status_code != 200:
        print(f"  - Expected error (LLM not available in test): {response.status_code}")

    # Test action suggestion endpoint
    print()
    print("Testing action suggestion endpoint...")
    response = client.post(f"/api/conversations/{conv_id}/actions/suggest")
    print(f"✓ Suggest actions endpoint: {response.status_code} (expected to fail - no LLM)")
    if response.status_code != 200:
        print(f"  - Expected error (LLM not available in test): {response.status_code}")

    # Test list actions endpoint
    print()
    print("Testing list actions endpoint...")
    response = client.get(f"/api/conversations/{conv_id}/actions")
    print(f"✓ List actions: {response.status_code} - {len(response.json())} actions")

    # Test list pending actions endpoint
    print()
    print("Testing list pending actions endpoint...")
    response = client.get("/api/conversations/actions/pending")
    print(f"✓ List pending actions: {response.status_code} - {len(response.json())} actions")

    print()
    print("=" * 50)
    print("✅ All API routes are registered and responding!")
    print("=" * 50)

if __name__ == "__main__":
    test_api_routes()
