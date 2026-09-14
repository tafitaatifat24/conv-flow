"""LinkedIn conversation sync service."""
import json
import logging
from datetime import datetime
from typing import Optional
from cryptography.fernet import Fernet

from sqlalchemy.orm import Session

from conv_flow.db.linkedin_models import LinkedInAuthORM
from conv_flow.db.models import ConversationORM
from conv_flow.integrations.linkedin_client import LinkedInVoyagerClient
from conv_flow.config import settings

logger = logging.getLogger(__name__)


class LinkedInEncryption:
    """Handle encryption/decryption of sensitive LinkedIn data."""
    
    def __init__(self):
        """Initialize cipher with app secret."""
        # In production, use proper secrets management
        key = settings.encryption_key.encode() if hasattr(settings, 'encryption_key') else b'dummy_key_for_dev'
        # Ensure key is 32 bytes for Fernet
        if len(key) < 32:
            key = (key * (32 // len(key) + 1))[:32]
        # Fernet requires URL-safe base64 encoded 32-byte key
        import base64
        self.cipher = Fernet(base64.urlsafe_b64encode(key))
    
    def encrypt(self, data: dict) -> str:
        """Encrypt dict to string."""
        json_str = json.dumps(data)
        encrypted = self.cipher.encrypt(json_str.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_str: str) -> dict:
        """Decrypt string to dict."""
        try:
            decrypted = self.cipher.decrypt(encrypted_str.encode())
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt LinkedIn cookies: {str(e)}")
            return {}


class LinkedInSyncService:
    """Service for syncing LinkedIn conversations."""
    
    def __init__(self, db: Session):
        """
        Initialize LinkedIn sync service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.encryption = LinkedInEncryption()
    
    def add_or_update_auth(
        self,
        user_id: str,
        session_cookies: dict,
        email: Optional[str] = None,
    ) -> LinkedInAuthORM:
        """
        Store or update LinkedIn session cookies for a user.
        
        Args:
            user_id: LinkedIn profile ID
            session_cookies: Dict of cookies to store
            email: Optional LinkedIn email
        
        Returns:
            LinkedInAuthORM instance
        """
        logger.info(f"Storing LinkedIn auth for user {user_id}")
        
        # Encrypt cookies
        encrypted_cookies = self.encryption.encrypt(session_cookies)
        
        # Check if already exists
        auth = self.db.query(LinkedInAuthORM).filter(
            LinkedInAuthORM.user_id == user_id
        ).first()
        
        if auth:
            # Update existing
            auth.session_cookies = encrypted_cookies
            auth.email = email
            auth.updated_at = datetime.now()
            logger.info(f"Updated LinkedIn auth for user {user_id}")
        else:
            # Create new
            auth = LinkedInAuthORM(
                user_id=user_id,
                session_cookies=encrypted_cookies,
                email=email,
                is_active=True,
            )
            self.db.add(auth)
            logger.info(f"Created new LinkedIn auth for user {user_id}")
        
        self.db.commit()
        self.db.refresh(auth)
        return auth
    
    def get_auth(self, user_id: str) -> Optional[LinkedInAuthORM]:
        """Get stored LinkedIn auth."""
        return self.db.query(LinkedInAuthORM).filter(
            LinkedInAuthORM.user_id == user_id
        ).first()
    
    def sync_conversations(
        self,
        user_id: str,
        limit: int = 20,
    ) -> list[ConversationORM]:
        """
        Sync LinkedIn conversations for a user.
        
        Args:
            user_id: LinkedIn user ID
            limit: Max conversations to fetch
        
        Returns:
            List of created/updated ConversationORM instances
        """
        logger.info(f"Starting LinkedIn sync for user {user_id}")
        
        # Get stored auth
        auth = self.get_auth(user_id)
        if not auth:
            logger.error(f"No LinkedIn auth found for user {user_id}")
            return []
        
        if not auth.is_active:
            logger.warning(f"LinkedIn auth not active for user {user_id}")
            return []
        
        # Decrypt cookies
        cookies = self.encryption.decrypt(auth.session_cookies)
        if not cookies:
            logger.error(f"Failed to decrypt cookies for user {user_id}")
            return []
        
        try:
            # Create client
            client = LinkedInVoyagerClient(cookies)
            
            # Verify session is still valid
            if not client.verify_session():
                logger.warning(f"LinkedIn session expired for user {user_id}")
                auth.is_active = False
                self.db.commit()
                return []
            
            # Fetch conversations
            linkedin_conversations = client.get_inbox_conversations(limit=limit)
            logger.info(f"Fetched {len(linkedin_conversations)} conversations from LinkedIn")
            
            # Store/update in database
            stored_conversations = []
            for linkedin_conv in linkedin_conversations:
                conv = self._store_linkedin_conversation(user_id, linkedin_conv, client)
                if conv:
                    stored_conversations.append(conv)
            
            # Update last sync timestamp
            auth.last_sync = datetime.now()
            self.db.commit()
            
            logger.info(f"Synced {len(stored_conversations)} conversations for user {user_id}")
            return stored_conversations
        
        except Exception as e:
            logger.error(f"LinkedIn sync failed for user {user_id}: {str(e)}")
            # Mark as inactive on error (likely session expired)
            auth.is_active = False
            self.db.commit()
            return []
    
    def _store_linkedin_conversation(
        self,
        user_id: str,
        linkedin_conv: dict,
        client: LinkedInVoyagerClient,
    ) -> Optional[ConversationORM]:
        """
        Store a single LinkedIn conversation as ConversationORM.
        
        Args:
            user_id: LinkedIn user ID
            linkedin_conv: Conversation dict from API
            client: LinkedInVoyagerClient instance
        
        Returns:
            ConversationORM or None if failed
        """
        try:
            conv_id = linkedin_conv.get("conversation_id")
            participants = linkedin_conv.get("participants", [])
            
            # Fetch messages for this conversation
            messages = client.get_conversation_messages(conv_id, limit=50)
            
            # Construct conversation content from messages
            conversation_text = self._build_conversation_text(participants, messages)
            
            # Check if conversation already exists (to avoid duplicates)
            existing = self.db.query(ConversationORM).filter(
                ConversationORM.source == "linkedin",
                ConversationORM.notes == f"linkedin:{conv_id}",  # Use notes as unique identifier
            ).first()
            
            if existing:
                # Update existing
                existing.content = conversation_text
                existing.updated_at = datetime.now()
                self.db.commit()
                self.db.refresh(existing)
                logger.info(f"Updated LinkedIn conversation {conv_id}")
                return existing
            else:
                # Create new
                conversation = ConversationORM(
                    source="linkedin",
                    content=conversation_text,
                    participants=participants,
                    notes=f"linkedin:{conv_id}",  # Store LinkedIn ID for reference
                    status="active",
                )
                self.db.add(conversation)
                self.db.commit()
                self.db.refresh(conversation)
                logger.info(f"Created new LinkedIn conversation {conv_id}")
                return conversation
        
        except Exception as e:
            logger.error(f"Failed to store LinkedIn conversation: {str(e)}")
            return None
    
    @staticmethod
    def _build_conversation_text(participants: list[str], messages: list[dict]) -> str:
        """
        Build conversation text from participants and messages.
        
        Args:
            participants: List of participant names
            messages: List of message dicts
        
        Returns:
            Formatted conversation text
        """
        lines = [f"Conversation between: {', '.join(participants)}", ""]
        
        for msg in sorted(messages, key=lambda m: m.get("timestamp", 0)):
            timestamp = msg.get("timestamp", "")
            sender = msg.get("sender", "Unknown")
            content = msg.get("content", "")
            
            lines.append(f"[{timestamp}] {sender}: {content}")
        
        return "\n".join(lines)
    
    def deactivate_auth(self, user_id: str) -> None:
        """
        Deactivate LinkedIn auth (when user logs out).
        
        Args:
            user_id: LinkedIn user ID
        """
        auth = self.get_auth(user_id)
        if auth:
            auth.is_active = False
            self.db.commit()
            logger.info(f"Deactivated LinkedIn auth for user {user_id}")
