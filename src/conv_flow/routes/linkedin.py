"""LinkedIn integration API endpoints."""
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from conv_flow.db.session import get_db
from conv_flow.config import settings
from conv_flow.services.linkedin_sync import LinkedInSyncService
from conv_flow.models.domain import ConversationModel

router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])


class LinkedInCookiesRequest(BaseModel):
    """Request model for LinkedIn session cookies."""
    user_id: str  # LinkedIn profile ID
    cookies: dict  # Session cookies dict
    email: Optional[str] = None


class LinkedInAuthResponse(BaseModel):
    """Response model for LinkedIn auth."""
    status: str  # "authenticated", "stored", etc.
    user_id: str
    message: str


class LinkedInSyncResponse(BaseModel):
    """Response model for sync operation."""
    status: str
    synced_conversations: int
    conversations: list[ConversationModel]


@router.post("/auth", response_model=LinkedInAuthResponse)
def store_linkedin_auth(
    request: LinkedInCookiesRequest,
    db: Session = Depends(get_db),
):
    """
    Store LinkedIn session cookies from user's manual login.
    
    Steps for user:
    1. Open LinkedIn in browser
    2. Log in manually
    3. Open browser DevTools → Application tab
    4. Copy all cookies from linkedin.com
    5. Send cookies dict here along with their user_id
    
    Args:
        request: LinkedInCookiesRequest with cookies dict
        db: Database session
    
    Returns:
        Authentication confirmation
    """
    if not settings.linkedin_enabled:
        raise HTTPException(
            status_code=403,
            detail="LinkedIn integration is not enabled",
        )
    
    if not request.cookies or not request.user_id:
        raise HTTPException(
            status_code=400,
            detail="Both user_id and cookies are required",
        )
    
    service = LinkedInSyncService(db)
    
    try:
        auth = service.add_or_update_auth(
            user_id=request.user_id,
            session_cookies=request.cookies,
            email=request.email,
        )
        
        return LinkedInAuthResponse(
            status="authenticated",
            user_id=auth.user_id,
            message=f"LinkedIn cookies stored for user {auth.user_id}",
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store LinkedIn auth: {str(e)}",
        )


@router.post("/sync/{user_id}", response_model=LinkedInSyncResponse)
def sync_linkedin_conversations(
    user_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """
    Sync LinkedIn conversations for a user.
    
    Fetches recent conversations and messages, stores as conversations.
    
    Args:
        user_id: LinkedIn user ID
        limit: Max conversations to fetch (default: 20)
        db: Database session
    
    Returns:
        Sync result with stored conversations
    """
    if not settings.linkedin_enabled:
        raise HTTPException(
            status_code=403,
            detail="LinkedIn integration is not enabled",
        )
    
    service = LinkedInSyncService(db)
    
    try:
        # Check if auth exists
        auth = service.get_auth(user_id)
        if not auth:
            raise HTTPException(
                status_code=404,
                detail=f"No LinkedIn auth found for user {user_id}. Please authenticate first.",
            )
        
        # Sync conversations
        conversations = service.sync_conversations(user_id, limit=limit)
        
        return LinkedInSyncResponse(
            status="success",
            synced_conversations=len(conversations),
            conversations=conversations,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LinkedIn sync failed: {str(e)}",
        )


@router.post("/logout/{user_id}")
def logout_linkedin_user(
    user_id: str,
    db: Session = Depends(get_db),
):
    """
    Log out a LinkedIn user (deactivate their stored cookies).
    
    Args:
        user_id: LinkedIn user ID
        db: Database session
    
    Returns:
        Logout confirmation
    """
    if not settings.linkedin_enabled:
        raise HTTPException(
            status_code=403,
            detail="LinkedIn integration is not enabled",
        )
    
    service = LinkedInSyncService(db)
    
    try:
        service.deactivate_auth(user_id)
        
        return {
            "status": "logged_out",
            "user_id": user_id,
            "message": "LinkedIn auth deactivated",
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to logout: {str(e)}",
        )


@router.get("/auth-status/{user_id}")
def check_linkedin_auth_status(
    user_id: str,
    db: Session = Depends(get_db),
):
    """
    Check if a user has active LinkedIn authentication.
    
    Args:
        user_id: LinkedIn user ID
        db: Database session
    
    Returns:
        Auth status
    """
    if not settings.linkedin_enabled:
        raise HTTPException(
            status_code=403,
            detail="LinkedIn integration is not enabled",
        )
    
    service = LinkedInSyncService(db)
    auth = service.get_auth(user_id)
    
    if not auth:
        return {
            "user_id": user_id,
            "authenticated": False,
            "message": "No authentication found",
        }
    
    return {
        "user_id": user_id,
        "authenticated": auth.is_active,
        "last_sync": auth.last_sync,
        "profile_name": auth.profile_name,
        "message": "Authenticated and active" if auth.is_active else "Auth exists but inactive",
    }
