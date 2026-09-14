"""Workflow action service for managing CRM actions and approvals."""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from conv_flow.agents.graphs import get_crm_action_suggester_graph
from conv_flow.db.models import ConversationAnalysisORM, ConversationORM, HumanReviewORM, WorkflowActionORM, StageClassificationORM
from conv_flow.exceptions import ConversationNotFound, InvalidActionError, LLMProcessingError, WorkflowActionNotFound
from conv_flow.models.domain import WorkflowActionTypeEnum, WorkflowActionStatusEnum
from conv_flow.services.conversation import ConversationService

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for workflow action management."""

    def __init__(self, db: Session):
        """
        Initialize workflow service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.conversation_service = ConversationService(db)
        self.graph = get_crm_action_suggester_graph()

    def suggest_actions(self, conversation_id: int) -> list[WorkflowActionORM]:
        """
        Suggest workflow actions for a conversation based on analysis.

        Args:
            conversation_id: ID of conversation

        Returns:
            List of WorkflowActionORM instances

        Raises:
            ConversationNotFound: If conversation doesn't exist
            LLMProcessingError: If action suggestion fails
        """
        # Get conversation
        try:
            conversation = self.conversation_service.get_conversation(conversation_id)
        except ConversationNotFound:
            raise

        # Get existing stage classification and analysis for context
        stage_data = self.db.query(StageClassificationORM).filter(
            StageClassificationORM.conversation_id == conversation_id
        ).first()

        analysis_data = self.db.query(ConversationAnalysisORM).filter(
            ConversationAnalysisORM.conversation_id == conversation_id
        ).first()

        # Prepare context for LLM
        stage_str = stage_data.stage.value if stage_data else "unknown"
        analysis_dict = {
            "summary": analysis_data.summary,
            "sentiment": analysis_data.sentiment,
            "key_topics": analysis_data.key_topics,
        } if analysis_data else None

        # Run LangGraph workflow
        try:
            logger.info(f"Suggesting actions for conversation {conversation_id}")

            state = {
                "conversation_text": conversation.content,
                "stage": stage_str,
                "analysis": analysis_dict,
                "result": None,
                "error": None,
            }
            result_state = self.graph.invoke(state)

            if result_state.get("error"):
                logger.error(f"LLM error: {result_state['error']}")
                raise LLMProcessingError(
                    f"Failed to suggest actions: {result_state['error']}"
                )

            result = result_state.get("result")
            if not result:
                raise LLMProcessingError("No result returned from action suggestion")

            logger.info(f"Suggested {len(result.actions)} actions for conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Action suggestion failed: {str(e)}")
            if isinstance(e, LLMProcessingError):
                raise
            raise LLMProcessingError(f"Action suggestion error: {str(e)}")

        # Delete existing pending actions
        self.db.query(WorkflowActionORM).filter(
            WorkflowActionORM.conversation_id == conversation_id,
            WorkflowActionORM.status == WorkflowActionStatusEnum.PENDING,
        ).delete()

        # Store suggested actions in database
        created_actions = []
        for action in result.actions:
            # Parse suggested_date string
            suggested_date = None
            if action.suggested_date:
                try:
                    # Simple date parsing - could be enhanced
                    suggested_date = datetime.fromisoformat(action.suggested_date)
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse suggested date: {action.suggested_date}")

            workflow_action = WorkflowActionORM(
                conversation_id=conversation_id,
                action_type=WorkflowActionTypeEnum(action.action_type.lower()),
                description=action.description,
                suggested_date=suggested_date,
                priority=action.priority.lower(),
                status=WorkflowActionStatusEnum.PENDING,
            )
            self.db.add(workflow_action)
            created_actions.append(workflow_action)

        self.db.commit()
        for action in created_actions:
            self.db.refresh(action)

        logger.info(f"Stored {len(created_actions)} actions for conversation {conversation_id}")
        return created_actions

    def get_action(self, action_id: int) -> WorkflowActionORM:
        """
        Get a workflow action by ID.

        Args:
            action_id: Action ID

        Returns:
            WorkflowActionORM instance

        Raises:
            WorkflowActionNotFound: If action doesn't exist
        """
        action = self.db.query(WorkflowActionORM).filter(
            WorkflowActionORM.id == action_id
        ).first()

        if not action:
            raise WorkflowActionNotFound(f"Action with ID {action_id} not found")

        return action

    def list_pending_actions(self, skip: int = 0, limit: int = 100) -> list[WorkflowActionORM]:
        """
        List all pending workflow actions.

        Args:
            skip: Number of results to skip
            limit: Maximum number of results

        Returns:
            List of WorkflowActionORM instances
        """
        return self.db.query(WorkflowActionORM).filter(
            WorkflowActionORM.status == WorkflowActionStatusEnum.PENDING
        ).order_by(WorkflowActionORM.created_at.desc()).offset(skip).limit(limit).all()

    def list_actions_for_conversation(
        self, conversation_id: int, status: Optional[WorkflowActionStatusEnum] = None
    ) -> list[WorkflowActionORM]:
        """
        List workflow actions for a conversation.

        Args:
            conversation_id: Conversation ID
            status: Optional status filter

        Returns:
            List of WorkflowActionORM instances
        """
        query = self.db.query(WorkflowActionORM).filter(
            WorkflowActionORM.conversation_id == conversation_id
        )

        if status:
            query = query.filter(WorkflowActionORM.status == status)

        return query.order_by(WorkflowActionORM.created_at.desc()).all()

    def approve_action(
        self, action_id: int, reviewed_by: str, notes: Optional[str] = None
    ) -> WorkflowActionORM:
        """
        Approve a workflow action.

        Args:
            action_id: Action ID
            reviewed_by: User ID or name of reviewer
            notes: Optional review notes

        Returns:
            Updated WorkflowActionORM instance

        Raises:
            WorkflowActionNotFound: If action doesn't exist
            InvalidActionError: If action is not in PENDING status
        """
        action = self.get_action(action_id)

        if action.status != WorkflowActionStatusEnum.PENDING:
            raise InvalidActionError(
                f"Cannot approve action in {action.status} status. Only PENDING actions can be approved."
            )

        # Delete existing review if present
        existing_review = self.db.query(HumanReviewORM).filter(
            HumanReviewORM.workflow_action_id == action_id
        ).first()
        if existing_review:
            self.db.delete(existing_review)

        # Create human review audit trail
        review = HumanReviewORM(
            workflow_action_id=action_id,
            reviewed_by=reviewed_by,
            notes=notes,
            approved="yes",
        )
        self.db.add(review)

        # Update action status
        action.status = WorkflowActionStatusEnum.APPROVED
        action.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(action)

        logger.info(f"Action {action_id} approved by {reviewed_by}")
        return action

    def reject_action(
        self, action_id: int, reviewed_by: str, notes: Optional[str] = None
    ) -> WorkflowActionORM:
        """
        Reject a workflow action.

        Args:
            action_id: Action ID
            reviewed_by: User ID or name of reviewer
            notes: Optional review notes

        Returns:
            Updated WorkflowActionORM instance

        Raises:
            WorkflowActionNotFound: If action doesn't exist
            InvalidActionError: If action is not in PENDING status
        """
        action = self.get_action(action_id)

        if action.status != WorkflowActionStatusEnum.PENDING:
            raise InvalidActionError(
                f"Cannot reject action in {action.status} status. Only PENDING actions can be rejected."
            )

        # Delete existing review if present
        existing_review = self.db.query(HumanReviewORM).filter(
            HumanReviewORM.workflow_action_id == action_id
        ).first()
        if existing_review:
            self.db.delete(existing_review)

        # Create human review audit trail
        review = HumanReviewORM(
            workflow_action_id=action_id,
            reviewed_by=reviewed_by,
            notes=notes,
            approved="no",
        )
        self.db.add(review)

        # Update action status
        action.status = WorkflowActionStatusEnum.REJECTED
        action.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(action)

        logger.info(f"Action {action_id} rejected by {reviewed_by}")
        return action

    def mark_executed(self, action_id: int) -> WorkflowActionORM:
        """
        Mark an action as executed (after CRM sync).

        Args:
            action_id: Action ID

        Returns:
            Updated WorkflowActionORM instance

        Raises:
            WorkflowActionNotFound: If action doesn't exist
            InvalidActionError: If action is not APPROVED
        """
        action = self.get_action(action_id)

        if action.status != WorkflowActionStatusEnum.APPROVED:
            raise InvalidActionError(
                f"Cannot execute action in {action.status} status. Only APPROVED actions can be executed."
            )

        action.status = WorkflowActionStatusEnum.EXECUTED
        action.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(action)

        logger.info(f"Action {action_id} marked as executed")
        return action

    def mark_failed(self, action_id: int, error_message: Optional[str] = None) -> WorkflowActionORM:
        """
        Mark an action as failed (CRM sync or execution failed).

        Args:
            action_id: Action ID
            error_message: Optional error message

        Returns:
            Updated WorkflowActionORM instance

        Raises:
            WorkflowActionNotFound: If action doesn't exist
        """
        action = self.get_action(action_id)

        action.status = WorkflowActionStatusEnum.FAILED
        action.crm_sync_status = f"failed: {error_message}" if error_message else "failed"
        action.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(action)

        logger.error(f"Action {action_id} marked as failed: {error_message}")
        return action

    def count_pending_actions(self) -> int:
        """
        Count pending workflow actions.

        Returns:
            Count of pending actions
        """
        return self.db.query(WorkflowActionORM).filter(
            WorkflowActionORM.status == WorkflowActionStatusEnum.PENDING
        ).count()
