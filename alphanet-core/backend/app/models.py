"""SQLAlchemy models.

`AgentState` and `log_events` track cumulative daily spend (USDC burned on
x402 data purchases) and cumulative x402 API revenue earned; `signals` and
`x402_receipts` are the audit trail behind every sold rationale.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)

from app.database import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def today_key() -> str:
    return _utcnow().strftime("%Y-%m-%d")


class AgentState(Base):
    """Singleton-ish row (id=1) holding the live agent status + risk flags."""

    __tablename__ = "agent_state"

    id = Column(Integer, primary_key=True)
    status = Column(String, default="IDLE")  # IDLE | SCOUTING | HALTED
    trading_mode = Column(String, default="LIVE")
    halted = Column(Boolean, default=False)
    halt_reason = Column(String, default="")

    # Cumulative daily spend tracking (resets per day_key)
    day_key = Column(String, default=today_key)
    daily_spend_usdc = Column(Float, default=0.0)
    daily_revenue_usdc = Column(Float, default=0.0)
    realized_pnl_usdc = Column(Float, default=0.0)
    daily_drawdown_usdc = Column(Float, default=0.0)

    wallet_address = Column(String, default="")
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class LogEvent(Base):
    """Append-only event log; doubles as the spend/revenue ledger."""

    __tablename__ = "log_events"

    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=_utcnow, index=True)
    day_key = Column(String, default=today_key, index=True)
    level = Column(String, default="INFO")  # INFO | WARN | ERROR | SPEND | REVENUE
    category = Column(String, default="SYSTEM")  # SCOUT | QUANT | RISK | X402 | SYSTEM
    ticker = Column(String, default="")
    message = Column(Text, default="")
    amount_usdc = Column(Float, default=0.0)  # signed: -spend / +revenue


class Signal(Base):
    """A quant decision produced for a ticker each cycle."""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=_utcnow, index=True)
    ticker = Column(String, index=True)
    sentiment = Column(String, default="neutral")  # bullish | bearish | neutral
    confidence = Column(Float, default=0.0)
    whale_action = Column(Text, default="")
    prior_price = Column(Float, default=0.5)  # market-implied prior probability
    posterior = Column(Float, default=0.5)  # Bayesian posterior probability
    edge = Column(Float, default=0.0)  # posterior - prior
    decision = Column(String, default="HOLD")  # BUY | SELL | HOLD
    leakage_ok = Column(Boolean, default=True)
    source_snippet = Column(Text, default="")
    # Idempotency: one row per (scout cycle, ticker); retries must not duplicate.
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)
    # Full causal chain for B2B rationale payloads (JSON text).
    nlp_features_json = Column(Text, default="")
    evidence_json = Column(Text, default="")


class X402Receipt(Base):
    """Idempotent x402 buyer receipts: same payment proof + signal must not double-bill."""

    __tablename__ = "x402_receipts"

    id = Column(Integer, primary_key=True)
    receipt_key = Column(String(128), unique=True, nullable=False, index=True)
    signal_id = Column(Integer, nullable=False, index=True)
    ticker = Column(String, default="")
    amount_usdc = Column(Float, default=0.0)
    created_at = Column(DateTime, default=_utcnow)
    payload_json = Column(Text, default="")
