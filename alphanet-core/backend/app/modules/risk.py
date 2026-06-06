"""Risk overseer — global kill-switches between quant output and execution.

Enforces:
  * Daily drawdown limit → halt if realized losses breach cap.
  * Daily spend limit → halt if scout budget is exhausted.
  * Max position sizing → cap notional risked per BUY/SELL signal.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AgentState, LogEvent, today_key


@dataclass
class RiskVerdict:
    approved: bool
    reason: str
    position_size_usdc: float = 0.0


# Notional bankroll for demo position sizing (USDC-equivalent display units).
DEMO_BANKROLL_USDC = 1_000.0
MAX_POSITION_FRACTION = 0.10  # never risk more than 10% of bankroll per trade


class RiskOverseer:
    def __init__(self, db: Session):
        self.db = db

    def _state(self) -> AgentState:
        state = self.db.get(AgentState, 1)
        if state is None:
            state = AgentState(id=1, trading_mode=settings.TRADING_MODE)
            self.db.add(state)
            self.db.commit()
        return state

    def halt(self, reason: str) -> None:
        state = self._state()
        state.halted = True
        state.status = "HALTED"
        state.halt_reason = reason
        self.db.add(
            LogEvent(level="ERROR", category="RISK", message=f"KILL-SWITCH: {reason}")
        )
        self.db.commit()

    def is_halted(self) -> bool:
        return bool(self._state().halted)

    def check_global_killswitches(self) -> RiskVerdict:
        state = self._state()

        if state.halted:
            return RiskVerdict(False, state.halt_reason or "Agent halted")

        if state.daily_drawdown_usdc >= settings.DAILY_DRAWDOWN_LIMIT_USDC:
            self.halt(
                f"Drawdown {state.daily_drawdown_usdc:.2f} >= limit "
                f"{settings.DAILY_DRAWDOWN_LIMIT_USDC:.2f} USDC"
            )
            return RiskVerdict(False, state.halt_reason)

        if state.daily_spend_usdc >= settings.MAX_DAILY_SPEND_USDC:
            self.halt(
                f"Daily spend {state.daily_spend_usdc:.2f} >= cap "
                f"{settings.MAX_DAILY_SPEND_USDC:.2f} USDC"
            )
            return RiskVerdict(False, state.halt_reason)

        return RiskVerdict(True, "ok")

    def size_position(self, edge: float, confidence: float) -> RiskVerdict:
        """Approve a trade and compute a risk-capped position size.
        Uses a fractional-Kelly-style scaling on |edge| * confidence."""
        verdict = self.check_global_killswitches()
        if not verdict.approved:
            return verdict

        scale = min(1.0, abs(edge) / max(settings.EDGE_THRESHOLD, 1e-6)) * confidence
        size = round(DEMO_BANKROLL_USDC * MAX_POSITION_FRACTION * scale, 2)
        if size <= 0:
            return RiskVerdict(False, "Edge too small to size a position")
        return RiskVerdict(True, "sized", position_size_usdc=size)

    def register_pnl(self, pnl_usdc: float) -> None:
        """Record realized PnL; track drawdown for the kill-switch."""
        state = self._state()
        if state.day_key != today_key():
            state.day_key = today_key()
            state.daily_spend_usdc = 0.0
            state.daily_revenue_usdc = 0.0
            state.daily_drawdown_usdc = 0.0
        state.realized_pnl_usdc = float(state.realized_pnl_usdc) + pnl_usdc
        if pnl_usdc < 0:
            state.daily_drawdown_usdc = float(state.daily_drawdown_usdc) + abs(pnl_usdc)
        self.db.commit()
        self.check_global_killswitches()
