"""Analysis and classification API endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from conv_flow.db.session import get_db
from conv_flow.exceptions import ConversationNotFound, LLMProcessingError
from conv_flow.models.domain import (
    StageClassificationModel,
    ConversationAnalysisModel,
)
from conv_flow.services import (
    StageClassificationService,
    AnalysisService,
)

router = APIRouter(prefix="/api/conversations", tags=["analysis"])


@router.post("/{conversation_id}/classify", response_model=StageClassificationModel)
def classify_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """Classify the stage of a conversation."""
    service = StageClassificationService(db)
    try:
        classification = service.classify_conversation_stage(conversation_id)
        return classification
    except ConversationNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found",
        )
    except LLMProcessingError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}",
        )


@router.get("/{conversation_id}/classification", response_model=StageClassificationModel | None)
def get_latest_classification(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """Get the latest stage classification for a conversation."""
    service = StageClassificationService(db)
    classification = service.get_latest_classification(conversation_id)
    if not classification:
        raise HTTPException(
            status_code=404,
            detail=f"No classification found for conversation {conversation_id}",
        )
    return classification


@router.post("/{conversation_id}/analyze", response_model=ConversationAnalysisModel)
def analyze_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """Analyze a conversation using LLM."""
    service = AnalysisService(db)
    try:
        analysis = service.analyze_conversation(conversation_id)
        return analysis
    except ConversationNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found",
        )
    except LLMProcessingError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}",
        )


@router.get("/{conversation_id}/analysis", response_model=ConversationAnalysisModel | None)
def get_latest_analysis(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """Get the latest analysis for a conversation."""
    service = AnalysisService(db)
    analysis = service.get_latest_analysis(conversation_id)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis found for conversation {conversation_id}",
        )
    return analysis
