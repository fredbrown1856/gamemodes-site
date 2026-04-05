# Gamemodes — Project Dev Log

> **Gamemodes (Game Model Development Studio)**
> Updated: 2026-04-06
> Contact: gamemodes.dev@gmail.com

---

## Overview

Gamemodes is building an AI-native NPC engine that generates psychologically authentic, dynamic dialogue using fine-tuned 1-bit quantized models running on consumer hardware. The engine is game-agnostic — proven across four projects.

| Project | Role | Status |
|---------|------|--------|
| **Gamemodes Core** | Training pipeline & engine | 🔧 Active Development |
| **Shadow City** | Showcase game | ✅ Rebuild Complete (266 tests) |
| **Skyrim Mod** | Skyrim integration | 🔧 In Development |
| **Fallout 4 Mod** | Fallout 4 integration | 🔧 In Development |

---

## 🔧 Gamemodes Core Engine

### What It Is

The core NPC dialogue engine — a training pipeline and fine-tuning system designed to produce lightweight, game-ready dialogue models. Trains `meta-llama-3.2-1b-instruct` to generate psychologically grounded NPC responses based on structured game state inputs.

### Status

| Milestone | Status |
|-----------|--------|
| Schema definitions (9 JSON configs) | ✅ Complete |
| Gold standard seed examples (10) | ✅ Complete |
| Generation scripts | ✅ Complete |
| Validation & merge pipeline | ✅ Complete |
| Quality filtering (LLM judge) | ✅ Complete |
| Alpaca format converter | ✅ Complete |
| Fine-tuning guide (QLoRA) | ✅ Complete |
| Batch data generation (2,100 target) | 🔲 Not started |
| Model fine-tuning | 🔲 Pending data |
| GGUF export & deployment | 🔲 Pending fine-tuning |

### Training Data Targets

| Category | Target | Generated |
|----------|--------|-----------|
| single_state | 300 | 0 |
| combined_states | 400 | 0 |
| intensity_gradient | 200 | 0 |
| part_switching | 150 | 0 |
| archetype_variety | 400 | 0 |
| player_interaction | 300 | 0 |
| multi_turn | 150 | 0 |
| edge_case | 100 | 0 |
| part_transition | 100 | 0 |
| **Total** | **2,100** | **10 seed** |

### Architecture

```
Game Engine → States + Profile + Context → Fine-tuned LLM → NPC Dialogue

7 Physiological States (0-100 each)
3 Psychological Modes
20 Personality Archetypes
8 Game Genres
7 Relationship Levels (-3 to +3)
5 Awareness Tiers
```

### Pipeline

1. **Generate** — Larger LLM produces training examples per category
2. **Validate** — Schema compliance, field completeness, distribution balance
3. **Merge** — Deduplicate and combine into unified dataset
4. **Filter** — LLM judge scores on 5 dimensions (accept if avg ≥ 4.5/5)
5. **Convert** — Alpaca format with 4 instruction templates + 20% augmentation
6. **Fine-tune** — QLoRA on Llama 3.2 1B (rank=16, adamw_8bit)
7. **Deploy** — GGUF q4_k_m export → llama.cpp local inference

### Next Steps

- [ ] Begin batch generation across all 9 categories
- [ ] Monitor LLM judge quality scores and adjust thresholds
- [ ] Run merge and validation after first generation pass
- [ ] Fine-tune base model on accepted data
- [ ] Benchmark fine-tuned model against base Llama 3.2 1B

---

## ✅ Shadow City

### What It Is

A noir RPG designed to showcase the Gamemodes NPC engine. Set in a rain-soaked dystopian metropolis where six factions wage silent war for control. The game runs as a Flask web application backed by SQLite, with LLM-powered NPC dialogue.

### Status

**Rebuild v2: Complete — 266 tests passing across 5 phases.**

| Phase | Name | Tests | Status |
|-------|------|-------|--------|
| R1 | LLM Module Rebuild | 74 | ✅ Complete |
| R2 | IFS Prompt Engineering | 70 | ✅ Complete |
| R3 | Integration + Engine Updates | 36 | ✅ Complete |
| R4 | Model Swap Infrastructure | 43 | ✅ Complete |
| R5 | Testing + Tuning | 43 | ✅ Complete |

### What Was Built

**Core Systems:**
- World engine — tick processing, faction scores, D20 rolls, victory checking
- Task engine — pool-based job assignment, quest tree progression, difficulty scaling
- Storyline engine — faction narrative tracking, victory/defeat generation
- NPC interaction — affinity system, psychological profiles, help requests, romance
- Conversation engine — NPC-NPC spawning, player interaction, conversation simulation
- Asylum engine — commitment system, sanity checks
- Simulation engine — high-speed tick loop for batch testing

**LLM Module (shadow-city/server/llm/):**
- Abstract `LLMProvider` interface — model-agnostic design
- Bonsai 8B provider via llama.cpp (default model, ~1GB VRAM)
- OpenAI-compatible fallback provider
- Synchronous LLM client with retry logic
- Noir post-processor for dialogue responses
- 6 model profiles (bonsai-8b, bonsai-4b, llama-3.2-1b, qwen2.5-7b, mistral-7b, generic-openai)
- Response caching layer
- Prompt proficiency evaluation system
- Model-agnostic prompt templates with behavioral instructions per psychological mode
- Context assembly and window management
- Model-specific chat template formatters (qwen3, chatml, llama3)
- Fallback dialogue system when LLM unavailable

