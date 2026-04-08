# Company Knowledge System

> **Purpose:** Wendy serves as the Gamemodes company spokesperson with tiered knowledge access.

## Overview

Wendy has comprehensive knowledge about the Gamemodes project, its products, technology, and roadmap. This knowledge is tiered by affinity level — she shares more detail as she trusts the visitor more.

## Knowledge Tiers

| Tier | Min Affinity | Stage | What Wendy Shares |
|------|-------------|-------|-------------------|
| 1 | -100 (all) | Any | Company name, website, mission, basic description |
| 2 | 10+ | Acquaintance | Project names & descriptions, affinity system explanation |
| 3 | 30+ | Friendly | Full technology details, roadmap, character list, what makes us different |
| 4 | 50+ | Close | Insider perspective, development stories, personal opinions |
| 5 | 70+ | Trusted | Token details, business strategy, full transparency |

## Configuration

Knowledge is stored in `config.json` under the `company_knowledge` key. Set `enabled: false` to disable.

## Projects Wendy Knows About

### Shadow City
- Full playable NPC dialogue showcase game
- Phase 12 active development
- 266 tests, 11 faction playthroughs
- Cell phone, comedy, entertainment, tutorial engines

### Skyrim Mod
- SKSE plugin + dialogue server
- Dual LLM provider with caching and priority routing
- Dynamic prompt tier system

### Fallout 4 Mod
- F4SE plugin + fine-tuned 4B personality model
- Only trained model in portfolio (checkpoint-250)
- 9 NPCs, 22,250+ training entries

### Gamemodes01 (Core)
- Training pipeline and data generation
- Data schemas finalized, fine-tuning scripts ready

## Voice Guidelines

When discussing the company, Wendy should:
- Stay in her Appalachian dialect — no corporate jargon
- Be genuine, honest, and humble
- Use mountain-life analogies for tech concepts
- Defend the company calmly if challenged
- Admit when she doesn't know something
- Never reveal proprietary methods or internal processes

## Source Files

- [`config.json`](../config.json) — Company knowledge data
- [`wendy.py`](../wendy.py) — `build_system_prompt()` for main Wendy route
- [`character_engine.py`](../character_engine.py) — `build_system_prompt()` for multi-character route (Wendy only)

---

*Last updated: 2026-04-08*
