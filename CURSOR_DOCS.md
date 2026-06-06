# Agentic Wallet & x402 Protocol Reference

This document contains the exact CLI commands, protocols, and architectural patterns required to build AlphaNet-402. Do not hallucinate SDKs; rely strictly on these documented patterns.

For the **hackathon pitch** and how Fintel maps to CHF + Poly, see [`docs/HACKATHON_CONCEPT.md`](docs/HACKATHON_CONCEPT.md). For the full systems narrative (x402 state machine, AWAL onboarding, Fintel-inspired features, Bayesian log-odds, leakage guards, and build sequencing), see [`docs/ARCHITECTURE_BLUEPRINT.md`](docs/ARCHITECTURE_BLUEPRINT.md). When anything in those docs disagrees with **this** file (network, route paths, env names), **this file wins** for production mainnet targets.

> **Note:** The shipped `alphanet-core/backend/.env.example` defaults to **Base Sepolia** (`eip155:84532`) for safer hackathon demos. For **Base Mainnet** (`eip155:8453`), override `NETWORK_CAIP_ID`, `USDC_CONTRACT_ADDRESS`, and typically clear `AWAL_X402_PAY_EXTRA` in your `.env`.

## 0. Stack & subscriptions (pre-flight checklist)

**Principle:** Treat this file as the source of truth for `awal` / x402 behavior so the model does **not** invent a “Coinbase Python SDK” or a Tavily SDK path that bypasses micropayments. Ingestion and payments are **CLI + `subprocess`**, not proprietary Python SDKs from Coinbase.

### What to link in Cursor before pasting the master prompt

| Resource | Role | Keys / spend |
| --- | --- | --- |
| **Tavily x402** | AI-native search billed per request | **No** traditional Tavily API key for the `402.tavily.com` flow. Pay **~$0.01 USDC** per search via AWAL. **Do not** use `tavily-python` for this path. |
| **Coinbase AWAL** | Sign x402 micropayments from the agent | **No** Coinbase Python SDK in-app. Use `npx awal@latest` (or `npx awal`) via shell / `subprocess`. |
| **LLM** | High-throughput **NLP feature extraction only** | **Groq** (free tier, Llama 3) and/or **Azure OpenAI** (GitHub Student Pack / Azure for Students **$100** credit). Not for pricing or portfolio math. |
| **Hosting** | Laptop-safe demo | **DigitalOcean** (~**$200** student credit): Ubuntu droplet for FastAPI + React build artifacts + SQLite (e.g. `doa.db` on the droplet). **Azure** (~**$100** student credit): optional **App Service** mirror and **Azure DevOps** for clean CI builds. |
| **Monitoring** | Subprocess / wallet / 402 failures | **Sentry** (e.g. student plan) in `app/main.py`; **Datadog** (optional) if you want metrics beyond errors. |

### API keys and secrets (what you actually need)

