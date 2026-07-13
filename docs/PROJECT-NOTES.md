# AlphaNet-402 — project notes

Working notes for operators and reviewers. The README covers the pitch; this
covers how it actually behaves.

## Provenance

This repo began as a twin of the signalrelay hackathon submission. On
2026-07-12 it was diverged into a distinct project: the chf quant engine and
polymarket-sentiment-agent were removed (they live in signalrelay), and the
remaining alphanet-core + consumer stack was rebuilt around **real equities
data**. Branch `pre-campaign` preserves the pre-divergence tree.

## Data paths (exact behavior)

| Mode | Trigger | What flows |
| --- | --- | --- |
| `yfinance` | default, keyless | ~7mo daily bars + fundamentals → factual event snippets + base-rate prior |
| `yfinance+tavily_rest` | `TAVILY_API_KEY` set | + finance-topic news via Tavily REST (plan credits) |
| `yfinance+tavily_x402` | no key, `TRADING_MODE=LIVE` | + Tavily news bought with USDC via `npx awal x402 pay` |
| `demo` | `DEMO_MODE=1` only | synthetic headlines, `"demo": true` on every record, UI badge |

A failed yfinance fetch surfaces as "no data for ticker" in the log — the
agent never silently substitutes synthetic data.

The **prior** in real modes is the last-60-session up-day frequency, shrunk
toward 0.5 and clipped to [0.35, 0.65] (`market_data.estimate_prior`). In demo
mode it is a deterministic pseudo-prior. It is a base-rate estimate, not a
market-implied probability.

## Guardrails

- `MAX_PRICE_PER_SEARCH_USDC` (default $0.01) — per-query cap on x402 pays
- `MAX_DAILY_SPEND_USDC` (default $2.00) — daily scout budget, ledger-enforced
- `DAILY_DRAWDOWN_LIMIT_USDC` (default $5.00) — halts the loop
- `EDGE_THRESHOLD` (default 0.05) — minimum |edge| for a paper BUY/SELL
- Leakage guard rejects look-ahead priors, empty evidence, future-year text
- Payments fail hard: no `OUR_AWAL_WALLET_ADDRESS` (or awal login) → invoice
  endpoints return 503; the zero address is rejected everywhere

## Known limitations (honest list)

1. **Incoming x402 receipts are not cryptographically verified.** Any
   non-`demo-` `X-Payment` header settles a sale. Wiring a facilitator
   verification call is the next real milestone before charging anyone.
2. **Paper trading only.** Position sizes are notional (1,000 USDC demo
   bankroll, 10% cap, fractional-Kelly scaling). No broker integration.
3. **Signals are directional beliefs, not calibrated forecasts.** The
   log-odds evidence weights are hand-set, not fitted; no backtest is claimed.
4. **yfinance is an unofficial Yahoo API** — fine for a research agent, not a
   production market-data contract. Tavily is the paid upgrade path.
5. **SQLite on Render free tier is ephemeral** (`/tmp`); state resets on
   redeploy. Acceptable: signals regenerate each cycle.

## Verified runs (2026-07-12)

- Keyless end-to-end: `run_cycle()` over AAPL/MSFT produced real signals from
  live yfinance data (heuristic NLP path), decisions BUY/SELL with edges
  ±0.10–0.12 on that day's data.
- Live Tavily REST + Groq: NVDA scout returned 2 yfinance events + 5 real
  Tavily news results; Groq extracted features; posterior moved 0.490 → 0.539
  (edge +0.0485 → HOLD). API keys were provided at runtime only and are not in
  the repo or its history.
- Test suite: 50/50 passing offline in <1s (`pytest tests -q`).

## Deploy

- **Backend:** Render free tier via `render.yaml` (python runtime,
  `uvicorn app.main:app`). Set `OUR_AWAL_WALLET_ADDRESS`, `TAVILY_API_KEY`,
  `GROQ_API_KEY` in the dashboard as needed.
- **Frontend:** Vercel — root `alphanet-core/frontend`, build `npm run build`,
  output `dist`, env `VITE_API_BASE=https://<render-service>.onrender.com`.
- CORS is an explicit allowlist (`ALPHANET_ALLOWED_ORIGINS`, comma-separated;
  defaults to localhost dev origins, wildcard entries are rejected). Set it to
  the Vercel origin on the Render service.

## Dev

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r alphanet-core/backend/requirements.txt pytest ruff
cd alphanet-core/backend && ../../.venv/bin/pytest tests -q && ../../.venv/bin/ruff check .
cd ../frontend && npm ci && npm run build
```
