#!/usr/bin/env python
"""Test API approval workflow."""
from fastapi.testclient import TestClient
from conv_flow.main import app
from conv_flow.db.session import SessionLocal
from conv_flow.services import WorkflowService

def test_approval_workflow():
    """Test action approval/rejection workflow."""
    client = TestClient(app)
    db = SessionLocal()

    print("=" * 50)
    print("Testing Approval Workflow")
    print("=" * 50)

    # Create a conversation
    print("\n1. Creating conversation...")
    response = client.post("/api/conversations", json={
        "source": "email",
        "content": "Test conversation for approval workflow",
        "participants": ["user@example.com"],
    })
    conv_id = response.json().get("id")
    print(f"✓ Created conversation {conv_id}")

    # Create mock actions directly in database (simulate LLM suggestion)
    print("\n2. Creating mock workflow actions...")
    service = WorkflowService(db)
    from conv_flow.db.models import WorkflowActionORM
    from conv_flow.models.domain import WorkflowActionTypeEnum, WorkflowActionStatusEnum
    from datetime import datetime

    action = WorkflowActionORM(
        conversation_id=conv_id,
        action_type=WorkflowActionTypeEnum.FOLLOW_UP,
        description="Follow up with customer",
        suggested_date=datetime.now(),
        priority="high",
        status=WorkflowActionStatusEnum.PENDING,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    action_id = action.id
    print(f"✓ Created action {action_id} with status: PENDING")

    # Test approval endpoint
    print(f"\n3. Approving action {action_id}...")
    response = client.post(f"/api/conversations/actions/{action_id}/approve", json={
        "reviewed_by": "john.doe",
        "notes": "Looks good, proceed with follow-up",
    })
    print(f"✓ Approval endpoint: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  - Action status: {data.get('status')}")
    else:
        print(f"  - Error: {response.json()}")

    # Create another action for rejection test
    print("\n4. Creating another action for rejection test...")
    action2 = WorkflowActionORM(
        conversation_id=conv_id,
        action_type=WorkflowActionTypeEnum.SCHEDULE_CALL,
        description="Schedule call with customer",
        priority="medium",
        status=WorkflowActionStatusEnum.PENDING,
    )
    db.add(action2)
    db.commit()
    db.refresh(action2)
    action2_id = action2.id
    print(f"✓ Created action {action2_id} with status: PENDING")

    # Test rejection endpoint
    print(f"\n5. Rejecting action {action2_id}...")
    response = client.post(f"/api/conversations/actions/{action2_id}/reject", json={
        "reviewed_by": "jane.smith",
        "notes": "This action is not aligned with strategy",
    })
    print(f"✓ Rejection endpoint: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  - Action status: {data.get('status')}")
    else:
        print(f"  - Error: {response.json()}")

    # List pending actions (should be none now)
    print("\n6. Listing pending actions...")
    response = client.get("/api/conversations/actions/pending")
    pending = response.json()
    print(f"✓ Pending actions: {len(pending)}")

    # List all actions for conversation
    print(f"\n7. Listing all actions for conversation {conv_id}...")
    response = client.get(f"/api/conversations/{conv_id}/actions")
    actions = response.json()
    print(f"✓ Total actions: {len(actions)}")
    for action_data in actions:
        print(f"  - Action {action_data['id']}: {action_data['status']}")

    db.close()

    print("\n" + "=" * 50)
    print("✅ Approval workflow test complete!")
    print("=" * 50)

if __name__ == "__main__":
    test_approval_workflow()
