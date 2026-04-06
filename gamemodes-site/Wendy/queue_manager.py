"""
Queue manager for the Wendy public demo.
Manages a FIFO wait queue when all session slots are occupied.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional


# In-memory FIFO queue. Each entry is a dict:
# {queue_id: str, ip_hash: str, joined_at: str, last_poll_at: str}
_queue: list[dict] = []


def join_queue(ip_hash: str, config: dict) -> Optional[int]:
    """
    Add a visitor to the wait queue.
    
    Args:
        ip_hash: Hashed IP address of the visitor
        config: Configuration dictionary (expects demo.max_queue_size)
        
    Returns:
        1-indexed position in queue, or None if the queue is full
    """
    max_size = config.get("demo", {}).get("max_queue_size", 20)
    
    if len(_queue) >= max_size:
        return None
    
    now = datetime.utcnow().isoformat()
    entry = {
        "queue_id": str(uuid.uuid4()),
        "ip_hash": ip_hash,
        "joined_at": now,
        "last_poll_at": now
    }
    
    _queue.append(entry)
    return len(_queue)


def leave_queue(queue_id: str) -> bool:
    """
    Remove a visitor from the queue by their queue ID.
    
    Args:
        queue_id: The unique queue identifier
        
    Returns:
        True if the entry was found and removed, False otherwise
    """
    for i, entry in enumerate(_queue):
        if entry["queue_id"] == queue_id:
            _queue.pop(i)
            return True
    return False


def get_queue_position(queue_id: str) -> Optional[int]:
    """
    Get the 1-indexed position of a visitor in the queue.
    
    Args:
        queue_id: The unique queue identifier
        
    Returns:
        1-indexed position, or None if not in queue
    """
    for i, entry in enumerate(_queue):
        if entry["queue_id"] == queue_id:
            return i + 1
    return None


def update_poll_time(queue_id: str) -> bool:
    """
    Update the last_poll_at timestamp for keepalive.
    
    Args:
        queue_id: The unique queue identifier
        
    Returns:
        True if the entry was found and updated, False otherwise
    """
    for entry in _queue:
        if entry["queue_id"] == queue_id:
            entry["last_poll_at"] = datetime.utcnow().isoformat()
            return True
    return False


def cleanup_stale(config: dict) -> int:
    """
    Remove entries that have not been polled within the timeout window.
    
    Args:
        config: Configuration dictionary (expects demo.queue_timeout_minutes)
        
    Returns:
        Number of entries removed
    """
    timeout_minutes = config.get("demo", {}).get("queue_timeout_minutes", 5)
    cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    
    original_len = len(_queue)
    
    # Remove entries where last_poll_at is older than cutoff
    i = 0
    while i < len(_queue):
        try:
            last_poll = datetime.fromisoformat(_queue[i]["last_poll_at"])
            if last_poll < cutoff:
                _queue.pop(i)
            else:
                i += 1
        except (ValueError, TypeError):
            # Invalid timestamp, remove the entry
            _queue.pop(i)
    
    return original_len - len(_queue)


def get_next_in_queue() -> Optional[dict]:
    """
    Pop and return the first entry in the queue (FIFO).
    
    Returns:
        The first queue entry dict, or None if queue is empty
    """
    if _queue:
        return _queue.pop(0)
    return None


def get_queue_size() -> int:
    """
    Return the current number of entries in the queue.
    
    Returns:
        Queue length
    """
    return len(_queue)


def get_estimated_wait(queue_position: int) -> str:
    """
    Return an estimated wait time string based on queue position.
    
    Assumes an average session duration of ~10 minutes per person ahead.
    
    Args:
        queue_position: 1-indexed position in the queue
        
    Returns:
        Human-readable estimated wait string like "~5 min"
    """
    if queue_position <= 0:
        return "~0 min"
    
    # Assume ~10 minutes average session time, divided by 2 concurrent slots
    estimated_minutes = queue_position * 5
    return f"~{estimated_minutes} min"
