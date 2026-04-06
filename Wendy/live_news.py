"""
Live news integration for Wendy.
Fetches current headlines and formats them for injection into the system prompt.
Wendy can comment on current events in character.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import database

logger = logging.getLogger(__name__)


def fetch_headlines(config: dict) -> Optional[list[str]]:
    """
    Fetch top headlines using the configured news API provider.

    Tries the primary provider first (NewsAPI.org), then falls back to
    GNews.io if the primary fails. Returns None if all sources fail.

    Args:
        config: Full configuration dictionary (must contain 'live_news' section)

    Returns:
        List of headline strings, or None if fetching fails
    """
    news_config = config.get("live_news", {})
    max_headlines = news_config.get("max_headlines", 5)

    # Try primary provider (NewsAPI)
    provider = news_config.get("provider", "newsapi")
    api_key = news_config.get("api_key", "") or os.environ.get("NEWSAPI_KEY", "")

    if api_key:
        try:
            headlines = _fetch_newsapi(api_key, max_headlines)
            if headlines:
                logger.info(f"Fetched {len(headlines)} headlines from NewsAPI")
                return headlines
        except Exception as e:
            logger.warning(f"NewsAPI fetch failed: {e}")

    # Try fallback provider (GNews)
    fallback_provider = news_config.get("fallback_provider", "gnews")
    fallback_key = news_config.get("fallback_api_key", "") or os.environ.get("GNEWS_KEY", "")

    if fallback_key:
        try:
            headlines = _fetch_gnews(fallback_key, max_headlines)
            if headlines:
                logger.info(f"Fetched {len(headlines)} headlines from GNews")
                return headlines
        except Exception as e:
            logger.warning(f"GNews fetch failed: {e}")

    logger.info("No headlines fetched — all providers unavailable or unconfigured")
    return None


def _fetch_newsapi(api_key: str, max_headlines: int) -> Optional[list[str]]:
    """
    Fetch headlines from NewsAPI.org.

    Args:
        api_key: NewsAPI API key
        max_headlines: Maximum number of headlines to return

    Returns:
        List of headline strings, or None on failure
    """
    import requests

    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": "us",
        "pageSize": max_headlines,
        "apiKey": api_key
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    if data.get("status") != "ok":
        logger.warning(f"NewsAPI returned non-ok status: {data.get('status')}")
        return None

    articles = data.get("articles", [])
    headlines = []

    for article in articles:
        title = article.get("title", "").strip()
        # Skip "[Removed]" placeholder articles
        if title and title != "[Removed]":
            headlines.append(title)

    return headlines[:max_headlines] if headlines else None


def _fetch_gnews(api_key: str, max_headlines: int) -> Optional[list[str]]:
    """
    Fetch headlines from GNews.io.

    Args:
        api_key: GNews API key
        max_headlines: Maximum number of headlines to return

    Returns:
        List of headline strings, or None on failure
    """
    import requests

    url = "https://gnews.io/api/v4/top-headlines"
    params = {
        "country": "us",
        "max": max_headlines,
        "token": api_key
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    articles = data.get("articles", [])
    headlines = []

    for article in articles:
        title = article.get("title", "").strip()
        if title:
            headlines.append(title)

    return headlines[:max_headlines] if headlines else None


def format_news_for_prompt(headlines: list[str]) -> str:
    """
    Format headlines into a Wendy-appropriate prompt section.

    Args:
        headlines: List of headline strings

    Returns:
        Formatted prompt section string
    """
    now = datetime.utcnow().strftime("%B %-d, %Y")

    lines = [f"CURRENT EVENTS (as of {now}):"]
    for headline in headlines:
        lines.append(f"- {headline}")

    lines.append("You may reference these if the user asks about current events. React to them in character — you have your own opinions.")

    return "\n".join(lines)


def get_cached_news(db_path: str, cache_hours: int = 2) -> Optional[list[str]]:
    """
    Retrieve cached news headlines from the daily_cache table if still fresh.

    Args:
        db_path: Path to the SQLite database file
        cache_hours: Number of hours to cache headlines (default 2)

    Returns:
        List of headline strings if fresh cache exists, None otherwise
    """
    try:
        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")

        cached = database.get_daily_cache(today, "news_cache")
        if not cached:
            return None

        # Check if cache is still within the time window
        created_str = cached.get("created_at", "")
        if created_str:
            try:
                created_time = datetime.fromisoformat(created_str)
                if (now - created_time) > timedelta(hours=cache_hours):
                    logger.debug("News cache expired")
                    return None
            except (ValueError, TypeError):
                # If we can't parse the time, use the cache anyway
                pass

        # Parse the cached headlines JSON
        try:
            headlines = json.loads(cached["response_text"])
            if isinstance(headlines, list) and len(headlines) > 0:
                logger.debug(f"Using cached news: {len(headlines)} headlines")
                return headlines
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse cached news JSON")
            return None

    except Exception as e:
        logger.warning(f"Error reading news cache: {e}")
        return None


def cache_news(headlines: list[str], db_path: str) -> None:
    """
    Cache headlines in the daily_cache table.

    Args:
        headlines: List of headline strings to cache
        db_path: Path to the SQLite database file
    """
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        headlines_json = json.dumps(headlines)
        database.set_daily_cache(
            cache_date=today,
            cache_type="news_cache",
            response_text=headlines_json,
            question_hash=None,
            question_text=None
        )
        logger.info(f"Cached {len(headlines)} news headlines")
    except Exception as e:
        logger.warning(f"Failed to cache news: {e}")


def get_news_prompt_section(config: dict, db_path: str) -> Optional[str]:
    """
    Main entry point for live news integration.

    Checks if news is enabled, returns cached headlines if fresh,
    fetches new headlines if needed, and returns a formatted prompt section.

    Args:
        config: Full configuration dictionary
        db_path: Path to the SQLite database file

    Returns:
        Formatted news prompt section string, or None if unavailable
    """
    news_config = config.get("live_news", {})

    # Check if live news is enabled
    if not news_config.get("enabled", False):
        return None

    # Check if any API key is configured (config or env)
    primary_key = news_config.get("api_key", "") or os.environ.get("NEWSAPI_KEY", "")
    fallback_key = news_config.get("fallback_api_key", "") or os.environ.get("GNEWS_KEY", "")

    if not primary_key and not fallback_key:
        logger.debug("Live news enabled but no API keys configured")
        return None

    cache_hours = news_config.get("cache_hours", 2)

    # Try cache first
    cached = get_cached_news(db_path, cache_hours)
    if cached:
        return format_news_for_prompt(cached)

    # Fetch fresh headlines
    try:
        headlines = fetch_headlines(config)
        if headlines:
            cache_news(headlines, db_path)
            return format_news_for_prompt(headlines)
    except Exception as e:
        logger.warning(f"Failed to fetch news headlines: {e}")

    return None
