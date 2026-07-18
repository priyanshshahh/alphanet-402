"""x402 settlement verification — the branch that books real money.

Covers the settlement helper in isolation (tx-hash extraction, USDC transfer
matching, RPC verdicts) and the full revenue path end-to-end: a verified
settlement books $0.01, an unverified one is served but excluded from revenue,
a demo header books nothing, and receipts stay idempotent on replay.
"""
from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient

from app.api.routes import resolve_pay_to
from app.core.config import settings
from app.main import app
from app.models import AgentState, Signal
from app.modules import settlement as settlement_mod
from app.modules.settlement import (
    _extract_tx_hash,
    _matches_usdc_transfer,
    verify_settlement,
)

PAY_TO = "0xAbC0000000000000000000000000000000000001"
USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
TX_HASH = "0x" + "ab" * 32
RPC = "https://sepolia.base.example/rpc"


@pytest.fixture(autouse=True)
def _clear_pay_to_cache():
    resolve_pay_to.cache_clear()
    yield
    resolve_pay_to.cache_clear()


def _topic_addr(addr: str) -> str:
    return "0x" + "0" * 24 + addr[2:].lower()


def _receipt(*, to=PAY_TO, amount=10000, status="0x1", address=USDC):
    return {
        "status": status,
        "logs": [
            {
                "address": address,
                "topics": [
                    settlement_mod._TRANSFER_TOPIC,
                    _topic_addr("0x00000000000000000000000000000000000000ff"),
                    _topic_addr(to),
                ],
                "data": "0x" + format(amount, "064x"),
            }
        ],
    }


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _mock_rpc(monkeypatch, receipt):
    def _post(url, json=None, timeout=None):  # noqa: A002
        return _FakeResp({"jsonrpc": "2.0", "id": 1, "result": receipt})

    monkeypatch.setattr(settlement_mod.httpx, "post", _post)


# --- tx hash extraction ------------------------------------------------------
def test_extract_raw_tx_hash():
    assert _extract_tx_hash(TX_HASH) == TX_HASH


def test_extract_tx_hash_from_json_proof():
    proof = json.dumps({"scheme": "exact", "settlement": {"txHash": TX_HASH}})
    assert _extract_tx_hash(proof) == TX_HASH


def test_extract_tx_hash_from_base64_proof():
    proof = base64.b64encode(json.dumps({"transactionHash": TX_HASH}).encode()).decode()
    assert _extract_tx_hash(proof) == TX_HASH


def test_extract_tx_hash_none_for_opaque_string():
    assert _extract_tx_hash("just-some-header") is None
    assert _extract_tx_hash("") is None


# --- USDC transfer matching --------------------------------------------------
def test_matches_usdc_transfer_positive():
    assert _matches_usdc_transfer(_receipt(), USDC, PAY_TO, 1000) is True


def test_transfer_to_wrong_address_fails():
    other = "0x00000000000000000000000000000000000000aa"
    assert _matches_usdc_transfer(_receipt(to=other), USDC, PAY_TO, 1000) is False


def test_transfer_below_amount_fails():
    assert _matches_usdc_transfer(_receipt(amount=500), USDC, PAY_TO, 1000) is False


def test_transfer_from_wrong_contract_fails():
    wrong = "0x1111111111111111111111111111111111111111"
    assert _matches_usdc_transfer(_receipt(address=wrong), USDC, PAY_TO, 1000) is False


# --- verify_settlement verdicts ---------------------------------------------
def test_verify_unverified_without_tx_hash(monkeypatch):
    v = verify_settlement(
        x_payment="opaque", pay_to=PAY_TO, usdc_contract=USDC, min_atomic=1000, rpc_url=RPC
    )
    assert v.status == "unverified" and "no settlement tx hash" in v.reason


def test_verify_unverified_without_rpc():
    v = verify_settlement(
        x_payment=TX_HASH, pay_to=PAY_TO, usdc_contract=USDC, min_atomic=1000, rpc_url=""
    )
    assert v.status == "unverified" and "no settlement RPC" in v.reason


def test_verify_verified_on_matching_receipt(monkeypatch):
    _mock_rpc(monkeypatch, _receipt())
    v = verify_settlement(
        x_payment=TX_HASH, pay_to=PAY_TO, usdc_contract=USDC, min_atomic=1000, rpc_url=RPC
    )
    assert v.verified and v.tx_hash == TX_HASH


def test_verify_unverified_on_reverted_tx(monkeypatch):
    _mock_rpc(monkeypatch, _receipt(status="0x0"))
    v = verify_settlement(
        x_payment=TX_HASH, pay_to=PAY_TO, usdc_contract=USDC, min_atomic=1000, rpc_url=RPC
    )
    assert v.status == "unverified" and "reverted" in v.reason


def test_verify_unverified_when_tx_not_found(monkeypatch):
    _mock_rpc(monkeypatch, None)
    v = verify_settlement(
        x_payment=TX_HASH, pay_to=PAY_TO, usdc_contract=USDC, min_atomic=1000, rpc_url=RPC
    )
    assert v.status == "unverified" and "not found" in v.reason


# --- full revenue path (the branch that books money) ------------------------
def _seed_signal(db):
    db.add(Signal(ticker="AAPL", sentiment="bullish", decision="BUY"))
    db.add(AgentState(id=1))
    db.commit()


