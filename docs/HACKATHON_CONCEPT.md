# AlphaNet-402: Hackathon Concept & Fintel Tie-In

Short reference: what you are building, how **Fintel.io** inspires it, and how **Project CHF** + **polymarket-sentiment-agent** merge with **x402** and **Coinbase AWAL** (not “AWOL”).

---

## 1. What Fintel.io Is (The Inspiration)

**Fintel** is an investment research platform focused on “smart money”: institutional data such as SEC **13F / 13D** filings, **insider** activity, and **options** flow. Their pipelines produce scores like a **Fund Sentiment Score**—a quantitative read on how heavily institutions and whales are accumulating (or distributing) a name.

**AlphaNet-402** is a decentralized, **agentic** analogue for **crypto and prediction markets**: live-ish signals from the open web, **pay-per-query** micro-payments instead of monthly subscriptions, and strict **quant + risk** machinery on top.

---

## 2. The Core Concept: AlphaNet-402

You are building an **autonomous quantitative agent** that is simultaneously:

- **A trader** — consumes intelligence, updates beliefs, acts under risk limits.  
- **A data provider** — sells processed, math-backed rationale to other agents via **HTTP 402 / x402**.

Unlike leaning on delayed quarterly filings or hitting **API walls** (as in early CHF data access), the system **hunts** for real-time institutional sentiment and whale-like behavior using **Tavily** behind **x402** (~**$0.01 USDC** per search with **AWAL**). It turns text into features, runs **Bayesian** updates in **Python**, executes (e.g. paper / Polymarket), and **monetizes** the causal chain for other bots.

---

## 3. How the Repositories Merge

| Layer | Role | Source ideas |
| --- | --- | --- |
| **Fintel-style Scout (ingestion)** | Replace brittle or capped historical API pulls with **Tavily 402** + subprocess **`npx awal x402 pay`**. Search for whale flows, ETF / institutional crypto narratives, macro regulatory items—**Fintel-like** signals without a single monolithic data vendor. | CHF (**MarketDataAgent** pain → web + pay-per-call model) |
| **Poly-Quant engine (analysis)** | **LLM = text parser only** (direction of smart money, structured fields). **Python = all probability / log-odds / edge math.** Prior (e.g. market price / implied odds) + evidence → actionable edge. | **polymarket-sentiment-agent** |
| **CHF overseer (risk)** | **Leakage guards** and sanity checks before trusting a signal; **drawdown / kill-switches** and sizing from the Poly side so the loop cannot run amok. | **chf** + Poly risk modules |
| **x402 paywall (monetization)** | Same pattern as Fintel’s subscription, but **per-call** for machines: expose a rationale endpoint behind **402**, verify payment, return the full causal payload. | Poly-style rationale route |

**Route naming:** The Poly agent may use `GET /api/trade/{id}/rationale`. The canonical envelope in this repo is documented under **`GET /api/alpha/{ticker}/rationale`** in [`CURSOR_DOCS.md`](../CURSOR_DOCS.md)—unify naming in code to one pattern before demo.

---

## 4. The Pitch (One Paragraph)

You are building an agent that **buys** Fintel-style smart-money signal text through **micro-payments**, **validates** alpha with rigorous quant architecture (leakage-safe, Bayesian, risk-capped), **trades** the edge, and **funds** ongoing ingestion by **selling** processed insights to other agents for **~$0.01 USDC** per call—a **self-sustaining**, machine-native research and trading loop on the **agentic web**.

---

## See Also

- [`CURSOR_DOCS.md`](../CURSOR_DOCS.md) — AWAL CLI, Base `eip155:8453`, 402 JSON, env limits.  
- [`docs/ARCHITECTURE_BLUEPRINT.md`](ARCHITECTURE_BLUEPRINT.md) — Long-form system dynamics and citations.
