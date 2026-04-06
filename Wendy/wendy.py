"""
Wendy character system module for the Wendy NPC Conversation Demo.
Handles system prompt assembly, affinity calculations, and stage resolution.
"""

import re
import random
from typing import Optional


def build_system_prompt(affinity: int, config: dict) -> str:
    """
    Construct the full system prompt for the LLM.
    Combines base character description with stage-specific behavioral instructions.
    
    Args:
        affinity: Current affinity value (-100 to 100)
        config: Full configuration dictionary
        
    Returns:
        Complete system prompt string
    """
    wendy_config = config.get("wendy", {})
    stages = config.get("affinity_stages", [])
    
    # Get current stage info
    stage_info = get_stage(affinity, config)
    
    # Get the base system prompt template
    base_prompt = wendy_config.get("system_prompt_base", "")
    
    # Replace placeholders with actual values
    system_prompt = base_prompt.replace("{affinity}", str(affinity))
    system_prompt = system_prompt.replace("{stage_label}", stage_info["label"])
    system_prompt = system_prompt.replace("{stage_description}", stage_info["behavior"])
    
    # Add stage-specific instructions
    system_prompt += f"\n\n--- AFFINITY STAGE: {stage_info['label']} ---\n"
    system_prompt += stage_info["behavior"]
    
    return system_prompt


def get_stage(affinity: int, config: dict) -> dict:
    """
    Determine the current affinity stage for a given affinity value.
    
    Args:
        affinity: Current affinity value (-100 to 100)
        config: Full configuration dictionary containing affinity_stages
        
    Returns:
        Dict with keys: label, description, behavior, color, min, max
    """
    stages = config.get("affinity_stages", [])
    
    for stage in stages:
        if stage["min"] <= affinity <= stage["max"]:
            return {
                "label": stage["label"],
                "description": stage["behavior"],
                "behavior": stage["behavior"],
                "color": stage["color"],
                "min": stage["min"],
                "max": stage["max"]
            }
    
    # Default to Stranger if no stage matches
    return {
        "label": "Stranger",
        "description": "Wendy is neutral and cautious.",
        "behavior": "Wendy is neutral and cautious. She is polite but reserved.",
        "color": "#6b7280",
        "min": -9,
        "max": 9
    }


def get_stage_label(affinity: int, stages: list[dict]) -> str:
    """
    Determine the current affinity stage label for a given affinity value.
    
    Args:
        affinity: Current affinity value
        stages: List of stage definitions from config
        
    Returns:
        Stage label string, e.g. "Stranger", "Friendly"
    """
    for stage in stages:
        if stage["min"] <= affinity <= stage["max"]:
            return stage["label"]
    
    return "Stranger"


def get_stage_behavior(stage_label: str, stages: list[dict]) -> str:
    """
    Return the behavior description string for a given stage label.
    
    Args:
        stage_label: The stage label to look up
        stages: List of stage definitions from config
        
    Returns:
        Behavior instruction string
    """
    for stage in stages:
        if stage["label"] == stage_label:
            return stage["behavior"]
    
    return "Wendy is neutral and cautious."


def format_messages(messages: list[dict]) -> list[dict]:
    """
    Format database messages into the structure expected by the LLM client.
    Filters out system messages from the history (system prompt is added separately).
    
    Args:
        messages: List of message dicts from the database
        
    Returns:
        List of {"role": str, "content": str} dicts in OpenAI format
    """
    formatted = []
    for msg in messages:
        if msg.get("role") in ("user", "assistant"):
            formatted.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    return formatted


def format_messages_for_llm(messages: list[dict], system_prompt: str) -> list[dict]:
    """
    Format database messages into the structure expected by the LLM client.
    Prepends the system_prompt as a system message.
    Filters out any existing system messages from the history.
    
    Args:
        messages: List of message dicts from the database
        system_prompt: The system prompt to prepend
        
    Returns:
        List of {"role": str, "content": str} dicts with system message first
    """
    formatted = [{"role": "system", "content": system_prompt}]
    
    for msg in messages:
        if msg.get("role") in ("user", "assistant"):
            formatted.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    return formatted


def calculate_affinity_shift(analysis_result: dict, config: dict = None) -> int:
    """
    Process the raw LLM affinity analysis and return a clamped shift value.
    
    Args:
        analysis_result: Dict with {"shift": int, "reason": str} from LLM analysis
        config: Optional config dict for max_shift_per_message setting
        
    Returns:
        Integer shift value clamped to ±max_shift_per_message
    """
    shift = analysis_result.get("shift", 0)
    
    # Get max shift from config, default to 15
    max_shift = 15
    if config:
        max_shift = config.get("affinity", {}).get("max_shift_per_message", 15)
    
    # Clamp to max_shift range
    return max(-max_shift, min(max_shift, shift))


