# Character Data

Character JSON files for the multi-NPC dialogue system.

## Available Characters

| ID | Name | Game | Description |
|----|------|------|-------------|
| wendy | Wendy | Original | Appalachian mountain woman |
| fallout4_kellan | Kellan Voss | Fallout 4 | Brotherhood of Steel Knight |
| fallout4_desdemona | Desdemona | Fallout 4 | Railroad leader |
| skyrim_lydia | Lydia | Skyrim | Housecarl of Whiterun |
| skyrim_brynjolf | Brynjolf | Skyrim | Thieves Guild second |
| skyrim_serana | Serana | Skyrim | Ancient vampire |

## Adding New Characters

Create a JSON file following the schema below. See existing files for complete examples.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (matches filename) |
| `name` | string | Display name |
| `game` | string | Source game franchise |
| `role` | string | One-line character description |
| `short_description` | string | Card description for selector page |
| `system_prompt_base` | string | Base LLM system prompt |
| `stages` | object | Affinity stage definitions (see below) |

### Stage Schema

Each key in `stages` is a stage identifier. Stages must have:

```json
{
  "stage_key": {
    "threshold": 15,
    "label": "Display Label",
    "behavior": "How the NPC acts at this stage",
    "description": "Narrative description of the relationship"
  }
}
```

Stages are ordered by `threshold` (ascending). The engine selects the highest
threshold that is ≤ the current affinity value.

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `faction` | string | Faction/allegiance for display |
| `personality_layers` | object | Generic personality system (outer, reactive, inner, true_self) |
| `speech_patterns` | array/dict | How the character speaks |
| `vocabulary` | array | Character-specific words/phrases |
| `rules` | array | Character-specific behavior rules |
| `affinity_shifts` | object | Trigger words for affinity changes |
| `end_conversation` | object | max_messages and min_affinity thresholds |
| `theme` | object | Visual customization (colors, fonts) |

### Auto-Discovery

New characters are automatically discovered — just drop the JSON file in this
directory. No code changes needed. The character appears on the selector page
and is available via the API immediately.
