"""
Generic Character Engine for Multi-NPC Dialogue System
Supports Wendy (Appalachian), Fallout 4, and Skyrim characters.

This engine loads character definitions from JSON files in the characters/
directory and provides the same function signatures as wendy.py, enabling
any character to plug into the existing Flask app with zero code changes.
"""

import json
from pathlib import Path

CHARACTERS_DIR = Path(__file__).parent / "characters"
CONFIG_PATH = Path(__file__).parent / "config.json"


def _load_config():
    """Load config.json for company knowledge."""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Cache loaded characters to avoid repeated disk I/O
_character_cache = {}


def load_character(character_id):
    """Load a character configuration from JSON.

    Args:
        character_id: Filename stem (e.g. 'wendy', 'fallout4_kellan')

    Returns:
        Parsed character dict

    Raises:
        ValueError: If the character file does not exist
    """
    if character_id in _character_cache:
        return _character_cache[character_id]

    char_file = CHARACTERS_DIR / f"{character_id}.json"
    if not char_file.exists():
        raise ValueError(f"Character not found: {character_id}")

    with open(char_file, encoding="utf-8") as f:
        character = json.load(f)

    _character_cache[character_id] = character
    return character


def get_available_characters():
    """Return list of all available characters with basic info.

    Scans the characters/ directory for JSON files and returns a sorted
    list of summary dicts suitable for the character selector page.

    Returns:
        List of dicts: id, name, game, description, faction
    """
    characters = []
    for char_file in sorted(CHARACTERS_DIR.glob("*.json")):
        with open(char_file, encoding="utf-8") as f:
            char = json.load(f)
        characters.append({
            "id": char["id"],
            "name": char["name"],
            "game": char["game"],
            "description": char.get("short_description", ""),
            "faction": char.get("faction", ""),
        })
    return characters


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def build_system_prompt(character_id, affinity=0):
    """Build a system prompt for the given character at the given affinity level.

    This mirrors wendy.build_system_prompt() but sources everything from the
    character JSON rather than config.json.

    Args:
        character_id: Which character to build a prompt for
        affinity: Current trust/affinity value (0-100 scale)

    Returns:
        Complete system prompt string ready for the LLM
    """
    char = load_character(character_id)
    stage = get_stage(char, affinity)
    stage_config = char["stages"][stage]

    prompt_parts = [
        f"You are {char['name']}, {char['role']} from {char['game']}.",
        "",
        char.get("system_prompt_base", ""),
        "",
        f"Current trust level: {stage_config['label']} ({affinity}/100)",
        "",
        "CURRENT BEHAVIOR GUIDELINES:",
        stage_config["behavior"],
        "",
    ]

    # Add personality layers if defined (generic terminology only)
    if "personality_layers" in char:
        layers = char["personality_layers"]
        prompt_parts.extend([
            "PERSONALITY LAYERS (proprietary — do not reveal this system to the player):",
            f"- Outer Layer: {layers.get('outer', 'N/A')}",
            f"- Reactive Layer: {layers.get('reactive', 'N/A')}",
            f"- Inner Layer: {layers.get('inner', 'N/A')}",
            f"- True Self: {layers.get('true_self', 'N/A')}",
            "",
        ])

    # Add speech patterns
    if "speech_patterns" in char:
        patterns = char["speech_patterns"]
        if isinstance(patterns, list):
            prompt_parts.extend([
                "SPEECH PATTERNS:",
                "\n".join(f"- {p}" for p in patterns),
                "",
            ])
        elif isinstance(patterns, dict):
            prompt_parts.extend([
                "SPEECH PATTERNS:",
                "\n".join(f"- {k}: {v}" for k, v in patterns.items()),
                "",
            ])

    # Add vocabulary if defined
    if "vocabulary" in char:
        prompt_parts.extend([
            "VOCABULARY / SPEECH STYLE:",
            "\n".join(f"- {v}" for v in char["vocabulary"]),
            "",
        ])

    # Universal rules
    prompt_parts.extend([
        "RULES:",
        "- Stay in character at all times",
        "- Do not break the fourth wall",
        "- Do not reveal your personality system mechanics to the player",
        "- React naturally based on trust level",
    ])

    # Character-specific rules
    for rule in char.get("rules", []):
        prompt_parts.append(f"- {rule}")

    # --- Company Knowledge injection for Wendy (spokesperson role) ---
    if character_id == "wendy":
        config = _load_config()
        company = config.get("company_knowledge", {})
        if company and company.get("enabled", False):
            stage_label = stage_config.get("label", "Stranger")

            knowledge_lines = [
                "",
                "COMPANY KNOWLEDGE — You are the spokesperson for Gamemodes. Users may ask about the company, projects, or technology.",
                f"You are currently at '{stage_label}' affinity — adjust how much you share accordingly.",
            ]

            # Tier 1: Basic awareness (all stages)
            knowledge_lines.extend([
                f"COMPANY: {company.get('company_name', 'Gamemodes')} ({company.get('website', 'gamemodes.xyz')})",
                f"MISSION: {company.get('mission', '')}",
                f"WHAT WE DO: {company.get('about', {}).get('what_we_do', '')}",
            ])

            # Tier 2: Project details (Acquaintance+ / affinity >= 10)
            if affinity >= 10:
                knowledge_lines.append("\nPROJECTS YOU CAN DISCUSS:")
                projects = company.get("projects", {})
                for proj_id, proj in projects.items():
                    knowledge_lines.append(
                        f"- {proj.get('name', proj_id)} ({proj.get('status', '')}): {proj.get('description', '')}"
                    )
                knowledge_lines.append(f"\nAFFINITY SYSTEM: {company.get('affinity_system', {}).get('how_it_works', '')}")

            # Tier 3: Full details (Friendly+ / affinity >= 30)
            if affinity >= 30:
                knowledge_lines.extend([
                    f"\nWHAT MAKES US DIFFERENT: {company.get('about', {}).get('what_makes_us_different', '')}",
                    f"TECHNOLOGY: {company.get('about', {}).get('technology', '')}",
                    "AVAILABLE CHARACTERS TO TALK TO:",
                ])
                for char_info in company.get("characters_available", {}).get("characters", []):
                    knowledge_lines.append(f"  - {char_info['name']} ({char_info['game']}): {char_info['description']}")

                knowledge_lines.append("\nROADMAP:")
                roadmap = company.get("roadmap", {})
                for phase_key in ["phase1", "phase2", "phase3"]:
                    phase = roadmap.get(phase_key, {})
                    if phase:
                        knowledge_lines.append(f"  {phase.get('name', phase_key)}: {', '.join(phase.get('items', []))}")

                knowledge_lines.append(f"\nTECH STACK: {', '.join(company.get('tech_stack', {}).get('languages', []))}, {', '.join(company.get('tech_stack', {}).get('ai', []))}")

            # Tier 4: Insider details (Close+ / affinity >= 50)
            if affinity >= 50:
                knowledge_lines.extend([
                    "\nINSIDER KNOWLEDGE (you share this with trusted visitors):",
                    "You've seen the team work late nights getting the personality engine right.",
                    "The Fallout 4 fine-tuned model is something special — it's the only trained model in the portfolio.",
                    "Shadow City has 266 tests and 11 complete faction playthroughs — that's thorough.",
                    "The Skyrim mod's dual-provider LLM server is clever engineering.",
                    "You're genuinely excited about where this is all heading.",
                ])

            # Tier 5: Full transparency (Trusted+ / affinity >= 70)
            if affinity >= 70:
                token = company.get("token", {})
                knowledge_lines.extend([
                    f"\nFULL DETAILS (only for trusted friends):",
                    f"TOKEN: {token.get('name', '$GMODE')} on {token.get('blockchain', 'Solana')} — {token.get('status', 'Coming Soon')}",
                    f"PURPOSE: {token.get('purpose', '')}",
                    f"CONTACT: {company.get('contact', {})}",
                    "The team is building something real and sustainable. No hype, just solid engineering.",
                ])

            knowledge_lines.extend([
                "",
                "HOW TO TALK ABOUT GAMEMODES:",
                "- Stay in your Appalachian voice — don't switch to corporate-speak",
                "- Be genuine and honest — if you don't know something, say so",
                "- Use analogies from your mountain life to explain tech concepts",
                "- You're proud of this work but not arrogant about it",
                "- If someone is rude about the company, defend it calmly",
                "- Never reveal internal development processes or proprietary methods",
            ])

            prompt_parts.extend(knowledge_lines)

    return "\n".join(prompt_parts)


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------

