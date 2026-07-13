"""Test bootstrap: isolate the sqlite DB and neutralize env-dependent settings
BEFORE any app module is imported."""
from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="alphanet-tests-")
os.environ["ALPHANET_DB_PATH"] = os.path.join(_TMP, "test.db")

import pytest  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402

init_db()


@pytest.fixture(autouse=True)
def _neutral_settings(monkeypatch):
    """Deterministic, keyless, offline defaults for every test."""
    monkeypatch.setattr(settings, "TRADING_MODE", "PAPER")
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(settings, "OUR_AWAL_WALLET_ADDRESS", "")
    monkeypatch.setattr(settings, "MAX_DAILY_SPEND_USDC", 2.00)
    monkeypatch.setattr(settings, "MAX_PRICE_PER_SEARCH_USDC", 0.01)
    monkeypatch.setattr(settings, "EDGE_THRESHOLD", 0.05)
    yield


@pytest.fixture()
def db():
    """Fresh session against a wiped database for each test."""
    from app import models  # noqa: F401
    from app.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
