# 🎮 Gamemodes — Start Here

## Project Overview
**Gamemodes** (Game Model Development Studio) is an AI-native NPC dialogue engine that generates psychologically authentic, dynamic dialogue for video game characters using fine-tuned language models. It replaces traditional pre-written dialogue trees with real-time, contextually aware responses.

## Website
- **Domain**: gamemodes.xyz (GitHub Pages)
- **Entry Point**: `index.html` (single-page static site)
- **No build tools** — plain HTML, CSS, and JavaScript

## Repository Structure
```
/
├── index.html    — Main website (single-page, all content inline)
├── CNAME         — Custom domain for GitHub Pages (gamemodes.xyz)
├── DEVLOG.md     — Development log tracking all project milestones
├── README.md     — Project documentation and setup instructions
├── LICENSE       — Apache 2.0 license
├── .skills/      — AI bot skill files (this directory)
├── plans/        — Architecture plans and integration designs
└── Wendy/        — Live NPC demo with affinity system
```

## Five Projects Showcased
1. **Shadow City** — Noir RPG showcase game (266 tests passing)
2. **Skyrim Mod** — Skyrim Special Edition integration (18 NPCs)
3. **Fallout 4 Mod** — Fallout 4 integration (9 NPCs, 10,682 training examples)
4. **Gamemodes Core** — Training pipeline and fine-tuning system
5. **Wendy** — Live NPC demo with affinity system (chat.gamemodes.xyz)

## Tech Stack (for reference when editing content)
- Python/Flask (dialogue server backend)
- C++ SKSE/F4SE (game plugin integration)
- llama.cpp (local LLM inference)
- SQLite (database for Shadow City)
- QLoRA (fine-tuning methodology)
- GGUF format (model deployment)

## Key Conventions
- All website content lives in `index.html` (inline CSS and JS)
- The DEVLOG uses emoji headers and status tables with ✅/🚧/⏳ markers
- The site uses a dark theme with syntax-highlighted code blocks
- No external dependencies or frameworks

## Related Skill Files
- [Content Guidelines](./content_guidelines.md) — What can/cannot appear in public content
- [Website Editing Guide](./website_editing.md) — How to edit the site safely
- [Deployment](./deployment.md) — How the site is deployed
