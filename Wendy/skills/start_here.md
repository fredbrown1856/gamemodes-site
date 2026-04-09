# Start Here — Wendy NPC Conversation Demo

## Project Summary

Wendy is an interactive NPC conversation demo featuring a 22-year-old Appalachian woman from eastern Kentucky. The project uses an LLM (OpenAI GPT) to generate character-driven dialogue that dynamically adapts based on an "affinity" system — a numerical score (-100 to +100) tracking how much Wendy likes or trusts the user. Conversations flow through Flask endpoints, affinity is analyzed per-message via a secondary LLM call, and all state is persisted in SQLite. The frontend is vanilla HTML/CSS/JS with no frameworks.

## ⚠️ PROPRIETARY NOTICE — WEBSITE PROJECT

> **This project publishes content to the PUBLIC website at gamemodes.xyz.**
>
> The IFS (Internal Family Systems) psychology model is **proprietary**. When updating any website content:
>
> 1. **NEVER** reference "IFS", "Internal Family Systems", "parts system", "Manager/Firefighter/Exile" on the website
> 2. **NEVER** reveal the proprietary personality model's structure or mechanics publicly
> 3. Use only generic descriptions: "personality engine", "behavioral depth", "psychological realism"
> 4. Before pushing ANY update, search for: "IFS", "Internal Family Systems", "Manager", "Firefighter", "Exile", "Self Energy", "affinity", "protector", "parts"
> 5. Remove or replace all matches with generic terminology
>
> The website is PUBLIC and indexed by search engines. Protect the IP.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Web Framework | Flask 3.x |
| Database | SQLite 3 (stdlib) |
| LLM Provider | OpenAI API (gpt-4o-mini default) |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Dependencies | `flask>=3.0.0`, `openai>=1.0.0` |

## Quick Start

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
python app.py
```

Or set the key in [`config.json`](../config.json:12) under `llm.api_key`. The app runs on `http://127.0.0.1:5000` by default.

If no API key is configured, the app falls back to [`MockClient`](../llm_client.py:223) which returns canned responses.

## Architecture Overview

```
User message
  → POST /api/chat (app.py)
    → Save user message to DB (database.py)
    → LLM analyzes affinity shift (llm_client.py::analyze_affinity)
    → Fallback: keyword matching if LLM fails (wendy.py::fallback_affinity_analysis)
    → Clamp shift, update affinity in DB (database.py::update_affinity)
    → Build system prompt with new affinity (wendy.py::build_system_prompt)
    → LLM generates Wendy's response (llm_client.py::generate_response)
    → Save assistant message to DB
    → Return JSON: message + affinity + stage
  → Frontend updates UI (script.js)
```

### Demo Mode

When accessed with `?demo` URL parameter, the app runs in public demo mode:
- Visitors pass a honeypot bot check
- If 2 slots are available, they get a 10-minute timed session
- If full, they enter a FIFO queue and are promoted when a slot opens
- Wendy's daily briefing is injected for consistency across visitors
- Self-referential responses are cached per day
- All conversations are stored for encrypted training data export

