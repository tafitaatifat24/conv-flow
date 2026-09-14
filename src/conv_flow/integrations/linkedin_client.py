"""LinkedIn Voyager API client for fetching conversations and messages."""
import json
import logging
from typing import Optional, Any
from datetime import datetime
import requests
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class LinkedInVoyagerClient:
    """LinkedIn Voyager API client that mimics real browser."""

    # LinkedIn API endpoints
    BASE_URL = "https://www.linkedin.com/voyager/api"
    MESSAGING_BASE = "https://www.linkedin.com/voyager/api/messaging"
    
    # Standard browser headers to avoid detection
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/vnd.linkedin.normalized+json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "X-Restli-Protocol-Version": "2.0.0",
        "X-LinkedIn-sdet": "true",
        "Referer": "https://www.linkedin.com/",
    }

    def __init__(self, session_cookies: dict):
        """
        Initialize LinkedIn client with session cookies.

        Args:
            session_cookies: Dict of cookies from active LinkedIn session
                Example: {"li_at": "...", "JSESSIONID": "...", etc.}
        """
        self.session_cookies = session_cookies
        self.session = requests.Session()
        
        # Set cookies
        for name, value in session_cookies.items():
            self.session.cookies.set(name, value)
        
        # Set headers
        self.session.headers.update(self.DEFAULT_HEADERS)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        timeout: int = 30,
    ) -> dict:
        """
        Make authenticated request to LinkedIn API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response

        Raises:
            Exception: If request fails or authentication expires
        """
        url = urljoin(self.BASE_URL, endpoint)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=timeout,
                allow_redirects=True,
            )
            
            # Check for auth failure
            if response.status_code == 401:
                raise Exception("LinkedIn session expired. Please re-authenticate.")
            
            if response.status_code == 429:
                logger.warning("LinkedIn rate limit hit. Please wait before retrying.")
                return {"error": "rate_limited"}
            
            response.raise_for_status()
            
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"LinkedIn API request failed: {str(e)}")
            raise

    def get_inbox_conversations(self, limit: int = 20) -> list[dict]:
        """
        Fetch conversations from LinkedIn inbox.

        Args:
            limit: Max conversations to fetch

        Returns:
            List of conversation metadata
        """
        try:
            logger.info(f"Fetching LinkedIn inbox conversations (limit: {limit})")
            
            # Voyager API for messaging conversations
            endpoint = "/messaging/conversations"
            params = {
                "q": "viewerConversations",
                "limit": limit,
                "sortOption": "RECENT",
            }
            
            response = self._make_request("GET", endpoint, params=params)
            
            if "error" in response:
                return []
            
            # Extract conversations from response
            conversations = []
            for element in response.get("elements", []):
                conv = self._parse_conversation_element(element)
                if conv:
                    conversations.append(conv)
            
            logger.info(f"Fetched {len(conversations)} conversations from LinkedIn")
            return conversations
        
        except Exception as e:
            logger.error(f"Failed to fetch LinkedIn inbox: {str(e)}")
            return []

    def get_conversation_messages(
        self, 
        conversation_id: str, 
        limit: int = 50
    ) -> list[dict]:
        """
        Fetch messages from a specific conversation.

        Args:
            conversation_id: LinkedIn conversation ID
            limit: Max messages to fetch

        Returns:
            List of messages in conversation
        """
        try:
            logger.info(f"Fetching messages for conversation {conversation_id}")
            
            # Voyager API for conversation events
            endpoint = f"/messaging/conversations/{conversation_id}/events"
            params = {
                "includeDeliveredReceipts": True,
                "includeReadReceipts": True,
                "limit": limit,
            }
            
            response = self._make_request("GET", endpoint, params=params)
            
            if "error" in response:
                return []
            
            # Extract and parse messages
            messages = []
            for element in response.get("elements", []):
                msg = self._parse_message_element(element)
                if msg:
                    messages.append(msg)
            
            logger.info(f"Fetched {len(messages)} messages from conversation")
            return messages
        
        except Exception as e:
            logger.error(f"Failed to fetch conversation messages: {str(e)}")
            return []

    def get_profile_info(self) -> dict:
        """
        Get current user's profile information.

        Returns:
            Profile data (name, email, profile_picture, etc.)
        """
        try:
            logger.info("Fetching LinkedIn profile info")
            
            endpoint = "/me"
            response = self._make_request("GET", endpoint)
            
            if "error" in response:
                return {}
            
            # Extract profile data
            profile = response.get("data", {})
            return {
                "id": profile.get("id"),
                "name": profile.get("localizedFirstName", "") + " " + profile.get("localizedLastName", ""),
                "email": profile.get("emailAddress"),
                "profile_picture": profile.get("profilePicture", {}).get("displayImage"),
            }
        
        except Exception as e:
            logger.error(f"Failed to fetch profile info: {str(e)}")
            return {}

    def verify_session(self) -> bool:
        """
        Verify that session cookies are still valid.

        Returns:
            True if session is valid, False otherwise
        """
        try:
            profile = self.get_profile_info()
            return bool(profile.get("id"))
        except Exception:
            return False

    @staticmethod
    def _parse_conversation_element(element: dict) -> Optional[dict]:
        """Parse a conversation element from API response."""
        try:
            conversation_id = element.get("entityUrn", "").split(":")[-1]
            
            # Get participant info
            participants = element.get("participants", [])
            participant_names = []
            for participant in participants:
                name = participant.get("name", {})
                full_name = name.get("localized", {}).get("en_US", "Unknown")
                participant_names.append(full_name)
            
            # Get last message
            last_message_meta = element.get("lastActivityMetadata", {})
            last_message_timestamp = last_message_meta.get("timestamp")
            
            return {
                "conversation_id": conversation_id,
                "participants": participant_names,
                "last_activity_timestamp": last_message_timestamp,
                "raw_element": element,
            }
        except Exception as e:
            logger.warning(f"Failed to parse conversation element: {str(e)}")
            return None

    @staticmethod
    def _parse_message_element(element: dict) -> Optional[dict]:
        """Parse a message element from API response."""
        try:
            # Check message type
            if element.get("type") == "MESSAGE_EVENT":
                message_content = element.get("eventContent", {}).get("message", "")
                sender = element.get("from", {}).get("name", {}).get("localized", {}).get("en_US", "Unknown")
                timestamp = element.get("createdAt")
                
                return {
                    "timestamp": timestamp,
                    "sender": sender,
                    "content": message_content,
                    "type": "message",
                }
            
            elif element.get("type") in ["PROFILE_UPDATE", "CONNECTION_EVENT"]:
                # Parse system events if needed
                return {
                    "timestamp": element.get("createdAt"),
                    "type": element.get("type").lower(),
                    "content": element.get("description", ""),
                }
            
            return None
        except Exception as e:
            logger.warning(f"Failed to parse message element: {str(e)}")
            return None
