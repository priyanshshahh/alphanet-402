"""Dashboard API consumed by the React Command Center, plus the judge-demo
narrative endpoints. Read-mostly; no payment settlement lives here (see x402.py).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import agent_loop
from app.api.x402 import PaymentConfigError, _invoice_payload, resolve_pay_to
from app.core.config import settings
from app.database import SessionLocal
from app.models import AgentState, LogEvent, Signal, today_key

router = APIRouter(tags=["dashboard"])


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


@router.get("/api/economics")
def get_economics():
    """Unit economics from the append-only log_events ledger — the agent's
    real self-funding P&L. Spend = USDC burned buying data (SPEND rows);
    revenue = *verified* x402 sales (REVENUE rows). All-time, real logged
    numbers only; unverified sales are reported separately and never counted
    as revenue."""
    db = SessionLocal()
    try:
        spend_rows = db.query(LogEvent).filter(LogEvent.level == "SPEND").all()
        revenue_rows = db.query(LogEvent).filter(LogEvent.level == "REVENUE").all()
        unverified = (
            db.query(LogEvent)
            .filter(LogEvent.level == "WARN", LogEvent.category == "X402")
            .filter(LogEvent.message.like("%UNVERIFIED%"))
            .count()
        )
        signals_produced = db.query(Signal).count()

        total_spend = round(sum(abs(r.amount_usdc or 0.0) for r in spend_rows), 6)
        total_revenue = round(sum(r.amount_usdc or 0.0 for r in revenue_rows), 6)
        purchases = len(spend_rows)
        sales = len(revenue_rows)

        def _safe_div(a, b):
            return round(a / b, 6) if b else 0.0

        ledger = [
            {
                "ts": e.ts.isoformat() if e.ts else None,
                "kind": e.level,
                "category": e.category,
                "ticker": e.ticker,
                "amount_usdc": e.amount_usdc,
                "message": e.message,
            }
            for e in sorted(
                spend_rows + revenue_rows,
                key=lambda x: x.ts or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )[:30]
        ]

        return {
            "currency": "USDC",
            "net_margin_usdc": round(total_revenue - total_spend, 6),
            "break_even": total_revenue >= total_spend,
            "cumulative": {
                "spend_usdc": total_spend,
                "revenue_usdc": total_revenue,
                "purchases": purchases,
                "sales_verified": sales,
                "sales_unverified": unverified,
                "signals_produced": signals_produced,
                "avg_cost_per_purchase_usdc": _safe_div(total_spend, purchases),
                "avg_revenue_per_sale_usdc": _safe_div(total_revenue, sales),
                "cost_per_signal_usdc": _safe_div(total_spend, signals_produced),
            },
            "ledger": ledger,
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
            "detail": "Sell the causal chain behind each signal for $0.01 USDC via x402, revenue booked only on verified on-chain settlement.",
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
