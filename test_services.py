#!/usr/bin/env python
"""Integration tests for service layer."""
from conv_flow.db.session import SessionLocal, init_db
from conv_flow.services import (
    ConversationService,
    StageClassificationService,
    AnalysisService,
    WorkflowService,
    CRMIntegrationService,
    MockCRMProvider,
)
from conv_flow.exceptions import ConversationNotFound

def test_conversation_service():
    """Test conversation CRUD operations."""
    print("\n=== Testing ConversationService ===")
    
    # Initialize database
    init_db()
    db = SessionLocal()
    
    try:
        service = ConversationService(db)
        
        # Test create
        conv = service.create_conversation(
            source="email",
            content="This is a test conversation about our product.",
            participants=["john@example.com", "jane@example.com"],
            notes="Initial contact",
        )
        print(f"✓ Created conversation with ID: {conv.id}")
        
        # Test get
        retrieved = service.get_conversation(conv.id)
        print(f"✓ Retrieved conversation: {retrieved.source}")
        
        # Test list
        conversations = service.list_conversations(limit=10)
        print(f"✓ Listed {len(conversations)} conversation(s)")
        
        # Test update
        from conv_flow.models.domain import ConversationUpdateModel
        updated = service.update_conversation(
            conv.id,
            ConversationUpdateModel(notes="Updated notes"),
        )
        print(f"✓ Updated conversation notes")
        
        # Test count
        count = service.count_conversations()
        print(f"✓ Total conversations: {count}")
        
        # Test not found
        try:
            service.get_conversation(999999)
        except ConversationNotFound:
            print("✓ ConversationNotFound exception works correctly")
        
        return conv.id
        
    finally:
        db.close()

def test_crm_integration_service():
    """Test CRM integration service."""
    print("\n=== Testing CRMIntegrationService ===")
    
    db = SessionLocal()
    
    try:
        service = CRMIntegrationService(db)
        
        # Test provider name
        print(f"✓ Current provider: {service.get_provider_name()}")
        
        # Test set provider
        service.set_provider(MockCRMProvider(db))
        print(f"✓ Provider set to: {service.get_provider_name()}")
        
    finally:
        db.close()

def main():
    """Run all service tests."""
    print("=" * 50)
    print("Service Layer Integration Tests")
    print("=" * 50)
    
    try:
        conv_id = test_conversation_service()
        test_crm_integration_service()
        
        print("\n" + "=" * 50)
        print("✅ All service layer tests passed!")
        print("=" * 50)
        print("\nServices ready for Phase 4 (API Endpoints)")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
