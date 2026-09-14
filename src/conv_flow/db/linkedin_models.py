"""LinkedIn authentication and session cookie management."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship

from conv_flow.db.session import Base


class LinkedInAuthORM(Base):
    """Store LinkedIn session cookies and authentication info."""
    
    __tablename__ = "linkedin_auth"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), unique=True, nullable=False, index=True)  # LinkedIn profile ID
    email = Column(String(255))
    
    # Encrypted cookies/session data
    session_cookies = Column(Text, nullable=False)  # JSON encrypted
    
    # LinkedIn profile info
    profile_name = Column(String(255))
    profile_picture_url = Column(String(500))
    
    # Session metadata
    last_sync = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<LinkedInAuth user={self.user_id}>"
