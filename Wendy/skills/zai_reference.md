# Z.AI (GLM-5.1) API Reference

## API Configuration

- **Base URL:** `https://api.z.ai/api/coding/paas/v4`
- **Chat Completions:** `https://api.z.ai/api/coding/paas/v4/chat/completions`
- **Model:** `glm-5.1`
- **API Key:** `64a6d808fa664b478f2695e3690fc435.Rdra3ykmNXC46ApT`

## OpenAI-Compatible Usage

```python
import requests

response = requests.post(
    "https://api.z.ai/api/coding/paas/v4/chat/completions",
    headers={
        "Authorization": "Bearer 64a6d808fa664b478f2695e3690fc435.Rdra3ykmNXC46ApT",
        "Content-Type": "application/json"
    },
    json={
        "model": "glm-5.1",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"}
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    },
    timeout=60
)
response.raise_for_status()
result = response.json()["choices"][0]["message"]["content"]
```

## Supported Models

| Model | Description | Quota Cost |
|-------|-------------|------------|
| glm-5.1 | Most capable, rivals Claude Opus | 3x peak / 1x off-peak |
| glm-5 | Advanced reasoning | Standard |
| glm-5-turbo | Fast advanced model | 3x peak / 1x off-peak |
| glm-4.7 | Balanced performance | Standard |
| glm-4.5-air | Lightweight, fast | Standard |

## Quota Limits

| Plan | 5-Hour Limit | Weekly Limit |
|------|-------------|-------------|
| Lite | ~80 prompts | ~400 prompts |
| Pro | ~400 prompts | ~2,000 prompts |
| Max | ~1,600 prompts | ~8,000 prompts |

**Peak hours:** 14:00-18:00 UTC+8 (GLM-5.1 costs 3x quota)
**Off-peak:** All other times (GLM-5.1 costs 1x quota, promo through end of April)

## MCP Tools Available

- **Vision Understanding** — Image analysis
- **Web Search** — Real-time web search
- **Web Reader** — Web page content extraction
- **Zread** — GitHub repository analysis

## Usage in Gamemodes Projects

All projects can use this API key. Key tools:
- **GPM:** Daily planning (`gpm/config.json`)
- **Data Collector:** Training data generation (`data_collector/config.json`)
- **Website (Wendy):** NPC dialogue (`Gamemodes-site/Wendy/config.json`)

---

*Reference saved: 2026-04-07*