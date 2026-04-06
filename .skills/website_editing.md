# 🌐 Website Editing Guide

## Architecture
The entire website is a single `index.html` file with:
- **Inline CSS** in a `<style>` block
- **Inline JavaScript** in `<script>` blocks
- **No external dependencies** (no CDN links, no build tools)

## Sections in index.html
The page is structured as a single-page site with sections:
1. **Hero/Header** — Project name and tagline
2. **Stats Bar** — Key metrics (models, NPCs, accuracy, etc.)
3. **Shadow City** — Noir RPG showcase section
4. **Skyrim Mod** — Skyrim integration section
5. **Fallout 4 Mod** — Fallout 4 integration section
6. **Gamemodes Core** — Training pipeline section
7. **Architecture** — Technical architecture overview
8. **Footer** — Links and licensing

## Editing Rules
1. **Always preserve the dark theme** — CSS custom properties at the top control colors
2. **Code blocks use custom syntax highlighting** — CSS classes: `.cm` (comments), `.fn` (function names), `.hl1`-`.hl3` (highlights), `.kw` (keywords), `.st` (strings), `.tp` (types)
3. **Status badges** use emoji indicators: ✅ Complete, 🚧 In Progress, ⏳ Planned
4. **Keep all content in a single file** — do not split into multiple HTML files
5. **Test locally** by opening index.html directly in a browser

## Common Edits
- **Adding a new stat**: Find the stats bar grid and add a new `.stat-card` div
- **Updating NPC counts**: Search for the current number and replace
- **Adding a dev log entry**: Edit DEVLOG.md (separate from the website)
- **Updating progress**: Change emoji status indicators in tables
