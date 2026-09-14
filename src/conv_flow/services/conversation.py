"""Conversation service for managing conversation CRUD operations."""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from conv_flow.db.models import ConversationORM
from conv_flow.exceptions import ConversationNotFound
from conv_flow.models.domain import ConversationCreateModel, ConversationUpdateModel


class ConversationService:
    """Service for conversation management."""

    def __init__(self, db: Session):
        """
        Initialize conversation service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_conversation(
        self,
        source: str,
        content: str,
        participants: list[str] | None = None,
        notes: Optional[str] = None,
    ) -> ConversationORM:
        """
        Create a new conversation.

        Args:
            source: Source of conversation (email, chat, call, etc.)
            content: Conversation text content
            participants: List of participant names/emails
            notes: Internal notes

        Returns:
            Created ConversationORM instance

        Raises:
            Exception: If database operation fails
        """
        if participants is None:
            participants = []

        conversation = ConversationORM(
            source=source,
            content=content,
            participants=participants,
            notes=notes,
            status="active",
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation(self, conversation_id: int) -> ConversationORM:
        """
        Get a conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            ConversationORM instance

        Raises:
            ConversationNotFound: If conversation doesn't exist
        """
        conversation = self.db.query(ConversationORM).filter(
            ConversationORM.id == conversation_id
        ).first()

        if not conversation:
            raise ConversationNotFound(
                f"Conversation with ID {conversation_id} not found"
            )

        return conversation

    def list_conversations(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        source: Optional[str] = None,
    ) -> list[ConversationORM]:
        """
        List conversations with optional filtering.

        Args:
            skip: Number of results to skip (pagination)
            limit: Maximum number of results
            status: Filter by status (active, archived, deleted)
            source: Filter by source (email, chat, call, etc.)

        Returns:
            List of ConversationORM instances
        """
        query = self.db.query(ConversationORM)

        if status:
            query = query.filter(ConversationORM.status == status)

        if source:
            query = query.filter(ConversationORM.source == source)

        return query.order_by(ConversationORM.created_at.desc()).offset(skip).limit(
            limit
        ).all()

    def update_conversation(
        self,
        conversation_id: int,
        update_data: ConversationUpdateModel,
    ) -> ConversationORM:
        """
        Update a conversation.

        Args:
            conversation_id: Conversation ID
            update_data: Update data model

        Returns:
            Updated ConversationORM instance

        Raises:
            ConversationNotFound: If conversation doesn't exist
        """
        conversation = self.get_conversation(conversation_id)

        if update_data.notes is not None:
            conversation.notes = update_data.notes

        if update_data.status is not None:
            conversation.status = update_data.status

        conversation.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def delete_conversation(self, conversation_id: int) -> None:
        """
        Soft delete a conversation (mark as deleted, don't remove from DB).

        Args:
            conversation_id: Conversation ID

        Raises:
            ConversationNotFound: If conversation doesn't exist
        """
        conversation = self.get_conversation(conversation_id)
        conversation.status = "deleted"
        conversation.updated_at = datetime.now()
        self.db.commit()

    def count_conversations(self, status: Optional[str] = None) -> int:
        """
        Count conversations.

        Args:
            status: Filter by status

        Returns:
            Count of conversations
        """
        query = self.db.query(ConversationORM)

        if status:
            query = query.filter(ConversationORM.status == status)

        return query.count()