def should_end_conversation(affinity: int, config: dict = None) -> bool:
    """
    Return True if affinity has reached the hostile threshold.
    
    Args:
        affinity: Current affinity value
        config: Optional config dict for hostile_threshold setting
        
    Returns:
        True if conversation should end (affinity <= hostile_threshold)
    """
    threshold = -50
    if config:
        threshold = config.get("affinity", {}).get("hostile_threshold", -50)
    
    return affinity <= threshold


def get_affinity_description(affinity: int) -> str:
    """
    Return a human-readable description of Wendy's current emotional state.
    
    Args:
        affinity: Current affinity value (-100 to 100)
        
    Returns:
        Human-readable description string
    """
    if affinity <= -50:
        return "Hostile — Wendy is furious and wants you to leave."
    elif affinity <= -20:
        return "Cold — Wendy is guarded and dismissive."
    elif affinity <= -10:
        return "Distant — Wendy is polite but keeping her distance."
    elif affinity <= 9:
        return "Stranger — Wendy is neutral, the way she'd be with someone she just met."
    elif affinity <= 29:
        return "Acquaintance — Wendy is warming up and starting to share more."
    elif affinity <= 49:
        return "Friendly — Wendy is openly friendly and uses terms of endearment."
    elif affinity <= 69:
        return "Close — Wendy treats you like a trusted old friend."
    else:
        return "Trusted — Wendy fully trusts you and shares her deepest thoughts."


def fallback_affinity_analysis(message: str, config: dict = None) -> dict:
    """
    Perform keyword-based sentiment analysis when LLM is unavailable.
    Uses positive and negative keywords from config to determine affinity shift.
    
    Args:
        message: The user's message to analyze
        config: Optional config dict with affinity_shift keyword lists
        
    Returns:
        Dict with {"shift": int, "reason": str}
    """
    message_lower = message.lower()
    
    # Default keywords if config not provided
    positive_keywords = [
        "thank", "thanks", "appreciate", "kind", "nice", "love", "like",
        "great", "awesome", "wonderful", "beautiful", "sweet", "helpful",
        "friendly", "welcome"
    ]
    negative_keywords = [
        "hate", "stupid", "dumb", "ugly", "shut up", "go away", "leave",
        "boring", "annoying", "terrible", "awful", "worst", "idiot",
        "moron", "fool"
    ]
    
    positive_boost = 3
    negative_penalty = -3
    
    # Load from config if available
    if config:
        affinity_shift_config = config.get("affinity_shift", {})
        positive_keywords = affinity_shift_config.get("positive_keywords", positive_keywords)
        negative_keywords = affinity_shift_config.get("negative_keywords", negative_keywords)
        positive_boost = affinity_shift_config.get("positive_boost", positive_boost)
        negative_penalty = affinity_shift_config.get("negative_penalty", negative_penalty)
    
    # Count keyword matches
    positive_count = sum(1 for keyword in positive_keywords if keyword in message_lower)
    negative_count = sum(1 for keyword in negative_keywords if keyword in message_lower)
    
    # Calculate shift
    if positive_count > 0 and negative_count == 0:
        # Positive message
        shift = min(positive_boost, positive_count)
        reason = f"Message contained {positive_count} positive keyword(s)"
    elif negative_count > 0 and positive_count == 0:
        # Negative message
        shift = max(negative_penalty, -negative_count)
        reason = f"Message contained {negative_count} negative keyword(s)"
    elif positive_count > negative_count:
        # Mostly positive
        shift = 2
        reason = "Message was mostly positive with some negative elements"
    elif negative_count > positive_count:
        # Mostly negative
        shift = -2
        reason = "Message was mostly negative with some positive elements"
    else:
        # Mixed or neutral
        shift = 0
        reason = "Message was neutral or contained mixed sentiment"
    
    return {"shift": shift, "reason": reason}


def get_dismissive_message() -> str:
    """
    Return Wendy's final dismissive message when conversation ends due to low affinity.
    
    Returns:
        A dismissive message in Wendy's voice
    """
    messages = [
        "I ain't got no more patience for this. I'm done talkin' to you.",
        "You ain't worth the breath. Get on now.",
        "I reckon I've had enough of your nonsense. Leave me be.",
        "Well, I'm done here. Don't let the door hit ya on the way out.",
        "I don't need this kind of disrespect. We're finished.",
        "That's it. I ain't sayin' another word to you."
    ]
    return random.choice(messages)


def build_demo_system_prompt(affinity: int, config: dict, daily_briefing: Optional[str] = None) -> str:
    """
    Build system prompt for demo mode with daily briefing injected.
    
    Constructs the standard system prompt and appends the daily briefing
    context block if provided, ensuring Wendy's responses are consistent
    with her daily context across all demo sessions.
    
    Args:
        affinity: Current affinity value (-100 to 100)
        config: Full configuration dictionary
        daily_briefing: Optional daily briefing text to inject
        
    Returns:
        Complete system prompt string with daily briefing appended
    """
    base = build_system_prompt(affinity, config)
    if daily_briefing:
        base += f"\n\n--- TODAY'S CONTEXT ---\n{daily_briefing}"
    return base
