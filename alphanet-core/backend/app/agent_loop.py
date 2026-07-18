"""Autonomous loop: Scout (yfinance + optional paid news) -> Quant (Bayes) -> Risk -> log.

Runs as a background asyncio task. Each cycle iterates the equity watchlist
(free yfinance data always; x402 USDC micropayments for news only in LIVE
mode) and halts immediately on any spend/risk breach.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import uuid

from app.core.config import settings
from app.database import SessionLocal
from app.models import AgentState, LogEvent, Signal
from app.modules.ingestion import EquityScout, SpendLimitExceeded
from app.modules.quant_pipeline import run_quant
from app.modules.risk import RiskOverseer

_task: asyncio.Task | None = None
_running = False


def _log(db, level, category, message, ticker="", amount=0.0):
    db.add(
        LogEvent(
            level=level,
            category=category,
            ticker=ticker,
            message=message,
            amount_usdc=amount,
        )
    )
    db.commit()


def run_cycle() -> dict:
    """One full scout->quant->risk pass over the watchlist. Synchronous so it
    can also be triggered on-demand from an API route."""
    db = SessionLocal()
    summary = {"cycle_at": dt.datetime.now(dt.timezone.utc).isoformat(), "signals": []}
    try:
        state = db.get(AgentState, 1)
        if state is None:
            state = AgentState(id=1, trading_mode=settings.TRADING_MODE)
            db.add(state)
            db.commit()

        risk = RiskOverseer(db)
        verdict = risk.check_global_killswitches()
        if not verdict.approved:
            _log(db, "WARN", "RISK", f"Cycle skipped: {verdict.reason}")
            summary["halted"] = True
            summary["reason"] = verdict.reason
            return summary

        state.status = "SCOUTING"
        db.commit()

        scout = EquityScout(db)
        cycle_id = str(uuid.uuid4())
        for ticker in settings.watchlist:
            idem_key = f"{cycle_id}:{ticker}"
            try:
                result = scout.scout(ticker)
            except SpendLimitExceeded as exc:
                risk.halt(str(exc))
                _log(db, "ERROR", "X402", f"Spend limit halt: {exc}", ticker)
                summary["halted"] = True
                summary["reason"] = str(exc)
                break

            if not result.paid:
                _log(db, "WARN", "SCOUT", f"No data for {ticker} — skipping", ticker)
                continue

            sig = run_quant(result)
            sized = risk.size_position(sig.edge, sig.confidence)

            db.add(
                Signal(
                    ticker=sig.ticker,
                    sentiment=sig.sentiment,
                    confidence=sig.confidence,
                    whale_action=sig.whale_action,
                    prior_price=sig.prior,
                    posterior=sig.posterior,
                    edge=sig.edge,
                    decision=sig.decision if sized.approved else "HOLD",
                    leakage_ok=sig.leakage_ok,
                    source_snippet=sig.source_snippet,
                    idempotency_key=idem_key,
                    nlp_features_json=json.dumps(sig.nlp_features, default=str),
                    evidence_json=json.dumps(sig.evidence, default=str),
                )
            )
            db.commit()

            msg = (
                f"{sig.ticker}: {sig.sentiment} conf={sig.confidence:.2f} "
                f"prior={sig.prior:.2f} post={sig.posterior:.2f} "
                f"edge={sig.edge:+.3f} -> {sig.decision}"
            )
            _log(db, "INFO", "QUANT", msg, sig.ticker)
            summary["signals"].append(
                {
                    "ticker": sig.ticker,
                    "decision": sig.decision if sized.approved else "HOLD",
                    "edge": sig.edge,
                    "confidence": sig.confidence,
                    "size_usdc": sized.position_size_usdc if sized.approved else 0.0,
                }
            )

        state = db.get(AgentState, 1)
        if not state.halted:
            state.status = "IDLE"
            db.commit()
        return summary
    finally:
        db.close()


async def _loop():
    global _running
    _running = True
    while _running:
        try:
            # run_cycle() does blocking network I/O (yfinance, Tavily, the awal
            # subprocess). Off-load it to a worker thread so a slow scout can
            # never freeze the uvicorn event loop that also serves the API.
            await asyncio.to_thread(run_cycle)
        except Exception as exc:  # never let the loop die silently
            db = SessionLocal()
            try:
                _log(db, "ERROR", "SYSTEM", f"Loop error: {exc}")
            finally:
                db.close()
        await asyncio.sleep(settings.LOOP_INTERVAL_SECONDS)


def start_loop() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())


def stop_loop() -> None:
    global _running
    _running = False
