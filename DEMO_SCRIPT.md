# SignalRelay — 3-Minute Pitch + Live Demo Script

**Verified working:** a Privy-authorized agent pays **$0.01 USDC on Base Sepolia** for a Bayesian
signal — real on-chain settlement (wallet debited exactly $0.01). Two surfaces to demo:
an **interactive multipage app** (`localhost:5173`) and a **one-command terminal demo** (`./run-demo.sh`).

---

## Setup (before you present)
- Provider running: `localhost:8000` · Frontend: `localhost:5173` · HTTPS tunnel up (`*.loca.lt`)
- Browser tabs open to: **Pitch Deck** (`/pitch`), **x402 Lab** (`/x402-lab`), **Command Center** (`/`)
- One terminal ready with: `PROVIDER_URL=https://<tunnel>.loca.lt ./run-demo.sh`

---

## [0:00–0:30] — The problem (Pitch Deck slide 1–2)
> "Autonomous trading agents need an edge — calibrated probabilities. Today they buy data with
> API keys, monthly subscriptions, and a human holding a credit card. That model breaks the
> moment the agent is actually autonomous.
>
> SignalRelay fixes it: a Polymarket sentiment oracle an agent can **discover, pay, and use on
> its own** — real USDC on Base, no human in the payment loop."

*Arrow-key through Pitch Deck slides 1→2.*

---

## [0:30–1:00] — The product (Command Center)
*Switch to `/` — the live dashboard.*
> "This is the oracle. It pulls **live Polymarket markets**, parses crypto news, and turns it into
> a **Bayesian edge** — the gap between the market's implied probability and our updated posterior.
> Here's its track record" — *point at the rising equity curve (+$6.47)* — "and every signal is
> backed by the news that moved it."

---

## [1:00–2:10] — The money shot (terminal: `./run-demo.sh`)
*Switch to the terminal, run it. Narrate the 4 acts as they print:*

1. **Wallet** → "This agent has a **Privy embedded wallet** — private key sealed in a TEE. I
   authorized it once in a browser; after that it's on its own. Here's its live USDC balance on Base."
2. **402** → "It asks for a signal with no payment — and gets slapped with **HTTP 402 Payment
   Required**: one cent of USDC, on Base, machine-readable. This is the x402 protocol."
3. **Pay + 200** → "Now it pays **itself** — Privy's TEE signs the USDC authorization, the
   facilitator settles on Base and sponsors the gas, the request retries. **200 OK.** The alpha:
   market priced this Fed market at 62%, our posterior says 87% — a **25-point edge**."
4. **Settled** → "And the balance just dropped **exactly one cent.** Real settlement, on-chain, no human."

---

## [2:10–2:40] — Prove it's real (x402 Lab)
*Switch to `/x402-lab`, click "▶ Run the x402 payment".*
> "Same loop, visualized: the **real** 402 challenge decoded — Base Sepolia, USDC, $0.01 — the Privy
> signing step, settlement, and the alpha delivered. That balance is read **straight from Base**."

---

## [2:40–3:00] — Why it wins
> "This is the bounty, exactly: **x402 moving USDC on Base**, a service that **earns**, an agent
> that **spends**, true **agent-to-agent commerce** — built on **Privy + Base**.
>
> PMF is real: every autonomous trading agent needs calibrated probability, and per-signal pricing
> beats subscriptions — no keys, no counterparty risk. Pre-existing: the Polymarket Bayesian engine.
> Built today: Privy Agent Authorization + the live x402 payment. **Machines hiring machines for alpha.**"

---

## Recording a 60–90s clip (if submitting video)
1. Pitch Deck slide 1 (3s) → Command Center equity curve (7s)
2. `./run-demo.sh` full run (40s) — this is the hero
3. x402 Lab "Run the payment" animation (20s)
Screen-record terminal + browser; no voiceover needed if you overlay the captions above.