* **Tavily:** No `TAVILY_API_KEY` for traffic that **only** hits `https://402.tavily.com/v1/search` through **`npx awal x402 pay`** with a JSON body.
* **Groq (default inference):** `GROQ_API_KEY` — free tier, keeps LLM cost at **$0** while USDC goes to data.
* **Azure OpenAI (optional):** `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, plus deployment name (see `.env.example`) if you prefer student credits.
* **Sentry (recommended for demo):** `SENTRY_DSN` optional in `.env`.
* **Wallet:** Fund the address from `npx awal address` with **USDC on the chain you run** (Sepolia test USDC for dev; **Base Mainnet** USDC for a real-money judge story). Enforce `MAX_DAILY_SPEND_USDC` / `MAX_PRICE_PER_SEARCH_USDC` in the app DB, not just in your head.

### Repository clones (sibling repos under `alphanet-402`)

```bash
git clone https://github.com/priyanshshahh/chf.git
git clone https://github.com/priyanshshahh/polymarket-sentiment-agent.git
```

Ship the unified app under **`alphanet-core/`**; use the clones for `@chf` / `@polymarket-sentiment-agent` context in Cursor.

### AWAL: wallet skills, auth, Sepolia vs Mainnet

1. **Skills registry (run in a terminal while Cursor scaffolds code):**  
   `npx skills add coinbase/agentic-wallet-skills`  
   Aligns local docs/skills with the same CLI entrypoints your Python `subprocess` calls.

2. **Login (use your own email — do not commit it to git):**  
   `npx awal@latest auth login <your-email>`  
   Complete the OTP / email verification flow your CLI prints. Then confirm:  
   `npx awal status`  
   You want the wallet server **running** and **authenticated** (not “Not authenticated”).

3. **Base Sepolia (safe integration):** Use the **Coinbase Base Sepolia faucet** and testnet USDC while wiring `x402 pay` and retries. Balance checks often use a `--chain` flag (see `npx awal balance --help` for your installed version).

4. **Base Mainnet (strong hackathon demo):** Real **USDC** on Base shows **economic** value to judges. Example: **$5 USDC** supports on the order of **five hundred** one-cent searches if each query is capped at **$0.01** and daily caps in `.env` are respected. **Canonical** CAIP-2 and invoice `network` for this repo remain **`eip155:8453`** (§1, §4); switch AWAL funding and chain flags when you move off Sepolia.

### Tavily 402 and B2B x402 (why this doc matters)

* **Tavily:** Endpoint, JSON payload, and **forbid `tavily-python`** — §5.  
* **Monetization:** Exact **402** JSON envelope for unpaid rationale — §4.  
* **Cursor / Copilot:** Use **Composer** to generate templates fast; use **Groq** (or Azure) only as the **NLP extractor** so token spend stays low while USDC spend goes to **Tavily x402** ingestion.

## 1. Network & Spend Limitations

* **Network:** Base Mainnet
* **CAIP-2 Identifier:** `eip155:8453`
* **Asset:** USDC
* **Budgeting:** The agent must enforce strict spend limitations to prevent infinite loops. The FastAPI application must track `DAILY_SPEND_USDC` and reject any further `x402 pay` commands if the spend exceeds the `.env` limit.

## 2. Coinbase Agentic Wallet (`awal`) CLI

The Agentic Wallet CLI provides AI agents with an isolated enclave to handle micro-transactions natively on Base [cite: 1.2.1].

**Core CLI Commands (Execute via Python `subprocess`):**

* `npx awal status` — Checks server health and auth status [cite: 1.2.4].
* `npx awal address` — Returns the wallet's EVM address [cite: 1.2.4].
* `npx awal balance` — Returns the USDC wallet balance [cite: 1.2.4].
* `npx awal x402 pay <url>` — The core command to make a paid API request to an x402-gated endpoint [cite: 1.2.4].

> **Implementation note:** `awal x402 pay` supports `-X <METHOD>`, `-d '<json body>'`, `--max-amount <atomic USDC units>`, and `--json`. Use these flags to POST the Tavily search payload and cap the per-request spend.

## 3. The x402 Payment Protocol (HTTP 402)

1. **Client Request:** The agent makes a standard request to a paid endpoint like `https://402.tavily.com/v1/search`.
2. **Server Response:** The server rejects it with an `HTTP 402 Payment Required` status containing the invoice [cite: 1.1.1].
3. **Payment & Retry:** The `npx awal x402 pay <url>` command signs the transaction and resends the request.
4. **Settlement:** The server returns an `HTTP 200 OK` with the data payload.

## 4. Serving our own x402 API (B2B Monetization)

When an external agent hits `GET /api/alpha/{ticker}/rationale` without an `X-Payment` header, our FastAPI server must return **HTTP 402** with a JSON body like:

```http
HTTP/1.1 402 Payment Required
Content-Type: application/json
```

```json
{
  "x402Version": 1,
  "accepts": [{
    "scheme": "exact",
    "network": "eip155:8453",
    "maxAmountRequired": "1000",
    "asset": "USDC",
    "payTo": "<OUR_AWAL_WALLET_ADDRESS>"
  }]
}
```

(Note: `maxAmountRequired: "1000"` represents 1000 micro-USDC, which equals $0.01.)

## 5. Tavily 402 Search Integration

* **Endpoint:** `https://402.tavily.com/v1/search` [cite: 1.1.1]
* **Payload:** `{"query": "institutional accumulation and whale wallet shifts for <TICKER>", "search_depth": "advanced"}`
* **Execution:** Use Python's `subprocess.run(['npx', 'awal', 'x402', 'pay', ...])` to execute the search and pay the 1 cent fee. Do **not** use `tavily-python`.

---

## 6. Configuration: `.env.example`

Before running the agent, define environmental boundaries. Generate `.env` from this structure (copy to `.env` and fill secrets):

```env
# Runtime Configuration (LIVE = Tavily 402 + AWAL; PAPER = local simulation only)
TRADING_MODE=LIVE
LOOP_INTERVAL_SECONDS=30

# Blockchain Networks (Base Mainnet)
NETWORK_CAIP_ID=eip155:8453
USDC_CONTRACT_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bda02913

# Strict Agent Spending Limits & Guardrails
MAX_DAILY_SPEND_USDC=2.00
MAX_PRICE_PER_SEARCH_USDC=0.01
EDGE_THRESHOLD=0.05
DAILY_DRAWDOWN_LIMIT_USDC=5.00

# API Gateways (x402 Keyless Infrastructure)
TAVILY_402_ENDPOINT=https://402.tavily.com/v1/search

# Our own x402 B2B monetization wallet (payTo in 402 invoices); optional if resolved from CLI
OUR_AWAL_WALLET_ADDRESS=

# Free inference routing (no credit card for Groq free tier)
GROQ_API_KEY=your_free_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Optional: Azure OpenAI (GitHub Student Pack / Azure for Students)
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT_NAME=

# Optional: monitoring (Sentry student plan)
SENTRY_DSN=
```

---

## 7. Master Cursor Prompt (fresh Agent session)

Open a fresh Agent session (Cmd/Ctrl + I), tag `@CURSOR_DOCS.md`, `@chf`, and `@polymarket-sentiment-agent`, then paste:

