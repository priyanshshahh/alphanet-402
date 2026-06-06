"""The Trader — idempotent execution.

PAPER mode (default): simulates fills at the current best ask, no chain
interaction. Tracks shares, basis, and PnL deterministically.

LIVE mode: stubbed. The MVP wires the seam (idem key, single-write,
status transitions) so the on-chain integration is mechanical to add.
We deliberately DO NOT ship a half-working chain signer in the MVP —
that's a footgun on a public repo. Set TRADING_MODE=LIVE only after
implementing the signer in `_execute_live`.

Idempotency:
  * `Trade.idem_key` has a UNIQUE constraint.
  * The orchestrator constructs the idem_key deterministically from
    (condition_id, outcome, signal_id). Retries hit the unique index
    and become no-ops.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError

from ..config import settings
from ..database import session_scope
from ..models import Trade
from .risk import TradePlan

log = logging.getLogger("trader")


def make_idem_key(condition_id: str, outcome: str, signal_id: Optional[int]) -> str:
    """Deterministic — same signal can't fill twice."""
    return f"{condition_id}:{outcome}:{signal_id or 'none'}"


def _execute_paper(plan: TradePlan) -> Trade:
    # Fill at the best ask. For YES, that's plan.price; cost is size_usdc.
    fill_price = max(0.01, min(0.99, plan.price))
    shares = plan.size_usdc / fill_price
    trade = Trade(
        idem_key=plan.idem_key,
        mode="PAPER",
        status="FILLED",
        condition_id=plan.condition_id,
        market_question=plan.market_question,
        outcome=plan.outcome,
        side=plan.side,
        price=fill_price,
        size_usdc=plan.size_usdc,
        shares=shares,
        fees_usdc=0.0,
        model_probability=plan.model_probability,
        edge=plan.edge,
        signal_id=plan.signal_id,
        snapshot_id=plan.snapshot_id,
        notes="Paper fill at best ask",
    )
    return trade


def _execute_live(plan: TradePlan) -> Trade:
    # Placeholder. The Polymarket Python CLOB client signs an L2 order
    # against the exchange after EIP-712 signing. For the MVP we refuse
    # to execute unless explicitly built out, to prevent accidental loss.
    raise NotImplementedError(
        "LIVE mode is intentionally not implemented in the MVP. "
        "Implement EIP-712 order signing via py-clob-client before enabling."
    )


def execute(plan: TradePlan) -> Optional[Trade]:
    """Idempotent execution. Returns the Trade row, or None if duplicate."""
    if settings.trading_mode == "LIVE":
        trade = _execute_live(plan)
    else:
        trade = _execute_paper(plan)

    with session_scope() as s:
        s.add(trade)
        try:
            s.flush()
        except IntegrityError:
            s.rollback()
            log.info("Idempotency hit: %s already executed", plan.idem_key)
            return None
        s.refresh(trade)
        s.expunge(trade)
    log.info(
        "Trade fired: %s %s %.4f x %.2f USDC (edge %.3f)",
        plan.outcome,
        plan.condition_id[:10],
        plan.price,
        plan.size_usdc,
        plan.edge,
    )
    return trade


def mark_to_market(current_price_lookup) -> None:
    """Update unrealized PnL on open positions.

    `current_price_lookup(condition_id, outcome) -> Optional[float]`
    """
    with session_scope() as s:
        open_trades = (
            s.query(Trade)
            .filter(Trade.status == "FILLED")
            .filter(Trade.closed_at.is_(None))
            .all()
        )
        for t in open_trades:
            cur = current_price_lookup(t.condition_id, t.outcome)
            if cur is None:
                continue
            t.exit_price = cur
            t.pnl_usdc = (cur - t.price) * t.shares
