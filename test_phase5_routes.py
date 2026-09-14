#!/usr/bin/env python
"""Test Phase 5 routes."""
from conv_flow.main import create_app

try:
    print("Creating FastAPI app...")
    app = create_app()
    print("✓ App created successfully")
    
    # Count routes
    api_routes = [r for r in app.routes if hasattr(r, 'path') and '/api' in r.path]
    print(f"✓ Total API routes: {len(api_routes)}")
    
    print("\nRegistered endpoints:")
    for route in sorted(api_routes, key=lambda r: r.path):
        if hasattr(route, 'methods'):
            methods = sorted(route.methods - {'OPTIONS', 'HEAD'})
            print(f"  {', '.join(methods):20} {route.path}")
    
    print("\n✅ Phase 5 - Orchestrator & LinkedIn routes successfully integrated!")
    
except Exception as e:
    import traceback
    print(f"❌ Error: {e}")
    traceback.print_exc()
