# AlphaNet-402 — architecture

AlphaNet-402 is a **closed loop**: ingest → infer → guard → expose. Market
data and money move through the same contract surfaces you can hit with a
browser and a wallet.

---

## Visual loop

```
┌──────────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│    SCOUT     │ ──► │    QUANT    │ ──► │    RISK     │ ──► │  COMMAND     │
│  yfinance +  │     │  (Bayesian) │     │  (limits)   │     │  CENTER +    │
│ Tavily x402  │     │  + LLM NLP  │     │  halt/kill  │     │  x402 APIs   │
└──────────────┘     └─────────────┘     └─────────────┘     └──────────────┘
       │                    │                   │                    │
       └────────────────────┴───────────────────┴────────────────────┘
                              SQLite state
```

---

## Scout module (`app/modules/ingestion.py`, `app/modules/market_data.py`)

- **Role:** acquire fresh market evidence for each equity on the watchlist.
- **Mechanisms, in order:**
  1. **yfinance** (keyless, always on): ~7 months of daily bars + fundamental
     ratios, distilled into factual event snippets plus a base-rate prior
     derived from actual up-day frequency.
  2. **Tavily news layer** on top: REST when `TAVILY_API_KEY` is set (plan
     credits), else `npx awal x402 pay` against Tavily's 402 endpoint in
     `TRADING_MODE=LIVE` (USDC micropayment per query).
  3. **`DEMO_MODE=1` only:** deterministic synthetic snippets, every record
     labeled `"demo": true`. Never a silent fallback — a failed fetch surfaces
     as "no data", not fake data.
- **Observability:** structured log rows (`SCOUT`, `TAVILY`, `X402`, `SPEND`).

---

## Quant module (`app/modules/quant_pipeline.py`)

- **Role:** turn prose into **strict JSON features** (Groq LLM when a key is
  set, deterministic heuristic otherwise), then compute **posterior beliefs
  and edge** in **Python only** via a Bayesian log-odds update with fixed
  evidence weights.
- **Invariant:** the language model is **not** the portfolio engine; it never
  computes probabilities, prices, or sizes.
- **Leakage guard:** `verify_no_leakage()` rejects look-ahead priors, empty
  evidence, and future-year references before any decision is recorded.

---

## Risk module (`app/modules/risk.py`)

- **Role:** compliance layer over the loop: **daily spend cap**, **per-query
  price cap**, **drawdown limit**, fractional-Kelly-style position sizing,
  and a **halt** kill-switch when anything breaches.
- **Outputs:** agent state (`IDLE` / `SCOUTING` / `HALTED`), reasons, and log
  events readable in the UI or API.

---

## Surfaces

- **FastAPI** — `/api/state`, `/api/signals`, `/api/cycle`, `/api/demo/*`, and
  **402**-protected rationale routes (refused with 503 until a payTo wallet
  is configured — no zero-address fallback).
- **React** — operator overview, signal drill-down, **x402 Lab**, walkthrough,
  pitch deck. Demo mode is labeled with a visible badge.
- **SQLite** — durable signals, idempotent x402 receipts, spend/revenue ledger.
