"""
Critical Facts Caching System for Wendy.

Ensures consistency of personal facts across conversations by caching
established facts and injecting them into the system prompt. Facts are
extracted from Wendy's responses using the LLM and persisted in SQLite.
"""

import json
import logging
from typing import Optional

import database

logger = logging.getLogger(__name__)

# Valid fact categories
VALID_CATEGORIES = {"family", "personal", "location", "relationship", "background"}


def init_critical_facts_table(db_path: str) -> None:
    """
    Create the critical_facts table and indexes if they do not exist.

    Args:
        db_path: Path to the SQLite database file
    """
    conn = database.get_connection()
    cursor = conn.cursor()

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
    logger.info("Critical facts table initialized")


def get_all_active_facts(db_path: str) -> list[dict]:
    """
    Return all active facts as a list of dicts.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        List of fact dicts with keys: id, category, fact_key, fact_value,
        source, conversation_id, confidence, is_active, created_at, updated_at
    """
    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM critical_facts WHERE is_active = 1 ORDER BY category, fact_key"
    )
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_fact(db_path: str, category: str, key: str) -> Optional[dict]:
    """
    Get a specific fact by category and key.

    Args:
        db_path: Path to the SQLite database file
        category: Fact category (e.g., 'family', 'personal')
        key: Fact key (e.g., 'father_name', 'age')

    Returns:
        Fact dict if found and active, None otherwise
    """
    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM critical_facts WHERE category = ? AND fact_key = ? AND is_active = 1",
        (category, key)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)


