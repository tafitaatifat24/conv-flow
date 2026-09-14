"""Conversation API endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from conv_flow.db.session import get_db
from conv_flow.exceptions import ConversationNotFound
from conv_flow.models.domain import (
    ConversationModel,
    ConversationUpdateModel,
)
from conv_flow.services import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationModel, status_code=201)
def create_conversation(
    data: ConversationModel,
    db: Session = Depends(get_db),
):
    """Create a new conversation."""
    service = ConversationService(db)
    conversation = service.create_conversation(
        source=data.source,
        content=data.content,
        participants=data.participants,
        notes=data.notes,
    )
    return conversation


@router.get("", response_model=list[ConversationModel])
def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List conversations with pagination and filtering."""
    service = ConversationService(db)
    conversations = service.list_conversations(
        skip=skip,
        limit=limit,
        status=status,
        source=source,
    )
    return conversations


@router.get("/{conversation_id}", response_model=ConversationModel)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """Get a conversation by ID."""
    service = ConversationService(db)
    try:
        conversation = service.get_conversation(conversation_id)
        return conversation
    except ConversationNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found",
        )


@router.patch("/{conversation_id}", response_model=ConversationModel)
def update_conversation(
    conversation_id: int,
    data: ConversationUpdateModel,
    db: Session = Depends(get_db),
):
    """Update a conversation."""
    service = ConversationService(db)
    try:
        conversation = service.update_conversation(conversation_id, data)
        return conversation
    except ConversationNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found",
        )


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """Delete a conversation (soft delete)."""
    service = ConversationService(db)
    try:
        service.delete_conversation(conversation_id)
    except ConversationNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found",
        )
