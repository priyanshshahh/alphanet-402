# Architectural Blueprint and System Dynamics of Autonomous Quantitative Agents: A Case Study on AlphaNet-402

> **Elevator pitch & Fintel mapping:** See [`HACKATHON_CONCEPT.md`](HACKATHON_CONCEPT.md).  
> **Canonical implementation boundary:** For exact CLI flags, CAIP-2 IDs, JSON 402 envelopes, and env var names, treat [`CURSOR_DOCS.md`](../CURSOR_DOCS.md) as authoritative. This document is the conceptual and systems narrative; where it mentions Base Sepolia for safe MVP iteration or `GET /api/trade/{id}/rationale`, align shipping code with `CURSOR_DOCS.md` (Base Mainnet `eip155:8453`, `GET /api/alpha/{ticker}/rationale`) unless you explicitly choose testnet for a demo.

---

## The Macroeconomic Shift Toward Agentic Commerce

The digital economy is restructuring from human-centric, interface-driven interactions toward autonomous machine-to-machine (M2M) commercial ecosystems. Historically, AI agents were bound by human administrative overhead: accounts, subscription tiers, API keys, and billing monitoring—friction that contradicts programmatic, instantaneous operation and blocks full autonomy.

HTTP **402 Payment Required**, long dormant, is now operationalized through the **x402** protocol. The x402 Foundation (Linux Foundation) and industry participants (Coinbase, Stripe, Cloudflare, Google, AWS, and others) define an open standard for internet-native payments. Agents can discover, negotiate, and pay for resources at runtime without prior subscriptions or human-in-the-loop billing, using stablecoins such as USDC on high-throughput chains (Base, Polygon, Solana, etc.) for sub-cent microtransactions.

**AlphaNet-402** merges deterministic quant research (from Project CHF) with live Bayesian trading logic (from the Polymarket sentiment agent): it **consumes** x402-gated data to compute edges and **produces** monetized analytics behind the same payment pattern.

---

## The x402 Protocol: Mechanics and State Machine

x402 embeds settlement in normal HTTP cycles: a legacy status code becomes a cryptographic payment handshake. The flow is transport-agnostic and supports fiat and crypto rails.

### Four-step HTTP payment handshake

| HTTP status / action | Protocol state | Actor responsibility | Header implication |
| --- | --- | --- | --- |
| `GET /resource` | Initiation | Client (AI agent) | Standard HTTP headers |
| `402 Payment Required` | Challenge | Server (resource host) | Machine-readable invoice (e.g. `payment-required` / body per spec) |
| Facilitator work | Execution | Facilitator (Coinbase, Stripe, open facilitators, etc.) | Off-chain verification → on-chain settlement |
| `GET /resource` (retry) | Retry | Client | `PAYMENT-SIGNATURE` / `X-Payment` (proof of payment) |
| `200 OK` | Fulfillment | Server | Payload + payment receipt metadata |

**Failure handling:** Implement explicit handling for facilitator rejections (`invalid_payload`, etc.), insufficient balance, and malformed proofs so the agent **halts** rather than loops or double-pays.

---

## Foundational Stack and Resource Provisioning

| Layer | Role |
| --- | --- |
| **Hosting (e.g. DigitalOcean)** | Ubuntu droplet for 24/7 FastAPI + SQLite; avoids laptop sleep/Wi-Fi drops during demos. |
| **LLM (Azure OpenAI or Groq)** | Feature extraction only; Groq/Llama 3 favors low latency. **No** LLM-driven arithmetic for prices or P\&L. |
| **Search (Tavily)** | AI-native search; **402** path (`https://402.tavily.com/v1/search`) or keyless modes exercise true x402 pay-per-call (~$0.01 USDC) without traditional API-key subscription friction. |
| **Wallet (Coinbase AWAL)** | `npx awal` CLI (or MCP/skills) for programmatic signing; narrative often uses **Base Sepolia** for MVP; production target in `CURSOR_DOCS.md` is **Base Mainnet**. |

### Directory preparation (workspace)

