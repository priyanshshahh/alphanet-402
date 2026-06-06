# AlphaNet-402 — judge demo guide & pitch script

**Pitch deck only:** see **[`PITCH_DECK_PRESENT.md`](./PITCH_DECK_PRESENT.md)** (slide order, LIVE vs Tavily key, embedded video).

**Total target time:** **3–5 minutes** (including the **~60–120s** embedded demo video on `/pitch-deck` — Judge demo **then** Command Center Overview — or a live click-through on `/demo`).

**Before you speak:** `./run_demo.sh` + `./run_frontend.sh` → open **http://localhost:5173/pitch-deck** (deck) or **http://localhost:5173/demo** (live console).

Default **`TRADING_MODE=LIVE`** (override in `.env` to `PAPER` for zero-wallet dry runs). With a **Tavily API key**, scout uses REST credits (not on-chain USDC for search).

---

## Part A — four demonstration beats (technical)

### 1) Opening statement — the “autonomous fund” narrative

**Say (≈45s):**

> “AlphaNet-402 is a **mini crypto hedge fund that runs itself economically**. It isn’t a chatbot with a portfolio — it’s a **machine-native fund**: it **pays** for intelligence when it needs it, **computes** its edge in code you can audit, **stops** when risk limits hit, and **sells** its research back to other agents for **micro-USDC** over **HTTP 402**. We built the vertical slice judges can actually run: **FastAPI**, **React**, **SQLite**, **Base**, and **Coinbase AWAL**.”

**Show:** Pitch deck slide 1 (title), then advance once.

---

### 2) “Real-time signal” — Scout hitting Tavily (logs)

**Say (≈40s):**

> “The **Scout** is the fund’s research desk. With a **Tavily API key**, it hits the real **Tavily REST** endpoint — you’ll see **`TAVILY` / `SPEND`** lines in the API logs and in the Command Center log stream. Without a key, the stack still runs end-to-end using the **offline** scout path so nothing breaks on stage; with keys, it’s **live intelligence**.”

**Do:**

1. Open **Overview** (`/`) or keep terminal on `uvicorn` stdout.  
2. Trigger a cycle: **Judge demo** → **Run pipeline** *or* `POST /api/cycle` / `POST /api/demo/judge-run`.  
3. Point at log lines mentioning **Tavily** / scout activity.

---

### 3) “Micropayment” — x402 flow

**Say (≈45s):**

> “This is where **agentic finance** shows up: our **alpha** is an **HTTP resource with a price tag**. Unpaid `GET` returns **402** with an **invoice** — `payTo`, **USDC** micro-amount on **Base**, **AWAL**-compatible. Paid retry with settlement proof returns the **full rationale** — structured evidence the buyer can machine-ingest. Receipts are **idempotent** so we don’t double-book revenue.”

**Do:**

1. Go to **x402 Lab** (`/x402-lab`).  
2. Request an **unpaid** rationale → show **402 JSON**.  
3. Retry with the **demo `X-Payment`** header (as wired in the lab) → show **paid JSON body** (evidence + quant fields).

---

### 4) Closing — future of agentic finance

**Say (≈35s):**

> “Capital allocation is moving from **humans clicking brokers** to **agents settling machine-to-machine**. AlphaNet-402 is the **shape of that stack**: **metered intelligence**, **deterministic risk**, **on-chain micro-settlement**, and **B2B APIs** that sell **truth bundles**, not vibes. Today it’s a hackathon slice; tomorrow it’s the **operating system for autonomous funds**.”

**Show:** Pitch deck final slide or **Command Center** signal row → signal detail.

---

## Part B — 3–5 minute pitch deck + video script (interesting, “mini fund” angle)

Use **`/pitch-deck`**. Advance with **Space** or **→**. Aim for **~45s per slide** + **~45–90s demo video** (Judge + Overview; longer if `RECORD_POST_CLICK_MS` is high for LIVE AWAL) ≈ **~4–5 min**.

| Slide | Your script (approx.) |
| --- | --- |
| **1 — Title** | “AlphaNet-402: a **self-funding crypto hedge fund in a box**. Not a dashboard pretending to be AI — an **economic agent** with a budget and a product.” |
| **2 — The loop** | “**Scout** buys the world’s noise as data — Tavily, optionally paid by **x402**. **Quant** turns stories into numbers — Groq structures text; **Python** owns the edge. **Risk** is the CIO that pulls the plug. **402** is how we wholesale alpha to **other bots**.” |
| **3 — Demo video** | “Here’s the fund **actually running** — one click fires the whole pipeline: scout → quant → risk → fresh signals.” *(Let `pitch-demo.webm` play, or narrate live on `/demo/embed`.)* |
| **4 — Stack & money** | “**FastAPI + SQLite** for honest persistence; **React** for humans; **Base + AWAL** for USDC; **402** so **machines** can check out like customers.” |
| **5 — Close** | “We’re not pitching magic returns — we’re pitching **infrastructure**: the first place **autonomy meets accounting**. Questions?” |

**If you run over 5 minutes:** drop slide 4 spoken detail and let chips/tags on screen carry; keep **demo video** and **x402 Lab** live proof.

---

## Quick reference URLs

| URL | Use |
| --- | --- |
| http://localhost:5173/pitch-deck | Timed story + embedded demo |
| http://localhost:5173/demo | Full judge script + pipeline button |
| http://localhost:5173/x402-lab | 402 unpaid vs paid rationale |
| http://localhost:8000/health | API + `tavily_mode` sanity check |

---

## Backup line (if something fails)

> “Judges: the **architecture and receipts** are the submission — live keys enhance the Tavily trail, but the **loop, risk gates, and 402 surface** run regardless.”
