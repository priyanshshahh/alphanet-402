"""HTTP API aggregator.

The routes are split into three logical routers — dashboard, admin control,
and the x402 seller — each in its own module. This file wires them into one
`router` for the app to include, and re-exports the payment helpers that tests
and the dashboard router reference.
"""
from __future__ import annotations

from fastapi import APIRouter

from app import agent_loop  # re-exported for tests that patch run_cycle
from app.api import admin, dashboard, x402
from app.api.x402 import (  # noqa: F401 — re-exported for backward compatibility
    ALPHA_PRICE_ATOMIC,
    ALPHA_PRICE_USDC,
    PaymentConfigError,
    resolve_pay_to,
)

__all__ = [
    "router",
    "agent_loop",
    "PaymentConfigError",
    "resolve_pay_to",
    "ALPHA_PRICE_ATOMIC",
    "ALPHA_PRICE_USDC",
]

router = APIRouter()
router.include_router(dashboard.router)
router.include_router(admin.router)
router.include_router(x402.router)
