"""Workflow orchestration API endpoints."""
from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from conv_flow.db.session import get_db
from conv_flow.services.orchestrator import WorkflowOrchestrator
from conv_flow.exceptions import ConversationNotFound

router = APIRouter(prefix="/api/orchestrator", tags=["orchestration"])


class ProcessRequest(BaseModel):
    """Request to process a conversation through pipeline."""
    skip_classification: Optional[bool] = False
    skip_analysis: Optional[bool] = False
    skip_action_suggestion: Optional[bool] = False


class BatchProcessRequest(BaseModel):
    """Request to process multiple conversations."""
    conversation_ids: List[int]
    skip_classification: Optional[bool] = False
    skip_analysis: Optional[bool] = False
    skip_action_suggestion: Optional[bool] = False


class ReprocessRequest(BaseModel):
    """Request to reprocess a conversation."""
    force_reclassify: Optional[bool] = True
    force_reanalyze: Optional[bool] = True
    force_resuggest: Optional[bool] = True


@router.post("/process/{conversation_id}")
def process_conversation(
    conversation_id: int,
    request: ProcessRequest = ProcessRequest(),
    db: Session = Depends(get_db),
):
    """
    Process a single conversation through the full pipeline.

    Pipeline steps:
    1. Stage classification (lead/prospect/negotiation/etc)
    2. Conversation analysis (sentiment, topics, entities)
    3. Workflow action suggestion (follow-up, call, proposal, etc)

    Each step is optional and non-blocking. All errors are logged but don't stop
    the pipeline.

    Args:
        conversation_id: Conversation to process
        request: Process options (which steps to skip)
        db: Database session

    Returns:
        Pipeline result with classifications, analysis, and suggested actions
    """
    orchestrator = WorkflowOrchestrator(db)

    try:
        result = orchestrator.process_conversation_full_pipeline(
            conversation_id,
            skip_classification=request.skip_classification,
            skip_analysis=request.skip_analysis,
            skip_action_suggestion=request.skip_action_suggestion,
        )
        return result

    except ConversationNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline processing failed: {str(e)}",
        )


@router.post("/process-batch")
def process_batch(
    request: BatchProcessRequest,
    db: Session = Depends(get_db),
):
    """
    Process multiple conversations through the full pipeline.

    Each conversation is processed independently. Failures don't stop other
    conversations from being processed.

    Args:
        request: Batch request with conversation IDs and options
        db: Database session

    Returns:
        Batch result with individual results for each conversation
    """
    if not request.conversation_ids:
        raise HTTPException(
            status_code=400,
            detail="conversation_ids list cannot be empty",
        )

    if len(request.conversation_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 conversations per batch",
        )

    orchestrator = WorkflowOrchestrator(db)

    try:
        result = orchestrator.process_batch_conversations(
            request.conversation_ids,
            skip_classification=request.skip_classification,
            skip_analysis=request.skip_analysis,
            skip_action_suggestion=request.skip_action_suggestion,
        )
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}",
        )


@router.post("/reprocess/{conversation_id}")
def reprocess_conversation(
    conversation_id: int,
    request: ReprocessRequest = ReprocessRequest(),
    db: Session = Depends(get_db),
):
    """
    Reprocess a conversation, optionally deleting previous results.

    Useful for:
    - Testing LLM model changes
    - Reprocessing after configuration updates
    - Overwriting incorrect classifications/analysis

    Args:
        conversation_id: Conversation to reprocess
        request: Reprocess options
        db: Database session

    Returns:
        Reprocessing result including what was deleted and new pipeline results
    """
    orchestrator = WorkflowOrchestrator(db)

    try:
        result = orchestrator.reprocess_conversation(
            conversation_id,
            force_reclassify=request.force_reclassify,
            force_reanalyze=request.force_reanalyze,
            force_resuggest=request.force_resuggest,
        )
        return result

    except ConversationNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Reprocessing failed: {str(e)}",
        )


@router.get("/status/{conversation_id}")
def get_pipeline_status(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """
    Get the current processing status of a conversation.

    Shows:
    - Classification status (completed, stage, confidence)
    - Analysis status (completed, sentiment, topics)
    - Workflow actions status (counts by status: pending, approved, rejected, etc)

    Args:
        conversation_id: Conversation ID
        db: Database session

    Returns:
        Status information for each pipeline step
    """
    orchestrator = WorkflowOrchestrator(db)

    try:
        status = orchestrator.get_pipeline_status(conversation_id)
        return status

    except ConversationNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}",
        )
