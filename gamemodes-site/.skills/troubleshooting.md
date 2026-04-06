# 🔧 Troubleshooting Guide

Common bugs encountered during development and their fixes. Use this as a diagnostic reference when similar issues arise.

---

## 🖱️ Start Conversation Button Doesn't Work

**Symptoms**: Clicking the CTA button on gamemodes.xyz does nothing; the modal never appears or the form never submits.

### Check List
1. **CSS z-index conflicts** — The `.demo-screen` overlay and `.modal-overlay` compete for layering. Ensure `modal-overlay` has a higher `z-index` than `demo-screen`.
2. **Form submit binding timing** — The `form.addEventListener("submit", ...)` must be bound **before** any `await` calls in the same scope. If the binding happens after an async call, the event may be missed on fast clicks.
3. **Honeypot field name** — The hidden anti-bot field must be named `website_url` (not `honeypot`). The server-side check in [`bot_check.py`](../Wendy/bot_check.py) looks for `website_url` specifically. A mismatch means every submission is rejected as a bot.

```html
<!-- Correct honeypot field -->
<input type="text" name="website_url" style="display:none" tabindex="-1" autocomplete="off">
```

---

## 👋 Wendy Leaves After 1 Message

**Symptoms**: Wendy sends a dismissive message and the conversation ends after the first exchange.

### Check List
1. **`session_active` vs `conversation_active` field name** — The frontend must read the same field name the backend returns. The demo chat endpoint returns `session_active`, not `conversation_active`. A mismatch causes the frontend to think the session ended.
2. **`force_active` parameter** — [`database.update_affinity()`](../Wendy/database.py) must be called with `force_active=True` in demo mode. Without it, a negative affinity shift deactivates the conversation.
3. **`min_messages_before_hostile` config** — Set to `99999` in demo config to effectively disable hostile deactivation. If this is missing or set to a low number, Wendy can "leave" after just a few messages.
4. **Shift clamping** — Demo mode clamps shifts so affinity never crosses the hostile threshold. See the demo protection logic in [`app.py`](../Wendy/app.py:690).

---

## ⏱️ Timer Shows Wrong Duration

**Symptoms**: The session timer counts down from the wrong starting value, or shows negative time, or jumps.

### Check List
1. **ISO 8601 `Z` suffix** — The `expires_at` timestamp from the server must end with `Z` to indicate UTC. Without `Z`, JavaScript's `new Date()` parses it as local time, causing an offset equal to the user's timezone.
2. **Python `datetime.utcnow()` consistency** — Ensure all server-side time calculations use `datetime.utcnow()` (not `datetime.now()`).
3. **Frontend timer math** — The frontend should parse `expires_at` and compute `Math.max(0, expiresAt - Date.now())` on each tick.

```javascript
// Correct: Z suffix ensures UTC parsing
const expiresAt = new Date("2026-04-06T13:15:00Z");
const remaining = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));
```

---

## 🌐 Railway 404 on Custom Domain

**Symptoms**: `chat.gamemodes.xyz` returns 404 or a Railway error page.

### Check List
1. **CNAME target** — Must point to the correct Railway URL (e.g., `your-project.up.railway.app`). Check in DNS dashboard.
2. **TXT verification record** — Railway requires a `TXT` record at `_railway.chat.<domain>` for domain verification. Without it, Railway won't route traffic.
3. **Port binding** — The Flask app must bind to `0.0.0.0` (not `127.0.0.1`). Railway injects a `PORT` env var; the app must use it. Check [`app.py`](../Wendy/app.py) startup:
   ```python
   port = int(os.environ.get("PORT", config["server"]["port"]))
   app.run(host="0.0.0.0", port=port)
   ```
4. **Domain added in Railway** — Run `railway domain add chat.gamemodes.xyz` or add via dashboard.

---

## 🔒 CORS Errors

**Symptoms**: Browser console shows "blocked by CORS policy" when the main site tries to call `chat.gamemodes.xyz` APIs.

### Check List
1. **`allowed_origins` in config.json** — Must include `https://gamemodes.xyz` and `https://www.gamemodes.xyz`. See [`config.json`](../Wendy/config.json):
   ```json
   "cors": {
     "allowed_origins": ["https://gamemodes.xyz", "https://www.gamemodes.xyz", "https://chat.gamemodes.xyz"]
   }
   ```
2. **CORS initialization in app.py** — The `CORS()` call must match. See [`app.py`](../Wendy/app.py:70).
3. **`supports_credentials`** — If sending cookies or auth headers, ensure `supports_credentials` is configured.
4. **Local development** — Add `http://localhost:5000` and `http://127.0.0.1:5000` for local testing.

---

## 🤖 Bot Check Blocking Legitimate Users

**Symptoms**: Real users get "Invalid submission" or "Access denied" errors.

### Check List
1. **User-Agent blocking list** — The blocked list in [`config.json`](../Wendy/config.json) includes common crawler strings. If a user's browser extension modifies the UA to include "bot" or "crawler", they'll be blocked. Review the list:
   ```json
   "blocked_user_agents": ["python-requests", "curl", "wget", "bot", "crawler", "spider", "scraper"]
   ```
2. **Honeypot field visibility** — The honeypot input must have `display:none` (not `visibility:hidden` or `opacity:0` which some bots check). Also set `tabindex="-1"` and `autocomplete="off"` to prevent autofill.
3. **Rate limit too aggressive** — Default is 3 session attempts per IP per hour. Shared networks (NAT, VPNs) can exhaust this. Adjust `max_session_attempts_per_ip_per_hour` in config.
