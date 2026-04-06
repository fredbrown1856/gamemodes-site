# 🚀 Deployment

## How the Site is Deployed
- **Platform**: GitHub Pages
- **Custom Domain**: gamemodes.xyz (configured via CNAME file)
- **Branch**: Changes to the main branch are automatically deployed
- **No build step required** — static files served directly

## Files Critical to Deployment
- `index.html` — The entire website
- `CNAME` — Must contain `gamemodes.xyz` for custom domain routing

## Deployment Checklist
1. Verify changes locally by opening `index.html` in a browser
2. Ensure no proprietary information (see content_guidelines.md) is present
3. Commit and push to main branch
4. Verify live site at https://gamemodes.xyz within a few minutes

## Notes
- GitHub Pages serves static content only — no server-side processing
- The CNAME file must NOT be deleted or modified
- DNS is managed externally (not in this repo)

---

## 🚂 Wendy Backend Deployment (Railway)

The Wendy NPC demo backend runs as a Flask app on [Railway.app](https://railway.app).

### Domain
- **Subdomain**: `chat.gamemodes.xyz` (CNAME to Railway)
- **DNS Records**:
  - `CNAME chat → <project>.up.railway.app`
  - `TXT _railway.chat.<domain> → <verification-token>` (required for custom domain)

### Environment Variables

Set via `railway variables` or the Railway dashboard. See [`Wendy/.env.example`](../Wendy/.env.example) for the full list:

| Variable | Purpose |
|----------|---------|
| `CEREBRAS_API_KEY` | LLM API key (Cerebras free tier) |
| `SESSION_SECRET` | Signing key for session tokens |
| `ADMIN_TOKEN` | Bearer token for admin endpoints (training export) |
| `TRAINING_ENCRYPTION_KEY` | AES-256-GCM key for encrypted exports |
| `IP_HASH_SALT` | Salt for hashing visitor IPs (privacy-preserving rate limiting) |
| `RAILWAY_VOLUME_MOUNT_PATH` | Path to persistent volume (auto-set by Railway) |

### Railway CLI Commands

```bash
# Install CLI
npm install -g @railway/cli

# Login
railway login

# Link to project (from Wendy/ directory)
railway link

# Deploy (from Wendy/ directory)
railway up

# View logs
railway logs

# Set a variable
railway variables set KEY=value

# Add a custom domain
railway domain add chat.gamemodes.xyz

# Open the live app
railway open
```

### Persistent SQLite Volume

- Railway provides an ephemeral filesystem — the database is lost on redeploy without a volume
- Add a **Volume** in the Railway dashboard, mounted at `/data`
- The app auto-detects `RAILWAY_VOLUME_MOUNT_PATH` and stores `wendy.db` there
- Config in [`Wendy/railway.toml`](../Wendy/railway.toml) and [`Wendy/nixpacks.toml`](../Wendy/nixpacks.toml)

### Port Binding
- Railway injects a `PORT` env var — the app **must** bind to `0.0.0.0` (not `127.0.0.1`)
- See [`Wendy/app.py`](../Wendy/app.py) startup config

### Redeploy After Changes
1. Make changes in `Wendy/`
2. Test locally: `cd Wendy && python app.py`
3. Deploy: `cd Wendy && railway up`
4. Verify: `railway logs` and check `https://chat.gamemodes.xyz/api/demo/stats`
