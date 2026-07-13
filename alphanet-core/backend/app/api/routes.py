"""HTTP API.

Two surfaces:
  * Dashboard API (consumed by the React Command Center).
  * B2B x402 monetization endpoint that sells our alpha rationale for $0.01.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import agent_loop
from app.core.config import settings
from app.database import SessionLocal
from app.models import AgentState, LogEvent, Signal, X402Receipt, today_key

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
            timeout=20,
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


def _causal_payload(sig: Signal, x_payment: str) -> dict:
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
    demo = _is_demo_proof(x_payment)
    return {
        "ticker": sig.ticker,
        "signal_id": sig.id,
        "settled_usdc": 0.0 if demo else ALPHA_PRICE_USDC,
        "demo_payment": demo,
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
        "leakage_verified": sig.leakage_ok,
        "computed_at": sig.ts.isoformat() if sig.ts else None,
    }


def _settle_rationale_sale(
    db, sig: Signal, ticker: str, x_payment: str
) -> dict:
    """Record revenue once per (payment proof, signal) pair; return causal JSON."""
    key = _receipt_key(x_payment, sig.id)
    existing = db.query(X402Receipt).filter(X402Receipt.receipt_key == key).first()
    if existing:
        try:
            return json.loads(existing.payload_json or "{}")
        except json.JSONDecodeError:
            pass

    body = _causal_payload(sig, x_payment)
    demo = _is_demo_proof(x_payment)

    if demo:
        # Demo header from the x402 Lab UI: return the causal chain, but never
        # book revenue for a payment that did not settle on-chain.
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
    else:
        state = db.get(AgentState, 1)
        if state.day_key != today_key():
            state.day_key = today_key()
            state.daily_revenue_usdc = 0.0
        state.daily_revenue_usdc = float(state.daily_revenue_usdc) + ALPHA_PRICE_USDC
        db.add(
            LogEvent(
                level="REVENUE",
                category="X402",
                ticker=ticker,
                message=f"Sold alpha rationale for signal #{sig.id} ({ticker}) $0.01",
                amount_usdc=ALPHA_PRICE_USDC,
            )
        )
    db.add(
        X402Receipt(
            receipt_key=key,
            signal_id=sig.id,
            ticker=ticker,
            amount_usdc=0.0 if demo else ALPHA_PRICE_USDC,
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
def trigger_cycle():
    """Run one scout->quant->risk cycle on demand (handy for demos)."""
    return agent_loop.run_cycle()


@router.post("/api/reset")
def reset_day():
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


@router.get("/api/alpha/{ticker}/rationale")
def alpha_rationale(
    ticker: str,
    x_payment: Optional[str] = Header(default=None, alias="X-Payment"),
):
    ticker = ticker.upper()

    # Unpaid request -> issue a 402 invoice (network from settings, default Base Sepolia).
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

    # Paid request -> settle revenue and return the full causal chain.
    db = SessionLocal()
    try:
        sig = (
            db.query(Signal)
            .filter(Signal.ticker == ticker)
            .order_by(desc(Signal.ts))
            .first()
        )
        if sig is None:
            return JSONResponse(
                status_code=404,
                content={"error": f"No rationale computed yet for {ticker}"},
            )

        return _settle_rationale_sale(db, sig, ticker, x_payment)
    finally:
        db.close()


@router.get("/api/trade/{signal_id}/rationale")
def trade_rationale_by_id(
    signal_id: int,
    x_payment: Optional[str] = Header(default=None, alias="X-Payment"),
):
    """Blueprint alias: monetize rationale for a specific stored signal row."""
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
        sig = db.get(Signal, signal_id)
        if sig is None:
            return JSONResponse(
                status_code=404,
                content={"error": f"No signal #{signal_id}"},
            )
        return _settle_rationale_sale(db, sig, sig.ticker, x_payment)
    finally:
        db.close()
