"""x402 settlement verification (sell side).

Before booking revenue for a paid rationale sale, confirm the `X-Payment`
proof corresponds to a *real, settled* USDC transfer on-chain — rather than
trusting the header string, which was the repo's documented limitation #1.

Approach (testnet-honest, dependency-free):
  1. Extract a settlement transaction hash from the proof. Supported forms:
       * a raw ``0x``-prefixed 32-byte hex hash, or
       * a JSON object (optionally base64-encoded) carrying a ``txHash`` /
         ``transactionHash`` / ``tx`` field (what a CDP-style facilitator
         `settle` response, or our own consumer agent, returns).
  2. Look the receipt up over JSON-RPC (`eth_getTransactionReceipt`) against a
     Base Sepolia node, using httpx (already a dependency — no web3.py).
  3. Require: receipt status == success AND at least one ERC-20 ``Transfer``
     log emitted by the configured USDC contract, *to* our payTo address, for
     at least the invoiced amount.

Only a proof that clears all three is `verified`. Anything else is
`unverified` (served, but never counted as revenue). In a full production x402
deploy the tx hash is handed back by the facilitator's settle call; here we
read it straight off Base so the verification is genuine on testnet.
"""
from __future__ import annotations

import base64
import binascii
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

_log = logging.getLogger("alphanet.settlement")

# keccak256("Transfer(address,address,uint256)")
_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

_TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
_TX_HASH_KEYS = ("txHash", "transactionHash", "tx", "hash", "settlementTxHash")


@dataclass
class SettlementVerdict:
    status: str  # "verified" | "unverified"
    tx_hash: str = ""
    reason: str = ""

    @property
    def verified(self) -> bool:
        return self.status == "verified"


def _extract_tx_hash(x_payment: str) -> Optional[str]:
    """Pull a settlement tx hash out of an x402 payment proof, if present."""
    proof = (x_payment or "").strip()
    if not proof:
        return None
    if _TX_HASH_RE.match(proof):
        return proof

    # Try raw JSON, then base64-wrapped JSON (the canonical X-Payment encoding).
    candidates = [proof]
    try:
        candidates.append(base64.b64decode(proof, validate=False).decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, ValueError):
        pass

    for text in candidates:
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            continue
        found = _search_tx_hash(data)
        if found:
            return found
    return None


def _search_tx_hash(obj: object) -> Optional[str]:
    """Depth-limited search for a tx-hash-shaped value in a decoded proof."""
    if isinstance(obj, str):
        return obj if _TX_HASH_RE.match(obj) else None
    if isinstance(obj, dict):
        for key in _TX_HASH_KEYS:
            val = obj.get(key)
            if isinstance(val, str) and _TX_HASH_RE.match(val):
                return val
        for val in obj.values():
            found = _search_tx_hash(val)
            if found:
                return found
    elif isinstance(obj, list):
        for val in obj:
            found = _search_tx_hash(val)
            if found:
                return found
    return None


def _topic_is_address(topic: str, address: str) -> bool:
    """A 32-byte log topic left-pads a 20-byte address with zeros."""
    return topic[-40:].lower() == address[-40:].lower()


def _matches_usdc_transfer(
    receipt: dict, usdc_contract: str, pay_to: str, min_atomic: int
) -> bool:
    logs = receipt.get("logs") or []
    for entry in logs:
        if not isinstance(entry, dict):
            continue
        if (entry.get("address") or "").lower() != usdc_contract.lower():
            continue
        topics = entry.get("topics") or []
        if len(topics) < 3 or topics[0].lower() != _TRANSFER_TOPIC:
            continue
        if not _topic_is_address(topics[2], pay_to):
            continue
        try:
            value = int(entry.get("data") or "0x0", 16)
        except (TypeError, ValueError):
            continue
        if value >= min_atomic:
            return True
    return False


def verify_settlement(
    *,
    x_payment: str,
    pay_to: str,
    usdc_contract: str,
    min_atomic: int,
    rpc_url: str,
    timeout: float = 8.0,
) -> SettlementVerdict:
    """Verify an x402 payment proof settled on-chain. Never raises — an
    unreachable node or a malformed proof degrades to `unverified`."""
    tx_hash = _extract_tx_hash(x_payment)
    if not tx_hash:
        return SettlementVerdict("unverified", reason="no settlement tx hash in proof")
    if not (rpc_url or "").strip():
        return SettlementVerdict(
            "unverified", tx_hash=tx_hash, reason="no settlement RPC configured"
        )
    if not (pay_to or "").strip():
        return SettlementVerdict(
            "unverified", tx_hash=tx_hash, reason="no payTo address to verify against"
        )

    try:
        resp = httpx.post(
            rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        receipt = (resp.json() or {}).get("result")
    except (httpx.HTTPError, ValueError) as exc:
        _log.warning("Settlement RPC lookup failed for %s: %s", tx_hash, exc)
        return SettlementVerdict("unverified", tx_hash=tx_hash, reason=f"rpc error: {exc}")

    if not receipt:
        return SettlementVerdict(
            "unverified", tx_hash=tx_hash, reason="transaction not found / not mined"
        )
    if (receipt.get("status") or "").lower() not in ("0x1", "1"):
        return SettlementVerdict(
            "unverified", tx_hash=tx_hash, reason="transaction reverted (status != success)"
        )
    if not _matches_usdc_transfer(receipt, usdc_contract, pay_to, min_atomic):
        return SettlementVerdict(
            "unverified",
            tx_hash=tx_hash,
            reason="no USDC transfer to payTo for the invoiced amount",
        )
    return SettlementVerdict("verified", tx_hash=tx_hash, reason="usdc transfer confirmed")
