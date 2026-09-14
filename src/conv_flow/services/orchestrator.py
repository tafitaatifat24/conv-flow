"""Workflow orchestration service - coordinates full pipeline."""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from conv_flow.db.models import ConversationORM
from conv_flow.services.conversation import ConversationService
from conv_flow.services.stage_classification import StageClassificationService
from conv_flow.services.analysis import AnalysisService
from conv_flow.services.workflow import WorkflowService
from conv_flow.exceptions import ConversationNotFound, LLMProcessingError

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrates the complete conversation processing pipeline:
    1. Ingest conversation (from any source)
    2. Classify stage (lead/prospect/negotiation/etc)
    3. Analyze sentiment/topics/entities
    4. Suggest workflow actions (follow-up/call/proposal/etc)
    5. Await human approval
    6. Execute approved actions
    """

    def __init__(self, db: Session):
        """
        Initialize orchestrator with all services.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.conversation_service = ConversationService(db)
        self.classification_service = StageClassificationService(db)
        self.analysis_service = AnalysisService(db)
        self.workflow_service = WorkflowService(db)

    def process_conversation_full_pipeline(
        self,
        conversation_id: int,
        skip_classification: bool = False,
        skip_analysis: bool = False,
        skip_action_suggestion: bool = False,
    ) -> dict:
        """
        Run full pipeline for a conversation.

        This coordinates classification → analysis → action suggestion.
        Each step is optional and errors don't stop the pipeline.

        Args:
            conversation_id: Conversation to process
            skip_classification: Skip stage classification if True
            skip_analysis: Skip analysis if True
            skip_action_suggestion: Skip action suggestion if True

        Returns:
            Pipeline result dict with status, classifications, analysis, actions

        Raises:
            ConversationNotFound: If conversation doesn't exist
        """
        logger.info(f"Starting full pipeline for conversation {conversation_id}")

        # Verify conversation exists
        try:
            conversation = self.conversation_service.get_conversation(conversation_id)
        except ConversationNotFound:
            logger.error(f"Conversation {conversation_id} not found")
            raise

        result = {
            "conversation_id": conversation_id,
            "pipeline_status": "in_progress",
            "steps_completed": [],
            "errors": [],
            "classification": None,
            "analysis": None,
            "workflow_actions": None,
            "started_at": datetime.now().isoformat(),
        }

        # Step 1: Stage Classification
        if not skip_classification:
            try:
                logger.info(f"Step 1/3: Classifying conversation {conversation_id}")
                classification = self.classification_service.classify_conversation_stage(
                    conversation_id
                )
                result["classification"] = classification
                result["steps_completed"].append("classification")
                logger.info(f"Classification complete: {classification.stage}")
            except LLMProcessingError as e:
                error_msg = f"Classification failed: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
            except Exception as e:
                error_msg = f"Unexpected error in classification: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)

        # Step 2: Conversation Analysis
        if not skip_analysis:
            try:
                logger.info(f"Step 2/3: Analyzing conversation {conversation_id}")
                analysis = self.analysis_service.analyze_conversation(conversation_id)
                result["analysis"] = analysis
                result["steps_completed"].append("analysis")
                logger.info(f"Analysis complete: {analysis.summary[:100]}...")
            except LLMProcessingError as e:
                error_msg = f"Analysis failed: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
            except Exception as e:
                error_msg = f"Unexpected error in analysis: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)

        # Step 3: Action Suggestion
        if not skip_action_suggestion:
            try:
                logger.info(f"Step 3/3: Suggesting actions for conversation {conversation_id}")
                actions = self.workflow_service.suggest_actions(conversation_id)
                result["workflow_actions"] = actions
                result["steps_completed"].append("action_suggestion")
                logger.info(f"Action suggestion complete: {len(actions)} actions suggested")
            except LLMProcessingError as e:
                error_msg = f"Action suggestion failed: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
            except Exception as e:
                error_msg = f"Unexpected error in action suggestion: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)

        # Final status
        if not result["errors"]:
            result["pipeline_status"] = "completed_successfully"
        elif len(result["steps_completed"]) > 0:
            result["pipeline_status"] = "completed_with_errors"
        else:
            result["pipeline_status"] = "failed"

        result["completed_at"] = datetime.now().isoformat()

        logger.info(
            f"Pipeline complete for conversation {conversation_id}: "
            f"status={result['pipeline_status']}, steps={len(result['steps_completed'])}"
        )

        return result

    def process_batch_conversations(
        self,
        conversation_ids: list[int],
        skip_classification: bool = False,
        skip_analysis: bool = False,
        skip_action_suggestion: bool = False,
    ) -> dict:
        """
        Process multiple conversations.

        Args:
            conversation_ids: List of conversation IDs
            skip_classification: Skip classification step
            skip_analysis: Skip analysis step
            skip_action_suggestion: Skip action suggestion step

        Returns:
            Batch processing result
        """
        logger.info(f"Starting batch pipeline for {len(conversation_ids)} conversations")

        results = {
            "total": len(conversation_ids),
            "successful": 0,
            "failed": 0,
            "conversations": [],
        }

        for conv_id in conversation_ids:
            try:
                result = self.process_conversation_full_pipeline(
                    conv_id,
                    skip_classification=skip_classification,
                    skip_analysis=skip_analysis,
                    skip_action_suggestion=skip_action_suggestion,
                )
                results["conversations"].append(result)
                if result["pipeline_status"].startswith("completed"):
                    results["successful"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Failed to process conversation {conv_id}: {str(e)}")
                results["conversations"].append({
                    "conversation_id": conv_id,
                    "pipeline_status": "failed",
                    "error": str(e),
                })
                results["failed"] += 1

        logger.info(
            f"Batch pipeline complete: {results['successful']} successful, "
            f"{results['failed']} failed"
        )

        return results

    def reprocess_conversation(
        self,
        conversation_id: int,
        force_reclassify: bool = True,
        force_reanalyze: bool = True,
        force_resuggest: bool = True,
    ) -> dict:
        """
        Reprocess an existing conversation (overwrite previous results).

        Useful for testing changes or updating LLM behavior.

        Args:
            conversation_id: Conversation to reprocess
            force_reclassify: Delete existing classification and create new
            force_reanalyze: Delete existing analysis and create new
            force_resuggest: Delete pending actions and suggest new

        Returns:
            Reprocessing result
        """
        logger.info(f"Reprocessing conversation {conversation_id}")

        result = {
            "conversation_id": conversation_id,
            "deleted_classification": False,
            "deleted_analysis": False,
            "deleted_pending_actions": False,
        }

        try:
            # Delete existing results if requested
            if force_reclassify:
                self.classification_service.delete_classification(conversation_id)
                result["deleted_classification"] = True
                logger.info(f"Deleted classification for conversation {conversation_id}")

            if force_reanalyze:
                self.analysis_service.delete_analysis(conversation_id)
                result["deleted_analysis"] = True
                logger.info(f"Deleted analysis for conversation {conversation_id}")

            if force_resuggest:
                # Delete pending actions
                pending = self.workflow_service.list_actions_for_conversation(
                    conversation_id,
                    status=None,  # All statuses
                )
                for action in pending:
                    if action.status.value == "pending":
                        self.db.delete(action)
                if pending:
                    self.db.commit()
                    result["deleted_pending_actions"] = True
                    logger.info(
                        f"Deleted {len(pending)} pending actions for conversation "
                        f"{conversation_id}"
                    )

            # Run full pipeline
            pipeline_result = self.process_conversation_full_pipeline(
                conversation_id,
                skip_classification=not force_reclassify,
                skip_analysis=not force_reanalyze,
                skip_action_suggestion=not force_resuggest,
            )

            result["pipeline_result"] = pipeline_result
            result["reprocess_status"] = "success"

        except Exception as e:
            logger.error(f"Reprocessing failed for conversation {conversation_id}: {str(e)}")
            result["reprocess_status"] = "failed"
            result["error"] = str(e)

        return result

    def get_pipeline_status(self, conversation_id: int) -> dict:
        """
        Get current processing status of a conversation.

        Returns what's been completed, what's pending, what failed.

        Args:
            conversation_id: Conversation ID

        Returns:
            Status dict showing completion of each pipeline step
        """
        try:
            conversation = self.conversation_service.get_conversation(conversation_id)

            classification = self.classification_service.get_latest_classification(
                conversation_id
            )
            analysis = self.analysis_service.get_latest_analysis(conversation_id)
            pending_actions = self.workflow_service.list_actions_for_conversation(
                conversation_id,
            )

            return {
                "conversation_id": conversation_id,
                "classification": {
                    "completed": bool(classification),
                    "stage": classification.stage if classification else None,
                    "confidence": classification.confidence if classification else None,
                },
                "analysis": {
                    "completed": bool(analysis),
                    "sentiment": analysis.sentiment if analysis else None,
                    "topics_count": len(analysis.key_topics) if analysis else 0,
                },
                "workflow_actions": {
                    "total_suggested": len(pending_actions),
                    "pending": len([a for a in pending_actions if a.status.value == "pending"]),
                    "approved": len([a for a in pending_actions if a.status.value == "approved"]),
                    "rejected": len([a for a in pending_actions if a.status.value == "rejected"]),
                    "executed": len([a for a in pending_actions if a.status.value == "executed"]),
                    "failed": len([a for a in pending_actions if a.status.value == "failed"]),
                },
            }

        except ConversationNotFound:
            raise
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {str(e)}")
            return {"error": str(e)}
