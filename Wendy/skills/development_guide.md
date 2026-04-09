# Development Guide

## Environment Variables

| Variable | Overrides | Description |
|----------|-----------|-------------|
| `WENDY_CONFIG_PATH` | config file path | Path to config.json |
| `WENDY_DB_PATH` | `database.path` | SQLite database file path |
| `WENDY_PORT` | `server.port` | Server port |
| `WENDY_OPENAI_API_KEY` | `llm.api_key` | OpenAI API key |

Priority: Environment variable > config.json value.

## Testing Without an OpenAI Key

Set `llm.provider` to `"mock"` in [`config.json`](../config.json:11), or let the app auto-fallback when no API key is found. [`MockClient`](../llm_client.py:223) returns:

- **Response:** `"Well hey there! This is a mock response since the LLM ain't configured..."`
- **Affinity shift:** Always `{"shift": 0, "reason": "Mock analysis..."}`

This lets you test the full UI and DB flow without API calls.

---

## How to Add a New LLM Provider

1. **Create a client class** in [`llm_client.py`](../llm_client.py) that extends `LLMClient`:

```python
class MyProviderClient(LLMClient):
    def __init__(self, config: dict):
        super().__init__(config)
        # Initialize your provider's SDK

    def generate_response(self, messages: list[dict]) -> str:
        # Call your provider's chat API
        # Return the assistant's text response
        pass

    def analyze_affinity(self, messages: list[dict], current_affinity: int) -> dict:
        # Call your provider to analyze sentiment
        # Return {"shift": int, "reason": str}
        pass
```

2. **Register in the factory** — update [`create_client()`](../llm_client.py:256):

```python
elif provider == "myprovider":
    return MyProviderClient(llm_config)
```

3. **Update config.json** — set `llm.provider` to `"myprovider"` and add any provider-specific settings.

4. **Add to requirements.txt** if your provider needs a pip package.

---

## How to Add a New API Endpoint

1. **Add route handler** in [`app.py`](../app.py) under the `# API Routes` section:

```python
@app.route("/api/my-endpoint", methods=["POST"])
def my_handler():
    try:
        data = request.get_json()
        # Validate input
        # Call database functions
        # Return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in my_handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
```

2. **Add database functions** in [`database.py`](../database.py) if needed.

3. **Add frontend calls** in [`static/script.js`](../static/script.js) under `// API Calls`:

```javascript
async function callMyEndpoint(data) {
    return apiRequest('/api/my-endpoint', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}
```

---

## How to Modify the Frontend

### HTML — [`templates/index.html`](../templates/index.html)
- Sidebar with conversation list
- Chat header with affinity display
- Messages area
- Input area
- Confirmation modal

### CSS — [`static/style.css`](../static/style.css)
- CSS variables at the top (lines 7-81) for colors, spacing, affinity gradient
- Sections clearly marked with comments
- Affinity colors defined in `--color-affinity-*` variables
- Gradient bar in `--affinity-gradient`

### JavaScript — [`static/script.js`](../static/script.js)
- **State** (lines 13-21): Central app state object
- **DOM** (lines 27-48): Cached element references
- **API Calls** (lines 93-136): All fetch wrappers
- **Affinity Display** (lines 239-271): `updateAffinityDisplay()` handles bar, marker, color, label
- **Message Rendering** (lines 276-356): Creates and appends message elements
- **Core Actions** (lines 505-661): Load/create conversations, send messages
- **Event Listeners** (lines 667-745): All DOM bindings

### Changing Affinity Colors
Update both:
1. `--color-affinity-*` CSS variables in [`style.css`](../static/style.css:32)
2. `getAffinityColor()` function in [`script.js`](../static/script.js:197)
3. Stage `color` values in [`config.json`](../config.json:27)

---

## How to Change Affinity Thresholds or Add Stages

### Changing Thresholds
Edit [`config.json`](../config.json:20) `affinity` section:
- `max_shift_per_message` — how fast affinity can change
- `hostile_threshold` — when conversations end

### Adding a New Stage
1. Add a new entry to the `affinity_stages` array in [`config.json`](../config.json:27):

```json
{
    "label": "Intimate",
    "min": 85,
    "max": 100,
    "color": "#db2777",
    "behavior": "Wendy is completely open and emotionally bonded..."
}
```