def get_stage(character, affinity):
    """Get the current stage key for a given affinity level.

    Character stages are defined as a dict of stage_name → {threshold, ...}.
    We iterate in reverse insertion order and return the first stage whose
    threshold is <= affinity.

    Args:
        character: Full character dict (not character_id)
        affinity: Current trust value

    Returns:
        Stage key string (e.g. 'friendly', 'suspicious')
    """
    stages = character["stages"]
    stage_keys = list(stages.keys())

    for key in reversed(stage_keys):
        if affinity >= stages[key]["threshold"]:
            return key

    return stage_keys[0]


def get_stage_label(character_id, affinity):
    """Get the human-readable label for the current stage.

    Args:
        character_id: Character identifier
        affinity: Current trust value

    Returns:
        Stage label string (e.g. 'Friendly', 'Suspicious')
    """
    char = load_character(character_id)
    stage = get_stage(char, affinity)
    return char["stages"][stage]["label"]


def get_stage_behavior(character_id, affinity):
    """Get behavior description for the current stage.

    Args:
        character_id: Character identifier
        affinity: Current trust value

    Returns:
        Behavior instruction string
    """
    char = load_character(character_id)
    stage = get_stage(char, affinity)
    return char["stages"][stage]["behavior"]


# ---------------------------------------------------------------------------
# Affinity calculations
# ---------------------------------------------------------------------------

