# SignalRelay: Polymarket Sentiment Relay

**Agent-to-agent commerce on Base.** An autonomous Polymarket sentiment oracle that
**earns** USDC by selling its Bayesian alpha over x402, and a **Privy-authorized consumer
agent** that **spends** USDC to hire it — one human approval, then fully autonomous
micropayments with no API keys or subscriptions.

> Bounty fit: x402 moves USDC on Base (✅), a service that earns (✅ provider),
> an agent that spends (✅ consumer), agent-to-agent commerce (✅), **Privy + Base** (✅ required).

---

## The economic loop

```
Human ──one-time approve──▶ Consumer Agent (Privy embedded wallet)
                                  │  GET /api/trade/1/rationale
                                  ▼
                           Provider Agent (FastAPI + x402 ASGI middleware)
                                  │  402 Payment Required  ($0.01 USDC, Base Sepolia)
                                  ▼
                           Privy TEE signs ──▶ x402 Facilitator settles on Base
                                  │  X-PAYMENT receipt
                                  ▼
                           200 OK: { trade, signal, news, snapshot }  ← the "alpha"
```

- **Provider (earns):** monitors Polymarket markets + news, runs an LLM-as-NLP-parser →
  deterministic **Bayesian posterior** update in Python, computes the **edge**
  (posterior − market prior), and paywalls the full rationale behind x402.
- **Consumer (spends):** a downstream trading agent that pays per-signal using a
  **Privy Agent Authorization** session. The agent never holds the private key.

---

## Built today vs. pre-existing

| Component | Status |
| --- | --- |
| Polymarket scout, Bayesian quant, paper-trader (`polymarket-sentiment-agent`) | **Pre-existing** |
| `x402[evm]` ASGI middleware gating `GET /api/trade/{id}/rationale` (`x402_setup.py`) | **Pre-existing** |
| CHF leakage / quant-rigor methodology (`chf`) | **Pre-existing (referenced)** |
| **Privy Agent Authorization consumer** (`consumer/consumer-agent.ts`) | **Built today** |
| **Live x402 payment demo** (Base Sepolia, two-terminal) + this submission | **Built today** |

---

## Run the demo (two terminals)

### Terminal A — Provider Agent (earns)

```bash
cd polymarket-sentiment-agent/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Enable the paywall: set your Base Sepolia receive address
#   X402_PAY_TO=0xYourAddress
#   X402_NETWORK=eip155:84532
#   X402_FACILITATOR_URL=https://x402.org/facilitator
#   X402_PRICE=$0.01
uvicorn app.main:app --port 8000
```

Verify the 402 challenge (no payment):

```bash
curl -i http://localhost:8000/api/trade/1/rationale   # -> HTTP/1.1 402 Payment Required
```

### Terminal B — Consumer Agent (spends, Privy-authorized)

```bash
cd consumer
npm install
cp .env.example .env            # fill PRIVY_APP_ID / PRIVY_APP_SECRET
npm run login                   # privy-agent-wallets login -> approve once in browser
# copy the printed wallet id into PRIVY_AGENT_WALLET_ID in .env
npm run agent                   # GET 402 -> Privy signs -> Facilitator settles -> 200 OK
```

**Prereqs:** In the Privy Dashboard enable **CLI and agent access**
(Authentication → Advanced). Fund the embedded wallet with Base Sepolia USDC via the
[Circle faucet](https://faucet.circle.com/). The facilitator sponsors gas — the agent
only needs USDC.

---

## What judges should watch (60s)

1. **Terminal A** logs `402 Payment Required` for the unpaid request.
2. **Terminal B** logs the Privy wallet address + signature, then the settlement.
3. **Terminal A** validates the `X-PAYMENT` receipt and returns `200 OK`.
4. **Terminal B** prints the acquired Bayesian rationale JSON (sentiment, posterior, edge).

---

## Telegram submission text

```
SignalRelay — agent-to-agent prediction-market alpha on Base

Autonomous Polymarket sentiment oracle. Provider agent monitors Polymarket,
computes Bayesian sentiment edges, and sells rationales via x402 ($0.01 USDC on Base).
Consumer agents hire it using Privy Agent Authorization — one human approve,
then autonomous 402 payments with no API keys or subscriptions. Built on Privy + Base.

Pre-existing: polymarket-sentiment-agent (scout/quant/trader), CHF quant methodology
Built today: Privy Agent Authorization consumer + live x402 payment on Base Sepolia

Repo:  https://github.com/priyanshshahh/alphanet-402
Demo:  <loom/youtube link>
```

---

## Architecture notes

- **Provider** — FastAPI + `x402[evm]` `PaymentMiddlewareASGI`, `ExactEvmServerScheme`
  registered on `eip155:84532`. Bayesian update is pure Python (`backend/app/modules/intelligence.py`):
  LLM only extracts `{sentiment, confidence, topic}`; the posterior is a log-odds Bayes update.
- **Consumer** — `@privy-io/node` + `@privy-io/node/x402` `createX402Client` +
  `@x402/fetch` `wrapFetchWithPayment`. Privy holds key shards in a TEE; the agent signs
  authorizations with a local P-256 session key bound to a one-time human approval.
- **Security** — replay protection via facilitator nonces; spend caps + revocation via the
  Privy Agent Sandbox; `maxValue` guard on the consumer fetch wrapper.
