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
