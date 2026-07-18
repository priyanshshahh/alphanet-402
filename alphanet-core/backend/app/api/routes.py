"""HTTP API.

Two surfaces:
  * Dashboard API (consumed by the React Command Center).
  * B2B x402 monetization endpoint that sells our alpha rationale for $0.01.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Header
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import agent_loop
from app.core.config import settings
from app.database import SessionLocal
from app.models import AgentState, LogEvent, Signal, X402Receipt, today_key
from app.modules.settlement import SettlementVerdict, verify_settlement

router = APIRouter()

# Price of our own alpha endpoint: 1000 micro-USDC = $0.01
ALPHA_PRICE_ATOMIC = "1000"
ALPHA_PRICE_USDC = 0.01

_ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class PaymentConfigError(RuntimeError):
    """Raised when x402 selling is attempted without a configured payTo wallet."""


@lru_cache
def resolve_pay_to() -> str:
    """payTo address for our 402 invoices. Prefer the configured address,
    else ask the wallet enclave via `npx awal address`. Fails hard rather
    than ever falling back to the zero address."""
    configured = (settings.OUR_AWAL_WALLET_ADDRESS or "").strip()
    if configured and configured.lower() != _ZERO_ADDRESS:
        return configured
    try:
        proc = subprocess.run(
            ["npx", "awal", "address", "--json"],
            capture_output=True,
            text=True,
            timeout=settings.AWAL_ADDRESS_TIMEOUT_SECONDS,
        )
        if proc.returncode == 0:
            data = json.loads(proc.stdout.strip() or "{}")
            addr = data.get("evm") or data.get("address") or data.get("evmAddress")
            if addr and str(addr).lower() != _ZERO_ADDRESS:
                return str(addr)
    except Exception:
        pass
    raise PaymentConfigError(
        "No payTo wallet configured: set OUR_AWAL_WALLET_ADDRESS (or log in "
        "with `npx awal auth login`) before selling rationale over x402."
    )


def _admin_auth_error(authorization: Optional[str]) -> Optional[JSONResponse]:
    """Guard for the control endpoints (/api/reset, /api/cycle).

    No ADMIN_TOKEN configured -> endpoint is disabled (503), never open.
    Otherwise require `Authorization: Bearer <token>`, compared in constant
    time, and reject with 401 on anything missing or wrong.
    """
    token = (settings.ADMIN_TOKEN or "").strip()
    if not token:
        return JSONResponse(
            status_code=503,
            content={
                "error": (
                    "Control endpoint disabled: set ADMIN_TOKEN in the "
                    "environment to enable it."
                )
            },
        )

    provided = ""
    if authorization and authorization.strip().lower().startswith("bearer "):
        provided = authorization.strip()[len("bearer "):].strip()

    if not provided or not secrets.compare_digest(provided, token):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized: missing or invalid bearer token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return None


def _payments_unavailable() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": (
                "x402 selling disabled: no payTo wallet configured. "
                "Set OUR_AWAL_WALLET_ADDRESS in the environment."
            )
        },
    )


# ---------------------------------------------------------------------------
# Dashboard API
# ---------------------------------------------------------------------------
def _agent_state_payload(db: Session) -> dict:
    state = db.get(AgentState, 1)
    if state is None:
        state = AgentState(id=1, trading_mode=settings.TRADING_MODE)
        db.add(state)
        db.commit()
    if state.day_key != today_key():
        state.day_key = today_key()
        state.daily_spend_usdc = 0.0
        state.daily_revenue_usdc = 0.0
        state.daily_unverified_usdc = 0.0
        state.daily_drawdown_usdc = 0.0
        db.commit()
    remaining = max(0.0, settings.MAX_DAILY_SPEND_USDC - state.daily_spend_usdc)
    try:
        pay_to = state.wallet_address or resolve_pay_to()
    except PaymentConfigError:
        pay_to = ""
    return {
        "status": state.status,
        "trading_mode": state.trading_mode,
        "halted": state.halted,
        "halt_reason": state.halt_reason,
        "network": settings.NETWORK_CAIP_ID,
        "wallet_address": pay_to,
        "daily_spend_usdc": round(state.daily_spend_usdc, 4),
        "daily_budget_usdc": settings.MAX_DAILY_SPEND_USDC,
        "daily_budget_remaining_usdc": round(remaining, 4),
        "daily_revenue_usdc": round(state.daily_revenue_usdc, 4),
        "daily_unverified_usdc": round(state.daily_unverified_usdc or 0.0, 4),
        "realized_pnl_usdc": round(state.realized_pnl_usdc, 4),
        "daily_drawdown_usdc": round(state.daily_drawdown_usdc, 4),
        "drawdown_limit_usdc": settings.DAILY_DRAWDOWN_LIMIT_USDC,
        "data_mode": settings.data_mode,
        "demo_mode": settings.DEMO_MODE,
    }


@router.get("/api/state")
def get_state():
    db = SessionLocal()
    try:
        return _agent_state_payload(db)
    finally:
        db.close()


def _receipt_key(x_payment: str, signal_id: int) -> str:
    raw = f"{x_payment}|{signal_id}".encode()
    return hashlib.sha256(raw).hexdigest()


def _is_demo_proof(x_payment: str) -> bool:
    return (x_payment or "").strip().lower().startswith("demo-")


def _payment_status(x_payment: str, verdict: Optional[SettlementVerdict]) -> str:
    if _is_demo_proof(x_payment):
        return "demo"
    return verdict.status if verdict else "unverified"


def _causal_payload(
    sig: Signal, x_payment: str, verdict: Optional[SettlementVerdict]
) -> dict:
    nlp = {}
    ev = {}
    try:
        nlp = json.loads(sig.nlp_features_json or "{}")
    except json.JSONDecodeError:
        pass
    try:
        ev = json.loads(sig.evidence_json or "{}")
    except json.JSONDecodeError:
        pass
    status = _payment_status(x_payment, verdict)
    # Provenance: the specific sources that fed THIS report, surfaced only in
    # the paid payload. Each is a checkable title/link (yfinance event or
    # Tavily result) so a buyer can audit the analysis, not just trust a number.
    sources = [
        {"title": u.get("title"), "url": u.get("url"), "score": u.get("score")}
        for u in (ev.get("urls") or [])
        if isinstance(u, dict) and u.get("url")
    ]
    return {
        "ticker": sig.ticker,
        "signal_id": sig.id,
        # settled_usdc is booked as revenue ONLY for a verified on-chain
        # settlement. Demo and unverified payments are served but count $0.
        "settled_usdc": ALPHA_PRICE_USDC if status == "verified" else 0.0,
        "payment_status": status,  # demo | verified | unverified
        "demo_payment": status == "demo",
        "settlement_tx": verdict.tx_hash if verdict else "",
        "settlement_note": verdict.reason if verdict else "",
        "network": settings.NETWORK_CAIP_ID,
        "payment_proof_prefix": (x_payment or "")[:64],
        "causal_chain": {
            "1_prior_market_price": sig.prior_price,
            "2_tavily_evidence": ev,
            "3_nlp_features": nlp,
            "4_whale_action": sig.whale_action,
            "5_bayesian_posterior": sig.posterior,
            "6_edge": sig.edge,
            "7_decision": sig.decision,
        },
        "source_snippet": sig.source_snippet or "",
        "sources": sources,
        "leakage_verified": sig.leakage_ok,
        "computed_at": sig.ts.isoformat() if sig.ts else None,
    }


def _verify_payment(x_payment: str) -> SettlementVerdict:
    """On-chain settlement check for a non-demo x402 proof."""
    try:
        pay_to = resolve_pay_to()
    except PaymentConfigError:
        pay_to = ""
    return verify_settlement(
        x_payment=x_payment,
        pay_to=pay_to,
        usdc_contract=settings.USDC_CONTRACT_ADDRESS,
        min_atomic=int(ALPHA_PRICE_ATOMIC),
        rpc_url=settings.SETTLEMENT_RPC_URL,
    )


def _settle_rationale_sale(
    db, sig: Signal, ticker: str, x_payment: str
) -> dict:
    """Serve the causal chain; book revenue only for a *verified* settlement.

    Idempotent per (payment proof, signal) pair. Three outcomes:
      * demo      — x402 Lab header, served, never booked.
      * verified  — settlement confirmed on-chain, +$0.01 revenue.
      * unverified — served, recorded separately, excluded from revenue.
    """
    key = _receipt_key(x_payment, sig.id)
    existing = db.query(X402Receipt).filter(X402Receipt.receipt_key == key).first()
    if existing:
        try:
            return json.loads(existing.payload_json or "{}")
        except json.JSONDecodeError:
            pass

    demo = _is_demo_proof(x_payment)
    verdict = None if demo else _verify_payment(x_payment)
    body = _causal_payload(sig, x_payment, verdict)

    state = db.get(AgentState, 1)
    if state is not None and state.day_key != today_key():
        state.day_key = today_key()
        state.daily_revenue_usdc = 0.0
        state.daily_unverified_usdc = 0.0

    if demo:
        db.add(
            LogEvent(
                level="INFO",
                category="X402",
                ticker=ticker,
                message=(
                    f"Served rationale for signal #{sig.id} ({ticker}) against a "
                    "demo X-Payment header — no settlement, no revenue booked"
                ),
                amount_usdc=0.0,
            )
        )
        booked = 0.0
    elif verdict.verified:
        state.daily_revenue_usdc = float(state.daily_revenue_usdc) + ALPHA_PRICE_USDC
        db.add(
            LogEvent(
                level="REVENUE",
                category="X402",
                ticker=ticker,
                message=(
                    f"Sold alpha rationale for signal #{sig.id} ({ticker}) $0.01 "
                    f"— settlement verified (tx {verdict.tx_hash[:12]}…)"
                ),
                amount_usdc=ALPHA_PRICE_USDC,
            )
        )
        booked = ALPHA_PRICE_USDC
    else:
        state.daily_unverified_usdc = float(state.daily_unverified_usdc) + ALPHA_PRICE_USDC
        db.add(
            LogEvent(
                level="WARN",
                category="X402",
                ticker=ticker,
                message=(
                    f"Served rationale for signal #{sig.id} ({ticker}) against an "
                    f"UNVERIFIED payment — no revenue booked ({verdict.reason})"
                ),
                amount_usdc=0.0,
            )
        )
        booked = 0.0

    db.add(
        X402Receipt(
            receipt_key=key,
            signal_id=sig.id,
            ticker=ticker,
            amount_usdc=booked,
            payload_json=json.dumps(body),
        )
    )
    db.commit()
    return body


@router.get("/api/signals")
def get_signals(limit: int = 20):
    db = SessionLocal()
    try:
        rows = db.query(Signal).order_by(desc(Signal.ts)).limit(limit).all()
        return [
            {
                "id": s.id,
                "ts": s.ts.isoformat() if s.ts else None,
                "ticker": s.ticker,
                "sentiment": s.sentiment,
                "confidence": s.confidence,
                "whale_action": s.whale_action,
                "prior": s.prior_price,
                "posterior": s.posterior,
                "edge": s.edge,
                "decision": s.decision,
                "leakage_ok": s.leakage_ok,
            }
            for s in rows
        ]
    finally:
        db.close()


@router.get("/api/signals/{signal_id}")
def get_signal(signal_id: int):
    db = SessionLocal()
    try:
        s = db.get(Signal, signal_id)
        if s is None:
            return JSONResponse(status_code=404, content={"error": "Signal not found"})
        nlp = {}
        ev = {}
        try:
            nlp = json.loads(s.nlp_features_json or "{}")
        except json.JSONDecodeError:
            pass
        try:
            ev = json.loads(s.evidence_json or "{}")
        except json.JSONDecodeError:
            pass
        return {
            "id": s.id,
            "ts": s.ts.isoformat() if s.ts else None,
            "ticker": s.ticker,
            "sentiment": s.sentiment,
            "confidence": s.confidence,
            "whale_action": s.whale_action,
            "prior": s.prior_price,
            "posterior": s.posterior,
            "edge": s.edge,
            "decision": s.decision,
            "leakage_ok": s.leakage_ok,
            "source_snippet": s.source_snippet,
            "nlp_features": nlp,
            "evidence": ev,
        }
    finally:
        db.close()


@router.get("/api/logs")
def get_logs(limit: int = 40):
    db = SessionLocal()
    try:
        rows = db.query(LogEvent).order_by(desc(LogEvent.ts)).limit(limit).all()
        return [
            {
                "ts": e.ts.isoformat() if e.ts else None,
                "level": e.level,
                "category": e.category,
                "ticker": e.ticker,
                "message": e.message,
                "amount_usdc": e.amount_usdc,
            }
            for e in rows
        ]
    finally:
        db.close()


@router.post("/api/cycle")
async def trigger_cycle(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    """Run one scout->quant->risk cycle on demand (handy for demos)."""
    err = _admin_auth_error(authorization)
    if err:
        return err
    # run_cycle() blocks on network I/O — keep it off the event loop.
    return await run_in_threadpool(agent_loop.run_cycle)


@router.post("/api/reset")
def reset_day(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    err = _admin_auth_error(authorization)
    if err:
        return err
    db = SessionLocal()
    try:
        state = db.get(AgentState, 1)
        if state:
            state.halted = False
            state.halt_reason = ""
            state.status = "IDLE"
            state.day_key = today_key()
            state.daily_spend_usdc = 0.0
            state.daily_revenue_usdc = 0.0
            state.daily_unverified_usdc = 0.0
            state.daily_drawdown_usdc = 0.0
            db.commit()
        return {"ok": True}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Judge demo — one-shot narrative + orchestrated pipeline
# ---------------------------------------------------------------------------
JUDGE_BRIEFING = {
    "product": "AlphaNet-402",
    "elevator": (
        "An equities research agent that funds its own data: free fundamentals and price "
        "history via yfinance, paid news via Tavily (REST credits or x402+AWAL USDC), "
        "an LLM used strictly as an NLP parser, Bayesian log-odds belief updates in "
        "deterministic Python, and its own rationale re-sold to other agents over HTTP 402."
    ),
    "pillars": [
        {
            "name": "Scout",
            "detail": "Real price/fundamental events from yfinance (keyless); Tavily news layered on when paid access is configured.",
        },
        {
            "name": "Quant",
            "detail": "Groq parses text only; all edges and posteriors are computed in deterministic Python.",
        },
        {
            "name": "Risk",
            "detail": "Daily spend cap, drawdown limits, leakage guards — halt the loop on breach.",
        },
        {
            "name": "Monetize",
            "detail": "Sell the causal chain behind each signal for $0.01 USDC via x402 (demo headers in x402 Lab).",
        },
    ],
    "judge_tips": [
        "Open Network in /health — Base Sepolia by default; invoices use the same CAIP-2 id.",
        "After “Run pipeline”, open Overview → click a signal row for the drawer.",
        "Use x402 Lab to show raw 402 JSON then a paid retry with a demo X-Payment header.",
    ],
}


@router.get("/api/demo/briefing")
def demo_briefing():
    """Static talking points for the judge walkthrough."""
    return JUDGE_BRIEFING


@router.post("/api/demo/judge-run")
def demo_judge_run():
    """Single button: run scout→quant→risk, return state + latest signals + sample invoice."""
    summary = agent_loop.run_cycle()
    db = SessionLocal()
    try:
        state = _agent_state_payload(db)
        rows = db.query(Signal).order_by(desc(Signal.ts)).limit(6).all()
        latest = [
            {
                "id": s.id,
                "ticker": s.ticker,
                "sentiment": s.sentiment,
                "edge": s.edge,
                "decision": s.decision,
                "leakage_ok": s.leakage_ok,
            }
            for s in rows
        ]
        tick = rows[0].ticker if rows else (settings.watchlist[0] if settings.watchlist else "AAPL")
        sid = rows[0].id if rows else None
    finally:
        db.close()
    try:
        sample_invoice = _invoice_payload()
    except PaymentConfigError as exc:
        sample_invoice = {"unavailable": str(exc)}
    return {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "cycle": summary,
        "state": state,
        "latest_signals": latest,
        "sample_x402_invoice": sample_invoice,
        "deep_links": {
            "command_center": "/",
            "x402_lab": "/x402-lab",
            "alpha_rationale_unpaid": f"/api/alpha/{tick}/rationale",
            "trade_rationale_unpaid": f"/api/trade/{sid}/rationale" if sid else None,
        },
        "watchlist": settings.watchlist,
    }


# ---------------------------------------------------------------------------
# B2B x402 monetization endpoint
# ---------------------------------------------------------------------------
def _invoice_payload() -> dict:
    return {
        "x402Version": 1,
        "accepts": [
            {
                "scheme": "exact",
                "network": settings.NETWORK_CAIP_ID,
                "maxAmountRequired": ALPHA_PRICE_ATOMIC,
                "asset": "USDC",
                "payTo": resolve_pay_to(),
            }
        ],
    }


def _handle_rationale_request(x_payment, sig_lookup, not_found_msg):
    """Shared 402-invoice / settle flow for both rationale endpoints, differing
    only in how the target signal is looked up."""
    if not x_payment:
        try:
            invoice = _invoice_payload()
        except PaymentConfigError:
            return _payments_unavailable()
        return JSONResponse(
            status_code=402,
            content=invoice,
            headers={"Accept-Payment": "x402"},
        )

    db = SessionLocal()
    try:
        sig = sig_lookup(db)
        if sig is None:
            return JSONResponse(status_code=404, content={"error": not_found_msg})
        return _settle_rationale_sale(db, sig, sig.ticker, x_payment)
    finally:
        db.close()


@router.get("/api/alpha/{ticker}/rationale")
def alpha_rationale(
    ticker: str,
    x_payment: Optional[str] = Header(default=None, alias="X-Payment"),
):
    ticker = ticker.upper()
    return _handle_rationale_request(
        x_payment,
        lambda db: (
            db.query(Signal)
            .filter(Signal.ticker == ticker)
            .order_by(desc(Signal.ts))
            .first()
        ),
        f"No rationale computed yet for {ticker}",
    )


@router.get("/api/trade/{signal_id}/rationale")
def trade_rationale_by_id(
    signal_id: int,
    x_payment: Optional[str] = Header(default=None, alias="X-Payment"),
):
    """Blueprint alias: monetize rationale for a specific stored signal row."""
    return _handle_rationale_request(
        x_payment,
        lambda db: db.get(Signal, signal_id),
        f"No signal #{signal_id}",
    )
