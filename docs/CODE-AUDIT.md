# AlphaNet-402 — code audit

Honest, ranked audit of what's weak, dead, duplicated, or over-engineered.
Ranked by **value-to-fix** (impact × cheapness), highest first.

> **Resolution status (campaign 3).** Most findings below have since been
> addressed. Fixed: #1 (revenue honesty — verified/unverified now labeled in
> the UI **and** verified on-chain), #2 (the revenue path has tests —
> `test_settlement.py`), #3 (LIVE Node dependency now documented in
> README/PROJECT-NOTES), #4 (`run_cycle` off-loaded via `asyncio.to_thread` /
> `run_in_threadpool`), #5 (blend weight is now `BAYES_TABLE_WEIGHT` with tests
> and a corrected docstring), #6 (rationale flow deduped), #7 (`routes.py`
> split into dashboard/admin/x402 routers), #8 (the three silent excepts now
> log), #9 (timeouts consolidated to config constants), #10 (frontend
> stale/error indicator + dead-link removal; a frontend test suite is still
> absent). The text below is preserved as the original problem statement.

---

## 1. Revenue counter's unverified nature is documented in prose, not labeled where it's displayed — HIGH value, LOW cost

**What:** `daily_revenue_usdc` accrues whenever `POST` (well, `GET`)
`/api/alpha/{ticker}/rationale` or `/api/trade/{signal_id}/rationale`
receives an `X-Payment` header that does not start with `demo-`
(`api/routes.py::_settle_rationale_sale`, `_is_demo_proof`). There is no
facilitator call, no signature check, no on-chain lookup — any non-empty,
non-`demo-` string settles a sale. This is honestly called out in
`docs/PROJECT-NOTES.md` ("Known limitations #1") and in the README's
"Honest status" section.

**The gap:** none of the three UI surfaces that *render* this number carry
an inline caveat:
- `Dashboard.jsx` "x402 revenue" panel (line ~126) shows
  `fmtUsd(state.daily_revenue_usdc)` with sub-label `"Idempotent receipts ·
  $0.01 / rationale"` — no mention that the underlying receipts are
  unverified.
- `SignalDetail.jsx` "Monetize (x402)" panel and `SignalDrawer.jsx`'s
  matching section both quote the $0.01 price with no caveat.
- `X402Lab.jsx` is the one place that's honest by construction — its
  "simulate paid" buttons only ever send `demo-` prefixed headers and the
  raw JSON response it prints includes `demo_payment` / `settled_usdc`, so a
  user poking at that page can see the flag. But a user only looking at the
  Dashboard's headline revenue number gets no signal that it's a
  self-reported, unauthenticated counter.

**Fix shape (not applied):** a one-line badge/tooltip on the "x402 revenue"
stat ("unverified — no facilitator check yet") would close this for free;
it's a documentation-to-UI gap, not a code gap.

---

## 2. The riskiest code path has zero test coverage — HIGH value, LOW cost

**What:** every test that exercises `/api/alpha/*rationale` or
`/api/trade/*rationale` with a payment header uses the literal string
`"demo-proof-123"` (`tests/test_demo_and_config.py::test_demo_payment_header_books_no_revenue`).
Grep confirms it's the *only* `X-Payment` value used anywhere in the suite.
There is no test that sends an arbitrary non-`demo-` string and asserts that
revenue is booked, that the receipt is idempotent on retry, or that two
different bogus strings for the same signal both settle independently. The
actual "real" settlement branch — the one with the honesty gap in finding
#1 — is the one branch nobody tests.

---

## 3. `TRADING_MODE=LIVE` payments depend on an undeclared runtime dependency (`npx`/Node) that Render deploy doesn't provision — MEDIUM-HIGH value, LOW cost to document, MEDIUM cost to fix

