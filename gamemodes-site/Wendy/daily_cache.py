"""
Daily consistency cache for the Wendy public demo.
Ensures Wendy gives consistent answers about herself throughout a single day.
"""

import hashlib
from datetime import datetime
from typing import Optional

import database


# Keywords that suggest the user is asking about Wendy herself
_SELF_REFERENTIAL_KEYWORDS = [
    'you', 'your', 'yourself', 'who are', 'tell me about you',
    'how old', 'where do you live', 'your family', 'your name', 'about you'
]


def get_or_create_daily_briefing(config: dict, llm_client) -> str:
    """
    Get today's daily briefing, creating one if it doesn't exist.
    
    The daily briefing is a short context block that describes Wendy's
    day — weather, activities, mood, and a recent event. This ensures
    consistency across all conversations on a given day.
    
    Args:
        config: Configuration dictionary
        llm_client: LLM client instance for generating the briefing
        
    Returns:
        The daily briefing text (3-5 sentences)
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Check if briefing already exists
    cached = database.get_daily_cache(today, "daily_briefing")
    if cached:
        return cached["response_text"]
    
    # Determine season-appropriate weather
    month = datetime.utcnow().month
    if month in (3, 4, 5):
        season = "spring"
        weather_options = [
            "The sun's peekin' through the clouds, made the dogwoods start bloomin' down by the creek.",
            "Got a nice warm breeze today, smells like rain's comin' later though.",
            "Spring's in full swing — the redbuds are poppin' out all along the ridge."
        ]
    elif month in (6, 7, 8):
        season = "summer"
        weather_options = [
            "It's hot as blue blazes today, heat shimmerin' off the blacktop.",
            "Good sunny day, nice breeze comin' up the holler though.",
            "Humid enough to wring out the air, but the shade's nice."
        ]
    elif month in (9, 10, 11):
        season = "fall"
        weather_options = [
            "The leaves are turnin' real pretty up on the ridge, oranges and reds everywhere.",
            "Crisp mornin', perfect weather for the farmers market.",
            "Got that fall chill in the air, smells like wood smoke and dried leaves."
        ]
    else:
        season = "winter"
        weather_options = [
            "Cold and gray today, got a fire goin' in the stove.",
            "Frost on the ground this mornin', real pretty sparklin' in the sun.",
            "Bitter wind howlin' through the holler, bundled up by the wood stove."
        ]
    
    # Generate briefing via LLM
    briefing_prompt = f"""Generate a brief daily context for Wendy, a 22-year-old Appalachian woman from eastern Kentucky. Today is a {season} day. Write 3-5 sentences covering:
1. The weather in the holler (use today's actual context: pick one — {"; ".join(weather_options[:2])})
2. What Wendy is doing today (chores, farmers market, helping family, walking in the woods, canning, etc.)
3. Her current mood and why
4. One specific small event that happened today (found something, saw something, someone visited, etc.)

Write in third person, as context notes. Keep it grounded and realistic to Appalachian rural life. Do not use the word "spring", "summer", "fall", or "winter" directly."""

    try:
        briefing_text = llm_client.generate_response([
            {"role": "system", "content": "You are a creative writing assistant generating daily context notes for a character named Wendy. Be concise and evocative."},
            {"role": "user", "content": briefing_prompt}
        ])
    except Exception:
        # Fallback briefing if LLM fails
        import random
        briefing_text = (
            f"{weather_options[0]} Wendy's been helpin' her paw with chores around the farm this mornin'. "
            f"She's feelin' pretty good today — got a lot done already. "
            f"She heard a new bird call she ain't heard before down by the creek and been wonderin' what it was all day."
        )
    
    # Cache it
    database.set_daily_cache(today, "daily_briefing", briefing_text)
    
    return briefing_text


def get_cached_response(question: str, config: dict) -> Optional[str]:
    """
    Check the daily cache for a previously given response to the same question.
    
    Args:
        question: The user's question text
        config: Configuration dictionary
        
    Returns:
        Cached response text if found, None otherwise
    """
    if not config.get("daily_cache", {}).get("enabled", True):
        return None
    
    normalized = _normalize_question(question)
    question_hash = _hash_question(normalized)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    cached = database.get_daily_cache(today, "response_cache", question_hash)
    if cached:
        return cached["response_text"]
    
    return None


def cache_response(question: str, response: str) -> None:
    """
    Cache a response for a given question in the daily cache.
    
    Args:
        question: The user's question text
        response: The assistant's response text to cache
    """
    normalized = _normalize_question(question)
    question_hash = _hash_question(normalized)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    database.set_daily_cache(
        cache_date=today,
        cache_type="response_cache",
        response_text=response,
        question_hash=question_hash,
        question_text=normalized
    )


def is_self_referential(question: str) -> bool:
    """
    Determine if a question is asking about Wendy herself.
    
    Self-referential questions are candidates for caching to ensure
    Wendy gives consistent answers about herself throughout the day.
    
    Args:
        question: The user's question text
        
    Returns:
        True if the question appears to be about Wendy, False otherwise
    """
    question_lower = question.lower().strip()
    
    for keyword in _SELF_REFERENTIAL_KEYWORDS:
        if keyword in question_lower:
            return True
    
    return False


def clear_old_cache(days: int = 7) -> int:
    """
    Delete cache entries older than the specified number of days.
    
    Args:
        days: Number of days to retain (default 7)
        
    Returns:
        Number of deleted entries
    """
    from datetime import timedelta
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    conn = database.get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT COUNT(*) as count FROM daily_cache WHERE cache_date < ?",
        (cutoff,)
    )
    count = cursor.fetchone()["count"]
    
    cursor.execute(
        "DELETE FROM daily_cache WHERE cache_date < ?",
        (cutoff,)
    )
    
    conn.commit()
    conn.close()
    
    return count


def _normalize_question(question: str) -> str:
    """
    Normalize a question for consistent hashing.
    
    Args:
        question: Raw question text
        
    Returns:
        Normalized question string (lowercase, stripped whitespace)
    """
    return question.lower().strip()


def _hash_question(normalized_question: str) -> str:
    """
    Create a SHA-256 hash of a normalized question.
    
    Args:
        normalized_question: Pre-normalized question string
        
    Returns:
        Hex digest of the question hash
    """
    return hashlib.sha256(normalized_question.encode("utf-8")).hexdigest()
