"""
Bot protection for the Wendy public demo.
Uses honeypot fields and IP-based rate limiting.
"""

import hashlib
import os
from typing import Optional

import database


def check_honeypot(form_data: dict) -> bool:
    """
    Check for a hidden honeypot field to detect bot submissions.
    
    Bots tend to fill in all form fields, including hidden ones.
    A real user will leave the honeypot field empty.
    
    Args:
        form_data: Dictionary of form/json fields from the request
        
    Returns:
        True if the submission appears human (honeypot empty), False if bot detected
    """
    honeypot_value = form_data.get("website_url", "")
    if honeypot_value:
        return False
    return True


def check_rate_limit(ip_hash: str, max_attempts: int = 3, window_hours: int = 1) -> bool:
    """
    Check if an IP hash has exceeded the session creation rate limit.
    
    Queries the sessions table for sessions created by this IP hash
    within the specified time window.
    
    Args:
        ip_hash: Hashed IP address to check
        max_attempts: Maximum allowed sessions in the window
        window_hours: Time window in hours
        
    Returns:
        True if under the rate limit (allowed), False if exceeded (blocked)
    """
    sessions = database.get_active_sessions()
    
    # Also count recently ended sessions
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(hours=window_hours)).isoformat()
    
    # Query sessions for this ip_hash within the window
    conn = database.get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT COUNT(*) as count FROM sessions 
           WHERE ip_hash = ? AND started_at > ?""",
        (ip_hash, cutoff)
    )
    row = cursor.fetchone()
    conn.close()
    
    count = row["count"] if row else 0
    return count < max_attempts


def is_blocked_user_agent(user_agent_string: Optional[str]) -> bool:
    """
    Check if the user-agent string matches known bot patterns.
    
    Args:
        user_agent_string: The User-Agent header value from the request
        
    Returns:
        True if the user-agent matches a blocked pattern, False otherwise
    """
    if not user_agent_string:
        return False
    
    ua_lower = user_agent_string.lower()
    blocked_agents = [
        'python-requests', 'curl', 'wget', 'bot',
        'crawler', 'spider', 'scraper'
    ]
    
    for agent in blocked_agents:
        if agent in ua_lower:
            return True
    
    return False


def hash_ip(ip_address: str) -> str:
    """
    Hash an IP address using SHA-256 with a configurable salt.
    
    The salt is read from the IP_HASH_SALT environment variable,
    defaulting to 'gamemodes-wendy' if not set.
    
    Args:
        ip_address: The plain-text IP address to hash
        
    Returns:
        Hex-encoded SHA-256 digest of the salted IP address
    """
    salt = os.environ.get("IP_HASH_SALT", "gamemodes-wendy")
    salted = f"{salt}:{ip_address}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()
