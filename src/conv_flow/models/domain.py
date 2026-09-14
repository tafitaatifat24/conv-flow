"""Pydantic domain models for API requests/responses and data validation."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConversationStageEnum(str, Enum):
    """Enum for conversation stages."""
    LEAD = "lead"
    PROSPECT = "prospect"
    NEGOTIATION = "negotiation"
    QUALIFIED = "qualified"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    INACTIVE = "inactive"


class WorkflowActionTypeEnum(str, Enum):
    """Enum for workflow action types."""
    FOLLOW_UP = "follow_up"
    SCHEDULE_CALL = "schedule_call"
    SEND_PROPOSAL = "send_proposal"
    UPDATE_STATUS = "update_status"
    ASSIGN_TASK = "assign_task"
    CUSTOM = "custom"


class WorkflowActionStatusEnum(str, Enum):
    """Enum for workflow action status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class HumanReviewModel(BaseModel):
    """Model for human review audit trail."""
    reviewed_by: str = Field(..., description="User ID or name who reviewed")
    reviewed_at: datetime = Field(..., description="Timestamp of review")
    notes: Optional[str] = Field(None, description="Additional notes from reviewer")
    approved: bool = Field(..., description="Whether action was approved")


class ConversationAnalysisModel(BaseModel):
    """Model for conversation analysis results."""
    summary: str = Field(..., description="Brief summary of conversation")
    key_topics: list[str] = Field(default_factory=list, description="Key topics extracted")
    sentiment: str = Field(..., description="Sentiment analysis (positive/negative/neutral)")
    entities: dict[str, list[str]] = Field(default_factory=dict, description="Named entities extracted (person, company, etc.)")
    next_actions_suggested: list[str] = Field(default_factory=list, description="Suggested next actions")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score of analysis")


class StageClassificationModel(BaseModel):
    """Model for stage classification results."""
    stage: ConversationStageEnum = Field(..., description="Classified stage")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(..., description="Explanation for stage classification")


class WorkflowActionModel(BaseModel):
    """Model for workflow actions."""
    id: Optional[int] = Field(None, description="Action ID (auto-generated)")
    conversation_id: int = Field(..., description="Associated conversation ID")
    action_type: WorkflowActionTypeEnum = Field(..., description="Type of action")
    description: str = Field(..., description="Detailed description of action")
    suggested_date: Optional[datetime] = Field(None, description="Suggested date for action")
    priority: str = Field(default="medium", description="Priority level (low/medium/high)")
    status: WorkflowActionStatusEnum = Field(default=WorkflowActionStatusEnum.PENDING, description="Current status")
    created_at: Optional[datetime] = Field(None, description="When action was created")
    human_review: Optional[HumanReviewModel] = Field(None, description="Human review audit trail")
    crm_sync_status: Optional[str] = Field(None, description="Status of CRM sync (pending/synced/failed)")


class ConversationModel(BaseModel):
    """Model for conversations."""
    id: Optional[int] = Field(None, description="Conversation ID (auto-generated)")
    source: str = Field(..., description="Source of conversation (email/chat/call/etc.)")
    content: str = Field(..., description="Raw conversation text")
    participants: list[str] = Field(default_factory=list, description="List of participant names/emails")
    created_at: Optional[datetime] = Field(None, description="When conversation was created")
    updated_at: Optional[datetime] = Field(None, description="When conversation was last updated")
    stage: Optional[StageClassificationModel] = Field(None, description="Detected conversation stage")
    analysis: Optional[ConversationAnalysisModel] = Field(None, description="Analysis results")
    workflow_actions: list[WorkflowActionModel] = Field(default_factory=list, description="Associated workflow actions")
    notes: Optional[str] = Field(None, description="Internal notes")
    status: str = Field(default="active", description="Status (active/archived/deleted)")

    class Config:
        from_attributes = True


class ConversationCreateModel(BaseModel):
    """Model for creating new conversations."""
    source: str = Field(..., description="Source of conversation")
    content: str = Field(..., description="Conversation text")
    participants: list[str] = Field(default_factory=list, description="List of participants")
    notes: Optional[str] = Field(None, description="Internal notes")


class ConversationUpdateModel(BaseModel):
    """Model for updating conversations."""
    notes: Optional[str] = Field(None, description="Update internal notes")
    status: Optional[str] = Field(None, description="Update status")


class WorkflowActionApprovalModel(BaseModel):
    """Model for approving/rejecting workflow actions."""
    approved: bool = Field(..., description="Whether to approve the action")
    reviewed_by: str = Field(..., description="User ID or name reviewing")
    notes: Optional[str] = Field(None, description="Review notes")
