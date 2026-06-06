# AlphaNet-402 — architecture (submission overview)

AlphaNet-402 is a **closed loop**: ingest → infer → guard → expose. Money and data move through the same contract surfaces your judges can hit with a browser and a wallet.

---

## Visual loop

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   SCOUT     │ ──► │    QUANT    │ ──► │    RISK     │ ──► │  COMMAND     │
│  (Tavily)   │     │  (Bayesian) │     │  (limits)   │     │  CENTER +    │
│  x402/REST  │     │  + Groq NLP │     │  halt/kill  │     │  x402 APIs    │
└─────────────┘     └─────────────┘     └─────────────┘     └──────────────┘
       │                    │                   │                    │
       └────────────────────┴───────────────────┴────────────────────┘
                              SQLite state
```

---

## Scout module

- **Role:** Acquire fresh, text-rich market context (whale / flow / narrative) for each watchlist name.  
- **Mechanisms:** Prefer **Tavily REST** when an API key is configured; otherwise optional **x402 + AWAL** live pay; otherwise a deterministic **offline** scout path so the UI always remains demoable.  
- **Outputs:** Normalized search snippets + raw text bundle passed downstream.  
- **Observability:** Structured log rows (e.g. `TAVILY`, `X402`, `SPEND`) for live judge narration.

---

## Quant module

- **Role:** Turn prose into **strict JSON features** (LLM), then compute **posterior beliefs and edge** in **Python only**.  
- **Invariant:** The language model is **not** the portfolio engine; it does not silently “decide trades.”  
- **Outputs:** Persisted **signals** with sentiment, confidence, edge, decision metadata, and evidence payloads for the dashboard and for-sale rationales.

---

## Risk module

- **Role:** Oversee the agent like a compliance layer: **daily spend**, **per-query price cap**, **drawdown-style limits**, and **halt** when breached.  
- **Outputs:** Agent state (`IDLE` / halted), reasons, and log events judges can read in the UI or API.  
- **Purpose:** Makes autonomy **auditable** — the fund cannot “run away” from its budget in the demo configuration.

---

## Surfaces

- **FastAPI** — `/api/state`, `/api/signals`, `/api/cycle`, `/api/demo/*`, and **402**-protected rationale routes.  
- **React** — Operator overview, signal drill-down, **x402 Lab**, **Judge demo**, and **Pitch deck**.  
- **SQLite** — Durable signals, receipts, and agent accounting for repeatable demos.