Parent repo **`alphanet-402`**, with sibling clones for Cursor context:

```bash
mkdir alphanet-402
cd alphanet-402
git clone https://github.com/priyanshshahh/chf.git
git clone https://github.com/priyanshshahh/polymarket-sentiment-agent.git
```

Unified application code lives under **`/alphanet-core`** (backend + frontend), synthesizing **@chf** (leakage-aware research) and **@polymarket-sentiment-agent** (live Bayesian updates).

---

## Coinbase Agentic Wallet (AWAL)

AWAL targets **machine** use: CLI + skills vs. human-per-click browser wallets. Typical flow:

1. **Health:** `npx awal@latest status` — CDP connectivity and auth state.
2. **Auth:** `npx awal@latest auth login <email>` → `flowId`; then `npx awal@latest auth verify <flowId> <otp>`.
3. **Treasury:** `npx awal@latest balance --chain base-sepolia` (or mainnet per deployment); `npx awal@latest address`.
4. **Pay for HTTP resources:** `npx awal x402 pay <url> -X POST -d '<json>' --max-amount <atomic-units> [--json]` — **hard cap** per request to limit malicious invoices and runaway loops.

Optional: `npx skills add coinbase/agentic-wallet-skills` for structured agent skills mapping to these CLI primitives.

### Skill → CLI mapping (conceptual)

| Skill / primitive | CLI / path | Purpose |
| --- | --- | --- |
| authenticate-wallet | `npx awal auth login` | Session / identity |
| send-usdc | `npx awal send <amt> <recipient>` | Transfers |
| trade | `npx awal trade …` | Swaps on Base |
| pay-for-service | `npx awal x402 pay <url>` | 402 challenge → settle → retry |

---

## Tavily and Dynamic Data Acquisition

Legacy search returns noisy HTML; Tavily returns **LLM-oriented** structured text. For AlphaNet-402, the ingestion module targets **`402.tavily.com/v1/search`** (and/or keyless header patterns per Tavily docs).

Example POST body:

```json
{
  "query": "institutional accumulation, SEC filings, and whale wallet movements for <TICKER>",
  "search_depth": "advanced",
  "include_raw_content": false,
  "max_results": 5
}
```

**Flow:** Unpaid POST → **402** + invoice → backend catches 402 → **`npx awal x402 pay`** (subprocess) → retry with proof → **200** + JSON. Prefer **`subprocess` + AWAL** over `tavily-python` for the 402 path, per `CURSOR_DOCS.md`.

---

## Quantitative Signal Processing (Fintel-Inspired)

Conceptually mirror institutional screens:

- **Fund / insider sentiment:** multi-factor scores (e.g. 0–100 scale), net insider buy/sell counts, float and ownership context; officer activity weighted heavily vs. passive holders.
- **QVM-style decomposition:** quality (e.g. ROE, ROIC percentiles), value (e.g. EV/EBIT, book-to-market percentiles), momentum (e.g. 6-month return percentile)—**combined in Python**, not by the LLM.

**Hard rule:** The LLM outputs **only** structured features (booleans, enums, cited phrases), e.g. `has_recent_ceo_buying`, `institutional_accumulation_trend`, `qvm_metrics_mentioned`. All **math** (log-odds, edges, thresholds) runs in **`quant_pipeline.py`**.

---

## Bayesian Log-Odds and CHF Leakage Guards

Let **H** be the hypothesis (e.g. future upside) and **E** the evidence from Tavily + NLP features.

- **Odds:** \(O(H) = P(H) / P(\neg H)\).
- **Likelihood ratio:** \(\Lambda(E) = P(E|H) / P(E|\neg H)\).
- **Posterior odds:** \(O(H|E) = O(H) \cdot \Lambda(E)\).
- **Stable implementation:** work in **log-odds** space: \(\log O(H|E) = \log O(H) + \log \Lambda(E)\) to avoid underflow near 0/1.

Pre-defined **log \(\Lambda\)** weights per feature class (examples from the case study narrative):

