# Multi-Character System

> **Purpose:** Document the multi-NPC dialogue system architecture.

---

## Architecture

The website supports multiple NPC characters from different games, all using the same engine pattern established by Wendy.

### Characters

| ID | Name | Game | Template |
|----|------|------|----------|
| wendy | Wendy | Original | `characters/wendy.json` |
| fallout4_kellan | Kellan Voss | Fallout 4 | `characters/fallout4_kellan.json` |
| fallout4_desdemona | Desdemona | Fallout 4 | `characters/fallout4_desdemona.json` |
| skyrim_lydia | Lydia | Skyrim | `characters/skyrim_lydia.json` |
| skyrim_brynjolf | Brynjolf | Skyrim | `characters/skyrim_brynjolf.json` |
| skyrim_serana | Serana | Skyrim | `characters/skyrim_serana.json` |

### Data Flow

1. Player selects character → `/chat/<character_id>`
2. Frontend sends message → `/api/characters/<character_id>/chat`
3. `character_engine.py` loads character JSON, builds system prompt
4. LLM generates response using character-specific personality
5. Response returned with affinity/stage updates

### Adding New Characters

1. Create JSON file in `characters/` directory
2. Follow the schema in `character_engine.py`
3. Character auto-appears in selection page
4. No code changes needed

### Character JSON Schema
Required fields:
- `id` — Unique identifier
- `name` — Display name
- `game` — Source game
- `role` — Character description
- `system_prompt_base` — Base system prompt
- `stages` — Affinity stage definitions

Optional fields:
- `personality_layers` — Generic personality system (outer, reactive, inner, true_self)
- `speech_patterns` — How the character speaks
- `vocabulary` — Character-specific words/phrases
- `rules` — Character-specific behavior rules
- `affinity_shifts` — Trigger words for affinity changes
- `theme` — Visual customization

---

## ⚠️ PROPRIETARY NOTICE

All public-facing character data uses generic terminology only No IFS-specific fields are included.
 character data uses generic terminology only:
- "IFS" → "personality system"
- "Manager/Firefighter/Exile" → "outer layer/reactive layer/inner layer"
- "Self Energy" → "true self"
- "affinity threshold" → "trust level"
- "protector" → "defense mechanism"