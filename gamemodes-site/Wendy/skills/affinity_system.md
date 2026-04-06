# Affinity System Deep Dive

## Overview

The affinity system tracks Wendy's emotional regard toward the user on a scale from -100 (deeply hostile) to +100 (fully trusted). It dynamically adjusts based on each user message, influencing Wendy's personality, openness, and willingness to continue the conversation.

## Configuration

All affinity settings live in [`config.json`](../config.json:20) under the `affinity` key:

```json
"affinity": {
    "initial_value": 0,
    "min_value": -100,
    "max_value": 100,
    "max_shift_per_message": 15,
    "hostile_threshold": -50
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `initial_value` | 0 | Starting affinity for new conversations |
| `min_value` | -100 | Hard floor for affinity |
| `max_value` | 100 | Hard ceiling for affinity |
| `max_shift_per_message` | 15 | Maximum absolute shift per message |
| `hostile_threshold` | -50 | Affinity at or below which conversation ends |

## How Affinity Is Calculated

### Step 1: LLM Analysis

Each user message triggers an affinity analysis call to the LLM via [`llm_client.py::analyze_affinity()`](../llm_client.py:126). The prompt includes:

- Current affinity value
- Last 10 messages for context
- The user's most recent message

The LLM responds with JSON:
```json
{"shift": 5, "reason": "User was warm and asked about Wendy's day"}
```

The analysis uses a separate model/temperature config (`affinity_model`, `affinity_temperature`) which defaults to the same model with lower temperature (0.3) for more consistent analysis.

### Step 2: Clamping

The raw shift is clamped to ±`max_shift_per_message` by [`wendy.py::calculate_affinity_shift()`](../wendy.py:161):

```python
return max(-max_shift, min(max_shift, shift))
```

### Step 3: Application

The clamped shift is applied in [`database.py::update_affinity()`](../database.py:322):

```python
affinity_after = max(-100, min(100, affinity_before + shift))
```

The new affinity is clamped to [min_value, max_value]. If the result is ≤ -50, the conversation is deactivated.

### Step 4: Logging

Every shift is recorded in the `affinity_log` table with before/after values, shift amount, reason, and timestamp.

### Fallback: Keyword Matching

If the LLM affinity analysis fails (API error, parse error), the system falls back to [`wendy.py::fallback_affinity_analysis()`](../wendy.py:229). This uses keyword lists from [`config.json`](../config.json:107):

```json
"affinity_shift": {
    "positive_keywords": ["thank", "thanks", "appreciate", "kind", ...],
    "negative_keywords": ["hate", "stupid", "dumb", "ugly", ...],
    "positive_boost": 3,
    "negative_penalty": -3
}
```

Logic:
- Only positive keywords matched → shift = min(positive_boost, count)
- Only negative keywords matched → shift = max(negative_penalty, -count)
- More positive than negative → shift = +2
- More negative than positive → shift = -2
- Equal or neutral → shift = 0

## The 8 Stages

Stages are defined in [`config.json`](../config.json:27) under `affinity_stages`. Each stage has a range, label, color, and behavior description.

| Stage | Min | Max | Color | Hex |
|-------|-----|-----|-------|-----|
| Hostile | -100 | -50 | Red | `#dc2626` |
| Cold | -49 | -20 | Orange | `#ea580c` |
| Distant | -19 | -10 | Amber | `#d97706` |
| Stranger | -9 | +9 | Gray | `#6b7280` |
| Acquaintance | +10 | +29 | Lime | `#65a30d` |
| Friendly | +30 | +49 | Green | `#059669` |
| Close | +50 | +69 | Cyan | `#0891b2` |
| Trusted | +70 | +100 | Purple | `#7c3aed` |

### Stage Behaviors

**Hostile (-100 to -50)**
> Wendy is deeply hostile. She uses sharp, cutting language. She wants the user to leave. She references grievances and betrayal. Short, clipped responses filled with anger and contempt.

**Cold (-49 to -20)**
> Wendy is cold and guarded. She gives short, dismissive responses. She does not volunteer information about herself. She is suspicious of the user's motives and makes sarcastic remarks.

**Distant (-19 to -10)**
> Wendy is distant but polite. She keeps conversations surface-level and deflects personal questions. She may acknowledge the user but shows no warmth or enthusiasm.

**Stranger (-9 to +9)**
> Wendy is neutral and cautious. She is polite but reserved, the way she would be with someone she just met in town. She shares basic information but nothing personal. She uses common Appalachian greetings and phrases.