| Extracted NLP feature | \(\log \Lambda\) (illustrative) | Interpretation |
| --- | --- | --- |
| `has_recent_ceo_buying: true` | +0.45 | Strong bullish |
| `institutional_trend: "bullish"` | +0.22 | Moderate bullish |
| `regulatory_risk_mentioned: true` | −0.60 | Strong bearish |
| `insider_selling_spikes: true` | −0.35 | Moderate bearish |

**Leakage guards** (from CHF `FeatureAgent` / `BacktestAgent` ideas): validate timestamps and public availability of filings vs. simulation time; discard signals that imply lookahead or unverifiable chronology.

Compare posterior to **market-implied** probability (e.g. Polymarket odds); if edge exceeds **`EDGE_THRESHOLD`** (env), emit a signal—**paper mode** first.

---

## IDE Orchestration (Build Sequence)

1. **Scaffold** `alphanet-core/backend` (FastAPI, SQLAlchemy, SQLite) and `alphanet-core/frontend` (Vite, React, Tailwind); `requirements.txt`, `.env.example`.
2. **`Tavily402Scout`** in `app/modules/ingestion.py`: POST → on 402, shell out to AWAL → retry; strict budget checks.
3. **`quant_pipeline.py`**: `verify_no_leakage()`, `calculate_chf_leakage_safe_edge` (or equivalent), idempotent DB writes (idempotency keys for trades/signals).
4. **Risk** module from polymarket-sentiment-agent patterns (drawdown, sizing).
5. **Monetization route** in `app/api/routes.py`: expose a rationale endpoint behind x402; **naming:** case study uses `GET /api/trade/{id}/rationale`—implement the JSON contract from `CURSOR_DOCS.md` and the route shape your product needs (`/api/alpha/{ticker}/rationale` vs trade ID).
6. **Dashboard:** “AlphaNet-402 Command Center”—budget, x402 spend, logs, positions.

---

## Agentic Bazaar: Selling the Rationale

After paying Tavily and computing a verified edge, the system **sells** the explanation: **402** without valid payment header → invoice; with valid **`X-Payment` / proof** → facilitator verification → **200** with causal JSON (sources, LLM features, log-odds math, decision timestamp). **Idempotency** prevents double-charging on retries.

---

## Works cited (URLs)

1. x402 standard — https://www.x402.org/  
2. x402 ecosystem — https://www.x402.org/ecosystem  
3. HTTP 402 core concepts — https://docs.x402.org/core-concepts/http-402  
4. Cloudflare x402 foundation post — https://blog.cloudflare.com/x402/  
5. x402 PyPI — https://pypi.org/project/x402/  
6. x402 quickstart (sellers) — https://docs.x402.org/getting-started/quickstart-for-sellers  
7. Agentic Wallet CLI — https://docs.cdp.coinbase.com/agentic-wallet/cli/welcome  
8. Agentic wallets launch — https://www.coinbase.com/developer-platform/discover/launches/agentic-wallets  
9. AWAL quickstart — https://docs.cdp.coinbase.com/agentic-wallet/cli/quickstart  
10. Tavily agents — https://docs.tavily.com/agents  
11. Tavily keyless — https://docs.tavily.com/documentation/keyless  
12. Tavily x402 — https://docs.tavily.com/documentation/machine-payments/x402  
13. agentic-wallet-skills / x402-pay reference — https://github.com/coinbase/agentic-wallet-skills  
14. x402-facilitator (example) — https://github.com/second-state/x402-facilitator  
15. Agentkit issue (x402 pay rejection context) — https://github.com/coinbase/agentkit/issues/947  
16. Fintel quant models — https://fintel.io/quant-models  
17. Fintel workbench syntax — https://fintel.io/news/fintel-workbench-complete-syntax-reference-558  

Additional references from the original narrative: The Defiant (Linux Foundation x402), Stripe x402 docs, Allium / Algorand x402 explainers, awesome-x402, Tavily blog, Parallel / Exa / Tavily comparisons, Proxyway scraping report—use as background reading; pin versions and verify URLs before production dependencies.
