# SignalRelay

**Agent-to-agent prediction-market alpha, paid over x402 on Base.**

> ✅ **Live & verified:** a Privy-authorized agent pays **$0.01 USDC on Base Sepolia** per call.
> On-chain settlement confirmed (wallet debited exactly $0.01). One-command demo: `./run-demo.sh`.

SignalRelay is an autonomous **Polymarket sentiment oracle** that *earns* USDC by selling
its Bayesian trading edge, and a **Privy-authorized consumer agent** that *spends* USDC to
hire it — one human approval, then fully autonomous micropayments. No API keys, no
subscriptions. Just machines paying machines over HTTP.

> Built with **Privy** (Agent Authorization + embedded wallet) and **Base** (USDC on Base Sepolia via x402).

---

## The economic loop

```
Human ──one-time approve──▶ Consumer Agent (Privy embedded wallet, key in TEE)
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

- **Provider (earns):** watches Polymarket markets + crypto news, uses an LLM purely as an
  NLP parser, then computes a **deterministic Bayesian posterior** in Python and the
  **edge** = posterior − market-implied prior. The full rationale is paywalled with x402.
- **Consumer (spends):** a downstream trading agent that pays per-signal using a
  **Privy Agent Authorization** session. The agent never holds the private key.

---

## Built today vs. pre-existing

| Component | Status |
| --- | --- |
| Polymarket scout, Bayesian quant, paper-trader | **Pre-existing** (`polymarket-sentiment-agent`) |
| `x402[evm]` ASGI middleware gating `GET /api/trade/{id}/rationale` | **Pre-existing** (`x402_setup.py`) |
| Quant-rigor / leakage methodology | **Pre-existing (referenced)** (`chf`) |
| **Privy Agent Authorization consumer + live x402 payment on Base** | **Built today** |
| **SignalRelay rebrand, demo, submission** | **Built today** |

---

## Run the demo (two terminals)

### Terminal A — Provider (earns)
```bash
cd polymarket-sentiment-agent/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
echo "X402_PAY_TO=0xYourBaseSepoliaAddress" >> .env   # enables the paywall
uvicorn app.main:app --port 8000
# verify: curl -i http://localhost:8000/api/trade/1/rationale  -> 402 Payment Required
```

### One-command demo (after the provider + tunnel are up)
```bash
PROVIDER_URL=https://<your-tunnel>.loca.lt ./run-demo.sh
# [1] shows live USDC balance  [2] 402 challenge  [3] Privy pays + 200 OK alpha  [4] balance debited $0.01
```

### Terminal B — Consumer (spends, Privy-authorized)
```bash
# one-time: enable "CLI and agent access" in the Privy Dashboard
npx @privy-io/agent-wallet-cli login          # approve once in the browser
npx @privy-io/agent-wallet-cli list-wallets   # note the ethereum wallet + address
# fund that address with Base Sepolia USDC at https://faucet.circle.com

# x402 client only accepts HTTPS, so expose the provider:
npx localtunnel --port 8000                    # -> https://<name>.loca.lt

npx @privy-io/agent-wallet-cli fetch-x402 \
  --header "bypass-tunnel-reminder: 1" \
  https://<name>.loca.lt/api/trade/1/rationale
# -> 402 -> Privy TEE signs -> facilitator settles on Base -> 200 OK + rationale JSON
```

A Node version of the consumer (`@privy-io/node` + `@x402/fetch`) lives in
[`consumer/consumer-agent.ts`](consumer/consumer-agent.ts).

---

## Why it matters
Downstream trading agents need probabilistic edge, not subscriptions. SignalRelay proves
**usage-based, per-signal machine commerce**: any agent on Polymarket/Kalshi can discover
the endpoint, pay $0.01 in USDC on Base, and get a calibrated Bayesian signal — settled in
seconds, gas sponsored by the facilitator, key never exposed.

See [`SUBMISSION.md`](SUBMISSION.md) for the Telegram text and [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md)
for the 3-minute presentation.
