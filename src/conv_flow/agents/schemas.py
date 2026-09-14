"""Pydantic schemas for LLM structured outputs (used with LangChain)."""
from pydantic import BaseModel, Field

from conv_flow.models.domain import ConversationStageEnum


class StageClassificationSchema(BaseModel):
    """Schema for LLM stage classification output."""
    stage: ConversationStageEnum = Field(
        ...,
        description="The detected conversation stage from the following options: lead, prospect, negotiation, qualified, closed_won, closed_lost, inactive"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0) of the stage classification"
    )
    reasoning: str = Field(
        ...,
        description="Clear explanation of why this stage was selected, citing specific evidence from the conversation"
    )


class ConversationAnalysisSchema(BaseModel):
    """Schema for LLM conversation analysis output."""
    summary: str = Field(
        ...,
        description="Concise summary of the conversation (2-3 sentences max)"
    )
    key_topics: list[str] = Field(
        default_factory=list,
        description="List of 3-5 key topics discussed in the conversation"
    )
    sentiment: str = Field(
        ...,
        description="Overall sentiment of the conversation: 'positive', 'negative', or 'neutral'"
    )
    entities: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Named entities extracted from the conversation (e.g., {'person': ['John Smith'], 'company': ['Acme Corp'], 'product': ['Product A']})"
    )
    next_actions_suggested: list[str] = Field(
        default_factory=list,
        description="List of 2-4 suggested next actions or follow-ups based on the conversation"
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence score for this analysis (0.0 to 1.0)"
    )


class CRMActionSchema(BaseModel):
    """Schema for LLM-suggested CRM actions."""
    action_type: str = Field(
        ...,
        description="Type of action: 'follow_up', 'schedule_call', 'send_proposal', 'update_status', 'assign_task', or 'custom'"
    )
    description: str = Field(
        ...,
        description="Clear description of what action should be taken"
    )
    suggested_date: str = Field(
        default="",
        description="Suggested date/time for the action (e.g., 'tomorrow', '2025-09-20', 'in 3 days'). Leave empty if not applicable."
    )
    priority: str = Field(
        default="medium",
        description="Priority level: 'low', 'medium', or 'high'"
    )
    reasoning: str = Field(
        ...,
        description="Explanation for why this action is recommended"
    )


class CRMActionSuggesterSchema(BaseModel):
    """Schema for LLM CRM action suggestion output (may suggest multiple actions)."""
    actions: list[CRMActionSchema] = Field(
        default_factory=list,
        description="List of recommended CRM actions based on conversation analysis"
    )
    requires_human_review: bool = Field(
        default=True,
        description="Whether these actions require human review before execution"
    )
    review_notes: str = Field(
        default="",
        description="Optional notes on why human review is recommended"
    )
