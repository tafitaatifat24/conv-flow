#!/usr/bin/env python
"""Test Phase 5 routes - detailed debug."""
from conv_flow.main import create_app

try:
    print("Creating FastAPI app...")
    app = create_app()
    print("✓ App created successfully")
    
    print(f"\nTotal routes in app: {len(app.routes)}")
    
    print("\nAll routes:")
    for i, route in enumerate(app.routes):
        print(f"  {i}: {route} - {type(route)}")
        if hasattr(route, 'path'):
            print(f"     path: {route.path}")
        if hasattr(route, 'methods'):
            print(f"     methods: {route.methods}")
    
except Exception as e:
    import traceback
    print(f"❌ Error: {e}")
    traceback.print_exc()
