"""Workflow and action API endpoints."""
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from conv_flow.db.session import get_db
from conv_flow.exceptions import (
    ConversationNotFound,
    WorkflowActionNotFound,
    InvalidActionError,
    LLMProcessingError,
    CRMSyncError,
)
from conv_flow.models.domain import (
    WorkflowActionModel,
    WorkflowActionStatusEnum,
)
from conv_flow.services import (
    WorkflowService,
    CRMIntegrationService,
)

router = APIRouter(prefix="/api/conversations", tags=["workflows"])


class ApprovalRequest(BaseModel):
    """Request model for action approval/rejection."""
    reviewed_by: str
    notes: Optional[str] = None


class SyncRequest(BaseModel):
    """Request model for CRM sync."""
    action_id: int


@router.post("/{conversation_id}/actions/suggest", response_model=list[WorkflowActionModel])
def suggest_actions(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """Suggest workflow actions for a conversation."""
    service = WorkflowService(db)
    try:
        actions = service.suggest_actions(conversation_id)
        return actions
    except ConversationNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found",
        )
    except LLMProcessingError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Action suggestion failed: {str(e)}",
        )


@router.get("/{conversation_id}/actions", response_model=list[WorkflowActionModel])
def list_actions_for_conversation(
    conversation_id: int,
    status: Optional[WorkflowActionStatusEnum] = Query(None),
    db: Session = Depends(get_db),
):
    """List workflow actions for a conversation."""
    service = WorkflowService(db)
    actions = service.list_actions_for_conversation(conversation_id, status=status)
    return actions


@router.get("/actions/pending", response_model=list[WorkflowActionModel])
def list_pending_actions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List all pending actions across conversations."""
    service = WorkflowService(db)
    actions = service.list_pending_actions(skip=skip, limit=limit)
    return actions


@router.get("/actions/{action_id}", response_model=WorkflowActionModel)
def get_action(
    action_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific action."""
    service = WorkflowService(db)
    try:
        action = service.get_action(action_id)
        return action
    except WorkflowActionNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Action {action_id} not found",
        )


@router.post("/actions/{action_id}/approve", response_model=WorkflowActionModel)
def approve_action(
    action_id: int,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
):
    """Approve a workflow action."""
    service = WorkflowService(db)
    try:
        action = service.approve_action(
            action_id=action_id,
            reviewed_by=request.reviewed_by,
            notes=request.notes,
        )
        return action
    except WorkflowActionNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Action {action_id} not found",
        )
    except InvalidActionError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post("/actions/{action_id}/reject", response_model=WorkflowActionModel)
def reject_action(
    action_id: int,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
):
    """Reject a workflow action."""
    service = WorkflowService(db)
    try:
        action = service.reject_action(
            action_id=action_id,
            reviewed_by=request.reviewed_by,
            notes=request.notes,
        )
        return action
    except WorkflowActionNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Action {action_id} not found",
        )
    except InvalidActionError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post("/actions/{action_id}/sync-crm", response_model=dict)
def sync_action_to_crm(
    action_id: int,
    db: Session = Depends(get_db),
):
    """Sync an approved action to the CRM system."""
    workflow_service = WorkflowService(db)
    crm_service = CRMIntegrationService(db)
    
    try:
        action = workflow_service.get_action(action_id)
        
        if action.status.value != "approved":
            raise HTTPException(
                status_code=400,
                detail="Only approved actions can be synced to CRM",
            )
        
        result = crm_service.sync_action_to_crm(action)
        
        # Mark as executed after successful sync
        workflow_service.mark_executed(action_id)
        
        return {
            "success": True,
            "action_id": action_id,
            "external_id": result.get("external_id"),
            "message": "Action synced to CRM successfully",
        }
    except WorkflowActionNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Action {action_id} not found",
        )
    except CRMSyncError as e:
        # Mark action as failed
        try:
            workflow_service.mark_failed(action_id, error_message=str(e))
        except Exception:
            pass
        
        raise HTTPException(
            status_code=500,
            detail=f"CRM sync failed: {str(e)}",
        )
