# 🚂 Wendy Deployment Guide

How to deploy and manage the Wendy Flask backend on Railway.

---

## Prerequisites

- [Railway CLI](https://docs.railway.app/guides/cli) installed (`npm install -g @railway/cli`)
- Railway account with the Wendy project created
- Environment variables ready (see checklist below)

---

## 🔑 Environment Variables Checklist

Set these via `railway variables set KEY=value` or the Railway dashboard → Variables tab.

| Variable | Required | Description |
|----------|----------|-------------|
| `CEREBRAS_API_KEY` | ✅ | Cerebras LLM API key (free tier) |
| `SESSION_SECRET` | ✅ | Random string for signing session tokens |
| `ADMIN_TOKEN` | ✅ | Bearer token for admin endpoints (training export) |
| `TRAINING_ENCRYPTION_KEY` | ⚠️ | AES-256-GCM key for training exports (required for export feature) |
| `IP_HASH_SALT` | Optional | Salt for hashing visitor IPs (default: `gamemodes-wendy`) |
| `RAILWAY_VOLUME_MOUNT_PATH` | Auto | Set by Railway when a volume is attached |

Generate a session secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Generate an encryption key:
```bash
python -c "from training_export import generate_encryption_key; print(generate_encryption_key())"
```

---

## 📡 DNS Configuration

Configure these DNS records in your domain registrar:

| Type | Host | Value | Purpose |
|------|------|-------|---------|
| `CNAME` | `chat` | `<your-project>.up.railway.app` | Routes chat.gamemodes.xyz to Railway |
| `TXT` | `_railway.chat` | `<verification-token>` | Railway domain verification |

After adding records, verify in Railway:
```bash
railway domain add chat.gamemodes.xyz
```

---

## 💾 Persistent Volume for SQLite

Railway's filesystem is ephemeral — the database is lost on redeploy without a volume.

### Setup (one-time)
1. Go to Railway dashboard → Your project → **Volumes**
2. Create a new volume (1 GB is sufficient)
3. Set mount path to `/data`
4. Railway sets `RAILWAY_VOLUME_MOUNT_PATH=/data` automatically

The app detects this in [`app.py`](../app.py:49):
```python
if "RAILWAY_VOLUME_MOUNT_PATH" in os.environ:
    config["database"]["path"] = os.environ["RAILWAY_VOLUME_MOUNT_PATH"] + "/wendy.db"
```

### Backup
```bash
# SSH into the volume or copy via Railway CLI
railway run cp /data/wendy.db /tmp/wendy_backup.db
```

---

## 🚀 Deployment Commands

### First-time setup
```bash
cd Wendy
railway login
railway link        # Select the Wendy project
```

### Deploy
```bash
cd Wendy
railway up          # Build and deploy
```

### Check status
```bash
railway status
railway logs        # Stream logs
railway logs --tail # Follow logs in real-time
```

### Open the live app
```bash
railway open
```

---

## 🔧 Redeploying After Changes

1. Make code changes in `Wendy/`
2. Test locally:
   ```bash
   cd Wendy
   pip install -r requirements.txt
   python app.py
   ```
3. Deploy:
   ```bash
   cd Wendy
   railway up
   ```
4. Verify:
   ```bash
   railway logs
   curl https://chat.gamemodes.xyz/api/demo/stats
   ```

> **Note**: Redeploying without a persistent volume will reset the database. Always ensure the volume is attached.

---

## 📋 Monitoring

### Health check endpoint
```bash
curl https://chat.gamemodes.xyz/api/demo/stats
```
Returns `total_conversations`, `total_messages`, `active_sessions`, `slots_available`.

### Key log patterns
- `Demo affinity | conv=N` — Affinity shift per message
- `Demo protection (never deactivate)` — Shift was clamped to prevent hostile
- `Error in demo_start_handler` — Bot check or session creation failure
- `Session expired` — Normal session timeout

### Railway dashboard
- **Deployments** tab — Deploy history, rollback option
- **Logs** tab — Real-time and historical logs
- **Metrics** tab — CPU, memory, network
- **Variables** tab — Environment variable management

---

## TTS Configuration

TTS requires the MiMo Token Plan API key. Set in `config.json` under the `tts` key:

| Variable | Config Key | Required | Description |
|----------|-----------|----------|-------------|
| — | `tts.api_key` | Yes | MiMo Token Plan API key (`tp-...`) |
| — | `tts.base_url` | Yes | Must be `https://token-plan-sgp.xiaomimimo.com/v1` for Token Plan |
| — | `tts.enabled` | No | Set `false` to disable TTS without removing config |

**Important:** The base URL must match your subscription type:
- **Token Plan:** `https://token-plan-sgp.xiaomimimo.com/v1`
- **Standard:** `https://api.xiaomimimo.com/v1`

Using the wrong URL will result in 401 errors.

## Company Knowledge (Spokesperson Mode)

Wendy's company knowledge is configured in `config.json` under `company_knowledge`. This is a static data block injected into the system prompt — no external services required.

| Variable | Config Key | Required | Description |
|----------|-----------|----------|-------------|
| — | `company_knowledge.enabled` | No | Set `false` to disable spokesperson mode |
| — | `company_knowledge.investor_page` | No | Investor page URL and tier data |

To update project info, edit the `company_knowledge.projects` section in config.json.

---

## ⚠️ Common Issues

| Issue | Fix |
|-------|-----|
| 404 on custom domain | Add CNAME + TXT DNS records, run `railway domain add` |
| Database resets on deploy | Attach a persistent volume mounted at `/data` |
| Port binding error | Ensure app binds to `0.0.0.0` using `$PORT` env var |
| CORS errors from main site | Check `cors.allowed_origins` in [`config.json`](../config.json) |
| LLM errors | Verify `CEREBRAS_API_KEY` is set: `railway variables get CEREBRAS_API_KEY` |

---

## 📦 Training Data Export

Export encrypted training data via the admin endpoint:

```bash
# Export all conversations as encrypted Alpaca-format JSON
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
     https://chat.gamemodes.xyz/api/export/training \
     -o training_data.json.enc
```

The response is AES-256-GCM encrypted using `TRAINING_ENCRYPTION_KEY`. To decrypt:

```python
from training_export import decrypt_export

with open("training_data.json.enc", "r") as f:
    encrypted = f.read()

data = decrypt_export(encrypted, "your-encryption-key-here")
print(data)  # List of Alpaca-format dicts
```

> **Note**: The `TRAINING_ENCRYPTION_KEY` env var must be set for export to work. Generate one with:
> ```bash
> python -c "from training_export import generate_encryption_key; print(generate_encryption_key())"
> ```

---

## 📁 Key Config Files

| File | Purpose |
|------|---------|
| [`Procfile`](../Procfile) | Railway process definition (`web: python app.py`) |
| [`runtime.txt`](../runtime.txt) | Python version pin |
| [`nixpacks.toml`](../nixpacks.toml) | Build configuration |
| [`railway.toml`](../railway.toml) | Railway-specific settings |
| [`config.json`](../config.json) | App configuration (server, LLM, demo, affinity) |
| [`.env.example`](../.env.example) | Environment variable template |
| [`requirements.txt`](../requirements.txt) | Python dependencies |
