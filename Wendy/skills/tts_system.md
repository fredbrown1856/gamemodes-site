# TTS (Text-to-Speech) System

> **Purpose:** Document the MiMo TTS voice synthesis integration for Wendy and other NPCs.

## Overview

Wendy's chat interface includes Text-to-Speech powered by Xiaomi's MiMo-V2-TTS model. Each NPC response has a 🔊 speaker button that plays audio of the character speaking. Auto-play can be toggled on/off via the Voice toggle in the chat header.

## Configuration

TTS is configured in [`config.json`](../config.json) under the `tts` key:

| Key | Default | Purpose |
|-----|---------|---------|
| `enabled` | `true` | Enable/disable TTS |
| `provider` | `"mimo"` | TTS provider name |
| `base_url` | `"https://token-plan-sgp.xiaomimimo.com/v1"` | MiMo API endpoint |
| `api_key` | *(set)* | MiMo Token Plan API key |
| `model` | `"mimo-v2-tts"` | TTS model identifier |
| `default_voice` | `"default_en"` | Default English voice |
| `response_format` | `"mp3"` | Audio output format |
| `auto_play` | `true` | Auto-play audio after NPC responses |
| `timeout_seconds` | `30` | API request timeout |

## API Details

- **Endpoint:** `POST /v1/chat/completions` (OpenAI-compatible)
- **Payload:** Chat completions format with `messages` array and `audio` object
- **Response:** Base64-encoded audio in `choices[0].message.audio.data`
- **Voice:** Currently using `default_en` (single voice, additional voices TBD)

## Data Flow

```
User clicks 🔊 button
  → Frontend playTTS() sends POST /api/tts with {"text": "..."}
    → Flask tts_handler() calls tts_client.synthesize()
      → MiMo API: POST /v1/chat/completions with chat format + audio params
        → Response: base64-encoded mp3
      → Decode base64 → raw mp3 bytes
    → Return audio/mpeg Response
  → Frontend creates blob URL from audio
  → HTML5 Audio element plays the mp3
```

## Frontend Components

- **`<audio>` element:** Created dynamically via JavaScript (fallback if not in template)
- **`playTTS(text, btn)`:** Fetches audio, creates blob, plays via Audio element
- **`addTTSButton(bubble, text)`:** Adds 🔊 button to assistant message bubbles
- **`autoPlayTTS(text)`:** Auto-plays after NPC response when Voice toggle is On
- **Voice toggle button:** In chat header, toggles `state.ttsEnabled`

## Source Files

| File | Purpose |
|------|---------|
| [`tts_client.py`](../tts_client.py) | `MiMoTTSClient` class, `create_tts_client()` factory |
| [`app.py`](../app.py) | `POST /api/tts` route handler |
| [`static/script.js`](../static/script.js) | Frontend TTS playback logic |
| [`test_tts.py`](../test_tts.py) | Offline test script for API connectivity |

## Troubleshooting

- **Button does nothing:** Check browser console for `[TTS]` logs. If `Cannot set properties of null`, the audio element wasn't created.
- **401 error:** API key may be expired or wrong region endpoint.
- **404 error:** Wrong base URL. Token Plan uses `token-plan-sgp.xiaomimimo.com/v1`.
- **500 error:** MiMo API response format changed. Check [`tts_client.py`](../tts_client.py) base64 parsing.
- **Timeout:** MiMo API may be slow. Increase `timeout_seconds` in config.

---

*Last updated: 2026-04-09*
