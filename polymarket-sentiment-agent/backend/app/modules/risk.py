"""The Overseer — hard risk gates.

Every proposed trade passes through `evaluate()`. Returns either an
approved (possibly resized) trade plan, or a reason for rejection.
Risk decisions are written to the DB log so we can audit every kill.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func

from ..config import settings
from ..database import session_scope
from ..models import AgentState, LogEvent, Trade

log = logging.getLogger("overseer")


@dataclass
class TradePlan:
    condition_id: str
    market_question: str
    outcome: str
    token_id: str
    side: str            # BUY
    price: float
    model_probability: float
    edge: float
    size_usdc: float
    signal_id: Optional[int]
    snapshot_id: Optional[int]
    idem_key: str


@dataclass
class RiskDecision:
    approved: bool
    plan: Optional[TradePlan]
    reason: str = ""


def _kill_switch_state() -> bool:
    with session_scope() as s:
        row = s.get(AgentState, "kill_switch")
        if row and row.value:
            return row.value.lower() == "true"
    return settings.kill_switch


def set_kill_switch(enabled: bool) -> None:
    with session_scope() as s:
        row = s.get(AgentState, "kill_switch")
        if row is None:
            s.add(AgentState(key="kill_switch", value="true" if enabled else "false"))
        else:
            row.value = "true" if enabled else "false"
    log.warning("Kill switch set to %s", enabled)


def _daily_pnl() -> float:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    with session_scope() as s:
        total = (
            s.query(func.coalesce(func.sum(Trade.pnl_usdc), 0.0))
            .filter(Trade.created_at >= cutoff)
            .scalar()
        )
    return float(total or 0.0)


def _open_position_count() -> int:
    with session_scope() as s:
        return (
            s.query(func.count(Trade.id))
            .filter(Trade.status == "FILLED")
            .filter(Trade.closed_at.is_(None))
            .scalar()
            or 0
        )


def evaluate(plan: TradePlan) -> RiskDecision:
    if _kill_switch_state():
        return RiskDecision(False, None, "KILL_SWITCH active")

    if plan.size_usdc <= 0:
        return RiskDecision(False, None, "Non-positive size")

    if abs(plan.edge) < settings.edge_threshold:
        return RiskDecision(False, None, f"Edge {plan.edge:.3f} < threshold {settings.edge_threshold}")

    if plan.size_usdc > settings.max_usdc_per_trade:
        plan = TradePlan(**{**plan.__dict__, "size_usdc": settings.max_usdc_per_trade})

    if _open_position_count() >= settings.max_open_positions:
        return RiskDecision(False, None, "Max open positions reached")

    daily = _daily_pnl()
    if daily <= -abs(settings.daily_drawdown_usdc):
        # auto-engage kill switch if drawdown breached
        set_kill_switch(True)
        return RiskDecision(False, None, f"Daily drawdown breached: {daily:.2f} USDC")

    return RiskDecision(True, plan)


def record_event(component: str, level: str, message: str, data: Optional[dict] = None) -> None:
    with session_scope() as s:
        s.add(
            LogEvent(
                component=component,
                level=level,
                message=message,
                data=json.dumps(data or {}, default=str),
            )
        )
