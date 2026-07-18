"""Admin control endpoints — bearer-token gated (see _admin_auth_error)."""
from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, Header
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app import agent_loop
from app.core.config import settings
from app.database import SessionLocal
from app.models import AgentState, today_key

router = APIRouter(tags=["admin"])


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
