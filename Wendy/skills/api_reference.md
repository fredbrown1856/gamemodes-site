# API Reference

All API endpoints return JSON. Errors follow a consistent format.

## Error Response Format

```json
{
  "error": "Error message description"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad request (missing/invalid fields) |
| 403 | Forbidden (conversation ended) |
| 404 | Not found (conversation doesn't exist) |
| 500 | Internal server error |

---

## POST /api/chat

Send a message and receive Wendy's response.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `conversation_id` | int | Yes | ID of the conversation |
| `message` | string | Yes | User's message (max 2000 chars) |

```json
{
  "conversation_id": 1,
  "message": "Hey Wendy, how are you today?"
}
```

**Response (200 OK):**

| Field | Type | Description |
|-------|------|-------------|
| `message.id` | int | Message ID |
| `message.role` | string | Always `"assistant"` |
| `message.content` | string | Wendy's response text |
| `message.timestamp` | string | ISO 8601 UTC timestamp |
| `affinity.current` | int | New affinity value (-100 to 100) |
| `affinity.stage` | string | Stage label (e.g. "Friendly") |
| `affinity.shift` | int | Affinity change from this message |
| `affinity.reason` | string | Explanation of the shift |
| `conversation_active` | bool | Whether conversation is still active |

```json
{
  "message": {
    "id": 42,
    "role": "assistant",
    "content": "Well hey there! I'm doin' alright, just got back from the market.",
    "timestamp": "2026-04-06T12:34:56.789012"
  },
  "affinity": {
    "current": 5,
    "stage": "Stranger",
    "shift": 3,
    "reason": "Message was friendly and polite"
  },
  "conversation_active": true
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 400 | Missing `conversation_id` or `message`, or message is not a string |
| 400 | Message exceeds 2000 characters |
| 404 | Conversation not found |
| 403 | Conversation has ended (affinity dropped too low) |
| 500 | LLM error or internal server error |

**Conversation Ended Response (when affinity ≤ -50):**

```json
{
  "message": {
    "id": 43,
    "role": "assistant",
    "content": "I ain't got no more patience for this. I'm done talkin' to you.",
    "timestamp": "2026-04-06T12:35:00.123456"
  },
  "affinity": {
    "current": -52,
    "stage": "Hostile",
    "shift": -8,
    "reason": "User was repeatedly rude"
  },
  "conversation_active": false
}
```

---

## POST /api/conversations/new

Create a new conversation.

**Request Body:** None.

**Response (201 Created):**

| Field | Type | Description |
|-------|------|-------------|
| `conversation.id` | int | New conversation ID |
| `conversation.created_at` | string | ISO 8601 UTC timestamp |
| `conversation.updated_at` | string | ISO 8601 UTC timestamp |
| `conversation.affinity` | int | Initial affinity (always 0) |
| `conversation.is_active` | bool | Active status (always true) |
| `conversation.stage` | string | Initial stage (always "Stranger") |

```json
{
  "conversation": {
    "id": 5,
    "created_at": "2026-04-06T12:00:00.000000",
    "updated_at": "2026-04-06T12:00:00.000000",
    "affinity": 0,
    "is_active": true,
    "stage": "Stranger"
  }
}
```

---

## GET /api/conversations/:id

Load an existing conversation with its full message history.

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | int | Conversation ID |

**Response (200 OK):**

| Field | Type | Description |
|-------|------|-------------|
| `conversation.id` | int | Conversation ID |
| `conversation.created_at` | string | ISO 8601 timestamp |
| `conversation.updated_at` | string | ISO 8601 timestamp |
| `conversation.affinity` | int | Current affinity |
| `conversation.is_active` | bool | Active status |
| `conversation.stage` | string | Current stage label |
| `messages[]` | array | List of message objects |

Each message in `messages`:

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Message ID |
| `conversation_id` | int | Parent conversation ID |
| `role` | string | `"user"`, `"assistant"`, or `"system"` |
| `content` | string | Message text |
| `timestamp` | string | ISO 8601 timestamp |

```json
{
  "conversation": {
    "id": 1,
    "created_at": "2026-04-06T10:00:00.000000",
    "updated_at": "2026-04-06T10:05:00.000000",
    "affinity": 15,
    "is_active": true,
    "stage": "Acquaintance"
  },
  "messages": [
    {
      "id": 1,
      "conversation_id": 1,
      "role": "user",
      "content": "Hi Wendy!",
      "timestamp": "2026-04-06T10:00:00.000000"
    },
    {
      "id": 2,
      "conversation_id": 1,
      "role": "assistant",
      "content": "Well hey there! Nice to meet ya.",
      "timestamp": "2026-04-06T10:00:01.000000"
    }
  ]
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 404 | Conversation not found |

---

## GET /api/conversations

List all conversations, ordered by most recently updated first.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max conversations to return (1-100) |
| `offset` | int | 0 | Pagination offset |

**Response (200 OK):**

| Field | Type | Description |
|-------|------|-------------|
| `conversations[]` | array | List of conversation summaries |
| `total` | int | Total number of conversations |
| `limit` | int | Applied limit |
| `offset` | int | Applied offset |

Each conversation in `conversations`:

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Conversation ID |
| `created_at` | string | ISO 8601 timestamp |
| `updated_at` | string | ISO 8601 timestamp |
| `affinity` | int | Current affinity |
| `is_active` | bool | Active status |
| `last_message` | string \| null | Content of most recent message |
| `message_count` | int | Total messages in conversation |
| `stage` | string | Current stage label |

```json
{
  "conversations": [
    {
      "id": 3,
      "created_at": "2026-04-06T11:00:00.000000",
      "updated_at": "2026-04-06T11:30:00.000000",
      "affinity": 25,
      "is_active": true,
      "last_message": "That's real nice of you to say!",
      "message_count": 12,
      "stage": "Acquaintance"
    },
    {
      "id": 1,
      "created_at": "2026-04-06T10:00:00.000000",
      "updated_at": "2026-04-06T10:05:00.000000",
      "affinity": -52,
      "is_active": false,
      "last_message": "I ain't got no more patience for this.",
      "message_count": 4,
      "stage": "Hostile"
    }
  ],
  "total": 2,
  "limit": 50,
  "offset": 0
}
```

---

## DELETE /api/conversations/:id

Delete a conversation and all associated messages and affinity log entries.

**URL Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | int | Conversation ID |

**Response (200 OK):**

| Field | Type | Description |
|-------|------|-------------|
| `deleted` | bool | Always `true` |
| `conversation_id` | int | The deleted conversation ID |

```json
{
  "deleted": true,
  "conversation_id": 3
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 404 | Conversation not found |

---

## POST /api/demo/start

Start a demo session (public visitors). Runs bot checks, then allocates a session or queue slot.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `website_url` | string | No | Honeypot field — must be empty or missing for humans |

```json
{}
```

**Response — Session Allocated (201 Created):**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"active"` |
| `session_token` | string | Token for subsequent demo requests |
| `conversation_id` | int | New conversation ID |
| `affinity` | int | Initial affinity (0) |
| `stage` | string | Initial stage (`"Stranger"`) |
| `expires_at` | string | ISO 8601 UTC expiry timestamp |
| `time_remaining_seconds` | int | Seconds until session expires |

```json
{
  "status": "active",
  "session_token": "abc123...",
  "conversation_id": 42,
  "affinity": 0,
  "stage": "Stranger",
  "expires_at": "2026-04-06T13:15:00Z",
  "time_remaining_seconds": 900
}
```

**Response — Queued (202 Accepted):**

```json
{
  "status": "queued",
  "queue_id": "q_abc123",
  "position": 3,
  "estimated_wait": 420,
  "queue_size": 3
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 400 | Honeypot field filled (bot detected) |
| 403 | Blocked user-agent |
| 429 | Rate limit exceeded (max 3 session attempts per IP per hour) |
| 503 | Queue is full |
| 500 | Internal server error |

---

## GET /api/demo/status

Poll queue position or session time remaining.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `queue_id` | string | Queue entry ID (for waiting visitors) |
| `session_token` | string | Session token (for active visitors) |

**Response — Queue Status (200):**

```json
{
  "in_queue": true,
  "position": 2,
  "estimated_wait": 300,
  "queue_size": 3
}
```

**Response — Queue Ready (200):**

```json
{
  "in_queue": true,
  "position": 0,
  "ready": true,
  "message": "A slot is available! Start your session now."
}
```

**Response — Session Status (200):**

```json
{
  "is_active": true,
  "time_remaining_seconds": 742,
  "expires_at": "2026-04-06T13:15:00Z",
  "conversation_id": 42
}
```

**Response — Session Expired (200):**

```json
{
  "is_active": false,
  "time_remaining_seconds": 0,
  "message": "Session has expired or is invalid."
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 400 | Neither `queue_id` nor `session_token` provided |

---

## POST /api/demo/chat

Session-aware chat for demo mode. Validates session token and timer before processing.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_token` | string | Yes | Active demo session token |
| `message` | string | Yes | User's message (max 2000 chars) |

```json
{
  "session_token": "abc123...",
  "message": "Hey Wendy, what's it like living in the mountains?"
}
```

**Response (200 OK):**

| Field | Type | Description |
|-------|------|-------------|
| `message.content` | string | Wendy's response text |
| `message.cached` | bool | `true` if returned from daily cache |
| `affinity.current` | int | Current affinity value |
| `affinity.stage` | string | Current stage label |
| `time_remaining_seconds` | int | Seconds left in session |
| `session_active` | bool | Always `true` in demo mode |

```json
{
  "message": {
    "content": "Well, it ain't for everybody, but I reckon I wouldn't trade it for nothin'.",
    "cached": false
  },
  "affinity": {
    "current": 3,
    "stage": "Stranger"
  },
  "time_remaining_seconds": 842,
  "session_active": true
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 400 | Missing `session_token` or `message`, or message too long |
| 401 | Session expired or invalid |
| 404 | Conversation not found |
| 500 | LLM error or internal server error |

> **Note:** In demo mode, Wendy never leaves the conversation. Affinity shifts are clamped smaller (`max_shift_per_message_demo: 5`), and conversations are never deactivated regardless of affinity. The session timer is the only way a demo session ends.

---

## GET /api/demo/stats

Public counters for the website widget. No authentication required.

**Response (200 OK):**

```json
{
  "total_conversations": 142,
  "total_messages": 1847,
  "current_queue_size": 0,
  "slots_available": 2,
  "active_sessions": 0
}
```

---

## GET /api/export/training

Admin-only encrypted training data export.

**Headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <ADMIN_TOKEN>` |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_affinity` | int | 10 | Minimum affinity threshold for export |

**Response (200 OK):**

```json
{
  "filename": "wendy_training_2026-04-06.enc",
  "count": 87,
  "size_bytes": 45230,
  "export_date": "2026-04-06",
  "min_affinity": 10
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 401 | Missing or malformed Authorization header |
| 403 | Invalid admin token |
| 503 | `ADMIN_TOKEN` or `TRAINING_ENCRYPTION_KEY` not configured |

---

---

## POST /api/tts

Generate Text-to-Speech audio for a text string using MiMo-V2-TTS.

**Request:**

```json
{
    "text": "Well hey there, sugar. How are you doin' today?",
    "voice": "default_en"
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `text` | string | Yes | — | Text to synthesize (max 1000 chars) |
| `voice` | string | No | `"default_en"` | Voice identifier |

**Success Response:** `200 OK`

Returns `audio/mpeg` binary data (mp3 file).

```
Content-Type: audio/mpeg
Cache-Control: no-cache

<raw mp3 bytes>
```

**Error Responses:**

| Status | Condition | Body |
|--------|-----------|------|
| 400 | No text provided | `{"error": "No text provided"}` |
| 500 | TTS generation failed (API error, timeout, parse failure) | `{"error": "TTS generation failed"}` |
| 503 | TTS disabled or not configured | `{"error": "TTS not available"}` |

**Frontend Usage:**

```javascript
const resp = await fetch('/api/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: messageText }),
});
const blob = await resp.blob();
const url = URL.createObjectURL(blob);
const audio = new Audio(url);
await audio.play();
```

---

## Frontend Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Serves `templates/index.html` |
| `/static/<filename>` | GET | Serves files from `static/` directory |

---

## Source References

- Standard route handlers: [`app.py`](../app.py:80)
- Demo route handlers: [`app.py`](../app.py:377)
- Error handlers: [`app.py`](../app.py:900)
- Database operations: [`database.py`](../database.py)
- Session management: [`session_manager.py`](../session_manager.py)
- Queue management: [`queue_manager.py`](../queue_manager.py)
- Bot protection: [`bot_check.py`](../bot_check.py)
- Daily cache: [`daily_cache.py`](../daily_cache.py)
- Training export: [`training_export.py`](../training_export.py)