```text
# Role & Context
You are a Staff-Level Quant Engineer. We are sprinting at a hackathon to build "AlphaNet-402": an autonomous, self-funding crypto hedge fund that tracks institutional/whale sentiment.

We are merging two existing local repositories:
1. @chf (A deterministic quant pipeline with strict leakage guards).
2. @polymarket-sentiment-agent (A live Bayesian trading agent).

We are deploying on **Base Mainnet** using real USDC.

# Tech Stack & APIs
* Backend: FastAPI, SQLAlchemy, SQLite
* Frontend: React, Vite, TailwindCSS
* Data: Tavily 402 API (`https://402.tavily.com/v1/search`)
* Payments: Coinbase Agentic Wallet (AWAL via CLI `npx awal`)
* LLM: Groq / Llama-3 (Strictly for text extraction, NEVER for math/pricing)

# Execution Steps (Generate code sequentially)

## 1. Project Scaffolding & Config
* Create `/alphanet-core/backend/requirements.txt`.
* Create `/alphanet-core/backend/.env.example` utilizing the variables defined for MAX_DAILY_SPEND_USDC and MAX_PRICE_PER_SEARCH_USDC.
* Copy the FastAPI structure and `models.py` from @polymarket-sentiment-agent/backend. Modify the `AgentState` or `log_events` tables to track cumulative daily spend.

## 2. Scout Module (Tavily 402 + AWAL Integration)
* Create `/alphanet-core/backend/app/modules/ingestion.py`.
* Build a `Tavily402Scout` class.
* Implement a `BudgetManager` method that checks the SQLite database for total daily spend. If `current_spend + 0.01 > MAX_DAILY_SPEND_USDC`, it must throw a `SpendLimitExceeded` exception and halt the loop.
* If within budget, use Python's `subprocess` to trigger `npx awal x402 pay https://402.tavily.com/v1/search` per the architecture in @CURSOR_DOCS.md. Update the database spend tracker upon a successful 200 OK response.

## 3. Quant Engine (LLM Parsing + Pure Math + Leakage Guards)
* Create `/alphanet-core/backend/app/modules/quant_pipeline.py`.
* Pass the Tavily JSON to the LLM to strictly return structured JSON: `{sentiment: "bullish"|"bearish", confidence: float, whale_action: str}`.
* Implement the Bayesian log-odds formula from @polymarket-sentiment-agent (Prior = Current Market Price).
* Extract the forward-looking prevention logic from @chf/agents/FeatureAgent.py. Create a `verify_no_leakage()` method.

## 4. Risk Overseer & Execution
* Copy the risk kill-switches (drawdown limits, max position sizing) from @polymarket-sentiment-agent/backend/app/modules/risk.py.

## 5. Monetization: The x402 Server API
* In `/alphanet-core/backend/app/api/routes.py`, create the B2B endpoint: `GET /api/alpha/{ticker}/rationale`.
* Return `HTTP 402 Payment Required` with a $0.01 USDC invoice on Base Mainnet (`eip155:8453`) per the JSON envelope specified in @CURSOR_DOCS.md.
* If paid, return the full causal chain: Prior Market Price -> Tavily Whale Data -> Bayesian Edge.

## 6. Command Center (Frontend)
* Copy the React codebase from @polymarket-sentiment-agent/frontend to `/alphanet-core/frontend`.
* Update the UI to "AlphaNet-402 Command Center". Add widgets for "Daily Budget Remaining ($)" and "API Revenue Earned (x402)".

# Critical Directives
* Read @CURSOR_DOCS.md closely for exact network identifiers and JSON structures.
* Write robust Python. Use `try/except` blocks around the AWAL subprocess calls.
```

---

## 8. One-hour demo & LLM strategy

* **Workflow:** Use a high-throughput, low-latency LLM **only** to parse text features from Tavily search outputs (structured extraction), not for pricing or portfolio math.
* **Setup:** Use Cursor Composer to scaffold file templates quickly. For the live runtime loop, use a **free** Groq tier (Llama-3) or equivalent so internal reasoning stays cost-free while the agent spends budget on **data ingestion** (x402 / AWAL).

---

## 9. Infrastructure & live demo hosting (DigitalOcean + Microsoft Azure)

* **Problem:** A background async broker loop on a laptop fails if the machine sleeps or Wi-Fi drops during judging.
* **Solution:** Use **DigitalOcean** (e.g. student credit) to run a small **Ubuntu Droplet** with SQLite (`doa.db` or project DB) on the same host.
* **Azure:** Reserve **Azure** student credit for **App Service** containerized mirror deployments or **Azure DevOps** to verify builds in a clean environment.

---

## 10. Monitoring & failure tracking (Sentry + Datadog)

* **Problem:** Autonomous loops hit failed requests, wallet timeouts, and flaky 402 gates.
* **Solution:** Enable **Sentry** (e.g. student plan) and initialize the Sentry SDK in FastAPI (`app/main.py`). When `npx awal` subprocess output is malformed or an on-chain step stalls, Sentry surfaces the stack trace so you can hot-fix before demo time. Add **Datadog** (or similar) if you need metrics/dashboards beyond errors.