**What:** both the outbound buy path (`ingestion.py::_live_pay`, calls `npx
awal x402 pay ...`) and the payTo resolution fallback
(`routes.py::resolve_pay_to`, calls `npx awal address --json`) shell out via
`subprocess.run(["npx", "awal", ...])`. `render.yaml` declares
`runtime: python` with `buildCommand: pip install -r requirements.txt` —
there is no Node/npm installation step. On the documented free-tier Render
deploy, any attempt to actually go `LIVE` (either for Tavily x402 buys or to
resolve a wallet address via the CLI instead of the env var) will hit
`FileNotFoundError` and silently degrade (`paid=False` / `PaymentConfigError`
if `OUR_AWAL_WALLET_ADDRESS` also isn't set). This isn't wrong given the
project is "testnet + paper trading" by design, but it means the `LIVE`
code path is essentially unreachable on the one deploy target the repo
documents, and that's not called out anywhere.

---

## 4. `run_cycle()` is synchronous and blocks the single asyncio event loop — MEDIUM value, MEDIUM cost

**What:** `agent_loop._loop()` calls `run_cycle()` directly inside an `async
def` coroutine with no `run_in_executor`/`asyncio.to_thread`. `run_cycle()`
does blocking network I/O (yfinance via `t.history(...)`, Tavily REST via
`httpx.Client` in blocking mode with a **60s timeout**, and potentially a
120s-timeout `awal` subprocess call) for every ticker in the watchlist,
serially. Because FastAPI/uvicorn runs on the same event loop, a slow scout
cycle blocks every other concurrent request — `/health`, `/api/state`, the
Command Center's 4-second polling — for the duration. `POST /api/cycle`
(now admin-gated) calls the same synchronous function directly from an
async route handler, compounding the same issue on demand. With
`LOOP_INTERVAL_SECONDS=30` default and a single REST call alone allowed to
take up to 60s, a slow Tavily response can make one cycle overlap the next
cycle's scheduled start.

---

## 5. Two Bayesian update paths are blended with a hardcoded, untested ratio — MEDIUM value, MEDIUM cost

**What:** `quant_pipeline.run_quant()` computes `posterior_tbl` from the
documented, tested log-odds evidence table
(`calculate_chf_leakage_safe_edge`), then *also* computes `posterior_sent`
from `bayesian_update()` — whose docstring says "Legacy sentiment-only
log-odds bump (**used as fallback tie-break**)" — and blends them
unconditionally: `posterior = 0.65 * posterior_tbl + 0.35 * posterior_sent`.
That is not a "fallback tie-break"; it's a permanent 35% weight on a second,
simpler model in every single decision. Neither the 0.65/0.35 split nor the
blended output is asserted by any test (`test_quant_math.py` tests each
function independently — `bayesian_update`, `calculate_chf_leakage_safe_edge`
— but never the blend in `run_quant` beyond "prior passthrough" and "HOLD
when no edge", both of which happen to be blend-invariant). The docstring
and the code disagree about what this function is for.

---

## 6. Duplicated invoice/settlement logic between the two rationale endpoints — MEDIUM value, LOW cost

**What:** `alpha_rationale()` and `trade_rationale_by_id()` in
`api/routes.py` (lines ~481-547) are near-identical: same
"no X-Payment → build invoice or 503" branch, same DB session
open/lookup/close, same `_settle_rationale_sale` call — differing only in
whether the signal is looked up by ticker (latest) or by id. This is ~35
lines of copy-pasted control flow that could be one helper parameterized on
signal lookup.

---

## 7. `routes.py` is a 547-line god-module mixing four concerns — MEDIUM value, MEDIUM cost

**What:** one file holds the dashboard API, the admin control endpoints, the
judge-demo narrative endpoints (`JUDGE_BRIEFING` static dict + `/api/demo/*`),
and the B2B x402 seller. No `APIRouter(prefix=..., tags=...)` grouping, no
sub-module split. Fine at current size, but the judge-demo material in
particular (a hardcoded talking-points dict for hackathon judges) is
product-marketing content living in the same file as payment-settlement
logic — worth splitting before it grows further.

---

## 8. Broad `except Exception` swallows real failures without always logging them — MEDIUM value, LOW cost

Instances, roughly in order of how much they matter:

- `quant_pipeline._groq_extract`: any Groq SDK error (auth, rate limit,
  malformed JSON, network) is caught and silently returns `None`, falling
  through to the heuristic parser. Reasonable as a fallback strategy, but
  nothing is logged — an operator with a paid Groq key that's silently
  failing (e.g. wrong model name, expired key) would never see it in
  `/api/logs`; they'd just always get heuristic output and might not notice.
- `market_data.fetch_equity_events`: the fundamentals `t.info` fetch is
  wrapped in a bare `try/except Exception: fundamentals = {}` with a comment
  saying "best-effort" — also not logged.
- `database.init_db`: the lightweight SQLite column-migration helper
  (`_sqlite_add_column_if_missing` × 3) is wrapped in one outer
  `try/except Exception: pass`. Given SQLite state is documented as
  ephemeral on the deploy target this is low-stakes, but on a developer's
  persisted local `alphanet.db` a genuine migration failure (e.g. a locked
  file) would be invisible.
- `ingestion._live_pay`: catches `TimeoutExpired`, `FileNotFoundError`,
  `OSError` specifically (good — narrower than bare `Exception`) and does
  log via `_log_error`. This one's fine; contrast with the two above.

---

## 9. Timeout inconsistency across the scout's three network paths — LOW-MEDIUM value, LOW cost

- yfinance (`market_data.fetch_equity_events`): **no explicit timeout** —
  relies on whatever `yfinance`/`requests` defaults to internally. Combined
  with finding #4 (blocking the event loop), a hung Yahoo endpoint has no
  hard ceiling.
- Tavily REST (`ingestion._rest_search`): `httpx.Client(timeout=60.0)` — 60s,
  longer than the default 30s loop interval.
- `awal` subprocess pay (`ingestion._live_pay`): 120s.
- `awal` subprocess address resolution (`routes.resolve_pay_to`): 20s.

No single source of truth for "how long is this scout allowed to take";
four different implicit/explicit budgets across one cycle.

---

## 10. Frontend: no test suite, and errors are swallowed into permanent silence — LOW-MEDIUM value, MEDIUM cost

**What:** there are zero `*.test.*`/`*.spec.*` files anywhere under
`alphanet-core/frontend/src`. Separately, `Dashboard.jsx`'s `refresh()`
wraps all three parallel fetches in a `try { ... } catch { /* backend
warming */ }` — any error after the first successful load (network blip,
CORS misconfig, backend restart mid-poll) is silently discarded every 4
seconds forever, with no user-visible indicator that data has gone stale
beyond the numbers simply not updating. There's no "last updated" timestamp
or error banner to distinguish "healthy, no new signals" from "polling has
been silently failing for 10 minutes."

---

## Smaller / lower-priority items (documented, not fixed)

- **Dead doc links in the UI.** `pages/PitchDeck.jsx` links to
  `docs/DEMO_GUIDE.md` and `docs/PITCH_DECK_PRESENT.md`;
  `pages/WalletSetup.jsx` links to `docs/cdp-llms.txt`. None of the three
  exist in `docs/` — leftovers from before the `diverge-equities` split
  (see `docs/PROJECT-NOTES.md` provenance note). Low severity (they're
  reference links on secondary pages, not load-bearing), trivial to fix by
  either writing them or removing the links.
- **Module-level mutable loop state.** `agent_loop._task` / `_running` are
  plain module globals guarding a singleton background task. Fine for a
  single-process demo; would need rework (e.g. an app-state object) if this
  were ever run with multiple workers, since each worker would start its
  own independent loop against the same SQLite file.
- **Hardcoded price duplicated across services.** `ALPHA_PRICE_ATOMIC =
  "1000"` / `ALPHA_PRICE_USDC = 0.01` live in `routes.py`; the consumer
  agent (`consumer/consumer-agent.ts`) independently hardcodes a `$1.00`
  `maxValue` cap as a different, unrelated safety ceiling. Not a bug (they
  serve different purposes — one is the seller's price, the other is the
  buyer's spending cap) but worth knowing there's no shared constant if the
  price ever changes.
- **`Settings` is exercised two different ways in tests.** Most tests
  `monkeypatch.setattr(settings, ...)` on the cached singleton; one test
  (`test_cors_env_origins_honored`) instead constructs a fresh
  `Settings(_env_file=None)`. Both work, but it's an inconsistency a new
  contributor could trip on when adding config tests.
- **`_ZERO_ADDRESS` check is case-sensitive-safe but string-only.** The
  zero-address rejection in `resolve_pay_to()` does `.lower() != _ZERO_ADDRESS`
  — correct — but there's no checksum/format validation on
  `OUR_AWAL_WALLET_ADDRESS` beyond "non-empty and not the zero address," so
  a typo'd address (wrong length, missing `0x`) would be accepted and only
  fail later at actual settlement time.

---

## What's *not* a problem (called out so it isn't re-flagged later)

- The Bayesian math, leakage guard, budget caps, and demo-mode labeling are
  well-tested (`test_quant_math.py`, `test_ingestion.py`,
  `test_market_data.py`) and behave exactly as documented.
  `verify_no_leakage`'s three checks (look-ahead prior, empty evidence,
  future-year text) are simple, readable, and covered.
  `calculate_chf_leakage_safe_edge`'s fixed log-odds table is small,
  explicit, and each weight has a dedicated test.
- The zero-address / unconfigured-wallet fail-hard behavior
  (`resolve_pay_to`, `_payments_unavailable`) is genuinely fail-safe: no
  silent zero-address fallback exists anywhere in the seller path, and it's
  tested from both the unit level and the HTTP level (503 vs 402).
  Admin-token gating on `/api/reset` / `/api/cycle` (added 2026-07-16) is
  similarly fail-closed (empty token ⇒ 503, not open) and has full
  positive/negative test coverage including constant-time comparison.
  CORS is a real explicit allowlist with wildcard entries stripped even if
  someone tries to configure one via env — also tested.
