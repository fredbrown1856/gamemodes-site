<p align="center">
  <strong>GAMEMODES</strong><br>
  <em>Game Model Development Studio</em>
</p>

<p align="center">
  AI-native NPC dialogue engine. Psychologically dynamic characters.<br>
  Fine-tuned models running locally on consumer hardware.
</p>

<p align="center">
  <a href="https://gamemodes.xyz">Website</a> · 
  <a href="#projects">Projects</a> · 
  <a href="#what-makes-it-different">What Makes It Different</a> · 
  <a href="#get-involved">Get Involved</a> · 
  <a href="mailto:gamemodes.dev@gmail.com">Contact</a>
</p>

---

## What Is This?

Gamemodes builds NPC dialogue engines that generate dynamic, contextually aware responses using fine-tuned language models small enough to run on a player's existing GPU. No cloud API calls. No latency. No subscription fees.

Every NPC has a proprietary psychological profile that governs how they respond to the player. The engine tracks each character's internal state — stress, needs, relationships, recent experiences — and produces dialogue that reflects who the character is *right now*, not a static script.

The same NPC asked the same question gives a meaningfully different answer depending on their current psychological state, whether they're exhausted or rested, and how much they trust you.

**The result:** NPCs that feel like people having a bad day, not chatbots reciting lore.

## What Makes It Different

Most LLM-in-games projects connect a chatbot API to an NPC and call it a day. The NPC sounds the same whether they just watched a friend die or they're relaxing at home. Gamemodes solves this with a proprietary psychological modeling layer that sits between the game engine and the language model.

**What the engine tracks:**
- Physiological states (stress, hunger, energy, and more) that decay and recover over time
- Relationship depth with the player and other NPCs
- Recent events the character has witnessed or experienced
- Environmental context — location, time of day, danger level

**What the engine produces:**
- Dialogue that shifts in tone, openness, and behavior based on the character's internal state
- Characters who reference their own circumstances naturally ("I haven't eaten since yesterday" when hunger is high)
- Personality consistency — the same character responds differently under pressure, but still sounds like themselves
- Distinct voices across characters — not just different names on the same chatbot

**What's proprietary:**
The psychological modeling system, prompt architecture, training methodology, and fine-tuned model weights are proprietary technology developed by Gamemodes. The integration infrastructure (game plugins, server scaffolding, model routing) is open.

## Architecture

```
Game Engine  →  Character State + Profile  →  Dialogue Engine  →  Response
                        │                          │
              Tracked states &               Proprietary
              relationship data              psychological
              (open)                         modeling layer
                                             (proprietary)
                                                  │
                                                  ▼
                                          Fine-tuned LLM
                                          (local inference)
```

The engine is designed as a middleware layer. It receives structured game state from any game engine, applies its psychological modeling, constructs an optimized prompt, and routes the request to the appropriate local model. The game never needs to know what model is running or how the psychology works — it sends state, it gets dialogue back.

**Multi-model routing:** The engine runs multiple models simultaneously and routes requests based on complexity. High-stakes player-facing dialogue goes to a larger model. Background NPC chatter goes to a smaller, faster model. If any model goes down, requests automatically fall back to the next available option. If everything is down, pre-written template responses keep the game running.

## Model Strategy

We build on 1-bit quantized models — an emerging class of language models that deliver full-size intelligence at a fraction of the memory footprint.

| Model | Size on Disk | VRAM | Role |
|-------|-------------|------|------|
| **Bonsai 8B** | 1.15 GB | ~1 GB | Primary — complex dialogue |
| **Bonsai 4B** | 0.57 GB | ~0.7 GB | Mid-tier — balanced quality and speed |
| **Fine-tuned 1B** | ~0.5 GB | ~0.5 GB | Fast — background conversations |

All models serve locally via llama.cpp. No cloud dependency. No per-token costs. No data leaving the player's machine.

Our fine-tuned models are trained on proprietary datasets using a multi-stage pipeline: simulation-generated examples, automated quality scoring across multiple dimensions, and iterative refinement. The training methodology produces models that understand our psychological framework natively — they need minimal prompting to generate differentiated character behavior.

## Projects

### Shadow City — Showcase Game

A noir RPG set in a rain-soaked dystopian metropolis. Six factions wage a silent war for control while a hidden alien threat lurks beneath the surface. Built as a Flask web application to demonstrate the full capabilities of the engine.