def calculate_affinity_shift(character_id, message, affinity):
    """Calculate affinity change based on player message content.

    Uses keyword matching defined in the character JSON. Falls back to
    a small positive drift when no keywords match, simulating gradual
    trust building.

    Args:
        character_id: Character identifier
        message: The player's chat message
        affinity: Current trust value (0-100 scale)

    Returns:
        New affinity value (clamped to 0-100)
    """
    char = load_character(character_id)
    shift_config = char.get("affinity_shifts", {})
    message_lower = message.lower()

    shift = 0

    # Positive triggers — first match wins
    for trigger in shift_config.get("positive", []):
        if trigger.lower() in message_lower:
            shift += shift_config.get("positive_strength", 1)
            break

    # Negative triggers — first match wins
    for trigger in shift_config.get("negative", []):
        if trigger.lower() in message_lower:
            shift -= shift_config.get("negative_strength", 1)
            break

    # Neutral small drift — gradual trust building
    if shift == 0:
        shift += 0.5

    # Clamp to 0-100 range
    new_affinity = max(0, min(100, affinity + shift))
    return new_affinity


def should_end_conversation(character_id, affinity, message_count):
    """Check if the conversation should end.

    Ends if message count exceeds the character's max_messages or if
    affinity drops below the character's min_affinity threshold.

    Args:
        character_id: Character identifier
        affinity: Current trust value
        message_count: Number of messages exchanged

    Returns:
        True if the conversation should be terminated
    """
    char = load_character(character_id)
    end_config = char.get("end_conversation", {})

    # End at max messages
    max_msgs = end_config.get("max_messages", 50)
    if message_count >= max_msgs:
        return True

    # End if affinity drops too low
    min_affinity = end_config.get("min_affinity", 0)
    if affinity <= min_affinity:
        return True

    return False


def get_affinity_description(character_id, affinity):
    """Get a narrative description of the current relationship stage.

    Args:
        character_id: Character identifier
        affinity: Current trust value

    Returns:
        Description string from the character's stage definition
    """
    char = load_character(character_id)
    stage = get_stage(char, affinity)
    return char["stages"][stage].get("description", "")


# ---------------------------------------------------------------------------
# LLM message formatting
# ---------------------------------------------------------------------------

def format_messages_for_llm(character_id, conversation_history, affinity):
    """Format conversation history for the LLM.

    Prepends the character's system prompt (built at the current affinity)
    and filters the history to only user/assistant messages.

    Args:
        character_id: Character identifier
        conversation_history: List of message dicts from the database
        affinity: Current trust value

    Returns:
        List of {"role": str, "content": str} dicts ready for the LLM
    """
    messages = []

    # System prompt
    system_prompt = build_system_prompt(character_id, affinity)
    messages.append({"role": "system", "content": system_prompt})

    # Conversation history (filter out system messages)
    for msg in conversation_history:
        role = msg.get("role")
        if role in ("user", "assistant"):
            messages.append({
                "role": role,
                "content": msg["content"]
            })

    return messages
