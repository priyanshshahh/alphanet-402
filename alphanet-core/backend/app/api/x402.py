"""x402 seller surface: 402 invoices, on-chain settlement verification, and the
B2B rationale endpoints that resell each signal's causal chain for $0.01 USDC.

Also the single home of the payment plumbing (payTo resolution, invoice
construction, settlement booking) that the dashboard/judge-demo routers reuse.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from sqlalchemy import desc

from app.core.config import settings
from app.database import SessionLocal
from app.models import AgentState, LogEvent, Signal, X402Receipt, today_key
from app.modules.settlement import SettlementVerdict, verify_settlement

router = APIRouter(tags=["x402-seller"])

# Price of our own alpha endpoint: 1000 micro-USDC = $0.01
ALPHA_PRICE_ATOMIC = "1000"
ALPHA_PRICE_USDC = 0.01

_ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class PaymentConfigError(RuntimeError):
    """Raised when x402 selling is attempted without a configured payTo wallet."""


@lru_cache
def resolve_pay_to() -> str:
    """payTo address for our 402 invoices. Prefer the configured address,
    else ask the wallet enclave via `npx awal address`. Fails hard rather
    than ever falling back to the zero address."""
    configured = (settings.OUR_AWAL_WALLET_ADDRESS or "").strip()
    if configured and configured.lower() != _ZERO_ADDRESS:
        return configured
    try:
        proc = subprocess.run(
            ["npx", "awal", "address", "--json"],
            capture_output=True,
            text=True,
            timeout=settings.AWAL_ADDRESS_TIMEOUT_SECONDS,
        )
        if proc.returncode == 0:
            data = json.loads(proc.stdout.strip() or "{}")
            addr = data.get("evm") or data.get("address") or data.get("evmAddress")
            if addr and str(addr).lower() != _ZERO_ADDRESS:
                return str(addr)
    except Exception:
        pass
    raise PaymentConfigError(
        "No payTo wallet configured: set OUR_AWAL_WALLET_ADDRESS (or log in "
        "with `npx awal auth login`) before selling rationale over x402."
    )


def _payments_unavailable() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": (
                "x402 selling disabled: no payTo wallet configured. "
                "Set OUR_AWAL_WALLET_ADDRESS in the environment."
            )
        },
    )


def _invoice_payload() -> dict:
    return {
        "x402Version": 1,
        "accepts": [
            {
                "scheme": "exact",
                "network": settings.NETWORK_CAIP_ID,
                "maxAmountRequired": ALPHA_PRICE_ATOMIC,
                "asset": "USDC",
                "payTo": resolve_pay_to(),
            }
        ],
    }


def _receipt_key(x_payment: str, signal_id: int) -> str:
    raw = f"{x_payment}|{signal_id}".encode()
    return hashlib.sha256(raw).hexdigest()


def _is_demo_proof(x_payment: str) -> bool:
    return (x_payment or "").strip().lower().startswith("demo-")


def _payment_status(x_payment: str, verdict: Optional[SettlementVerdict]) -> str:
    if _is_demo_proof(x_payment):
        return "demo"
    return verdict.status if verdict else "unverified"


def _causal_payload(
    sig: Signal, x_payment: str, verdict: Optional[SettlementVerdict]
) -> dict:
    nlp = {}
    ev = {}
    try:
        nlp = json.loads(sig.nlp_features_json or "{}")
    except json.JSONDecodeError:
        pass
    try:
        ev = json.loads(sig.evidence_json or "{}")
    except json.JSONDecodeError:
        pass
    status = _payment_status(x_payment, verdict)
    # Provenance: the specific sources that fed THIS report, surfaced only in
    # the paid payload. Each is a checkable title/link (yfinance event or
    # Tavily result) so a buyer can audit the analysis, not just trust a number.
    sources = [
        {"title": u.get("title"), "url": u.get("url"), "score": u.get("score")}
        for u in (ev.get("urls") or [])
        if isinstance(u, dict) and u.get("url")
    ]
    return {
        "ticker": sig.ticker,
        "signal_id": sig.id,
        # settled_usdc is booked as revenue ONLY for a verified on-chain
        # settlement. Demo and unverified payments are served but count $0.
        "settled_usdc": ALPHA_PRICE_USDC if status == "verified" else 0.0,
        "payment_status": status,  # demo | verified | unverified
        "demo_payment": status == "demo",
        "settlement_tx": verdict.tx_hash if verdict else "",
        "settlement_note": verdict.reason if verdict else "",
        "network": settings.NETWORK_CAIP_ID,
        "payment_proof_prefix": (x_payment or "")[:64],
        "causal_chain": {
            "1_prior_market_price": sig.prior_price,
            "2_tavily_evidence": ev,
            "3_nlp_features": nlp,
            "4_whale_action": sig.whale_action,
            "5_bayesian_posterior": sig.posterior,
            "6_edge": sig.edge,
            "7_decision": sig.decision,
        },
        "source_snippet": sig.source_snippet or "",
        "sources": sources,
        "leakage_verified": sig.leakage_ok,
        "computed_at": sig.ts.isoformat() if sig.ts else None,
    }


def _verify_payment(x_payment: str) -> SettlementVerdict:
    """On-chain settlement check for a non-demo x402 proof."""
    try:
        pay_to = resolve_pay_to()
    except PaymentConfigError:
        pay_to = ""
    return verify_settlement(
        x_payment=x_payment,
        pay_to=pay_to,
        usdc_contract=settings.USDC_CONTRACT_ADDRESS,
        min_atomic=int(ALPHA_PRICE_ATOMIC),
        rpc_url=settings.SETTLEMENT_RPC_URL,
    )


def _settle_rationale_sale(db, sig: Signal, ticker: str, x_payment: str) -> dict:
    """Serve the causal chain; book revenue only for a *verified* settlement.

    Idempotent per (payment proof, signal) pair. Three outcomes:
      * demo      — x402 Lab header, served, never booked.
      * verified  — settlement confirmed on-chain, +$0.01 revenue.
      * unverified — served, recorded separately, excluded from revenue.
    """
    key = _receipt_key(x_payment, sig.id)
    existing = db.query(X402Receipt).filter(X402Receipt.receipt_key == key).first()
    if existing:
        try:
            return json.loads(existing.payload_json or "{}")
        except json.JSONDecodeError:
            pass

    demo = _is_demo_proof(x_payment)
    verdict = None if demo else _verify_payment(x_payment)
    body = _causal_payload(sig, x_payment, verdict)

    state = db.get(AgentState, 1)
    if state is not None and state.day_key != today_key():
        state.day_key = today_key()
        state.daily_revenue_usdc = 0.0
        state.daily_unverified_usdc = 0.0

    if demo:
        db.add(
            LogEvent(
                level="INFO",
                category="X402",
                ticker=ticker,
                message=(
                    f"Served rationale for signal #{sig.id} ({ticker}) against a "
                    "demo X-Payment header — no settlement, no revenue booked"
                ),
                amount_usdc=0.0,
            )
        )
        booked = 0.0
    elif verdict.verified:
        state.daily_revenue_usdc = float(state.daily_revenue_usdc) + ALPHA_PRICE_USDC
        db.add(
            LogEvent(
                level="REVENUE",
                category="X402",
                ticker=ticker,
                message=(
                    f"Sold alpha rationale for signal #{sig.id} ({ticker}) $0.01 "
                    f"— settlement verified (tx {verdict.tx_hash[:12]}…)"
                ),
                amount_usdc=ALPHA_PRICE_USDC,
            )
        )
        booked = ALPHA_PRICE_USDC
    else:
        state.daily_unverified_usdc = float(state.daily_unverified_usdc) + ALPHA_PRICE_USDC
        db.add(
            LogEvent(
                level="WARN",
                category="X402",
                ticker=ticker,
                message=(
                    f"Served rationale for signal #{sig.id} ({ticker}) against an "
                    f"UNVERIFIED payment — no revenue booked ({verdict.reason})"
                ),
                amount_usdc=0.0,
            )
        )
        booked = 0.0

    db.add(
        X402Receipt(
            receipt_key=key,
            signal_id=sig.id,
            ticker=ticker,
            amount_usdc=booked,
            payload_json=json.dumps(body),
        )
    )
    db.commit()
    return body


def _handle_rationale_request(x_payment, sig_lookup, not_found_msg):
    """Shared 402-invoice / settle flow for both rationale endpoints, differing
    only in how the target signal is looked up."""
    if not x_payment:
        try:
            invoice = _invoice_payload()
        except PaymentConfigError:
            return _payments_unavailable()
        return JSONResponse(
            status_code=402,
            content=invoice,
            headers={"Accept-Payment": "x402"},
        )

    db = SessionLocal()
    try:
        sig = sig_lookup(db)
        if sig is None:
            return JSONResponse(status_code=404, content={"error": not_found_msg})
        return _settle_rationale_sale(db, sig, sig.ticker, x_payment)
    finally:
        db.close()


@router.get("/api/alpha/{ticker}/rationale")
def alpha_rationale(
    ticker: str,
    x_payment: Optional[str] = Header(default=None, alias="X-Payment"),
):
    ticker = ticker.upper()
    return _handle_rationale_request(
        x_payment,
        lambda db: (
            db.query(Signal)
            .filter(Signal.ticker == ticker)
            .order_by(desc(Signal.ts))
            .first()
        ),
        f"No rationale computed yet for {ticker}",
    )


@router.get("/api/trade/{signal_id}/rationale")
def trade_rationale_by_id(
    signal_id: int,
    x_payment: Optional[str] = Header(default=None, alias="X-Payment"),
):
    """Blueprint alias: monetize rationale for a specific stored signal row."""
    return _handle_rationale_request(
        x_payment,
        lambda db: db.get(Signal, signal_id),
        f"No signal #{signal_id}",
    )


# ---------------------------------------------------------------------------
# x402 Bazaar-style discovery document (agent-discoverable seller metadata)
# ---------------------------------------------------------------------------
@router.get("/api/x402/discovery")
def x402_discovery():
    """Machine-readable discovery record so agents (and directories like
    Coinbase's x402 Bazaar / Agentic.Market) can find and price this seller
    without a human — resource, accepts terms, and I/O schema."""
    try:
        pay_to = resolve_pay_to()
    except PaymentConfigError:
        pay_to = ""
    return {
        "x402Version": 1,
        "resource": "/api/trade/{signal_id}/rationale",
        "type": "http",
        "accepts": [
            {
                "scheme": "exact",
                "network": settings.NETWORK_CAIP_ID,
                "maxAmountRequired": ALPHA_PRICE_ATOMIC,
                "asset": "USDC",
                "payTo": pay_to,
            }
        ],
        "metadata": {
            "name": "AlphaNet-402 equity rationale",
            "description": (
                "Bayesian causal chain (prior -> posterior -> edge) behind an "
                "equities signal, with source provenance. Research only; not "
                "investment advice."
            ),
            "input_schema": {
                "signal_id": "integer — stored signal row id (or use /api/alpha/{ticker}/rationale)",
                "headers": {"X-Payment": "x402 settlement proof (Base Sepolia USDC)"},
            },
            "output_schema": {
                "causal_chain": "object — prior, evidence, nlp_features, posterior, edge, decision",
                "sources": "array — {title, url, score} provenance",
                "payment_status": "demo | verified | unverified",
                "settled_usdc": "number — booked only on verified settlement",
            },
        },
        "lastUpdated": None,
    }
