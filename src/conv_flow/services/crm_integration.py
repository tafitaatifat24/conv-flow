"""CRM integration service for syncing actions to external CRM systems."""
import logging
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from conv_flow.db.models import WorkflowActionORM
from conv_flow.exceptions import CRMSyncError

logger = logging.getLogger(__name__)


class BaseCRMProvider(ABC):
    """Abstract base class for CRM providers."""

    def __init__(self, db: Session):
        """
        Initialize CRM provider.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the CRM system.

        Returns:
            True if authentication successful, False otherwise
        """
        pass

    @abstractmethod
    def sync_action(self, action: WorkflowActionORM, conversation_id: int) -> dict:
        """
        Sync a workflow action to the CRM system.

        Args:
            action: WorkflowActionORM instance to sync
            conversation_id: Associated conversation ID

        Returns:
            Dict with sync result and external ID (or error)

        Raises:
            CRMSyncError: If sync fails
        """
        pass

    @abstractmethod
    def get_external_id(self, conversation_id: int) -> str | None:
        """
        Get external CRM ID for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            External CRM ID or None if not found
        """
        pass


class MockCRMProvider(BaseCRMProvider):
    """Mock CRM provider for development and testing."""

    def authenticate(self) -> bool:
        """Authenticate with mock CRM (always succeeds)."""
        logger.info("Authenticated with mock CRM")
        return True

    def sync_action(self, action: WorkflowActionORM, conversation_id: int) -> dict:
        """
        Sync action to mock CRM (just logs the action).

        Args:
            action: WorkflowActionORM instance
            conversation_id: Conversation ID

        Returns:
            Mock sync result
        """
        logger.info(f"[MOCK CRM] Syncing action {action.id}: {action.description}")

        return {
            "success": True,
            "external_id": f"crm-mock-{action.id}",
            "message": "Mock sync completed",
        }

    def get_external_id(self, conversation_id: int) -> str | None:
        """Get mock external ID."""
        return f"mock-conv-{conversation_id}"


class CRMIntegrationService:
    """Service for CRM integration and action synchronization."""

    def __init__(self, db: Session, provider: BaseCRMProvider | None = None):
        """
        Initialize CRM integration service.

        Args:
            db: SQLAlchemy database session
            provider: CRM provider instance (defaults to MockCRMProvider)
        """
        self.db = db
        self.provider = provider or MockCRMProvider(db)

    def sync_action_to_crm(self, action: WorkflowActionORM) -> dict:
        """
        Sync a workflow action to the CRM system.

        Args:
            action: WorkflowActionORM instance to sync

        Returns:
            Sync result dict

        Raises:
            CRMSyncError: If sync fails
        """
        try:
            logger.info(f"Syncing action {action.id} to CRM")

            # Authenticate
            if not self.provider.authenticate():
                raise CRMSyncError("CRM authentication failed")

            # Sync action
            result = self.provider.sync_action(action, action.conversation_id)

            if not result.get("success"):
                raise CRMSyncError(f"CRM sync failed: {result.get('message')}")

            # Update action with CRM sync status
            action.crm_sync_status = f"synced: {result.get('external_id')}"
            self.db.commit()

            logger.info(f"Action {action.id} synced to CRM with ID: {result.get('external_id')}")

            return {
                "success": True,
                "action_id": action.id,
                "external_id": result.get("external_id"),
            }

        except Exception as e:
            logger.error(f"CRM sync failed for action {action.id}: {str(e)}")
            if isinstance(e, CRMSyncError):
                raise
            raise CRMSyncError(f"CRM sync error: {str(e)}")

    def set_provider(self, provider: BaseCRMProvider) -> None:
        """
        Set a new CRM provider.

        Args:
            provider: BaseCRMProvider instance
        """
        self.provider = provider
        logger.info(f"CRM provider set to {provider.__class__.__name__}")

    def get_provider_name(self) -> str:
        """Get name of current CRM provider."""
        return self.provider.__class__.__name__