2. Ensure ranges cover [-100, 100] without gaps or overlaps.
3. Add the color to CSS variables in [`style.css`](../static/style.css:32).
4. Add the color to `getAffinityColor()` in [`script.js`](../static/script.js:197).

### Removing a Stage
Remove from `affinity_stages` and adjust neighboring ranges to cover the gap.

---

## Deployment

### Heroku
1. Add `Procfile`:
   ```
   web: python app.py
   ```
2. Set config vars: `WENDY_OPENAI_API_KEY`, `WENDY_PORT` (Heroku sets PORT automatically — modify `app.py` to read it).
3. Set `server.host` to `0.0.0.0` and `server.debug` to `false`.

### VPS (Ubuntu/Debian)
1. Install Python 3.10+, clone repo.
2. `pip install -r requirements.txt`
3. Set environment variables in systemd service or `.env`.
4. Use gunicorn:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 "app:app"
   ```
5. Put nginx in front for SSL/reverse proxy.

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t wendy .
docker run -p 5000:5000 -e WENDY_OPENAI_API_KEY=sk-... wendy
```

### Production Checklist
- [ ] Set `server.debug` to `false`
- [ ] Set `server.host` to `0.0.0.0`
- [ ] Use a production WSGI server (gunicorn, waitress)
- [ ] Set `WENDY_OPENAI_API_KEY` via environment variable (not config.json)
- [ ] Back up `data/wendy.db` regularly
- [ ] Put a reverse proxy (nginx/caddy) in front for SSL
- [ ] Set appropriate `server.port`

---

## How to Modify TTS Voice or Provider

TTS configuration is in `config.json` under the `tts` key.

### Change the default voice
Edit `tts.default_voice` in config.json. Currently only `default_en` is confirmed working.

### Disable TTS
Set `tts.enabled` to `false` in config.json. The chat will work normally without audio.

### Switch TTS providers
1. Create a new client class in `tts_client.py` (implement the same interface as `MiMoTTSClient`)
2. Update `create_tts_client()` factory function to detect the provider
3. Add provider config to `config.json` under `tts.provider`

### Test TTS offline
```bash
cd Wendy
python test_tts.py
```

## How to Update Company Knowledge

Wendy's company knowledge is stored in `config.json` under `company_knowledge`.

### Add a new project
Add a new key under `company_knowledge.projects`:
```json
"new_project": {
    "name": "Project Name",
    "status": "In Development",
    "type": "Description",
    "description": "Full project description...",
    "highlights": ["Feature 1", "Feature 2"]
}
```

### Change what Wendy shares at each affinity level
Edit the tier logic in `wendy.py::build_system_prompt()` — search for "COMPANY KNOWLEDGE".

### Disable spokesperson mode
Set `company_knowledge.enabled` to `false` in config.json.

---

## Common Modification Patterns

### Change Wendy's personality
→ Edit `wendy.system_prompt_base` in [`config.json`](../config.json:105)

### Change how fast affinity shifts
→ Edit `affinity.max_shift_per_message` in [`config.json`](../config.json:24)

### Add new message validation
→ Edit [`app.py::chat_handler()`](../app.py:64) validation block (lines 84-98)

### Add logging
→ Use `app.logger.info()`, `app.logger.warning()`, `app.logger.error()` in [`app.py`](../app.py)

### Change the LLM model
→ Edit `llm.model` in [`config.json`](../config.json:13). Use different models for chat vs affinity analysis via `llm.affinity_model`.

### Change temperature/creativity
→ Edit `llm.temperature` (chat responses, default 0.8) and `llm.affinity_temperature` (affinity analysis, default 0.3) in [`config.json`](../config.json:14).

### Add a new static file
→ Place in `static/` directory. Served automatically via `/static/<filename>`.

### Reset the database
→ Delete `data/wendy.db` and restart the app. Tables are recreated automatically.

---

## Source References

- App entry point: [`app.py`](../app.py)
- Config loading with env overrides: [`app.py::load_config()`](../app.py:16)
- LLM client factory: [`llm_client.py::create_client()`](../llm_client.py:256)
- Mock client: [`llm_client.py::MockClient`](../llm_client.py:223)
- DB init: [`database.py::init_db()`](../database.py:17)
- Character system: [`wendy.py`](../wendy.py)
- Frontend: [`templates/index.html`](../templates/index.html), [`static/style.css`](../static/style.css), [`static/script.js`](../static/script.js)