**Key Design Decisions:**
1. **Prompts over fine-tuning** — structured prompt templates produce differentiated dialogue WITHOUT fine-tuning. The prompts ARE the product.
2. **Model-agnostic templates** — content defined separately from model-specific formatting
3. **Graceful degradation** — pre-written fallback responses when LLM unavailable; game never stops
4. **Runtime model swap** — switch between 6 model profiles at runtime via API, no restart needed

**Game Content:**
- 6 factions with distinct themes and victory quests
- Pool-based job system with quest tree progression
- 5-rank system (Recruit → Faction Leader)
- Phase 8 medical/mortality system — sickness, drugs, therapy, addiction
- NPC-NPC spontaneous conversations (3-5 per tick)
- Player-NPC conversations (2-3 per tick)
- Prompt proficiency system — evaluates player tactical thinking

### Six Factions

| Faction | Theme | Victory Quest |
|---------|-------|---------------|
| Police | Internal corruption vs. duty | "Operation: Takedown" |
| Crime | Family loyalty vs. ambition | "The Crown" |
| Journalist | Truth vs. survival | "The Final Story" |
| Political | Power vs. conscience | "The Great Cover-Up" |
| Military | Classified threat | "Eliminate the Threat" |
| Medical Corps | Neutral healer | N/A (supports all) |

### Model Infrastructure

| Model | Parameters | Quantization | VRAM | Role |
|-------|-----------|-------------|------|------|
| Bonsai 8B | 8.2B | Q1_0 (1-bit) | ~1 GB | Primary dialogue generation |
| Llama 3.2 1B | 1.2B | Q4_K_M | ~0.5 GB | Simple exchanges, fallback |
| Bonsai 4B | 4B | 1-bit | ~0.7 GB | Mid-tier (planned) |

### Next Steps

- [ ] Integration with fine-tuned Gamemodes model when available
- [ ] Performance benchmarks across model configurations
- [ ] Additional game content and faction quests
- [ ] Web UI polish and mobile support

---

## 🔧 Skyrim IFS Dialogue Engine

### What It Is

A Skyrim Special Edition mod that gives NPCs dynamic, psychologically authentic dialogue. Players type messages to NPCs via a console command; the engine generates responses through a C++ SKSE plugin communicating with a local Python dialogue server.

### Architecture

```
SKSE Plugin (C++) → HTTP POST → Python Flask Server (localhost:8080) → LLM (llama.cpp)
      ↑                                      ↓
  Skyrim Game                          NPC State + IFS Profiles
   Engine                              Prompt Builder → Response
```

### Status

| Component | Status |
|-----------|--------|
| Flask dialogue server (8 endpoints) | ✅ Complete |
| 18 NPC IFS profiles (all major factions) | ✅ Complete |
| 22 game event triggers with stress/part mappings | ✅ Complete |
| Dual model routing (Bonsai 8B + Llama 1B) | ✅ Complete |
| Three prompt tiers (Trained/Instructed/Hybrid) | ✅ Complete |
| SKSE plugin (C++ CommonLibSSE-NG) | ✅ Complete |
| NPC resolver (crosshair + name search) | ✅ Complete |
| Papyrus native function registration (3 functions) | ✅ Complete |
| Response cache (thread-safe, TTL-based) | ✅ Complete |
| Fallback dialogue system (~70 lines) | ✅ Complete |
| Training data generation (~5,000 Alpaca examples) | 🔄 In Progress |
| Fine-tuning on training data | 📋 Planned |
| Custom text input UI | 📋 Planned |
| Subtitle-style display with typewriter effect | 📋 Planned |
| Voice synthesis (xVASynth / Piper) | 📋 Planned |
| Dynamic NPC discovery | 📋 Planned |

### NPCs (18 total)

Covering all major Skyrim factions — companions, mages, guards, faction leaders, and civilians. Each NPC has full psychological profiles defining how each psychological mode manifests for that specific character.

### Dual Model Routing

| Request Type | Model | Port |
|-------------|-------|------|
| Complex (long prompt, high stress, multi-mode) | Bonsai 8B | 8080 |
| Simple (short prompt, low stress) | Llama 1B | 8081 |
| Both unavailable | Fallback dialogue | — |

### Prompt Tiers

| Tier | Used For | System Prompt | Behavioral Instructions | Genre Rules |
|------|----------|---------------|------------------------|-------------|
| Trained | Fine-tuned models | No | No | No |
| Instructed | Base models (Bonsai 8B) | Yes | Yes | Yes |
| Hybrid | Partially fine-tuned | Yes | Summary | Yes |

### Next Steps

- [ ] Complete training data generation
- [ ] Fine-tune Llama 1B on generated data
- [ ] Build custom text input UI (replace console command)
- [ ] Add subtitle-style display with typewriter effect
- [ ] Voice synthesis integration
- [ ] MCM (Mod Configuration Menu) integration

