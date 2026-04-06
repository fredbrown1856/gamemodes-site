"""
Database module for the Wendy NPC Conversation Demo.
Handles all SQLite operations including schema initialization and CRUD operations.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional


# Module-level database path, set during init_db()
_db_path: str = "data/wendy.db"


def init_db(db_path: str = "data/wendy.db") -> None:
    """
    Initialize the database, creating all tables if they do not exist.
    Called once at application startup.
    
    Args:
        db_path: Path to the SQLite database file
    """
    global _db_path
    _db_path = db_path
    
    # Ensure the data directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            affinity        INTEGER NOT NULL DEFAULT 0,
            is_active       INTEGER NOT NULL DEFAULT 1,
            CHECK (affinity >= -100 AND affinity <= 100)
        )
    """)
    
    # Create messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role            TEXT    NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content         TEXT    NOT NULL,
            timestamp       TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)
    
    # Create index on messages conversation_id
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
            ON messages(conversation_id)
    """)
    
    # Create affinity_log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS affinity_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            affinity_before INTEGER NOT NULL,
            affinity_after  INTEGER NOT NULL,
            shift           INTEGER NOT NULL,
            reason          TEXT    NOT NULL,
            timestamp       TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)
    
    # Create index on affinity_log conversation_id
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_affinity_log_conversation_id
            ON affinity_log(conversation_id)
    """)
    
    # Create sessions table for public demo access
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_token   TEXT    NOT NULL UNIQUE,
            ip_hash         TEXT    NOT NULL,
            conversation_id INTEGER,
            started_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            expires_at      TEXT    NOT NULL,
            ended_at        TEXT,
            is_active       INTEGER NOT NULL DEFAULT 1,
            queue_position  INTEGER,
            source          TEXT    NOT NULL DEFAULT 'website',
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active)
    """)
    
    # Create daily consistency cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_cache (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_date      TEXT    NOT NULL,
            cache_type      TEXT    NOT NULL CHECK (cache_type IN ('daily_briefing', 'response_cache', 'news_cache')),
            question_hash   TEXT,
            question_text   TEXT,
            response_text   TEXT    NOT NULL,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (cache_date, cache_type, question_hash)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_cache_date ON daily_cache(cache_date)
    """)
    
    # Create training data export log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS training_export_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            export_date     TEXT    NOT NULL,
            format          TEXT    NOT NULL DEFAULT 'alpaca',
            count           INTEGER NOT NULL,
            min_stage       TEXT    NOT NULL DEFAULT 'Acquaintance',
            filename        TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    # Create public stats counter
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS public_stats (
            key             TEXT    PRIMARY KEY,
            value           INTEGER NOT NULL DEFAULT 0,
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    # Create critical_facts table for consistency caching
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS critical_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            fact_key TEXT NOT NULL,
            fact_value TEXT NOT NULL,
            source TEXT DEFAULT 'conversation',
            conversation_id INTEGER,
            confidence REAL DEFAULT 0.8,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, fact_key)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_critical_facts_active
            ON critical_facts(is_active)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_critical_facts_category
            ON critical_facts(category)
    """)

    conn.commit()
    conn.close()


def get_connection() -> sqlite3.Connection:
    """
    Return a connection with row_factory set to sqlite3.Row.
    Caller is responsible for closing.
    
    Returns:
        SQLite connection with row factory configured
    """
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_conversation() -> dict:
    """
    Insert a new conversation row with default affinity=0, is_active=1.
    
    Returns:
        The new conversation as a dict with keys:
        id, created_at, updated_at, affinity, is_active
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.utcnow().isoformat()
    
    cursor.execute(
        "INSERT INTO conversations (created_at, updated_at, affinity, is_active) VALUES (?, ?, 0, 1)",
        (now, now)
    )
    
    conv_id = cursor.lastrowid
    conn.commit()
    
    # Fetch the created conversation
    cursor.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row)


