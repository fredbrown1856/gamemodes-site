"""
Session manager for the Wendy public demo.
Handles session token issuance, validation, and lifecycle.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

import database


def generate_session_token() -> str:
    """
    Generate a cryptographically secure session token.
    
    Returns:
        A URL-safe base64-encoded random token string
    """
    return secrets.token_urlsafe(32)


def create_demo_session(ip_hash: str, conversation_id: int, config: dict) -> Optional[dict]:
    """
    Create a new demo session with token and expiration.
    
    Args:
        ip_hash: Hashed IP address of the visitor
        conversation_id: ID of the conversation linked to this session
        config: Configuration dictionary (expects demo.session_duration_minutes)
        
    Returns:
        Session dict with token and details, or None if creation failed
    """
    token = generate_session_token()
    
    duration_minutes = config.get("demo", {}).get("session_duration_minutes", 10)
    now = datetime.utcnow()
    expires_at = (now + timedelta(minutes=duration_minutes)).isoformat() + "Z"
    
    source = config.get("demo", {}).get("source", "website")
    
    database.create_session(
        session_token=token,
        ip_hash=ip_hash,
        conversation_id=conversation_id,
        expires_at=expires_at,
        source=source
    )
    
    session = database.get_session_by_token(token)
    return session


def validate_session(session_token: str) -> Optional[dict]:
    """
    Validate an active session by token.
    
    Checks that the session exists, is marked active, and has not expired.
    
    Args:
        session_token: The session token to validate
        
    Returns:
        Session dict if valid, None otherwise
    """
    session = database.get_session_by_token(session_token)
    
    if session is None:
        return None
    
    if not session.get("is_active"):
        return None
    
    # Check expiration
    expires_at_str = session.get("expires_at")
    if expires_at_str:
        try:
            # Strip trailing "Z" (UTC marker) for Python <3.11 compatibility
            normalized = expires_at_str.rstrip("Z")
            expires_at = datetime.fromisoformat(normalized)
            if datetime.utcnow() > expires_at:
                return None
        except (ValueError, TypeError):
            return None
    
    return session


def end_demo_session(session_token: str) -> None:
    """
    End a demo session by marking it inactive.
    
    Args:
        session_token: The session token to end
    """
    database.end_session(session_token)


def get_active_session_count() -> int:
    """
    Return the number of currently active sessions.
    
    Returns:
        Count of active sessions
    """
    sessions = database.get_active_sessions()
    return len(sessions)


def can_start_session(config: dict) -> bool:
    """
    Check whether a new session can be started.
    
    Compares the current active session count against the configured maximum.
    
    Args:
        config: Configuration dictionary (expects demo.max_concurrent_sessions)
        
    Returns:
        True if a new session slot is available, False otherwise
    """
    max_concurrent = config.get("demo", {}).get("max_concurrent_sessions", 2)
    return get_active_session_count() < max_concurrent
