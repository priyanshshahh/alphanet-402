"""Demo-mode labeling and payment-config fail-hard behavior."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import routes as routes_mod
from app.api.routes import PaymentConfigError, resolve_pay_to
from app.core.config import settings
from app.main import app
from app.modules.ingestion import EquityScout
from app.modules.quant_pipeline import run_quant


@pytest.fixture(autouse=True)
def _clear_pay_to_cache():
    resolve_pay_to.cache_clear()
    yield
    resolve_pay_to.cache_clear()


# --- demo mode labeling ------------------------------------------------------
def test_demo_scout_labels_everything(db, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    r = EquityScout(db).scout("AAPL")
    assert r.demo is True
    assert r.source == "demo"
    assert r.amount_usdc == 0.0
    assert all(res.get("demo") is True for res in r.results)
    assert all("[DEMO" in res["title"] for res in r.results)


def test_demo_flag_flows_into_signal_evidence(db, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    sig = run_quant(EquityScout(db).scout("AAPL"))
    assert sig.evidence["demo"] is True
    assert sig.evidence["mode"] == "demo"


def test_real_scout_is_not_demo_labeled(db, monkeypatch):
    from app.modules import ingestion

    monkeypatch.setattr(
        ingestion,
        "fetch_equity_events",
        lambda t: ([{"title": "tech", "url": "u", "content": "bullish"}], 0.5),
    )
    sig = run_quant(EquityScout(db).scout("AAPL"))
    assert sig.evidence["demo"] is False


# --- payment config fail-hard ---------------------------------------------
def _awal_unavailable(monkeypatch):
    def _fail(*a, **k):
        raise FileNotFoundError("npx not available in tests")

    monkeypatch.setattr(routes_mod.subprocess, "run", _fail)


def test_resolve_pay_to_fails_hard_without_wallet(monkeypatch):
    _awal_unavailable(monkeypatch)
    with pytest.raises(PaymentConfigError):
        resolve_pay_to()


def test_resolve_pay_to_rejects_zero_address(monkeypatch):
    _awal_unavailable(monkeypatch)
    monkeypatch.setattr(
        settings, "OUR_AWAL_WALLET_ADDRESS", "0x0000000000000000000000000000000000000000"
    )
    with pytest.raises(PaymentConfigError):
        resolve_pay_to()


def test_resolve_pay_to_uses_configured_address(monkeypatch):
    monkeypatch.setattr(settings, "OUR_AWAL_WALLET_ADDRESS", "0xAbC0000000000000000000000000000000000001")
    assert resolve_pay_to() == "0xAbC0000000000000000000000000000000000001"


def test_invoice_endpoint_503_when_unconfigured(db, monkeypatch):
    _awal_unavailable(monkeypatch)
    client = TestClient(app)
    r = client.get("/api/alpha/AAPL/rationale")
    assert r.status_code == 503
    assert "OUR_AWAL_WALLET_ADDRESS" in r.json()["error"]


def test_invoice_endpoint_402_when_configured(db, monkeypatch):
    addr = "0xAbC0000000000000000000000000000000000001"
    monkeypatch.setattr(settings, "OUR_AWAL_WALLET_ADDRESS", addr)
    client = TestClient(app)
    r = client.get("/api/alpha/AAPL/rationale")
    assert r.status_code == 402
    inv = r.json()
    assert inv["accepts"][0]["payTo"] == addr
    assert inv["accepts"][0]["maxAmountRequired"] == "1000"


def test_demo_payment_header_books_no_revenue(db, monkeypatch):
    from app.models import AgentState, Signal

    addr = "0xAbC0000000000000000000000000000000000001"
    monkeypatch.setattr(settings, "OUR_AWAL_WALLET_ADDRESS", addr)
    db.add(Signal(ticker="AAPL", sentiment="bullish", decision="BUY"))
    db.add(AgentState(id=1))
    db.commit()

    client = TestClient(app)
    r = client.get("/api/alpha/AAPL/rationale", headers={"X-Payment": "demo-proof-123"})
    assert r.status_code == 200
    body = r.json()
    assert body["demo_payment"] is True
    assert body["settled_usdc"] == 0.0

    state = db.get(AgentState, 1)
    db.refresh(state)
    assert state.daily_revenue_usdc == 0.0


# --- unit economics --------------------------------------------------------
def test_economics_reads_the_ledger(db):
    from app.models import LogEvent, Signal

    db.add(LogEvent(level="SPEND", category="X402", ticker="AAPL", message="Tavily x402", amount_usdc=-0.01))
    db.add(LogEvent(level="SPEND", category="X402", ticker="MSFT", message="Tavily x402", amount_usdc=-0.01))
    db.add(LogEvent(level="REVENUE", category="X402", ticker="AAPL", message="Sold rationale — verified", amount_usdc=0.01))
    db.add(LogEvent(level="WARN", category="X402", ticker="NVDA", message="UNVERIFIED payment — no revenue", amount_usdc=0.0))
    db.add(Signal(ticker="AAPL", decision="BUY"))
    db.commit()

    client = TestClient(app)
    r = client.get("/api/economics")
    assert r.status_code == 200
    body = r.json()
    cum = body["cumulative"]
    assert cum["spend_usdc"] == pytest.approx(0.02)
    assert cum["revenue_usdc"] == pytest.approx(0.01)
    assert cum["purchases"] == 2
    assert cum["sales_verified"] == 1
    assert cum["sales_unverified"] == 1
    assert body["net_margin_usdc"] == pytest.approx(-0.01)
    assert body["break_even"] is False
    assert len(body["ledger"]) == 3  # 2 spend + 1 revenue, WARN excluded


# --- CORS ------------------------------------------------------------------
def _cors_middleware():
    from fastapi.middleware.cors import CORSMiddleware

    from app.main import app as app_mod

    for m in app_mod.user_middleware:
        if m.cls is CORSMiddleware:
            return m
    raise AssertionError("CORSMiddleware not registered")


def test_cors_wildcard_is_gone():
    origins = _cors_middleware().kwargs["allow_origins"]
    assert "*" not in origins
    assert "http://localhost:5173" in origins


def test_cors_preflight_rejects_unknown_origin(db):
    client = TestClient(app)
    r = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers


def test_cors_allows_configured_dev_origin(db):
    client = TestClient(app)
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_env_origins_honored(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv(
        "ALPHANET_ALLOWED_ORIGINS",
        "https://alphanet.vercel.app/, http://localhost:5173 ,*",
    )
    s = Settings(_env_file=None)
    # trailing slash and whitespace normalized, wildcard entries dropped
    assert s.allowed_origins == [
        "https://alphanet.vercel.app",
        "http://localhost:5173",
    ]


def test_health_reports_data_mode(db):
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["data_mode"] == "yfinance"
    assert body["demo_mode"] is False


# --- admin auth on control endpoints (/api/reset, /api/cycle) --------------
def test_control_endpoints_disabled_without_admin_token(db, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_TOKEN", "")
    client = TestClient(app)

    r = client.post("/api/reset")
    assert r.status_code == 503
    assert "ADMIN_TOKEN" in r.json()["error"]

    r = client.post("/api/cycle")
    assert r.status_code == 503
    assert "ADMIN_TOKEN" in r.json()["error"]


def test_control_endpoints_reject_missing_token(db, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_TOKEN", "s3cret-token")
    client = TestClient(app)

    r = client.post("/api/reset")
    assert r.status_code == 401

    r = client.post("/api/cycle")
    assert r.status_code == 401


def test_control_endpoints_reject_wrong_token(db, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_TOKEN", "s3cret-token")
    client = TestClient(app)
    headers = {"Authorization": "Bearer wrong-token"}

    r = client.post("/api/reset", headers=headers)
    assert r.status_code == 401

    r = client.post("/api/cycle", headers=headers)
    assert r.status_code == 401


def test_control_endpoints_accept_correct_token(db, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_TOKEN", "s3cret-token")
    # /api/cycle would otherwise hit real yfinance network calls; stub it out
    # so this test only exercises the auth gate, not the scout pipeline.
    monkeypatch.setattr(routes_mod.agent_loop, "run_cycle", lambda: {"stubbed": True})
    client = TestClient(app)
    headers = {"Authorization": "Bearer s3cret-token"}

    r = client.post("/api/reset", headers=headers)
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r = client.post("/api/cycle", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"stubbed": True}
