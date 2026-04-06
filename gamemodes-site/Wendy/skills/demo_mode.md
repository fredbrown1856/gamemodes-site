# Demo Mode — Wendy Public Demo

## Overview

Wendy can operate in "demo mode" for public visitors on the Gamemodes website. Demo mode adds session management, queuing, bot protection, daily consistency caching, and encrypted training data export on top of the existing chat system.

## Activation

Demo mode is triggered by adding `?demo` to the URL: `https://chat.gamemodes.xyz?demo`

The frontend checks for this parameter in [`script.js`](../static/script.js) and initializes the demo flow instead of the normal chat interface.

## User Flow

1. **Welcome Screen** → Visitor sees Wendy intro + "Start Conversation" button
2. **Bot Check** → Hidden honeypot field + IP rate limit check (server-side)
3. **Queue or Chat** → If slot available (2 max), enter chat. Otherwise, wait in queue.
4. **10-Minute Session** → Countdown timer in header, chat with Wendy
5. **Session End** → "Thanks for helping Wendy grow!" screen with stats

## Configuration

Demo mode is configured in [`config.json`](../config.json) under the `demo` section:

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | true | Enable/disable demo mode |
| `session_duration_minutes` | 10 | Session length |
| `max_concurrent_sessions` | 2 | Simultaneous sessions (Cerebras free tier limit) |
| `max_queue_size` | 20 | Max visitors waiting |
| `queue_timeout_minutes` | 5 | Remove from queue after no polling |
| `warning_seconds_before_expiry` | 30 | When timer turns red |

## Database Tables

Demo mode adds 4 tables to the SQLite database:

| Table | Purpose |
|-------|---------|
| `sessions` | Active and expired demo sessions |
| `daily_cache` | Daily briefing + cached self-referential responses |
| `training_export_log` | Audit trail of training data exports |
| `public_stats` | Live counters (total conversations, messages) |

## Daily Consistency Cache

Wendy maintains consistency across visitors each day through 3 layers:

1. **Fixed facts** — Always in system prompt (name, age, background)
2. **Daily briefing** — Generated once/day by LLM (weather, mood, activities)
3. **Response cache** — First response to self-referential questions is cached and reused

Cache is stored in `daily_cache` table and resets at midnight UTC.

## Training Data Export

All exports are AES-256-GCM encrypted to protect proprietary methodology:

```bash
# Generate an encryption key (one-time setup)
python -c "from training_export import generate_encryption_key; print(generate_encryption_key())"

# Export training data (requires admin token)
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     "https://chat.gamemodes.xyz/api/export/training?min_affinity=10" \
     -o training_data.enc
```

Quality filters:
- Only conversations reaching Acquaintance stage (affinity ≥ 10)
- Tagged by affinity stage for balanced training sets
- Deduplicated via training_export_log

## Deployment

See [`plans/wendy-live-demo-integration.md`](../../plans/wendy-live-demo-integration.md) for the full architecture and deployment guide.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CEREBRAS_API_KEY` | Yes | LLM inference API key |
| `SESSION_SECRET` | Yes | Secret for session token generation |
| `ADMIN_TOKEN` | Yes | Bearer token for training data export |
| `TRAINING_ENCRYPTION_KEY` | Yes | Base64-encoded 32-byte AES key |
| `IP_HASH_SALT` | No | Salt for IP hashing (default: gamemodes-wendy) |