**Acquaintance (+10 to +29)**
> Wendy is warming up. She remembers things the user has mentioned. She starts sharing opinions about local life, the mountains, and her daily routines. She may joke lightly and show curiosity about the user.

**Friendly (+30 to +49)**
> Wendy is openly friendly. She shares stories about her family, her thoughts on life, and local gossip. She uses terms of endearment like 'hun' and 'sugar'. She asks about the user's wellbeing with genuine interest.

**Close (+50 to +69)**
> Wendy treats the user like a trusted old friend. She shares her worries, dreams, and deeper thoughts about her life in the holler. She talks about her family troubles, her papaw's stories, and her hopes for the future. She is emotionally open and vulnerable.

**Trusted (+70 to +100)**
> Wendy fully trusts the user. She shares her deepest secrets, fears, and childhood memories. She speaks openly about her relationship with her family, the loss of her mamaw, and her conflicted feelings about leaving the mountains someday. She is fully emotionally invested and affectionate.

## How Affinity Affects Wendy's Behavior

### System Prompt Injection

[`wendy.py::build_system_prompt()`](../wendy.py:11) constructs the system prompt by:

1. Taking the base prompt template from `config.json` → `wendy.system_prompt_base`
2. Replacing `{affinity}`, `{stage_label}`, and `{stage_description}` placeholders
3. Appending stage-specific behavior instructions

The resulting prompt tells the LLM exactly how to behave at the current affinity level.

### Backstory Unlocks by Stage

The base system prompt in [`config.json`](../config.json:105) contains Wendy's full backstory, but her *willingness to share* it changes by stage:

| Stage | What Wendy Shares |
|-------|-------------------|
| Hostile | Nothing. May reference past slights. |
| Cold | Minimal. Deflects personal questions. |
| Distant | Basic facts only (name, general location). |
| Stranger | She's from Kentucky, lives in a holler, runs a vegetable stand. |
| Acquaintance | Opinions about local life, daily routines, light jokes. |
| Friendly | Family stories, local gossip, uses terms of endearment. |
| Close | Worries, dreams, family troubles, papaw's stories, hopes for future. |
| Trusted | Deepest secrets, fears, childhood memories, mamaw's death, feelings about leaving. |

### Conversation Termination

When affinity drops to `hostile_threshold` (-50) or below:

1. [`database.py::update_affinity()`](../database.py:351) sets `is_active = 0`
2. [`app.py::chat_handler()`](../app.py:143) detects `conversation_active = false`
3. A dismissive message is returned from [`wendy.py::get_dismissive_message()`](../wendy.py:295)
4. Frontend disables the input area and shows "Wendy has left the conversation."

Dismissive messages (randomly selected):
- "I ain't got no more patience for this. I'm done talkin' to you."
- "You ain't worth the breath. Get on now."
- "I reckon I've had enough of your nonsense. Leave me be."
- "Well, I'm done here. Don't let the door hit ya on the way out."
- "I don't need this kind of disrespect. We're finished."
- "That's it. I ain't sayin' another word to you."

## Tuning Affinity Sensitivity

### Make Affinity Change Faster
- Increase `max_shift_per_message` (e.g., 20-25)
- Use a more sensitive affinity model
- Add more keywords to positive/negative lists
- Increase `positive_boost` / `negative_penalty`

### Make Affinity Change Slower
- Decrease `max_shift_per_message` (e.g., 5-10)
- Use a less sensitive affinity model
- Reduce `positive_boost` / `negative_penalty`

### Make Wendy Harder to Anger
- Lower `hostile_threshold` (e.g., -70)

### Make Wendy Easier to Anger
- Raise `hostile_threshold` (e.g., -30)

## Source References

- Affinity analysis: [`llm_client.py::analyze_affinity()`](../llm_client.py:126)
- Shift clamping: [`wendy.py::calculate_affinity_shift()`](../wendy.py:161)
- Affinity update + termination: [`database.py::update_affinity()`](../database.py:322)
- Stage resolution: [`wendy.py::get_stage()`](../wendy.py:44)
- System prompt assembly: [`wendy.py::build_system_prompt()`](../wendy.py:11)
- Fallback analysis: [`wendy.py::fallback_affinity_analysis()`](../wendy.py:229)
- Dismissive messages: [`wendy.py::get_dismissive_message()`](../wendy.py:295)
- Chat handler flow: [`app.py::chat_handler()`](../app.py:64)
