"""The Oracle — read-only Polymarket market data via public APIs.

Uses two free public APIs:
  - Gamma API (https://gamma-api.polymarket.com) for market discovery.
  - CLOB API  (https://clob.polymarket.com) for live prices & order books.

No auth required for any of this. We capture a `MarketSnapshot` per
outcome on each poll so trades can be reconstructed from the audit log.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx

from ..config import settings
from ..database import session_scope
from ..models import MarketSnapshot

log = logging.getLogger("oracle")

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


@dataclass
class Outcome:
    name: str            # "Yes" / "No" / specific outcome
    token_id: str        # CLOB token id
    price: float         # mid / last
    best_bid: float
    best_ask: float


@dataclass
class Market:
    condition_id: str
    slug: str
    question: str
    end_date: Optional[str]
    volume_24h: float
    liquidity: float
    outcomes: List[Outcome]


def _safe_loads(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    try:
        return json.loads(v)
    except Exception:
        return []


async def _discover_markets(client: httpx.AsyncClient) -> List[dict]:
    """List active, tradable crypto-relevant markets from Gamma."""
    if settings.watch_list:
        # explicit override
        out: List[dict] = []
        for cid in settings.watch_list:
            try:
                r = await client.get(
                    f"{GAMMA}/markets",
                    params={"condition_ids": cid, "limit": 1},
                    timeout=15.0,
                )
                r.raise_for_status()
                arr = r.json()
                if isinstance(arr, list) and arr:
                    out.extend(arr)
            except Exception as e:
                log.warning("Failed to load watch market %s: %s", cid, e)
        return out

    try:
        r = await client.get(
            f"{GAMMA}/markets",
            params={
                "active": "true",
                "closed": "false",
                "limit": 100,
                "order": "volume24hr",
                "ascending": "false",
            },
            timeout=20.0,
        )
        r.raise_for_status()
        markets = r.json()
        if not isinstance(markets, list):
            return []
    except Exception as e:
        log.warning("Gamma /markets failed: %s", e)
        return []

    kws = settings.keyword_list
    if not kws:
        return markets[: settings.max_markets]

    relevant: List[dict] = []
    for m in markets:
        blob = " ".join(
            str(m.get(k, "") or "") for k in ("question", "slug", "category", "description")
        ).lower()
        if any(k in blob for k in kws):
            relevant.append(m)
        if len(relevant) >= settings.max_markets:
            break
    return relevant


async def _book_price(client: httpx.AsyncClient, token_id: str) -> dict:
    """Return {price, best_bid, best_ask} for a CLOB token id."""
    out = {"price": 0.5, "best_bid": 0.0, "best_ask": 1.0}
    if not token_id:
        return out
    try:
        # midpoint is the cleanest single number
        rm = await client.get(f"{CLOB}/midpoint", params={"token_id": token_id}, timeout=10.0)
        if rm.status_code == 200:
            out["price"] = float(rm.json().get("mid", out["price"]))
    except Exception as e:
        log.debug("midpoint failed for %s: %s", token_id, e)

    try:
        rbid = await client.get(
            f"{CLOB}/price", params={"token_id": token_id, "side": "BUY"}, timeout=10.0
        )
        if rbid.status_code == 200:
            out["best_bid"] = float(rbid.json().get("price", out["best_bid"]))
        rask = await client.get(
            f"{CLOB}/price", params={"token_id": token_id, "side": "SELL"}, timeout=10.0
        )
        if rask.status_code == 200:
            out["best_ask"] = float(rask.json().get("price", out["best_ask"]))
    except Exception as e:
        log.debug("price failed for %s: %s", token_id, e)
    return out


async def fetch_markets() -> List[Market]:
    async with httpx.AsyncClient() as client:
        raw = await _discover_markets(client)
        results: List[Market] = []
        for m in raw:
            outcomes_names = _safe_loads(m.get("outcomes"))
            token_ids = _safe_loads(m.get("clobTokenIds"))
            if not token_ids or len(token_ids) != len(outcomes_names):
                continue
            outs: List[Outcome] = []
            for name, tid in zip(outcomes_names, token_ids):
                p = await _book_price(client, str(tid))
                outs.append(
                    Outcome(
                        name=str(name),
                        token_id=str(tid),
                        price=p["price"],
                        best_bid=p["best_bid"],
                        best_ask=p["best_ask"],
                    )
                )
            if not outs:
                continue
            results.append(
                Market(
                    condition_id=str(m.get("conditionId", "")),
                    slug=str(m.get("slug", "")),
                    question=str(m.get("question", ""))[:1024],
                    end_date=str(m.get("endDateIso") or m.get("endDate") or ""),
                    volume_24h=float(m.get("volume24hr") or 0),
                    liquidity=float(m.get("liquidityNum") or 0),
                    outcomes=outs,
                )
            )
    return results


def persist_snapshot(markets: List[Market]) -> List[MarketSnapshot]:
    """Persist a snapshot per outcome. Returns inserted rows."""
    saved: List[MarketSnapshot] = []
    with session_scope() as s:
        for m in markets:
            for o in m.outcomes:
                row = MarketSnapshot(
                    condition_id=m.condition_id,
                    slug=m.slug,
                    question=m.question,
                    outcome=o.name,
                    token_id=o.token_id,
                    price=o.price,
                    best_bid=o.best_bid,
                    best_ask=o.best_ask,
                    liquidity=m.liquidity,
                    volume_24h=m.volume_24h,
                )
                s.add(row)
                s.flush()
                saved.append(row)
        s.expunge_all()
    return saved
