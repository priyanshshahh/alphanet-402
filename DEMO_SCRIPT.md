# SignalRelay — 3-Minute Demo Script

> Goal: show **an agent paying another agent** in USDC on **Base** via **x402**, authorized by **Privy**.

---

## [0:00–0:25] The hook
"Trading agents need an edge. Today they buy data with API keys, subscriptions, and a human
with a credit card. That breaks the moment the agent is autonomous.

**SignalRelay** is a Polymarket sentiment oracle that an agent can *discover, pay, and use*
on its own — settling real USDC on Base, with no human in the payment loop."

---

## [0:25–0:50] The architecture (one slide)
"Two agents. The **Provider** watches Polymarket and crypto news, and turns it into a
**Bayesian edge** — the gap between the market's implied probability and our updated
posterior. It sells that signal behind an **x402 paywall**: $0.01 USDC on Base.

The **Consumer** is a downstream trading agent. It holds a **Privy embedded wallet** — the
private key lives in a Privy TEE, never on the agent. A human approved it once; after that
it pays autonomously."

---

## [0:50–2:20] LIVE DEMO (terminals)
**Terminal A — Provider:**
"Here's the oracle running. It's pulling live Polymarket markets right now."
- Run: `curl -i http://localhost:8000/api/trade/1/rationale`
- Point at the response: **`HTTP/1.1 402 Payment Required`** + the x402 terms
  (network `eip155:84532` = Base Sepolia, asset USDC, amount `$0.01`, payTo).
"No payment, no data. That's the x402 challenge."

**Terminal B — Consumer (Privy):**
"This agent was authorized once via the Privy CLI — here's its wallet."
- Run: `npx @privy-io/agent-wallet-cli list-wallets`  → show the ETH address.
"Now it pays for the signal — it sees the 402, Privy's TEE signs a USDC authorization on
Base, the facilitator settles and sponsors gas, and the request auto-retries."
- Run:
  ```
  npx @privy-io/agent-wallet-cli fetch-x402 \
    --header "bypass-tunnel-reminder: 1" \
    https://<your-tunnel>.loca.lt/api/trade/1/rationale
  ```
- Show the **200 OK JSON**: the trade, the signal (sentiment, posterior, edge), the news
  that drove it, and the market snapshot.
"That's a completed agent-to-agent payment. USDC moved on Base. No human touched it."

---

## [2:20–2:50] Why it wins
"This hits the bounty dead-on: **x402 moving USDC on Base**, a **service that earns**, an
**agent that spends**, and **agent-to-agent commerce** — all on **Privy + Base**.

The PMF is real: every autonomous trading agent needs calibrated probability. Per-signal
pricing beats subscriptions — no counterparty risk, no integration friction, no keys to leak."

---

## [2:50–3:00] Close
"Pre-existing: the Polymarket Bayesian engine. Built today: the Privy Agent Authorization
consumer and the live x402 payment on Base. SignalRelay — machines hiring machines for alpha."

---

### Fallback if the on-chain settlement is slow
Show: (1) provider logs printing `402 Payment Required`, (2) `Logged in successfully` +
authorized Privy wallet addresses, (3) the decoded x402 Base Sepolia payment terms. That
alone demonstrates Privy + Base + x402 end to end.