def get_conversation(conversation_id: int) -> Optional[dict]:
    """
    Fetch a single conversation by ID.
    
    Args:
        conversation_id: The conversation ID to fetch
        
    Returns:
        A dict with keys: id, created_at, updated_at, affinity, is_active
        Returns None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
    
    return dict(row)


def list_conversations(limit: int = 50, offset: int = 0) -> dict:
    """
    Return conversations ordered by updated_at DESC.
    
    Args:
        limit: Maximum number of conversations to return
        offset: Pagination offset
        
    Returns:
        Dict with 'conversations' list and 'total' count.
        Each conversation dict includes: id, created_at, updated_at, affinity, is_active,
        last_message (content of the most recent message), message_count
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute("SELECT COUNT(*) as count FROM conversations")
    total = cursor.fetchone()["count"]
    
    # Get conversations with last message and message count
    cursor.execute("""
        SELECT 
            c.id,
            c.created_at,
            c.updated_at,
            c.affinity,
            c.is_active,
            (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) as last_message,
            (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count
        FROM conversations c
        ORDER BY c.updated_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    conversations = []
    for row in rows:
        conv = dict(row)
        # Convert is_active from integer to boolean
        conv["is_active"] = bool(conv["is_active"])
        conversations.append(conv)
    
    return {
        "conversations": conversations,
        "total": total,
        "limit": limit,
        "offset": offset
    }


def delete_conversation(conversation_id: int) -> bool:
    """
    Delete a conversation and all associated messages and affinity_log rows.
    
    Args:
        conversation_id: The conversation ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if conversation exists
    cursor.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
    if cursor.fetchone() is None:
        conn.close()
        return False
    
    # Delete (cascades to messages and affinity_log)
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()
    
    return True


def add_message(conversation_id: int, role: str, content: str) -> dict:
    """
    Insert a message and update the conversation's updated_at timestamp.
    
    Args:
        conversation_id: The conversation ID
        role: Message role ('user', 'assistant', or 'system')
        content: Message content
        
    Returns:
        The new message as a dict: id, conversation_id, role, content, timestamp
        
    Raises:
        ValueError: If role is invalid
    """
    if role not in ('user', 'assistant', 'system'):
        raise ValueError(f"Invalid role: {role}. Must be 'user', 'assistant', or 'system'")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.utcnow().isoformat()
    
    # Insert the message
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, now)
    )
    
    message_id = cursor.lastrowid
    
    # Update conversation's updated_at timestamp
    cursor.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (now, conversation_id)
    )
    
    conn.commit()
    
    # Fetch the created message
    cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row)


def get_messages(conversation_id: int, limit: Optional[int] = None) -> list[dict]:
    """
    Return all messages for a conversation ordered by timestamp ASC.
    
    Args:
        conversation_id: The conversation ID
        limit: Optional limit on number of messages (most recent)
        
    Returns:
        List of message dicts: id, conversation_id, role, content, timestamp
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if limit is not None:
        # Get the most recent 'limit' messages, still ordered by timestamp ASC
        cursor.execute("""
            SELECT * FROM (
                SELECT * FROM messages 
                WHERE conversation_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
        """, (conversation_id, limit))
    else:
        cursor.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
            (conversation_id,)
        )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# ============================================================================
# Session Management Functions
# ============================================================================

def create_session(
    session_token: str,
    ip_hash: str,
    conversation_id: int,
    expires_at: str,
    source: str = 'website'
) -> dict:
    """
    Insert a new demo session.
    
    Args:
        session_token: Unique session token string
        ip_hash: Hashed IP address of the visitor
        conversation_id: ID of the linked conversation
        expires_at: ISO 8601 timestamp when session expires
        source: Origin of the session (default 'website')
        
    Returns:
        The new session as a dict
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.utcnow().isoformat()
    
    cursor.execute(
        """INSERT INTO sessions
           (session_token, ip_hash, conversation_id, started_at, expires_at, is_active, source)
           VALUES (?, ?, ?, ?, ?, 1, ?)""",
        (session_token, ip_hash, conversation_id, now, expires_at, source)
    )
    
    session_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row)


