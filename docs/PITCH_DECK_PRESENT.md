# AlphaNet-402 — Pitch deck presenter guide

Use this with the fullscreen deck at **`/pitch-deck`** (e.g. `http://localhost:5173/pitch-deck` after `./run_demo.sh` + `./run_frontend.sh` or `npm run dev` in `alphanet-core/frontend`).

---

## Before you present (5 minutes)

1. **Backend + UI running** — API on **:8000** (or your port + `VITE_DEV_API_PROXY`), Vite on **:5173**.  
2. **`TRADING_MODE=LIVE`** — Default in repo is **LIVE** for hackathon demos that show real AWAL scout spend when Tavily is **not** using REST credits.  
3. **Tavily path (important)**  
   - If **`TAVILY_API_KEY`** is set → scout uses **REST (plan credits)** → **no USDC** leaves your wallet for search.  
   - To **force** Tavily **x402 + AWAL** (~micro USDC per search): **unset** or empty `TAVILY_API_KEY`, keep **`TRADING_MODE=LIVE`**, fund **Base Sepolia** test USDC on the wallet AWAL uses, run `npx awal auth verify`.  
4. **AWAL** — `OUR_AWAL_WALLET_ADDRESS` should match `npx awal address` for the session that runs `npx awal x402 pay`.  
5. **Optional video** — `alphanet-core/frontend/public/pitch-demo.webm` plays on the **Demo** slide. Regenerate (includes Judge demo + Overview):  
   `npm run record:demo` from repo root or `alphanet-core/frontend` (API + Vite must be up).

---

## Deck structure (~3–5 minutes)

| # | Slide | Your job (≈) | What to point at |
| --- | --- | --- | --- |
| 1 | **Title** | 45s — Hook: first autonomous, self-funding **mini crypto hedge fund**; scout → quant → risk → 402. | Title + subtitle. |
| 2 | **How the fund runs** | 60s — Walk the four bullets: paid intel, Python-only edge, kill-switches, sell rationale. | Scout / Quant / Risk / Monetize. |
| 3 | **Demo** | **60–120s** — Let **`pitch-demo.webm`** play, **or** live: open `/demo` in another tab, **Run pipeline**, then **Overview** for signals + `LIVE` pill + spend. | Embedded video or live UI. |
| 4 | **Stack & settlement** | 45s — FastAPI, React, SQLite, **Base Mainnet** story; **Sepolia** for this demo. | Chip row + Sepolia line. |
| 5 | **CTA** | 30s — Judge demo, x402 Lab, Command Center; Q&A. | Three buttons / links. |

**Keyboard:** Space / **→** next, **←** back, **Exit deck** returns to the shell.

---

## Slide 3 — Demo (video vs live)

### If using bundled **`pitch-demo.webm`**

The recorder script does this automatically:

1. **`/demo/embed`** — waits, clicks **Run pipeline**, waits for the cycle (longer wait when LIVE + AWAL).  
2. **`/` (Overview)** — Command Center: budget, `LIVE` / status pills, signals table, logs.

Narrate over the video: *“Here the agent just ran a full scout pass; on Overview you see state, spend cap progress, and fresh signals.”*

### If presenting live (no video file)

1. Open **`/demo`** → **Run pipeline** (or **`/demo/embed`** inside the deck iframe).  
2. Switch to **`/`** — scroll so **header** (`LIVE`, status) and **signal rows** are visible.  
3. Optionally expand a signal row / drawer.

---

## LIVE + money (talk track)

- **“Why is my AWAL balance unchanged?”** — If **`TAVILY_API_KEY`** is set, search does **not** use USDC. If **`TRADING_MODE=PAPER`**, there is no AWAL pay for Tavily.  
- **x402 Lab “paid” demo** — Uses a **demo `X-Payment`** header; it **does not** pull real USDC from your wallet; it proves the **402 + JSON body** shape.  
- **Real scout spend** — `LIVE` + **no** Tavily REST key → `npx awal x402 pay` for Tavily; small USDC movement on **Base Sepolia**.

---

## Backup lines

- *“Vertical slice: autonomous loop, risk caps, and machine-payable rationale—not a live hedge fund AUM.”*  
- *“With a Tavily dev key we burn credits, not gas, for the scout—that’s intentional for stable demos.”*

---

## Related docs

| File | Use |
| --- | --- |
| **`docs/DEMO_GUIDE.md`** | Full judge walk + micropayment beat + closing |
| **`docs/ARCHITECTURE.md`** | Scout / Quant / Risk diagram |
| **`README.md` (repo root)** | `./run_demo.sh`, `./run_frontend.sh`, optional `npm run record:demo` |
