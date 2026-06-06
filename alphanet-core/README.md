# AlphaNet-402 (`alphanet-core/`)

Primary submission docs: **[`../README.md`](../README.md)**, **[`../docs/DEMO_GUIDE.md`](../docs/DEMO_GUIDE.md)** (judge flow), **[`../docs/PITCH_DECK_PRESENT.md`](../docs/PITCH_DECK_PRESENT.md)** (pitch deck).

## Run (from repo root)

```bash
./run_demo.sh       # API → http://localhost:8000
./run_frontend.sh   # UI  → http://localhost:5173  (proxies /api to :8000)
```

Or manually:

```bash
cd alphanet-core/backend && cp .env.example .env   # add TAVILY_API_KEY, GROQ_API_KEY as needed
cd alphanet-core/frontend && npm install && npm run dev
```

`GET /health` exposes `tavily_mode`: `tavily_rest_credits` | `tavily_x402_awal` | `paper`. Default **`TRADING_MODE=LIVE`** in code and `.env.example` (set **`PAPER`** in `.env` for offline-only scout).

## UI entry points

| Path | Purpose |
| --- | --- |
| `/` | Command Center |
| `/demo` | Judge walkthrough + pipeline |
| `/pitch-deck` | 3–5 minute presenter deck |
| `/x402-lab` | 402 unpaid vs paid rationale |

## Key API routes

| Route | Purpose |
| --- | --- |
| `GET /api/demo/briefing` | Judge talking points |
| `POST /api/demo/judge-run` | One full cycle + signals + sample invoice |
| `GET /api/state` | Agent state + `tavily_mode` |
| `GET /api/signals`, `GET /api/signals/{id}` | Signals |
| `GET /api/alpha/{ticker}/rationale`, `GET /api/trade/{id}/rationale` | x402 rationale |

## Reference repos (optional siblings)

See root README for `chf` and `polymarket-sentiment-agent` clone commands.

## Further reading

- `../docs/ARCHITECTURE.md` — Scout / Quant / Risk overview  
- `../docs/ARCHITECTURE_BLUEPRINT.md` — extended narrative  
- `../docs/AWAL_WALLET_SETUP.md` — wallet checklist  
- `../CURSOR_DOCS.md` — Base mainnet CAIP-2 reference  