def set_fact(
    db_path: str,
    category: str,
    key: str,
    value: str,
    source: str = "conversation",
    conversation_id: Optional[int] = None,
    confidence: float = 0.8
) -> dict:
    """
    Insert or update a fact. On conflict (same category+key), keep the EXISTING value.

    The first cached value wins for consistency. If a fact already exists,
    it is not overwritten — the original cached value is preserved.

    Args:
        db_path: Path to the SQLite database file
        category: Fact category (e.g., 'family', 'personal')
        key: Fact key (e.g., 'father_name', 'age')
        value: Fact value
        source: Source of the fact (default 'conversation')
        conversation_id: Optional conversation ID where the fact was mentioned
        confidence: Confidence level 0.0-1.0 (default 0.8)

    Returns:
        The fact dict (existing or newly created)
    """
    conn = database.get_connection()
    cursor = conn.cursor()

    # Check if fact already exists
    cursor.execute(
        "SELECT * FROM critical_facts WHERE category = ? AND fact_key = ?",
        (category, key)
    )
    existing = cursor.fetchone()

    if existing is not None:
        existing_dict = dict(existing)
        # Keep existing value — first cached value wins
        if existing_dict["fact_value"] != value:
            logger.warning(
                f"Fact conflict for {category}.{key}: "
                f"existing='{existing_dict['fact_value']}' vs new='{value}'. "
                f"Keeping existing value."
            )
        conn.close()
        return existing_dict

    # Insert new fact
    cursor.execute(
        """INSERT INTO critical_facts
           (category, fact_key, fact_value, source, conversation_id, confidence)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (category, key, value, source, conversation_id, confidence)
    )

    fact_id = cursor.lastrowid
    conn.commit()

    # Fetch the created fact
    cursor.execute("SELECT * FROM critical_facts WHERE id = ?", (fact_id,))
    row = cursor.fetchone()
    conn.close()

    logger.info(f"Cached new fact: {category}.{key} = '{value}'")
    return dict(row)


def build_facts_prompt_section(db_path: str) -> str:
    """
    Build a text block for the system prompt listing all cached facts
    with a strong instruction to be consistent.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Formatted string block for inclusion in the system prompt,
        or empty string if no facts are cached.
    """
    facts = get_all_active_facts(db_path)

    if not facts:
        return ""

    lines = ["CRITICAL FACTS — You MUST be consistent with these established facts about yourself:"]

    for fact in facts:
        lines.append(f"- {fact['category']}.{fact['fact_key']}: {fact['fact_value']}")

    lines.append("IMPORTANT: You must use these cached values when asked. Never contradict established facts.")

    return "\n".join(lines)


def extract_facts_from_response(
    llm_client,
    messages: list[dict],
    response: str,
    db_path: str,
    conversation_id: int
) -> list[dict]:
    """
    Use the LLM to analyze Wendy's response and extract any critical facts mentioned.
    Parse JSON response. Cache new facts, warn on conflicts but keep original.

    Args:
        llm_client: LLM client instance (from llm_client.create_client)
        messages: List of conversation messages (formatted for LLM)
        response: Wendy's response text to analyze
        db_path: Path to the SQLite database file
        conversation_id: Current conversation ID

    Returns:
        List of extracted/cached fact dicts (may be empty if no facts found)
    """
    try:
        # Skip fact extraction if the client doesn't support direct API calls
        # (e.g., MockClient doesn't have a .client attribute)
        if not hasattr(llm_client, "client"):
            logger.debug("Fact extraction skipped: LLM client does not support direct API calls")
            return []

        # Build the extraction prompt
        extraction_prompt = f"""You are analyzing Wendy's response in a conversation. Extract any critical personal facts she revealed about herself.

Valid categories: family, personal, location, relationship, background

Wendy's response:
"{response}"

Extract facts as a JSON array. Each fact should have:
- "category": one of the valid categories
- "key": a short snake_case identifier (e.g., "father_name", "age", "home_region")
- "value": the factual value

Examples:
- If she says "My paw's name is Jasper" → {{"category": "family", "key": "father_name", "value": "Jasper"}}
- If she says "I'm 22 years old" → {{"category": "personal", "key": "age", "value": "22"}}
- If she says "I live in eastern Kentucky" → {{"category": "location", "key": "region", "value": "Appalachian region of eastern Kentucky"}}

Respond with ONLY a JSON array (no other text). If no facts are revealed, respond with an empty array: []"""

        # Call the LLM for fact extraction
        extraction_messages = [
            {"role": "system", "content": "You are a fact extraction system. Respond only with valid JSON arrays."},
            {"role": "user", "content": extraction_prompt}
        ]

        # Determine which model to use for extraction
        extraction_model = getattr(llm_client, "affinity_model", None) or getattr(llm_client, "model", "gpt-4o-mini")

        extraction_response = llm_client.client.chat.completions.create(
            model=extraction_model,
            messages=extraction_messages,
            temperature=0.1,
            max_tokens=300
        )

        response_text = extraction_response.choices[0].message.content.strip()

        # Handle markdown code blocks in response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        # Find JSON array in the response
        if "[" in response_text and "]" in response_text:
            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1
            response_text = response_text[json_start:json_end]

        extracted = json.loads(response_text)

        if not isinstance(extracted, list):
            logger.warning(f"Fact extraction returned non-list: {extracted}")
            return []

        # Cache each extracted fact
        cached_facts = []
        for fact_data in extracted:
            if not isinstance(fact_data, dict):
                continue

            category = fact_data.get("category", "")
            key = fact_data.get("key", "")
            value = fact_data.get("value", "")

            if not category or not key or not value:
                continue

            if category not in VALID_CATEGORIES:
                logger.warning(f"Invalid fact category: {category}")
                continue

            fact = set_fact(
                db_path=db_path,
                category=category,
                key=key,
                value=str(value),
                source="extraction",
                conversation_id=conversation_id,
                confidence=0.8
            )
            cached_facts.append(fact)

        return cached_facts

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse fact extraction JSON: {e}")
        return []
    except Exception as e:
        # Never break the chat flow due to extraction failure
        logger.error(f"Fact extraction error (non-fatal): {e}")
        return []


def seed_initial_facts(db_path: str, config: dict) -> None:
    """
    Seed known facts from the character definition at startup.
    Only seeds facts that don't already exist (existing values are preserved).

    Args:
        db_path: Path to the SQLite database file
        config: Full configuration dictionary
    """
    wendy_config = config.get("wendy", {})

    # Seed basic facts from config
    seed_facts = [
        ("personal", "name", wendy_config.get("name", "Wendy")),
        ("personal", "age", str(wendy_config.get("age", 22))),
        ("location", "region", "Appalachian region of eastern Kentucky"),
        # No specific father's name is established in character_bible.md
        # The father is only referred to as "paw" — leaving this unseeded
        # so it can be discovered/established through conversation
    ]

    for category, key, value in seed_facts:
        existing = get_fact(db_path, category, key)
        if existing is None:
            set_fact(
                db_path=db_path,
                category=category,
                key=key,
                value=value,
                source="character_definition",
                conversation_id=None,
                confidence=1.0
            )
            logger.info(f"Seeded fact: {category}.{key} = '{value}'")
        else:
            logger.debug(f"Fact already exists: {category}.{key} = '{existing['fact_value']}' (skipping seed)")

    logger.info("Initial fact seeding complete")