def get_session_by_token(session_token: str) -> Optional[dict]:
    """
    Fetch an active session by its token.
    
    Args:
        session_token: The session token to look up
        
    Returns:
        Session dict if found, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM sessions WHERE session_token = ?",
        (session_token,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
    
    return dict(row)


def get_active_sessions() -> list[dict]:
    """
    Return all currently active sessions.
    
    Returns:
        List of session dicts where is_active = 1
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sessions WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def end_session(session_token: str) -> bool:
    """
    End a session by marking it inactive and recording the end time.
    
    Args:
        session_token: The session token to end
        
    Returns:
        True if the session was found and ended, False otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.utcnow().isoformat()
    
    cursor.execute(
        "UPDATE sessions SET is_active = 0, ended_at = ? WHERE session_token = ? AND is_active = 1",
        (now, session_token)
    )
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return affected > 0


def expire_old_sessions() -> list[str]:
    """
    Find sessions past their expires_at timestamp and end them.
    
    Returns:
        List of session tokens that were expired
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.utcnow().isoformat()
    
    # Find expired but still active sessions
    cursor.execute(
        "SELECT session_token FROM sessions WHERE is_active = 1 AND expires_at < ?",
        (now,)
    )
    expired_rows = cursor.fetchall()
    expired_tokens = [row["session_token"] for row in expired_rows]
    
    # End them all
    if expired_tokens:
        now_str = datetime.utcnow().isoformat()
        cursor.execute(
            "UPDATE sessions SET is_active = 0, ended_at = ? WHERE is_active = 1 AND expires_at < ?",
            (now_str, now)
        )
        conn.commit()
    
    conn.close()
    
    return expired_tokens


# ============================================================================
# Daily Cache Functions
# ============================================================================

def get_daily_cache(
    cache_date: str,
    cache_type: str,
    question_hash: Optional[str] = None
) -> Optional[dict]:
    """
    Fetch a cached item from the daily cache.
    
    Args:
        cache_date: Date string in YYYY-MM-DD format
        cache_type: Either 'daily_briefing' or 'response_cache'
        question_hash: Optional SHA-256 hash of the normalized question
        
    Returns:
        Cache entry dict if found, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT * FROM daily_cache
           WHERE cache_date = ? AND cache_type = ? AND question_hash IS ?""",
        (cache_date, cache_type, question_hash)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
    
    return dict(row)


def set_daily_cache(
    cache_date: str,
    cache_type: str,
    response_text: str,
    question_hash: Optional[str] = None,
    question_text: Optional[str] = None
) -> None:
    """
    Insert a cache entry into the daily cache.
    
    Uses INSERT OR IGNORE to handle the UNIQUE constraint on
    (cache_date, cache_type, question_hash).
    
    Args:
        cache_date: Date string in YYYY-MM-DD format
        cache_type: Either 'daily_briefing' or 'response_cache'
        response_text: The text to cache
        question_hash: Optional hash of the question
        question_text: Optional original question text
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.utcnow().isoformat()
    
    cursor.execute(
        """INSERT OR IGNORE INTO daily_cache
           (cache_date, cache_type, question_hash, question_text, response_text, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (cache_date, cache_type, question_hash, question_text, response_text, now)
    )
    
    conn.commit()
    conn.close()


# ============================================================================
# Public Stats Functions
# ============================================================================

def increment_stat(key: str, amount: int = 1) -> int:
    """
    Increment a public_stats counter by the given amount.
    
    If the key does not exist, it is created with the amount as initial value.
    
    Args:
        key: The stat key to increment
        amount: Amount to increment by (default 1)
        
    Returns:
        The new value of the counter
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.utcnow().isoformat()
    
    # Try to update existing row
    cursor.execute(
        "UPDATE public_stats SET value = value + ?, updated_at = ? WHERE key = ?",
        (amount, now, key)
    )
    
    if cursor.rowcount == 0:
        # Key doesn't exist, insert it
        cursor.execute(
            "INSERT INTO public_stats (key, value, updated_at) VALUES (?, ?, ?)",
            (key, amount, now)
        )
    
    conn.commit()
    
    # Fetch the new value
    cursor.execute("SELECT value FROM public_stats WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    
    return row["value"] if row else amount


def get_stat(key: str) -> int:
    """
    Get a public_stats value.
    
    Args:
        key: The stat key to look up
        
    Returns:
        The current value, or 0 if the key does not exist
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT value FROM public_stats WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    
    return row["value"] if row else 0


