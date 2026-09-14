"""Custom exception classes for conv-flow application."""


class ConvFlowException(Exception):
    """Base exception for all conv-flow errors."""
    pass


class ConversationNotFound(ConvFlowException):
    """Raised when conversation is not found."""
    pass


class WorkflowActionNotFound(ConvFlowException):
    """Raised when workflow action is not found."""
    pass


class LLMProcessingError(ConvFlowException):
    """Raised when LLM processing fails."""
    pass


class CRMSyncError(ConvFlowException):
    """Raised when CRM sync fails."""
    pass


class InvalidActionError(ConvFlowException):
    """Raised when action is invalid for current state."""
    pass
