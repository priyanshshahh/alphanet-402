# SignalRelay — 3-Minute Spoken Script

Read it as-is. Advance slides with → arrow keys. Total ~3:00. The **Demo** slide plays the
live x402 payment video automatically — just let it run while you narrate.

---

## SLIDE 1 — "Machines hiring machines for alpha"  ⏱ 0:00–0:25
> "Hi — this is **SignalRelay**. It's two AI agents doing business with each other on Base.
> One agent **earns** USDC by selling prediction-market intelligence. Another agent **spends**
> USDC to buy it. The payment happens over x402 — with **no human in the loop**. Let me show you why that matters."

*(→)*

## SLIDE 2 — "Autonomous agents can't pay for data"  ⏱ 0:25–0:50
> "Today, if an AI agent wants data, a human has to create an account, paste in an API key, and
> manage a monthly subscription. That completely breaks the moment the agent is actually autonomous.
> And trading agents specifically need one thing — **calibrated probability**, an edge — priced
> per signal, not per month."

*(→)*

## SLIDE 3 — "A 402-gated Bayesian sentiment oracle"  ⏱ 0:50–1:20
> "So we built the oracle. It scouts **live Polymarket markets** and crypto news. An LLM only
> extracts sentiment — the actual probability is a **Bayesian update in Python**. The output is the
> **edge**: the gap between the market's implied probability and our posterior. And that edge is
> paywalled with **x402** — one cent of USDC per signal."

*(→)*

## SLIDE 4 — "Privy + Base, used well"  ⏱ 1:20–1:45
> "Here's where **Privy and Base** come in. The buyer is a **Privy-authorized agent**. Its private
> key never leaves Privy's secure enclave — the agent only holds a session key, approved once by a
> human. After that it pays on its own, on **Base**, with hard spending limits and instant revocation."

*(→)*

## SLIDE 5 — DEMO VIDEO (plays automatically)  ⏱ 1:45–2:35
> "And this is it, live. The agent asks for a signal — and gets hit with a real **402 Payment
> Required**: one cent of USDC, on Base Sepolia.
>
> *(as the video runs)* Now watch — **Privy's enclave signs** the payment, the **facilitator settles
> it on Base** and even sponsors the gas, and the request retries automatically. **200 OK.** The market
> priced this Fed rate-cut at 62%; our model says 87% — a **25-point edge**.
>
> And see the wallet balance — it just dropped **exactly one cent**. That's a real on-chain payment,
> machine to machine, fully autonomous."

*(→)*

## SLIDE 6 — "Novelty · PMF · depth"  ⏱ 2:35–3:00
> "So that's the whole loop: **x402 moving USDC on Base**, a service that earns, an agent that
> spends — real **agent-to-agent commerce**, built on **Privy and Base**.
>
> The market is real — every autonomous trading agent needs this, and per-signal pricing beats
> subscriptions. We took a working Polymarket Bayesian engine and, today, made it an **economic
> agent** with Privy Agent Authorization and live x402 settlement. **SignalRelay — machines hiring
> machines for alpha.** Thank you."

---

### One-liners if you run out of time
- "An agent that earns, an agent that spends, settling USDC on Base over x402 — no humans."
- "Privy keeps the key in a TEE; Base + the facilitator make the cent-sized payment instant and gasless."

### If asked "is the payment real?"
- "Yes — verified on-chain. The wallet balance drops exactly $0.01 per call on Base Sepolia."
