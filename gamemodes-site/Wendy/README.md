# Wendy — NPC Conversation Demo

A standalone web application for conversing with **Wendy**, a 22-year-old Appalachian woman NPC. The system features a chat-style web interface backed by a Flask server with OpenAI API integration, an affinity system that tracks emotional regard from -100 to +100, SQLite persistence, and character depth that unlocks progressively based on affinity thresholds.

![Wendy Chat Interface](static/img/wendy_screenshot.png)

## Features

- **Rich Character System**: Wendy speaks with authentic Appalachian dialect and has a deep, multi-layered personality
- **Dynamic Affinity System**: Tracks emotional regard from -100 to +100 with 8 distinct relationship stages
- **Persistent Conversations**: SQLite database stores all conversations, messages, and affinity changes
- **Conversation History**: Browse and resume past conversations from the sidebar
- **Graceful Fallback**: Works without an API key using a mock LLM client for testing
- **Responsive Design**: Beautiful dark theme with warm rustic tones, works on desktop and mobile

## Prerequisites

- Python 3.10 or higher
- An LLM API key (free options available):
  - **Cerebras** (free, recommended) — [Sign up](https://inference.cerebras.ai/) for a free API key
  - **OpenAI** (paid) — [Get an API key](https://platform.openai.com/api-keys)
  - Or use **mock mode** for testing without any API key

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Your API Key

**Option A: Cerebras (Free — Recommended)**

1. Sign up at [Cerebras Inference](https://inference.cerebras.ai/) for a free API key
2. Set the environment variable and update `config.json`:

**Windows (Command Prompt):**
```cmd
set CEREBRAS_API_KEY=your-cerebras-key-here
```

**Windows (PowerShell):**
```powershell
$env:CEREBRAS_API_KEY="your-cerebras-key-here"
```

**macOS / Linux:**
```bash
export CEREBRAS_API_KEY=your-cerebras-key-here
```

In `config.json`, change the `llm` section:
```json
"llm": {
    "provider": "cerebras",
    "api_key": "",
    "api_key_env": "CEREBRAS_API_KEY",
    "model": "llama3.1-8b",
    "temperature": 0.8,
    "max_tokens": 300,
    "base_url": "https://api.cerebras.ai/v1"
}
```

**Option B: OpenAI (Paid)**

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=your-key-here
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="your-key-here"
```

**macOS / Linux:**
```bash
export OPENAI_API_KEY=your-key-here
```

Alternatively, you can set the `api_key` field directly in `config.json` (not recommended for production).

### 3. Run the Application

```bash
python app.py
```

The server will start at [http://127.0.0.1:5000](http://127.0.0.1:5000).

> **Note:** If no API key is configured, the application will start using a mock LLM client that returns simulated responses. This is useful for testing the UI and database functionality.

## Configuration

All configuration is stored in [`config.json`](config.json). Key settings:

| Field | Default | Description |
|-------|---------|-------------|
| `server.host` | `127.0.0.1` | Flask bind address |
| `server.port` | `5000` | Flask bind port |
| `server.debug` | `true` | Enable Flask debug mode |
| `database.path` | `data/wendy.db` | SQLite database file path |
| `llm.provider` | `openai` | LLM provider (`openai`, `cerebras`, or `mock`) |
| `llm.api_key_env` | `WENDY_OPENAI_API_KEY` | Environment variable name for the API key |
| `llm.model` | `llama3.1-8b` | Model for chat completions |
| `llm.base_url` | `https://api.openai.com/v1` | API base URL |
| `llm.temperature` | `0.8` | Sampling temperature (higher = more creative) |
| `llm.max_tokens` | `300` | Max tokens per response |
| `llm.affinity_model` | `gpt-4o-mini` | Model for affinity analysis |
| `llm.affinity_temperature` | `0.3` | Temperature for affinity analysis |
| `affinity.max_shift_per_message` | `15` | Max affinity change per message |
| `affinity.hostile_threshold` | `-50` | Affinity at which conversation ends |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `WENDY_OPENAI_API_KEY` | OpenAI API key (or set `OPENAI_API_KEY`) |
| `CEREBRAS_API_KEY` | Cerebras API key |
| `WENDY_CONFIG_PATH` | Path to config.json (default: `./config.json`) |
| `WENDY_DB_PATH` | Overrides `database.path` in config |
| `WENDY_PORT` | Overrides `server.port` in config |

## API Documentation

### POST `/api/chat`

Send a message to Wendy and receive her response.

**Request:**
```json
{
    "conversation_id": 1,
    "message": "Hey Wendy, how are you today?"
}
```

**Response:**
```json
{
    "message": {
        "id": 42,
        "role": "assistant",
        "content": "Oh hey! I'm doin' alright...",
        "timestamp": "2026-04-05T19:30:00"
    },
    "affinity": {
        "current": 5,
        "stage": "Stranger",
        "shift": 2,
        "reason": "User greeted Wendy warmly"
    },
    "conversation_active": true
}
```

### POST `/api/conversations/new`

Create a new conversation.

**Response:**
```json
{
    "conversation": {
        "id": 2,
        "created_at": "2026-04-05T19:30:00",
        "updated_at": "2026-04-05T19:30:00",
        "affinity": 0,
        "is_active": true,
        "stage": "Stranger"
    }
}
```

### GET `/api/conversations/<id>`

Load a conversation with its full message history.

**Response:**
```json
{
    "conversation": {
        "id": 1,
        "affinity": 5,
        "is_active": true,
        "stage": "Stranger"
    },
    "messages": [
        {"id": 1, "role": "user", "content": "Hey!", "timestamp": "..."},
        {"id": 2, "role": "assistant", "content": "Well hey yourself!", "timestamp": "..."}
    ]
}
```

### GET `/api/conversations`

List all conversations (most recent first).

**Query Parameters:**
- `limit` (int, default 50): Max conversations to return
- `offset` (int, default 0): Pagination offset

**Response:**
```json
{
    "conversations": [
        {
            "id": 1,
            "affinity": 15,
            "is_active": true,
            "stage": "Acquaintance",
            "last_message": "Well that ain't nothin' but the truth!",
            "message_count": 24
        }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
}
```

### DELETE `/api/conversations/<id>`

Delete a conversation and all associated data.

**Response:**
```json
{
    "deleted": true,
    "conversation_id": 1
}
```

## Affinity Stages

Wendy's behavior changes based on the current affinity level:

| Stage | Range | Description |
|-------|-------|-------------|
| **Hostile** | -100 to -50 | Deeply hostile. Conversation ends at -50. |
| **Cold** | -49 to -20 | Guarded, dismissive, sarcastic. |
| **Distant** | -19 to -10 | Polite but guarded, surface-level only. |
| **Stranger** | -9 to +9 | Neutral Appalachian hospitality. Starting state. |
| **Acquaintance** | +10 to +29 | Warming up, sharing opinions, light jokes. |
| **Friendly** | +30 to +49 | Stories about family, uses terms of endearment. |
| **Close** | +50 to +69 | Trusted friend, emotionally open and vulnerable. |
| **Trusted** | +70 to +100 | Deepest secrets, fully emotionally invested. |

## Project Structure

```
c:/Wendy/
├── app.py                  # Flask application entry point
├── config.json             # Runtime configuration
├── database.py             # SQLite operations
├── llm_client.py           # LLM provider abstraction
├── wendy.py                # Character logic
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── ARCHITECTURE.md         # Detailed architecture documentation
├── static/
│   ├── style.css           # Chat UI styles
│   └── script.js           # Frontend logic
└── templates/
    └── index.html          # Single-page chat interface
```

## Switching LLM Providers

### Using Cerebras (Free — Recommended)

Cerebras provides free LLM inference with generous rate limits. The API is OpenAI-compatible, so it works out of the box.

1. Sign up at [Cerebras Inference](https://inference.cerebras.ai/)
2. Set the environment variable: `CEREBRAS_API_KEY=your-key`
3. In `config.json`, set the `llm` section to match `_cerebras_config`:
   ```json
   "llm": {
       "provider": "cerebras",
       "api_key_env": "CEREBRAS_API_KEY",
       "model": "llama3.1-8b",
       "temperature": 0.8,
       "max_tokens": 300,
       "base_url": "https://api.cerebras.ai/v1"
   }
   ```

**Available Cerebras Models:**
| Model | Description |
|-------|-------------|
| `llama3.1-8b` | Llama 3.1 8B — fast, great for chat |
| `qwen-3-235b-a22b-instruct-2507` | Qwen 3 235B — highest quality |
| `zai-glm-4.7` | GLM 4.7 — alternative option |

### Using OpenAI (Paid)

Set `llm.provider` to `"openai"` in `config.json` and provide an API key via:
- Environment variable: `WENDY_OPENAI_API_KEY` or `OPENAI_API_KEY`
- Or directly in config: `llm.api_key`

### Using Mock Client (Testing)

Set `llm.provider` to `"mock"` in `config.json`. The mock client returns simulated responses without making API calls.

### Adding a New Provider

Since the `OpenAIClient` uses the OpenAI Python library (which supports custom base URLs), adding any OpenAI-compatible API provider only requires:

1. Add the provider name and default base URL to `create_client()` in [`llm_client.py`](llm_client.py)
2. Set `llm.provider` to the new provider name in `config.json`
3. Set `llm.base_url` to the provider's API endpoint

For non-OpenAI-compatible providers:

1. Create a new class in [`llm_client.py`](llm_client.py) inheriting from `LLMClient`
2. Implement `generate_response()` and `analyze_affinity()` methods
3. Add the provider key to the `create_client()` factory function
4. Set `llm.provider` in `config.json`

## Deployment Tips

- **Free Hosting**: Use Cerebras for free LLM inference — perfect for personal projects and demos
- **Production API Key**: Use environment variables (`CEREBRAS_API_KEY` or `WENDY_OPENAI_API_KEY`) instead of storing keys in `config.json`
- **Debug Mode**: Set `server.debug` to `false` in production
- **Database Backup**: The SQLite database at `data/wendy.db` contains all conversation history — back it up regularly
- **Reverse Proxy**: Use nginx or similar as a reverse proxy for production deployments
- **WSGI Server**: Replace `app.run()` with a production WSGI server like gunicorn:
  ```bash
  pip install gunicorn
  gunicorn -w 4 -b 127.0.0.1:5000 app:app
  ```

## Free LLM Providers (No Credit Card Required)

| Provider | Free Tier | Best Model | Base URL |
|----------|-----------|------------|----------|
| **Cerebras** | Generous rate limits | `llama3.1-8b` | `https://api.cerebras.ai/v1` |
| **Groq** | ~30 msg/min | `llama-3.3-70b-versatile` | `https://api.groq.com/openai/v1` |
| **Google Gemini** | 15 RPM, 1M tokens/min | `gemini-2.0-flash` | N/A (needs SDK) |
| **OpenRouter** | Several free models | `meta-llama/llama-3.1-8b-instruct` | `https://openrouter.ai/api/v1` |

All of these (except Gemini) use the OpenAI-compatible API format, so you only need to change `llm.provider`, `llm.base_url`, and the API key in `config.json`.

## License

This project is provided as-is for demonstration purposes.
