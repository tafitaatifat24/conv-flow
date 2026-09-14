"""FastAPI application factory and main entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from conv_flow.config import settings
from conv_flow.db.session import init_db
from conv_flow.routes import health, conversations, analysis, workflows, linkedin, orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan (startup and shutdown).
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    init_db()
    print("Database initialized")
    
    yield
    
    # Shutdown
    print(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Conversation to CRM workflow automation with LLM reasoning",
        debug=settings.debug,
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include route handlers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(conversations.router)
    app.include_router(analysis.router)
    app.include_router(workflows.router)
    app.include_router(orchestrator.router)
    app.include_router(linkedin.router)
    
    return app


app = create_app()