---

## 🔧 Fallout 4 NPC Dialogue Engine

### What It Is

A Fallout 4 mod using the same engine architecture — F4SE plugin captures player input, routes through a Python dialogue server, and generates wasteland-appropriate dialogue. Nine NPCs across five factions, each with full psychological profiles.

### Status

| Component | Status |
|-----------|--------|
| NPC data profiles (9 NPCs, 5 factions) | ✅ Complete |
| IFS templates (per-faction psychological templates) | ✅ Complete |
| JSON schema (full validation) | ✅ Complete |
| LLM client (multi-backend with failover + rate limiting) | ✅ Complete |
| Dialogue server (Flask, port 8080, 3 endpoints) | ✅ Complete |
| Training data (10,682 Alpaca-format entries) | ✅ Complete |
| Training data scripts (generate, validate, fix) | ✅ Complete |
| Build system (CMake + VS 2022) | ✅ Working |
| F4SE plugin (C++ skeleton) | ⚠️ Skeleton only |
| Training data cleanup | 🔲 Needed |
| Fine-tuning script | 📋 Planned |
| Speech-to-text | 📋 Future |
| Text-to-speech | 📋 Future |

### NPCs (9 total)

| ID | Name | Faction | Dominant Mode | Stress |
|----|------|---------|---------------|--------|
| bos_kellan_voss | Kellan Voss | Brotherhood | Protective | 35 |
| bos_elena_cross | Elena Cross | Brotherhood | Protective | 50 |
| inst_dr_marlowe | Dr. Elias Marlowe | Institute | Reactive | 70 |
| inst_synth_xm7 | XM-7 ("Marcus") | Institute | Vulnerable | 65 |
| rr_desdemona_kane | Desdemona Kane | Railroad | Protective | 55 |
| raid_razor_jack | Jack "Razor" Morrison | Raiders | Reactive | 75 |
| raid_mama_murphy_clone | Chems Sally | Raiders | Reactive | 80 |
| sett_abigail_farm | Abigail Stone | Settlers | Protective | 40 |
| sett_young_tommy | Tommy Reyes | Settlers | Balanced | 15 |

### Training Data

**10,682 Alpaca-format entries** across 10 categories (generated 2026-03-31 to 2026-04-03):

| Category | Target | Actual |
|----------|--------|--------|
| npc_dialogue_ifs | 2,000 | 2,065 |
| faction_voice | 1,500 | 1,501 |
| affinity_modulated | 1,500 | 1,500 |
| task_guidance | 1,000 | 1,008 |
| medical_stress | 800 | 800 |
| romantic | 600 | 600 |
| moral_dilemma | 800 | 800 |
| companion_bonding | 800 | 800 |
| survival_scenarios | 800 | 808 |
| conversation_depth | 800 | 800 |

**Known issues:**
- 2 empty outputs (need removal)
- 47 truncated responses (need cleanup)
- 82 extra entries from generator restarts (need deduplication)

**Generation stats:** 1,222 successful LLM calls, 147 failed, 9 fallbacks.

### F4SE Plugin — What's Needed

The plugin currently loads and logs but doesn't hook console commands or make HTTP calls. Next steps:

1. Console command registration (`npcdialogue`)
2. WinHTTP client to call `http://localhost:8080/dialogue`
3. In-game text display for NPC responses

### Next Steps

- [ ] Clean training data (remove empty/truncated, deduplicate)
- [ ] Complete F4SE plugin (console command hook, HTTP client, display)
- [ ] Write fine-tuning script
- [ ] Fine-tune model on cleaned data
- [ ] Dynamic stress/loyalty tracking
- [ ] Multi-NPC conversations

---

## Cross-Project Roadmap

### Phase 1: Data (Current)
- [x] Shadow City — 266 tests, full simulation pipeline
- [x] Skyrim — training data generation in progress (~5,000)
- [x] Fallout 4 — 10,682 training examples generated
- [ ] Gamemodes Core — 2,100 examples to generate

### Phase 2: Training
- [ ] Clean and merge training data across projects
- [ ] Fine-tune Llama 3.2 1B on combined dataset
- [ ] Benchmark fine-tuned model vs. Bonsai 8B prompted approach
- [ ] Export GGUF for local inference

### Phase 3: Integration
- [ ] Deploy fine-tuned model to Shadow City
- [ ] Deploy fine-tuned model to Skyrim mod
- [ ] Deploy fine-tuned model to Fallout 4 mod
- [ ] Complete F4SE/SKSE plugin integration

### Phase 4: Optimization
- [ ] Evaluate BitNet (Microsoft) as next-gen baseline
- [ ] Bonsai 4B mid-tier routing
- [ ] Quantization optimization (TurboQuant pipeline)
- [ ] Performance benchmarks across hardware configs

### Phase 5: Expansion
- [ ] Additional game integrations
- [ ] Voice synthesis pipeline
- [ ] Dynamic NPC discovery (auto-profile generation)
- [ ] Community tools and contributor documentation

---

*Gamemodes — Game Model Development Studio*
*gamemodes.dev@gmail.com*