# ============================================================================
# Training Export Functions
# ============================================================================

def log_training_export(
    export_date: str,
    count: int,
    min_stage: str,
    filename: Optional[str] = None,
    format: str = 'alpaca'
) -> dict:
    """
    Log a training data export run.
    
    Args:
        export_date: Date string of the export
        count: Number of examples exported
        min_stage: Minimum affinity stage included
        filename: Optional filename of the export file
        format: Export format (default 'alpaca')
        
    Returns:
        The log entry as a dict
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.utcnow().isoformat()
    
    cursor.execute(
        """INSERT INTO training_export_log
           (export_date, format, count, min_stage, filename, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (export_date, format, count, min_stage, filename, now)
    )
    
    log_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM training_export_log WHERE id = ?", (log_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row)


def get_conversations_for_export(min_affinity: int = 10) -> list[dict]:
    """
    Return conversations with their messages where affinity >= min_affinity.
    
    Results are ordered by conversation ID then message timestamp for
    consistent export ordering.
    
    Args:
        min_affinity: Minimum affinity threshold (default 10)
        
    Returns:
        List of dicts, each with conversation fields and a 'messages' list
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get qualifying conversations
    cursor.execute(
        """SELECT id, created_at, updated_at, affinity, is_active
           FROM conversations
           WHERE affinity >= ?
           ORDER BY id ASC""",
        (min_affinity,)
    )
    
    conversations = []
    for row in cursor.fetchall():
        conv = dict(row)
        conv_id = conv["id"]
        
        # Get messages for this conversation
        cursor.execute(
            """SELECT id, conversation_id, role, content, timestamp
               FROM messages
               WHERE conversation_id = ?
               ORDER BY timestamp ASC""",
            (conv_id,)
        )
        msg_rows = cursor.fetchall()
        conv["messages"] = [dict(m) for m in msg_rows]
        
        conversations.append(conv)
    
    conn.close()
    
    return conversations


def update_affinity(conversation_id: int, shift: int, reason: str, force_active: bool = False) -> dict:
    """
    Apply an affinity shift to a conversation.
    
    Args:
        conversation_id: The conversation ID
        shift: The affinity change (positive or negative)
        reason: Explanation of why the shift occurred
        force_active: If True, never deactivate the conversation (used for demo mode)
        
    Returns:
        Dict with: affinity_before, affinity_after, shift, reason, conversation_active
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get current affinity
    cursor.execute("SELECT affinity FROM conversations WHERE id = ?", (conversation_id,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        raise ValueError(f"Conversation {conversation_id} not found")
    
    affinity_before = row["affinity"]
    
    # Calculate new affinity, clamped to [-100, 100]
    affinity_after = max(-100, min(100, affinity_before + shift))
    
    # Determine if conversation should be deactivated
    # In demo mode (force_active=True), conversations are NEVER deactivated
    if force_active:
        is_active = 1
    else:
        is_active = 1 if affinity_after > -50 else 0
    
    # Update the conversation
    cursor.execute(
        "UPDATE conversations SET affinity = ?, is_active = ?, updated_at = datetime('now') WHERE id = ?",
        (affinity_after, is_active, conversation_id)
    )
    
    # Log the affinity change
    cursor.execute(
        "INSERT INTO affinity_log (conversation_id, affinity_before, affinity_after, shift, reason) VALUES (?, ?, ?, ?, ?)",
        (conversation_id, affinity_before, affinity_after, shift, reason)
    )
    
    conn.commit()
    conn.close()
    
    return {
        "affinity_before": affinity_before,
        "affinity_after": affinity_after,
        "shift": shift,
        "reason": reason,
        "conversation_active": bool(is_active)
    }


def get_affinity_log(conversation_id: int) -> list[dict]:
    """
    Return all affinity_log entries for a conversation ordered by timestamp ASC.
    
    Args:
        conversation_id: The conversation ID
        
    Returns:
        List of dicts: id, conversation_id, affinity_before, affinity_after, shift, reason, timestamp
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM affinity_log WHERE conversation_id = ? ORDER BY timestamp ASC",
        (conversation_id,)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
