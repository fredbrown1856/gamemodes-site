# Database Schema

## Overview

The project uses SQLite 3 (Python stdlib `sqlite3`). The database file defaults to `data/wendy.db` and is configurable via `config.json` → `database.path` or the `WENDY_DB_PATH` environment variable.

Tables are created automatically on startup by [`database.py::init_db()`](../database.py:17).

## Tables

### conversations

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    affinity        INTEGER NOT NULL DEFAULT 0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    CHECK (affinity >= -100 AND affinity <= 100)
)
```

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | INTEGER | auto | Primary key |
| `created_at` | TEXT | now | ISO 8601 UTC creation timestamp |
| `updated_at` | TEXT | now | ISO 8601 UTC last-update timestamp |
| `affinity` | INTEGER | 0 | Current affinity (-100 to 100) |
| `is_active` | INTEGER | 1 | 1 = active, 0 = ended (affinity too low) |

### messages

```sql
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role            TEXT    NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT    NOT NULL,
    timestamp       TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
)

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
    ON messages(conversation_id)
```

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | INTEGER | auto | Primary key |
| `conversation_id` | INTEGER | — | FK to conversations.id |
| `role` | TEXT | — | `"user"`, `"assistant"`, or `"system"` |
| `content` | TEXT | — | Message text |
| `timestamp` | TEXT | now | ISO 8601 UTC timestamp |

### affinity_log

```sql
CREATE TABLE IF NOT EXISTS affinity_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    affinity_before INTEGER NOT NULL,
    affinity_after  INTEGER NOT NULL,
    shift           INTEGER NOT NULL,
    reason          TEXT    NOT NULL,
    timestamp       TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
)

CREATE INDEX IF NOT EXISTS idx_affinity_log_conversation_id
    ON affinity_log(conversation_id)
```

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | INTEGER | auto | Primary key |
| `conversation_id` | INTEGER | — | FK to conversations.id |
| `affinity_before` | INTEGER | — | Affinity before the shift |
| `affinity_after` | INTEGER | — | Affinity after the shift |
| `shift` | INTEGER | — | The change amount |
| `reason` | TEXT | — | Explanation from LLM analysis |
| `timestamp` | TEXT | now | ISO 8601 UTC timestamp |

### critical_facts

Stores established facts about Wendy for cross-conversation consistency.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `category` | TEXT | Fact category: family, personal, location, relationship, background |
| `fact_key` | TEXT | Short identifier (e.g., `father_name`, `age`) |
| `fact_value` | TEXT | The established fact value |
| `source` | TEXT | Where the fact came from: conversation, extraction, character_definition |
| `conversation_id` | INTEGER | Conversation where fact was established (nullable) |
| `confidence` | REAL | Confidence score 0.0-1.0 (default 0.8) |
| `is_active` | INTEGER | 1 = active, 0 = deactivated |
| `created_at` | TIMESTAMP | When the fact was created |
| `updated_at` | TIMESTAMP | Last update time |

**Unique constraint:** `(category, fact_key)` — first cached value wins for consistency.

See `critical_facts.py` for the full API.

## Relationships

```
conversations (1) ──< (many) messages
conversations (1) ──< (many) affinity_log
```

Both `messages` and `affinity_log` have `ON DELETE CASCADE` — deleting a conversation removes all its messages and affinity log entries.

## Database Functions

All functions are in [`database.py`](../database.py).

### init_db(db_path)

```python
def init_db(db_path: str = "data/wendy.db") -> None
```
Creates tables and indexes if they don't exist. Sets the module-level `_db_path`. Called once at app startup.

### get_connection()

```python
def get_connection() -> sqlite3.Connection
```
Returns a connection with `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`. Caller must close the connection.

### create_conversation()

```python
def create_conversation() -> dict
```
Inserts a new conversation with `affinity=0`, `is_active=1`. Returns the new conversation as a dict with keys: `id`, `created_at`, `updated_at`, `affinity`, `is_active`.

### get_conversation(conversation_id)

```python
def get_conversation(conversation_id: int) -> Optional[dict]
```
Fetches a single conversation by ID. Returns dict or `None`.

### list_conversations(limit, offset)

```python
def list_conversations(limit: int = 50, offset: int = 0) -> dict
```
Returns paginated conversations ordered by `updated_at DESC`. Each conversation includes `last_message` (content of most recent message) and `message_count`. Returns dict with `conversations`, `total`, `limit`, `offset`.

### delete_conversation(conversation_id)

```python
def delete_conversation(conversation_id: int) -> bool
```
Deletes a conversation and cascades to messages and affinity_log. Returns `True` if deleted, `False` if not found.

### add_message(conversation_id, role, content)

```python
def add_message(conversation_id: int, role: str, content: str) -> dict
```
Inserts a message and updates the conversation's `updated_at` timestamp. Returns the new message dict. Raises `ValueError` if role is invalid.

### get_messages(conversation_id, limit)

```python
def get_messages(conversation_id: int, limit: Optional[int] = None) -> list[dict]
```
Returns messages ordered by `timestamp ASC`. If `limit` is set, returns only the most recent N messages (still in chronological order).

### update_affinity(conversation_id, shift, reason)

```python
def update_affinity(conversation_id: int, shift: int, reason: str) -> dict
```
Applies an affinity shift, clamps to [-100, 100], deactivates conversation if affinity ≤ -50, logs the change to `affinity_log`. Returns dict with `affinity_before`, `affinity_after`, `shift`, `reason`, `conversation_active`.

### get_affinity_log(conversation_id)

```python
def get_affinity_log(conversation_id: int) -> list[dict]
```
Returns all affinity_log entries for a conversation ordered by `timestamp ASC`.

## Common Queries

### Get conversation with recent messages
```sql
SELECT * FROM conversations WHERE id = ?;
SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC;
```

### Get conversation summary with last message
```sql
SELECT
    c.*,
    (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) as last_message,
    (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count
FROM conversations c
ORDER BY c.updated_at DESC
LIMIT ? OFFSET ?;
```

### Get affinity history for a conversation
```sql
SELECT * FROM affinity_log WHERE conversation_id = ? ORDER BY timestamp ASC;
```

### Count total conversations
```sql
SELECT COUNT(*) as count FROM conversations;
```

## Adding New Tables

1. Add the `CREATE TABLE IF NOT EXISTS` statement in [`database.py::init_db()`](../database.py:17)
2. Add any indexes after the table creation
3. Create CRUD functions following the existing patterns:
   - Use `get_connection()` for connections
   - Use `sqlite3.Row` factory (already configured)
   - Return dicts via `dict(row)`
   - Close connections after use
   - Commit after writes

## Modifying the Schema

SQLite does not support `ALTER TABLE` for most operations. To modify an existing table:

1. **Add a column** (supported):
   ```sql
   ALTER TABLE conversations ADD COLUMN new_field TEXT DEFAULT '';
   ```

2. **Rename/delete a column** (not directly supported):
   - Create a new table with the desired schema
   - Copy data from old table
   - Drop old table
   - Rename new table
   - Recreate indexes

3. **After schema changes**, update all functions in `database.py` that read/write the modified table.

## Source References

- Schema definitions: [`database.py::init_db()`](../database.py:17) lines 17-87
- Connection management: [`database.py::get_connection()`](../database.py:90)
- All CRUD functions: [`database.py`](../database.py) lines 105-398
- Config: [`config.json`](../config.json:7) `database.path`