**Demo Routes** (in [`app.py`](../app.py)):

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/demo/start` | POST | Bot check + session/queue allocation |
| `/api/demo/status` | GET | Queue position or session time remaining |
| `/api/demo/chat` | POST | Session-aware chat (validates token, checks timer) |
| `/api/demo/stats` | GET | Public conversation/message counts |
| `/api/export/training` | GET | Admin-only encrypted training data export |

**Demo Modules**:

| Module | Purpose |
|--------|---------|
| [`session_manager.py`](../session_manager.py) | Session token lifecycle |
| [`queue_manager.py`](../queue_manager.py) | FIFO wait queue |
| [`bot_check.py`](../bot_check.py) | Honeypot + rate limiting |
| [`daily_cache.py`](../daily_cache.py) | Daily consistency cache |
| [`training_export.py`](../training_export.py) | AES-256-GCM encrypted export |

### TTS Module

| Module | Purpose |
|--------|---------|
| [`tts_client.py`](../tts_client.py) | MiMo TTS API client with base64 response parsing |
| [`test_tts.py`](../test_tts.py) | Offline test script for TTS connectivity |

### TTS Route (in [`app.py`](../app.py))

| Function | Route | Method | Purpose |
|----------|-------|--------|---------|
| `tts_handler()` | `/api/tts` | POST | Generate TTS audio for text, returns audio/mpeg |

## Key Concepts

### Affinity System
- Range: -100 to +100, starts at 0
- Each user message triggers an LLM analysis that produces a shift (typically ±1-15)
- Shift is clamped by `max_shift_per_message` (default 15)
- Affinity is clamped to [-100, 100]
- If affinity drops to -50 or below, conversation ends

### Affinity Stages
Eight stages define Wendy's behavior:

| Stage | Range | Color | Behavior |
|-------|-------|-------|----------|
| Hostile | -100 to -50 | Red | Angry, wants user to leave |
| Cold | -49 to -20 | Orange | Guarded, dismissive, sarcastic |
| Distant | -19 to -10 | Amber | Polite but surface-level |
| Stranger | -9 to +9 | Gray | Neutral, cautious, basic info only |
| Acquaintance | +10 to +29 | Lime | Warming up, sharing opinions |
| Friendly | +30 to +49 | Green | Open, uses terms of endearment |
| Close | +50 to +69 | Cyan | Trusted friend, emotionally open |
| Trusted | +70 to +100 | Purple | Deepest secrets, fully invested |

### Conversation Lifecycle
1. User creates conversation (affinity = 0, stage = Stranger)
2. Messages exchanged, affinity shifts per message
3. If affinity ≤ -50, conversation deactivates — Wendy gives a dismissive message and stops responding
4. User can start a new conversation from the sidebar

## File Index

### Root Files

| File | Purpose | Key Contents |
|------|---------|--------------|
| [`app.py`](../app.py) | Flask application, main entry point | All route handlers, app initialization |
| [`config.json`](../config.json) | Central configuration | Server, DB, LLM, affinity stages, Wendy character |
| [`database.py`](../database.py) | SQLite operations | Schema init, CRUD for conversations/messages/affinity |
| [`wendy.py`](../wendy.py) | Character system | System prompt assembly, affinity calculations, stage resolution |
| [`llm_client.py`](../llm_client.py) | LLM abstraction layer | `LLMClient` base, `OpenAIClient`, `MockClient`, factory function |
| [`requirements.txt`](../requirements.txt) | Python dependencies | flask, openai, flask-cors, cryptography |
| [`README.md`](../README.md) | Project readme | Overview and setup instructions |
| [`ARCHITECTURE.md`](../ARCHITECTURE.md) | Architecture documentation | System design notes |
| [`session_manager.py`](../session_manager.py) | Demo session lifecycle | Token create, validate, expire |
| [`queue_manager.py`](../queue_manager.py) | Demo FIFO wait queue | Queue position, promotion, timeout |
| [`bot_check.py`](../bot_check.py) | Bot protection | Honeypot, IP rate limit, UA blocking |
| [`daily_cache.py`](../daily_cache.py) | Daily consistency cache | Briefing + response caching |
| [`training_export.py`](../training_export.py) | Training data export | AES-256-GCM encrypted Alpaca format |
| [`tts_client.py`](../tts_client.py) | MiMo TTS client | `MiMoTTSClient`, `create_tts_client()` factory |
| [`test_tts.py`](../test_tts.py) | TTS offline test | API connectivity check, voice comparison |
| [`.env.example`](../.env.example) | Environment variable template | Required env vars for deployment |

### app.py — Routes

| Function | Route | Method | Purpose |
|----------|-------|--------|---------|
| `load_config()` | — | — | Load config.json with env var overrides |
| `chat_handler()` | `/api/chat` | POST | Process user message, return Wendy's response |
| `new_conversation_handler()` | `/api/conversations/new` | POST | Create new conversation |
| `get_conversation_handler()` | `/api/conversations/<id>` | GET | Load conversation with messages |
| `list_conversations_handler()` | `/api/conversations` | GET | List all conversations (paginated) |
| `delete_conversation_handler()` | `/api/conversations/<id>` | DELETE | Delete conversation and related data |
| `demo_start_handler()` | `/api/demo/start` | POST | Bot check + session/queue allocation |
| `demo_status_handler()` | `/api/demo/status` | GET | Queue position or session time remaining |
| `demo_chat_handler()` | `/api/demo/chat` | POST | Session-aware chat (validates token, checks timer) |
| `demo_stats_handler()` | `/api/demo/stats` | GET | Public conversation/message counters |
| `export_training_handler()` | `/api/export/training` | GET | Admin-only encrypted training data export |
| `index()` | `/` | GET | Serve main chat UI |
| `serve_static()` | `/static/<filename>` | GET | Serve static files |
| `not_found()` | — | — | 404 handler |
| `internal_error()` | — | — | 500 handler |

### Demo Config ([`config.json`](../config.json) `demo` section)

| Key | Default | Purpose |
|-----|---------|---------|
| `enabled` | `true` | Enable/disable demo mode |
| `session_duration_minutes` | `15` | How long each demo session lasts |
| `max_concurrent_sessions` | `2` | Simultaneous sessions allowed |
| `max_queue_size` | `20` | Max visitors waiting in queue |
| `queue_timeout_minutes` | `5` | How long before queue entry expires |
| `warning_seconds_before_expiry` | `30` | Timer warning before session ends |
| `max_shift_per_message_demo` | `5` | Smaller affinity shifts in demo (vs 15 normal) |
| `min_messages_before_hostile` | `99999` | Effectively disables hostile deactivation in demo |

### database.py — Functions

| Function | Purpose |
|----------|---------|
| `init_db(db_path)` | Create tables if not exist, set module-level DB path |
| `get_connection()` | Return SQLite connection with Row factory |
| `create_conversation()` | Insert new conversation (affinity=0, active=1) |
| `get_conversation(id)` | Fetch single conversation by ID |
| `list_conversations(limit, offset)` | Paginated conversation list with last message preview |
| `delete_conversation(id)` | Delete conversation (cascades to messages + affinity_log) |
| `add_message(conv_id, role, content)` | Insert message, update conversation timestamp |
| `get_messages(conv_id, limit)` | Fetch messages ordered by timestamp ASC |
| `update_affinity(conv_id, shift, reason)` | Apply affinity shift, log change, deactivate if hostile |
| `get_affinity_log(conv_id)` | Fetch affinity change history |

### wendy.py — Functions

| Function | Purpose |
|----------|---------|
| `build_system_prompt(affinity, config)` | Assemble full system prompt with stage info |
| `get_stage(affinity, config)` | Resolve affinity value to stage dict |
| `get_stage_label(affinity, stages)` | Get just the stage label string |
| `get_stage_behavior(label, stages)` | Get behavior description for a stage |
| `format_messages(messages)` | Format DB messages for LLM (user/assistant only) |
| `format_messages_for_llm(messages, system_prompt)` | Format with system prompt prepended |
| `calculate_affinity_shift(analysis, config)` | Clamp raw LLM shift to max_shift_per_message |
| `should_end_conversation(affinity, config)` | Check if affinity ≤ hostile_threshold |
| `get_affinity_description(affinity)` | Human-readable emotional state description |
| `fallback_affinity_analysis(message, config)` | Keyword-based sentiment fallback |
| `get_dismissive_message()` | Random dismissive line when conversation ends |

### llm_client.py — Classes & Functions

| Name | Purpose |
|------|---------|
| `LLMError` | Custom exception for LLM failures |
| `LLMClient` (ABC) | Abstract base: `generate_response()`, `analyze_affinity()` |
| `OpenAIClient` | OpenAI API implementation |
| `MockClient` | Test stub, returns canned responses |
| `create_client(config)` | Factory: returns OpenAIClient or MockClient |

### templates/index.html — Sections

| Section | Description |
|---------|-------------|
| Sidebar | Conversation list with "New Chat" button |
| Chat Header | Wendy avatar, name, stage label, affinity bar |
| Messages Area | Scrollable message list with typing indicator |
| Input Area | Textarea with send button, disabled state |
| Modal | Confirmation dialog for starting new chat |

### static/script.js — Key Sections

| Section | Description |
|---------|-------------|
| `state` (lines 13-21) | App state: conversation ID, messages, affinity, stage |
| `DOM` (lines 27-48) | Cached DOM element references |
| API Helpers (lines 54-136) | `apiRequest()`, `sendMessage()`, `createConversation()`, etc. |
| Utility Functions (lines 142-233) | `formatTimestamp()`, `getAffinityColor()`, `escapeHtml()`, `showError()` |
| Affinity Display (lines 239-271) | `updateAffinityDisplay()` — bar/marker/label updates |
| Message Rendering (lines 276-356) | `createMessageElement()`, `renderMessages()`, `appendMessage()` |
| Sidebar (lines 403-477) | `renderConversationList()`, `refreshConversationList()`, `toggleSidebar()` |
| Core Actions (lines 505-661) | `loadConversation()`, `startNewConversation()`, `handleSendMessage()` |
| Event Listeners (lines 667-745) | All DOM event bindings |
| Initialization (lines 751-767) | `init()` — loads conversations, creates first chat |

### static/style.css — Key Sections

| Lines | Section |
|-------|---------|
| 7-81 | CSS Variables (colors, spacing, affinity gradient) |
| 83-133 | Reset & base styles |
| 139-143 | App layout (flexbox container) |
| 149-326 | Sidebar styles |
| 332-338 | Main chat area |
| 344-412 | Chat header |
| 418-470 | Affinity display (bar, marker, value) |
| 476-500+ | Messages area and bubbles |
