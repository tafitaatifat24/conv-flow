"""Conversation analysis service using LangGraph agents."""
import logging
from sqlalchemy.orm import Session

from conv_flow.agents.graphs import get_conversation_analysis_graph
from conv_flow.db.models import ConversationORM, ConversationAnalysisORM
from conv_flow.exceptions import ConversationNotFound, LLMProcessingError
from conv_flow.services.conversation import ConversationService

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for conversation analysis."""

    def __init__(self, db: Session):
        """
        Initialize analysis service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.conversation_service = ConversationService(db)
        self.graph = get_conversation_analysis_graph()

    def analyze_conversation(self, conversation_id: int) -> ConversationAnalysisORM:
        """
        Analyze a conversation using LLM.

        Args:
            conversation_id: ID of conversation to analyze

        Returns:
            ConversationAnalysisORM instance

        Raises:
            ConversationNotFound: If conversation doesn't exist
            LLMProcessingError: If analysis fails
        """
        # Get conversation
        try:
            conversation = self.conversation_service.get_conversation(conversation_id)
        except ConversationNotFound:
            raise

        # Run LangGraph workflow
        try:
            logger.info(f"Analyzing conversation {conversation_id}")

            state = {"conversation_text": conversation.content, "result": None, "error": None}
            result_state = self.graph.invoke(state)

            if result_state.get("error"):
                logger.error(f"LLM error: {result_state['error']}")
                raise LLMProcessingError(
                    f"Failed to analyze conversation: {result_state['error']}"
                )

            result = result_state.get("result")
            if not result:
                raise LLMProcessingError("No result returned from analysis")

            logger.info(f"Analysis complete: {len(result.key_topics)} topics, sentiment: {result.sentiment}")

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            if isinstance(e, LLMProcessingError):
                raise
            raise LLMProcessingError(f"Analysis error: {str(e)}")

        # Delete existing analysis if present
        existing = self.db.query(ConversationAnalysisORM).filter(
            ConversationAnalysisORM.conversation_id == conversation_id
        ).first()
        if existing:
            self.db.delete(existing)

        # Store result in database
        analysis = ConversationAnalysisORM(
            conversation_id=conversation_id,
            summary=result.summary,
            key_topics=result.key_topics,
            sentiment=result.sentiment,
            entities=result.entities,
            next_actions_suggested=result.next_actions_suggested,
            confidence_score=result.confidence_score,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        logger.info(f"Stored analysis for conversation {conversation_id}")
        return analysis

    def get_latest_analysis(self, conversation_id: int) -> ConversationAnalysisORM | None:
        """
        Get the latest analysis for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            ConversationAnalysisORM instance or None if not analyzed
        """
        return self.db.query(ConversationAnalysisORM).filter(
            ConversationAnalysisORM.conversation_id == conversation_id
        ).order_by(ConversationAnalysisORM.created_at.desc()).first()

    def delete_analysis(self, conversation_id: int) -> None:
        """
        Delete analysis for a conversation.

        Args:
            conversation_id: Conversation ID
        """
        self.db.query(ConversationAnalysisORM).filter(
            ConversationAnalysisORM.conversation_id == conversation_id
        ).delete()
        self.db.commit()
