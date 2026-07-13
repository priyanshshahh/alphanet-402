# AlphaNet-402 (`alphanet-core/`)

Backend (FastAPI agent) + frontend (React Command Center). Product overview
lives in the **[root README](../README.md)**; operational details in
**[`../docs/PROJECT-NOTES.md`](../docs/PROJECT-NOTES.md)**.

## Run (from repo root)

```bash
./run_backend.sh    # API → http://localhost:8000
./run_frontend.sh   # UI  → http://localhost:5173  (proxies /api to :8000)
```

Or manually:

```bash
cd alphanet-core/backend && cp .env.example .env   # optional: TAVILY_API_KEY, GROQ_API_KEY
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn app.main:app --port 8000

cd alphanet-core/frontend && npm install && npm run dev
```

Everything runs **keyless** by default: real prices/fundamentals via yfinance,
deterministic heuristic NLP, Bayesian math in Python.
`GET /health` exposes `data_mode`: `yfinance` | `yfinance+tavily_rest` |
`yfinance+tavily_x402` | `demo`. `DEMO_MODE=1` switches to labeled synthetic
data only when you ask for it.

## Tests

```bash
cd alphanet-core/backend && pytest tests -q   # 50 offline tests, no network
```

## UI entry points

| Path | Purpose |
| --- | --- |
| `/` | Command Center |
| `/demo` | Guided walkthrough + pipeline |
| `/pitch-deck` | Presenter deck |
| `/x402-lab` | 402 unpaid vs paid rationale |

## Key API routes

| Route | Purpose |
| --- | --- |
| `GET /api/state` | Agent state + `data_mode` / `demo_mode` |
| `POST /api/cycle` | Run one scout→quant→risk pass |
| `GET /api/signals`, `GET /api/signals/{id}` | Signals + causal detail |
| `GET /api/alpha/{ticker}/rationale`, `GET /api/trade/{id}/rationale` | x402-paywalled rationale |

## Further reading

- `../docs/ARCHITECTURE.md` — Scout / Quant / Risk overview
- `../docs/AWAL_WALLET_SETUP.md` — wallet checklist
- `../docs/PROJECT-NOTES.md` — guardrails, deploy, honest status
