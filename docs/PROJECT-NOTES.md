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
- Control endpoints require auth: `POST /api/reset` and `POST /api/cycle`
  need `Authorization: Bearer $ADMIN_TOKEN`. No `ADMIN_TOKEN` set → both
  return 503 (disabled) rather than being open to an unauthenticated caller;
  wrong/missing token → 401. Token comparison is constant-time.
- Sell-side settlement verification: before booking revenue for a non-`demo-`
  sale, the seller extracts the settlement tx hash from the `X-Payment` proof
  and confirms it on Base Sepolia via `eth_getTransactionReceipt`
  (`SETTLEMENT_RPC_URL`, raw JSON-RPC over httpx — no web3.py). The tx must
  have succeeded and carried a USDC `Transfer` to our payTo for the invoiced
  amount. Verified → `daily_revenue_usdc += 0.01`; unverifiable → served but
  recorded in `daily_unverified_usdc` and **excluded from revenue**; demo →
  nothing booked. Empty `SETTLEMENT_RPC_URL` disables verification (everything
  non-demo then records as `unverified`).

## Known limitations (honest list)

1. **Incoming x402 receipts are now verified on-chain (was limitation #1).**
   Revenue is booked on proof of settlement, not a trusted header; unverifiable
   payments are excluded from the revenue counter. Verification depends on a
   reachable Base RPC and a settlement tx hash being present in the proof — in
   a full production x402 flow that hash comes from the facilitator's `settle`
   response.
2. **LIVE x402 *purchase* requires Node in the runtime.** The buy path
   (`ingestion._live_pay`) and CLI wallet resolution (`resolve_pay_to`) shell
   out to `npx awal` (Node). The documented Render deploy (`render.yaml`,
   `runtime: python`) does not provision Node, so the LIVE buy path is
   unreachable there — it hits `FileNotFoundError` and degrades to `paid=False`.
   This is fine by design (testnet + paper), but do not read the LIVE path as
   working on the Render blueprint. Set `OUR_AWAL_WALLET_ADDRESS` explicitly
   and prefer `TAVILY_API_KEY` (REST) there, or run locally with Node for
   actual x402 buys.
3. **Paper trading only.** Position sizes are notional (1,000 USDC demo
   bankroll, 10% cap, fractional-Kelly scaling). No broker integration.
4. **Signals are directional beliefs, not calibrated forecasts.** The
   log-odds evidence weights are hand-set, not fitted; no backtest is claimed.
   The two Bayesian channels are blended at a fixed, config-driven weight
   (`BAYES_TABLE_WEIGHT`, default 0.65), not a learned one.
5. **yfinance is an unofficial Yahoo API** — fine for a research agent, not a
   production market-data contract. Tavily is the paid upgrade path.
6. **SQLite on Render free tier is ephemeral** (`/tmp`); state resets on
   redeploy. Acceptable: signals regenerate each cycle.

## New surfaces (campaign 3)

- `GET /api/economics` + **Unit economics** page — real self-funding P&L from
  the SPEND/REVENUE ledger (spend vs verified revenue, margins, break-even).
- **Methodology** page — prior→posterior→edge, the configurable blend, data
  sources, limitations, and a not-investment-advice disclaimer.
- `GET /api/x402/discovery` — Bazaar-style discovery record so agents can find
  and price the seller endpoint.
- Paid rationale payload now carries `sources` (provenance), `payment_status`
  (demo | verified | unverified | duplicate), and a `quality` block.

**Settlement is booked at most once per tx, globally.** `X402Receipt.tx_hash`
is indexed and checked before revenue is credited: the same settled transfer
presented against a *different* signal is recorded as `duplicate` (served, no
revenue), not paid out again. The per-(proof, signal) `receipt_key` only stops
exact replays; this closes the cross-signal replay. Known follow-up: the
consumed-check and the insert aren't one atomic transaction, so two truly
concurrent requests with the same tx hash could each pass the read before
either commits — wrap check+insert in a locked transaction or add a DB-level
uniqueness rule on consuming rows to close that window.

**Quality gate is report-only (for now).** Each sold payload carries a
`quality` block — the signal's age plus checks for `leakage_ok`, evidence
present, an actionable edge, and freshness (≤24h), and a `sellable` verdict.
Today it *labels* the report so a buyer can see it cleared a bar; it does not
yet withhold a failing report from sale. Actually blocking a low-quality
rationale from being sold (return the teaser + a reason instead of settling)
is the documented next step.

## Verified runs (2026-07-12)

- Keyless end-to-end: `run_cycle()` over AAPL/MSFT produced real signals from
  live yfinance data (heuristic NLP path), decisions BUY/SELL with edges
  ±0.10–0.12 on that day's data.
- Live Tavily REST + Groq: NVDA scout returned 2 yfinance events + 5 real
  Tavily news results; Groq extracted features; posterior moved 0.490 → 0.539
  (edge +0.0485 → HOLD). API keys were provided at runtime only and are not in
  the repo or its history.
- Test suite: 81/81 passing offline in <1s (`pytest tests -q`), including
  admin-token auth coverage on `/api/reset` and `/api/cycle`, and on-chain
  settlement verification (verified/unverified/demo revenue paths, tx-hash
  extraction, USDC transfer matching) added in campaign 3.

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
