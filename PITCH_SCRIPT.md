# SignalRelay — 3-Minute Pitch Script

Flow: **App intro → 6 slides** (advance with →). The **Demo** slide auto-plays the full-app
video (Command Center → x402 Lab). Total ~3:00.

---

## 0 · APP INTRO (live app on screen, before the deck)  ⏱ 0:00–0:20
*Open the running app at `localhost:5173` — the SignalRelay Command Center.*
> "This is **SignalRelay**, running live. It's an autonomous agent that reads prediction markets,
> turns them into a trading edge — and then **sells that edge to other agents for USDC on Base.**
> A service that earns, and an agent that spends. Let me walk you through it."

*(switch to the deck → SLIDE 1)*

---

## 1 · "Machines hiring machines for alpha"  ⏱ 0:20–0:42
> "The big idea: two AI agents doing business. One **earns** USDC by selling market intelligence;
> one **spends** USDC to buy it. They settle over **x402, on Base** — with **no human in the loop.**
> This is what the machine economy actually looks like."

*(→)*

## 2 · "Autonomous agents can't pay for data"  ⏱ 0:42–1:05
> "Here's the problem. Every 'autonomous' agent today still has a human holding the credit card —
> API keys, subscriptions, someone clicking 'subscribe.' Take the human away and the agent goes
> blind. And trading agents are the hungriest of all: they live or die on **a probability edge.**"

*(→)*

## 3 · "A 402-gated Bayesian sentiment oracle"  ⏱ 1:05–1:30
> "So we built exactly what they'd pay for. SignalRelay watches **live Polymarket markets** and the
> news around them. An LLM reads the headlines — but it never guesses the odds. The probability is a
> **Bayesian update, in hard math.** The product is the **edge** — the gap between the truth and what
> the market believes — and we gate it with the protocol machines already speak: **x402.** One cent a signal."

*(→)*

## 4 · "The required pieces, used well"  ⏱ 1:30–1:55
> "Now the trust layer — **Privy and Base.** Would you hand an autonomous agent your private key?
> Neither would I. So the buyer runs on **Privy**: the key stays in a **secure enclave**, and the
> agent only holds a session token I approved once. It spends up to a limit, and I can revoke it
> instantly. **Privy holds the keys, Base moves the money.**"

*(→)*

## 5 · DEMO VIDEO — explanation (full-app clip auto-plays)  ⏱ 1:55–2:40
> "And here it is for real — no mockups.
>
> *(Command Center on screen)* First the oracle's brain: live Polymarket markets, Bayesian signals,
> and a real equity-curve track record.
>
> *(x402 Lab — payment runs)* Now the buyer requests a signal… and gets a real **402: Payment
> Required** — one cent, on Base Sepolia. Watch the steps light up: **Privy's enclave signs**, the
> **facilitator settles on Base**, gas sponsored, request retried — **200 OK.** The market priced
> this Fed market at 62%; our model says 87% — a **twenty-five-point edge.** And the wallet balance
> just dropped **exactly one cent.** Real, on-chain, agent to agent."

*(→)*

## 6 · "Novelty · PMF · depth"  ⏱ 2:40–3:00
> "So that's the loop: **x402 moving real USDC on Base** — a service that earns, an agent that
> spends, true **agent-to-agent commerce**, secured by **Privy.** It's not a toy — every autonomous
> trading agent needs calibrated probability, and they'll pay by the signal, not the month. We took a
> working quant engine and, today, turned it into an **economic agent.**
>
> **SignalRelay — machines hiring machines for alpha.** Thank you."

---

### Punchy one-liners (backup)
- "An agent that earns. An agent that spends. USDC on Base. Zero humans."
- "We didn't gate a demo — we gated a market. One cent at a time."

### If a judge asks "is the money real?"
- "100%. Base Sepolia — the balance drops exactly $0.01 per call. You can watch it live in the x402 Lab."

### "Built today vs. before?"
- "The Polymarket Bayesian engine existed. Today we added the Privy-authorized buyer and live x402 settlement — we turned a model into a business."
