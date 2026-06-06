# Deploy AlphaNet-402: DigitalOcean + Azure + Sentry

Short integration guide for a hackathon / judge-stable demo.

## 1. DigitalOcean (primary 24/7 host)

1. Create an **Ubuntu 22.04** Droplet (1 GB RAM is enough for SQLite + FastAPI + static React).
2. SSH in, install **Python 3.11+**, **Node 20+**, **git**, **nginx** (optional reverse proxy).
3. Clone the repo, create `alphanet-core/backend/.env` with `TAVILY_API_KEY`, `GROQ_API_KEY`, `SENTRY_DSN`, `TRADING_MODE`, etc.
4. Backend:
   ```bash
   cd alphanet-core/backend
   python -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   # systemd: run uvicorn on 127.0.0.1:8010, nginx TLS → proxy_pass to uvicorn
   ```
5. Frontend:
   ```bash
   cd alphanet-core/frontend
   npm ci && npm run build
   # Serve `dist/` with nginx `root` or `python -m http.server` behind nginx only for demos
   ```
6. Keep **SQLite** on the droplet (`alphanet.db`); back up the file before demos.

## 2. Microsoft Azure (optional mirror / CI)

- **App Service (Linux container)** — build a small Docker image with FastAPI + copied `dist/` OR split API + static hosting on **Azure Static Web Apps**.
- **Azure DevOps** — pipeline: `npm run build`, `pip install`, `pytest` (if you add tests), artifact to App Service.
- Use Azure for Students credits for **non-prod** slots; keep secrets in **Key Vault** or App Service **Configuration** (not in git).

## 3. Sentry (errors from FastAPI + agent loop)

1. Create a project at [sentry.io](https://sentry.io) (student plan if available).
2. Copy the **DSN** into `alphanet-core/backend/.env`:
   ```env
   SENTRY_DSN=https://<key>@o<number>.ingest.sentry.io/<project>
   SENTRY_ENVIRONMENT=demo
   ```
3. Restart the API. `GET /health` reports `"sentry": true` when the DSN is loaded.
4. Trigger a test error in staging to confirm events appear before judging.

## 4. End-to-end demo checklist

| Check | Notes |
| --- | --- |
| Tavily | With `TAVILY_API_KEY`, scout uses **REST credits**; with `TRADING_MODE=LIVE` and no key, uses **x402 + AWAL**. |
| AWAL | `npx awal status` authenticated; Base wallet funded if using x402. |
| Groq | `GROQ_API_KEY` for NLP extraction (or heuristic fallback). |
| CORS / proxy | Production: same origin or configure CORS + HTTPS. |

**Security:** never commit `.env`; rotate any API key that was pasted into a chat or screen share.
