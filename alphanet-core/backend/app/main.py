"""AlphaNet-402 backend entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import agent_loop
from app.api.routes import router
from app.core.config import settings
from app.database import SessionLocal, init_db
from app.models import AgentState


def _init_sentry() -> None:
    """Optional Sentry — activated when SENTRY_DSN is set (student plan / hackathon)."""
    dsn = (settings.SENTRY_DSN or "").strip()
    if not dsn:
        return
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        traces_sample_rate=0.1,
        environment=(settings.SENTRY_ENVIRONMENT or "development").strip(),
        send_default_pii=False,
    )


_init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        state = db.get(AgentState, 1)
        if state is None:
            state = AgentState(id=1, trading_mode=settings.TRADING_MODE)
            db.add(state)
        state.trading_mode = settings.TRADING_MODE
        if settings.OUR_AWAL_WALLET_ADDRESS:
            state.wallet_address = settings.OUR_AWAL_WALLET_ADDRESS.strip()
        db.commit()
    finally:
        db.close()
    agent_loop.start_loop()
    yield
    agent_loop.stop_loop()


app = FastAPI(title="AlphaNet-402", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "alphanet-402",
        "mode": settings.TRADING_MODE,
        "demo_mode": settings.DEMO_MODE,
        "data_mode": settings.data_mode,
        "network": settings.NETWORK_CAIP_ID,
        "awal_wallet": settings.OUR_AWAL_WALLET_ADDRESS or None,
        "tavily_402": settings.TAVILY_402_ENDPOINT,
        "tavily_rest": settings.TAVILY_REST_ENDPOINT,
        "sentry": bool((settings.SENTRY_DSN or "").strip()),
    }
