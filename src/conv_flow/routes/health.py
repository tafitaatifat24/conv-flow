"""Health check route handlers."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Status and version information
    """
    from conv_flow.config import settings
    
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/status")
async def status():
    """
    Application status endpoint.
    
    Returns:
        dict: Detailed status information
    """
    from conv_flow.config import settings
    
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "llm_provider": settings.llm_provider,
    }