def test_verified_payment_books_revenue(db, monkeypatch):
    monkeypatch.setattr(settings, "OUR_AWAL_WALLET_ADDRESS", PAY_TO)
    monkeypatch.setattr(settings, "SETTLEMENT_RPC_URL", RPC)
    monkeypatch.setattr(settings, "USDC_CONTRACT_ADDRESS", USDC)
    _mock_rpc(monkeypatch, _receipt())
    _seed_signal(db)

    client = TestClient(app)
    r = client.get("/api/alpha/AAPL/rationale", headers={"X-Payment": TX_HASH})
    assert r.status_code == 200
    body = r.json()
    assert body["payment_status"] == "verified"
    assert body["settled_usdc"] == 0.01
    assert body["settlement_tx"] == TX_HASH

    state = db.get(AgentState, 1)
    db.refresh(state)
    assert state.daily_revenue_usdc == pytest.approx(0.01)
    assert (state.daily_unverified_usdc or 0.0) == pytest.approx(0.0)


def test_unverified_payment_excluded_from_revenue(db, monkeypatch):
    monkeypatch.setattr(settings, "OUR_AWAL_WALLET_ADDRESS", PAY_TO)
    monkeypatch.setattr(settings, "SETTLEMENT_RPC_URL", RPC)
    monkeypatch.setattr(settings, "USDC_CONTRACT_ADDRESS", USDC)
    _mock_rpc(monkeypatch, _receipt(amount=1))  # transfer below invoiced amount
    _seed_signal(db)

    client = TestClient(app)
    r = client.get("/api/alpha/AAPL/rationale", headers={"X-Payment": TX_HASH})
    assert r.status_code == 200
    body = r.json()
    assert body["payment_status"] == "unverified"
    assert body["settled_usdc"] == 0.0

    state = db.get(AgentState, 1)
    db.refresh(state)
    assert state.daily_revenue_usdc == pytest.approx(0.0)
    assert state.daily_unverified_usdc == pytest.approx(0.01)


def test_non_demo_payment_unverified_without_rpc(db, monkeypatch):
    # SETTLEMENT_RPC_URL is "" via conftest — a real-looking proof cannot be
    # verified, so it must never book revenue.
    monkeypatch.setattr(settings, "OUR_AWAL_WALLET_ADDRESS", PAY_TO)
    _seed_signal(db)

    client = TestClient(app)
    r = client.get("/api/alpha/AAPL/rationale", headers={"X-Payment": TX_HASH})
    assert r.status_code == 200
    assert r.json()["payment_status"] == "unverified"

    state = db.get(AgentState, 1)
    db.refresh(state)
    assert state.daily_revenue_usdc == pytest.approx(0.0)
    assert state.daily_unverified_usdc == pytest.approx(0.01)


def test_verified_receipt_is_idempotent(db, monkeypatch):
    monkeypatch.setattr(settings, "OUR_AWAL_WALLET_ADDRESS", PAY_TO)
    monkeypatch.setattr(settings, "SETTLEMENT_RPC_URL", RPC)
    monkeypatch.setattr(settings, "USDC_CONTRACT_ADDRESS", USDC)
    _mock_rpc(monkeypatch, _receipt())
    _seed_signal(db)

    client = TestClient(app)
    for _ in range(3):
        r = client.get("/api/alpha/AAPL/rationale", headers={"X-Payment": TX_HASH})
        assert r.status_code == 200

    state = db.get(AgentState, 1)
    db.refresh(state)
    # Same (proof, signal) replayed thrice books revenue exactly once.
    assert state.daily_revenue_usdc == pytest.approx(0.01)


def test_paid_payload_carries_source_provenance(db, monkeypatch):
    monkeypatch.setattr(settings, "OUR_AWAL_WALLET_ADDRESS", PAY_TO)
    db.add(
        Signal(
            ticker="AAPL",
            sentiment="bullish",
            decision="BUY",
            source_snippet="AAPL closed 4% above its 50-day MA.",
            evidence_json=json.dumps(
                {"urls": [{"title": "yfinance snapshot", "url": "https://finance.yahoo.com/quote/AAPL", "score": None}]}
            ),
        )
    )
    db.add(AgentState(id=1))
    db.commit()

    client = TestClient(app)
    # Unpaid teaser: a 402 invoice with no sources.
    inv = client.get("/api/alpha/AAPL/rationale")
    assert inv.status_code == 402
    assert "sources" not in inv.json()

    # Paid payload: provenance surfaced.
    r = client.get("/api/alpha/AAPL/rationale", headers={"X-Payment": "demo-proof-1"})
    body = r.json()
    assert body["source_snippet"].startswith("AAPL closed")
    assert body["sources"] == [
        {"title": "yfinance snapshot", "url": "https://finance.yahoo.com/quote/AAPL", "score": None}
    ]
    # Quality gate: has evidence + leakage_ok => sellable.
    assert body["quality"]["sellable"] is True
    assert body["quality"]["checks"]["has_evidence"] is True


def test_demo_header_books_nothing_with_status(db, monkeypatch):
    monkeypatch.setattr(settings, "OUR_AWAL_WALLET_ADDRESS", PAY_TO)
    _seed_signal(db)

    client = TestClient(app)
    r = client.get("/api/alpha/AAPL/rationale", headers={"X-Payment": "demo-proof-1"})
    assert r.status_code == 200
    body = r.json()
    assert body["payment_status"] == "demo"
    assert body["demo_payment"] is True
    assert body["settled_usdc"] == 0.0

    state = db.get(AgentState, 1)
    db.refresh(state)
    assert state.daily_revenue_usdc == pytest.approx(0.0)
    assert (state.daily_unverified_usdc or 0.0) == pytest.approx(0.0)
