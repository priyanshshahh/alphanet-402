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


def test_health_reports_data_mode(db):
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["data_mode"] == "yfinance"
    assert body["demo_mode"] is False
