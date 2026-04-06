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

## Frontend Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Serves `templates/index.html` |
| `/static/<filename>` | GET | Serves files from `static/` directory |

---

## Source References

- Route handlers: [`app.py`](../app.py:63) lines 63-366
- Error handlers: [`app.py`](../app.py:373) lines 373-384
- Database operations called by routes: [`database.py`](../database.py)
