"""SQLAlchemy ORM models for database persistence."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship

from conv_flow.models.domain import (
    ConversationStageEnum,
    WorkflowActionStatusEnum,
    WorkflowActionTypeEnum,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class ConversationORM(Base):
    """ORM model for conversations."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False)
    participants = Column(JSON, default=[])
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="active", index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    stage_classification = relationship(
        "StageClassificationORM", back_populates="conversation", uselist=False, cascade="all, delete-orphan"
    )
    analysis = relationship(
        "ConversationAnalysisORM", back_populates="conversation", uselist=False, cascade="all, delete-orphan"
    )
    workflow_actions = relationship(
        "WorkflowActionORM", back_populates="conversation", cascade="all, delete-orphan"
    )


class StageClassificationORM(Base):
    """ORM model for stage classification results."""
    __tablename__ = "stage_classifications"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    stage = Column(Enum(ConversationStageEnum), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("ConversationORM", back_populates="stage_classification")


class ConversationAnalysisORM(Base):
    """ORM model for conversation analysis results."""
    __tablename__ = "conversation_analyses"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    key_topics = Column(JSON, default=[])
    sentiment = Column(String(50), nullable=False)
    entities = Column(JSON, default={})
    next_actions_suggested = Column(JSON, default=[])
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("ConversationORM", back_populates="analysis")


class WorkflowActionORM(Base):
    """ORM model for workflow actions."""
    __tablename__ = "workflow_actions"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    action_type = Column(Enum(WorkflowActionTypeEnum), nullable=False, index=True)
    description = Column(Text, nullable=False)
    suggested_date = Column(DateTime, nullable=True)
    priority = Column(String(50), default="medium")
    status = Column(Enum(WorkflowActionStatusEnum), default=WorkflowActionStatusEnum.PENDING, index=True)
    crm_sync_status = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    conversation = relationship("ConversationORM", back_populates="workflow_actions")
    human_review = relationship(
        "HumanReviewORM", back_populates="workflow_action", uselist=False, cascade="all, delete-orphan"
    )


class HumanReviewORM(Base):
    """ORM model for human review audit trail."""
    __tablename__ = "human_reviews"

    id = Column(Integer, primary_key=True, index=True)
    workflow_action_id = Column(Integer, ForeignKey("workflow_actions.id"), nullable=False, index=True)
    reviewed_by = Column(String(255), nullable=False)
    reviewed_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    approved = Column(String(10), nullable=False)  # "yes" or "no" for easier querying

    # Relationships
    workflow_action = relationship("WorkflowActionORM", back_populates="human_review")
