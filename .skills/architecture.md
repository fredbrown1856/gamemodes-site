# 🏗️ System Architecture

Overview of the Gamemodes project's two-tier deployment.

---

## 🌐 Two-Tier Deployment

```
┌─────────────────────────────────┐     ┌──────────────────────────────────┐
│   GitHub Pages (Static)         │     │   Railway (Flask Backend)        │
│   gamemodes.xyz                 │     │   chat.gamemodes.xyz             │
│                                 │     │                                  │
│   index.html (inline CSS/JS)    │────▸│   Wendy Flask App                │
│   - Hero, project showcases     │ API │   - Session management           │
│   - Stats bar (live fetch)      │     │   - Queue system                 │
│   - "Meet Wendy" CTA            │     │   - LLM chat (Cerebras)          │
│   - Footer                      │     │   - SQLite database              │
│                                 │     │   - Bot protection               │
└─────────────────────────────────┘     └──────────────────────────────────┘
```

- **GitHub Pages** serves the static marketing site — no server-side processing
- **Railway** runs the Wendy Flask backend — handles live demo sessions
- The only connection between tiers: the main site fetches live stats from the backend API and links to the demo CTA

---

## 🌍 Domain Structure

| Domain | Platform | Purpose |
|--------|----------|---------|
| `gamemodes.xyz` | GitHub Pages | Static marketing site |
| `www.gamemodes.xyz` | GitHub Pages | Redirects to `gamemodes.xyz` |
| `chat.gamemodes.xyz` | Railway (CNAME) | Wendy NPC demo backend |

---

## 📊 Data Flow: Demo Session

```
gamemodes.xyz                     chat.gamemodes.xyz
─────────────                     ──────────────────
User clicks CTA
      │
      ▼
Open chat.gamemodes.xyz/?demo
      │
      ├── POST /api/demo/start
      │     ├── Honeypot check (bot_check.py)
      │     ├── User-agent check
      │     ├── IP rate limit check
      │     ├── Slot available? → Create session + conversation
      │     └── Slot full? → Join FIFO queue
      │
      ├── GET /api/demo/status (poll every 3s)
      │     └── Returns queue position or time_remaining
      │
      ├── POST /api/demo/chat (user sends message)
      │     ├── Validate session token + timer
      │     ├── Check daily cache (self-referential?)
      │     ├── LLM affinity analysis
      │     ├── Clamp affinity shift (demo: max ±5)
      │     ├── Never deactivate in demo mode (force_active)
      │     ├── Build system prompt with daily briefing
      │     ├── LLM generates Wendy's response
      │     ├── Cache if self-referential
      │     └── Return response + time_remaining
      │
      └── Timer hits 0 → Session expires, UI shows goodbye
```

---

## 🧩 Backend Modules

| Module | File | Purpose |
|--------|------|---------|
| **Session Manager** | [`session_manager.py`](../Wendy/session_manager.py) | Token lifecycle — create, validate, expire demo sessions |
| **Queue Manager** | [`queue_manager.py`](../Wendy/queue_manager.py) | FIFO wait queue — join, poll, promote, timeout stale entries |
| **Bot Check** | [`bot_check.py`](../Wendy/bot_check.py) | Honeypot field validation, IP hash rate limiting, UA blocking |
| **Daily Cache** | [`daily_cache.py`](../Wendy/daily_cache.py) | Daily briefing generation + self-referential response caching |
| **Training Export** | [`training_export.py`](../Wendy/training_export.py) | AES-256-GCM encrypted Alpaca-format data export |
| **Database** | [`database.py`](../Wendy/database.py) | SQLite CRUD — conversations, messages, affinity, sessions, stats |
| **Wendy** | [`wendy.py`](../Wendy/wendy.py) | Character system — prompt assembly, affinity stages, fallback analysis |
| **LLM Client** | [`llm_client.py`](../Wendy/llm_client.py) | LLM abstraction — OpenAI-compatible API client with MockClient fallback |
| **App** | [`app.py`](../Wendy/app.py) | Flask routes, CORS, config loading, initialization |

---

## 💾 Database Schema

SQLite with 7 tables, managed by [`database.py`](../Wendy/database.py):

| Table | Purpose |
|-------|---------|
| `conversations` | Conversation records with affinity, active status, timestamps |
| `messages` | Individual messages (user/assistant/system roles) |
| `affinity_log` | Affinity change history with reasons |
| `sessions` | Demo session tokens with expiry times |
| `daily_cache` | Cached self-referential responses (refreshed daily) |
| `training_export_log` | Audit log of training data exports |
| `public_stats` | Key-value counters (total_sessions, total_messages) |

> See [`database_schema.md`](../Wendy/skills/database_schema.md) for full column details.

---

## 🔐 Security

| Layer | Mechanism |
|-------|-----------|
| **Bot protection** | Hidden honeypot field (`website_url`), blocked user-agents, IP-hash rate limiting |
| **Privacy** | Visitor IPs are salted + hashed before storage (never stored raw) |
| **Encryption** | Training exports use AES-256-GCM with env-var-stored key |
| **CORS** | Allowlist of specific origins in [`config.json`](../Wendy/config.json) |
| **Admin auth** | Bearer token (`ADMIN_TOKEN` env var) for protected endpoints |
| **Session tokens** | Signed with `SESSION_SECRET`, auto-expire after duration |
| **Rate limiting** | Max 3 session attempts per hashed IP per hour |

---

## ⚙️ Key Configuration

| Setting | Value | Location |
|---------|-------|----------|
| Concurrent sessions | 2 | `config.json → demo.max_concurrent_sessions` |
| Session duration | 15 minutes | `config.json → demo.session_duration_minutes` |
| Max affinity shift (demo) | ±5 per message | `config.json → demo.max_shift_per_message_demo` |
| Queue max size | 20 | `config.json → demo.max_queue_size` |
| Queue timeout | 5 minutes | `config.json → demo.queue_timeout_minutes` |
| LLM provider | Cerebras (free tier) | `config.json → llm.provider` |
| LLM model | llama3.1-8b | `config.json → llm.model` |
| Hostile deactivation | Disabled in demo | `config.json → demo.min_messages_before_hostile: 99999` |