- Complete game engine with tick-based world simulation
- Six competing factions with branching quest trees
- Drug system with realistic pharmacology, addiction mechanics, and recovery paths
- NPC autonomous behavior — characters eat, sleep, work, socialize, and die on their own
- 266 tests passing across the full system

### Skyrim Mod

A Skyrim Special Edition mod that brings dynamic NPC dialogue to the Elder Scrolls. An SKSE plugin captures player input, routes through a local dialogue server, and returns character-appropriate responses.

- 18 NPC profiles covering all major Skyrim factions
- Race-specific speech patterns (Khajiit, Nord, Dunmer, Argonian, and more)
- Game event detection that influences character psychological state
- Full C++ SKSE plugin with CommonLibSSE-NG

### Fallout 4 Mod

Same engine architecture adapted for the post-apocalyptic wasteland. Nine NPCs across five factions.

- 10,600+ training examples generated and validated
- Multi-backend LLM client with automatic failover
- F4SE plugin with CMake build system

### Gamemodes Core

The engine and training pipeline itself. Genre-agnostic — proven across noir, fantasy, and post-apocalyptic settings. The psychological modeling works independently of game setting; only surface-level flavor (vocabulary, lore references, speech patterns) changes between games.

- Complete data pipeline: generation, validation, quality filtering, format conversion
- Automated quality scoring across multiple evaluation dimensions
- Fine-tuning pipeline optimized for consumer GPUs
- Local deployment via llama.cpp with OpenAI-compatible API

## Technical Overview

**Game Integration:** The engine connects to games through a lightweight HTTP API. A game plugin (SKSE for Skyrim, F4SE for Fallout 4, or any HTTP client) sends a POST request with the NPC identifier and player message. The server returns generated dialogue as JSON. Integration with a new game requires only an HTTP client on the game side — the psychological modeling, prompt construction, and model routing happen server-side.

**Prompt Architecture:** The engine uses a tiered prompt system that adapts to the active model's capabilities. Fine-tuned models that already understand the psychological framework receive compact, structured prompts. Base models receive more detailed instructions. This allows the same game integration to work across models of vastly different sizes without code changes.

**Training Pipeline:** Training data is generated through a combination of game simulation and structured LLM generation, then filtered through an automated quality assessment pipeline before fine-tuning. The methodology ensures consistent character voice, psychologically grounded behavior, and genre-appropriate tone.

**Deployment:** Everything runs locally. The dialogue server is a Python Flask application. Models are served via llama.cpp. The entire stack — game plugin, dialogue server, and language model — runs on the player's machine with no internet connection required.

## Get Involved

Gamemodes is in active development. We're looking for contributors in several areas:

**Game Modders** — Help build integrations for new games, expand NPC profiles, or test existing mods. Skyrim and Fallout 4 modding experience is especially valuable.

**Python Developers** — Work on the dialogue server, training pipeline, quality filtering, or simulation engine.

**C++ Developers** — Contribute to SKSE/F4SE plugin development. CommonLibSSE-NG experience is a plus.

**Writers & Narrative Designers** — Craft NPC backgrounds, design character archetypes, or write training scenarios. Understanding of character psychology is valued.

**QA & Testing** — Run simulations, test dialogue quality across scenarios, or help build automated evaluation frameworks.

## Status

| Component | Status |
|-----------|--------|
| Core dialogue engine | ✅ Active |
| Shadow City (showcase game) | ✅ Rebuild complete |
| Skyrim mod (server + SKSE plugin) | ✅ Built, training data in progress |
| Fallout 4 mod (server + data) | ✅ Training data complete |
| Model fine-tuning pipeline | 🔧 In progress |
| Bonsai 8B integration | ✅ Active |
| Dual-model routing | ✅ Active |
| Voice synthesis | 📋 Planned |

## License

The integration infrastructure (game plugins, server scaffolding, API interfaces) is open source.

The psychological modeling system, prompt architecture, training data, training methodology, and fine-tuned model weights are proprietary. See [LICENSE](LICENSE) for details.

## Contact

**Email:** gamemodes.dev@gmail.com  
**Web:** [gamemodes.xyz](https://gamemodes.xyz)

---

<p align="center">
  <em>Gamemodes — Game Model Development Studio</em><br>
  <em>NPCs that think. Not chatbots that recite.</em>
</p>
