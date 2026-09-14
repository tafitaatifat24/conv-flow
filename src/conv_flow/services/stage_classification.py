"""Stage classification service using LangGraph agents."""
import logging
from sqlalchemy.orm import Session

from conv_flow.agents.graphs import get_stage_classification_graph
from conv_flow.db.models import ConversationORM, StageClassificationORM
from conv_flow.exceptions import ConversationNotFound, LLMProcessingError
from conv_flow.services.conversation import ConversationService

logger = logging.getLogger(__name__)


class StageClassificationService:
    """Service for conversation stage classification."""

    def __init__(self, db: Session):
        """
        Initialize stage classification service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.conversation_service = ConversationService(db)
        self.graph = get_stage_classification_graph()

    def classify_conversation_stage(self, conversation_id: int) -> StageClassificationORM:
        """
        Classify the stage of a conversation using LLM.

        Args:
            conversation_id: ID of conversation to classify

        Returns:
            StageClassificationORM instance

        Raises:
            ConversationNotFound: If conversation doesn't exist
            LLMProcessingError: If stage classification fails
        """
        # Get conversation
        try:
            conversation = self.conversation_service.get_conversation(conversation_id)
        except ConversationNotFound:
            raise

        # Run LangGraph workflow
        try:
            logger.info(f"Classifying stage for conversation {conversation_id}")

            state = {"conversation_text": conversation.content, "result": None, "error": None}
            result_state = self.graph.invoke(state)

            if result_state.get("error"):
                logger.error(f"LLM error: {result_state['error']}")
                raise LLMProcessingError(
                    f"Failed to classify stage: {result_state['error']}"
                )

            result = result_state.get("result")
            if not result:
                raise LLMProcessingError("No result returned from stage classification")

            logger.info(f"Stage classification result: {result.stage} (confidence: {result.confidence})")

        except Exception as e:
            logger.error(f"Stage classification failed: {str(e)}")
            if isinstance(e, LLMProcessingError):
                raise
            raise LLMProcessingError(f"Stage classification error: {str(e)}")

        # Delete existing classification if present
        existing = self.db.query(StageClassificationORM).filter(
            StageClassificationORM.conversation_id == conversation_id
        ).first()
        if existing:
            self.db.delete(existing)

        # Store result in database
        classification = StageClassificationORM(
            conversation_id=conversation_id,
            stage=result.stage,
            confidence=result.confidence,
            reasoning=result.reasoning,
        )
        self.db.add(classification)
        self.db.commit()
        self.db.refresh(classification)

        logger.info(f"Stored classification for conversation {conversation_id}")
        return classification

    def get_latest_classification(self, conversation_id: int) -> StageClassificationORM | None:
        """
        Get the latest stage classification for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            StageClassificationORM instance or None if not classified
        """
        return self.db.query(StageClassificationORM).filter(
            StageClassificationORM.conversation_id == conversation_id
        ).order_by(StageClassificationORM.created_at.desc()).first()

    def delete_classification(self, conversation_id: int) -> None:
        """
        Delete stage classification for a conversation.

        Args:
            conversation_id: Conversation ID
        """
        self.db.query(StageClassificationORM).filter(
            StageClassificationORM.conversation_id == conversation_id
        ).delete()
        self.db.commit()
