"""Scout module: real equities data first, paid news second, demo last.

Priority:
  1. yfinance (keyless, free) — real price/fundamental events. Always on
     unless DEMO_MODE is set.
  2. News layer on top: valid `TAVILY_API_KEY` → Tavily REST (plan credits);
     else `TRADING_MODE=LIVE` → `npx awal x402 pay` against Tavily's 402
     endpoint (USDC micropayment).
  3. `DEMO_MODE=1` only: deterministic synthetic snippets, every output
     labeled `"demo": true`. Never used as a silent fallback.
"""
from __future__ import annotations

import json
import random
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AgentState, LogEvent, today_key
from app.modules.market_data import MarketDataError, fetch_equity_events


class SpendLimitExceeded(Exception):
    """Raised when an x402 pay would push daily spend over the hard cap."""


@dataclass
class ScoutResult:
    ticker: str
    paid: bool  # True when the scout produced usable evidence
    amount_usdc: float
    results: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""
    tx_hash: str = ""
    source: str = "none"  # yfinance | tavily_rest | awal | demo (+ combinations)
    market_prior: Optional[float] = None  # real base-rate prior when available
    demo: bool = False  # True only for synthetic demo-mode data


class BudgetManager:
    """Single chokepoint that enforces MAX_DAILY_SPEND_USDC against the
    cumulative spend persisted in the database."""

    def __init__(self, db: Session):
        self.db = db

    def _state(self) -> AgentState:
        state = self.db.get(AgentState, 1)
        if state is None:
            state = AgentState(id=1, trading_mode=settings.TRADING_MODE)
            self.db.add(state)
            self.db.commit()
        if state.day_key != today_key():
            state.day_key = today_key()
            state.daily_spend_usdc = 0.0
            state.daily_revenue_usdc = 0.0
            state.daily_drawdown_usdc = 0.0
            self.db.commit()
        return state

    def current_spend(self) -> float:
        return float(self._state().daily_spend_usdc)

    def remaining(self) -> float:
        return max(0.0, settings.MAX_DAILY_SPEND_USDC - self.current_spend())

    def assert_can_spend(self, amount: float) -> None:
        current = self.current_spend()
        if current + amount > settings.MAX_DAILY_SPEND_USDC:
            raise SpendLimitExceeded(
                f"Daily spend cap hit: {current:.2f} + {amount:.2f} "
                f"> {settings.MAX_DAILY_SPEND_USDC:.2f} USDC"
            )
        if amount > settings.MAX_PRICE_PER_SEARCH_USDC:
            raise SpendLimitExceeded(
                f"Per-search price {amount:.2f} exceeds cap "
                f"{settings.MAX_PRICE_PER_SEARCH_USDC:.2f} USDC"
            )

    def record_spend(self, amount: float, ticker: str, message: str) -> None:
        state = self._state()
        state.daily_spend_usdc = float(state.daily_spend_usdc) + amount
        self.db.add(
            LogEvent(
                level="SPEND",
                category="X402",
                ticker=ticker,
                message=message,
                amount_usdc=-abs(amount),
            )
        )
        self.db.commit()


def _tavily_rest_key_ok() -> bool:
    k = (settings.TAVILY_API_KEY or "").strip()
    return bool(k) and not k.lower().startswith("your_")


class EquityScout:
    """Equities scout: yfinance (real, free) + optional Tavily news layer.

    DEMO_MODE short-circuits everything with labeled synthetic data.
    """

    def __init__(self, db: Session):
        self.db = db
        self.budget = BudgetManager(db)

    @staticmethod
    def _build_payload(ticker: str) -> Dict[str, Any]:
        return {
            "query": (
                "institutional ownership changes, insider transactions, and "
                f"analyst actions for {ticker} stock"
            ),
            "search_depth": "advanced",
        }

    def scout(self, ticker: str) -> ScoutResult:
        if settings.DEMO_MODE:
            return self._demo_search(ticker)

        result = self._market_data_scout(ticker)
        news = self._news_scout(ticker)
        return _merge_results(result, news)

    # -- real, keyless -----------------------------------------------------
    def _market_data_scout(self, ticker: str) -> ScoutResult:
        try:
            events, prior = fetch_equity_events(ticker)
        except MarketDataError as exc:
            self._log_error(ticker, f"yfinance scout failed: {exc}", category="SCOUT")
            return ScoutResult(ticker, paid=False, amount_usdc=0.0, source="yfinance")
        return ScoutResult(
            ticker=ticker,
            paid=True,
            amount_usdc=0.0,
            results=events,
            raw_text=json.dumps(events)[:4000],
            source="yfinance",
            market_prior=prior,
        )

    # -- paid news layer (optional) ------------------------------------------
    def _news_scout(self, ticker: str) -> Optional[ScoutResult]:
        payload = self._build_payload(ticker)

        if _tavily_rest_key_ok():
            result = self._rest_search(ticker, payload)
            if result.paid:
                self.db.add(
                    LogEvent(
                        level="INFO",
                        category="TAVILY",
                        ticker=ticker,
                        message="Tavily REST news — API credits, no USDC spend",
                        amount_usdc=0.0,
                    )
                )
                self.db.commit()
            return result

        if settings.is_live:
            price = settings.MAX_PRICE_PER_SEARCH_USDC
            self.budget.assert_can_spend(price)
            result = self._live_pay(ticker, payload, price)
            if result.paid:
                self.budget.record_spend(
                    result.amount_usdc,
                    ticker,
                    f"Tavily x402 news for {ticker} ({result.source})",
                )
            return result

        return None

    def _rest_search(self, ticker: str, payload: Dict[str, Any]) -> ScoutResult:
        body = {
            "api_key": settings.TAVILY_API_KEY.strip(),
            "query": payload["query"],
            "search_depth": payload.get("search_depth", "advanced"),
            "max_results": 5,
            "include_answer": False,
            "topic": "finance",
        }
        try:
            with httpx.Client(timeout=settings.SCOUT_HTTP_TIMEOUT_SECONDS) as client:
                r = client.post(settings.TAVILY_REST_ENDPOINT, json=body)
            if r.status_code != 200:
                self._log_error(
                    ticker,
                    f"Tavily REST {r.status_code}: {(r.text or '')[:400]}",
                    category="TAVILY",
                )
                return ScoutResult(ticker, paid=False, amount_usdc=0.0, source="tavily_rest")
            data = r.json()
            results = data.get("results") if isinstance(data.get("results"), list) else []
            norm: List[Dict[str, Any]] = []
            for row in results:
                if not isinstance(row, dict):
                    continue
                norm.append(
                    {
                        "title": row.get("title", ""),
                        "url": row.get("url", ""),
                        "content": row.get("content", ""),
                        "score": row.get("score"),
                    }
                )
            return ScoutResult(
                ticker=ticker,
                paid=True,
                amount_usdc=0.0,
                results=norm,
                raw_text=json.dumps(norm)[:4000],
                tx_hash="",
                source="tavily_rest",
            )
        except httpx.HTTPError as exc:
            self._log_error(ticker, f"Tavily REST HTTP error: {exc}", category="TAVILY")
            return ScoutResult(ticker, paid=False, amount_usdc=0.0, source="tavily_rest")

    def _live_pay(
        self, ticker: str, payload: Dict[str, Any], price: float
    ) -> ScoutResult:
        max_amount_atomic = str(int(round(price * 1_000_000)))
        cmd = [
            "npx",
            "awal",
            "x402",
            "pay",
            settings.TAVILY_402_ENDPOINT,
            "-X",
            "POST",
            "-d",
            json.dumps(payload),
            "--max-amount",
            max_amount_atomic,
            "--json",
        ]
        extra = (settings.AWAL_X402_PAY_EXTRA or "").strip()
        if extra:
            cmd.extend(shlex.split(extra))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.AWAL_PAY_TIMEOUT_SECONDS,
            )
            if proc.returncode != 0:
                self._log_error(
                    ticker,
                    f"awal pay rc={proc.returncode}: {proc.stderr[:300]}",
                    category="X402",
                )
                return ScoutResult(ticker, paid=False, amount_usdc=0.0, source="awal")
            data = self._safe_json(proc.stdout)
            results = self._extract_results(data)
            return ScoutResult(
                ticker=ticker,
                paid=True,
                amount_usdc=price,
                results=results,
                raw_text=json.dumps(results)[:4000],
                tx_hash=str(data.get("txHash") or data.get("transactionHash") or ""),
                source="awal",
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            self._log_error(ticker, f"awal subprocess failed: {exc}", category="X402")
            return ScoutResult(ticker, paid=False, amount_usdc=0.0, source="awal")

    # -- demo mode only ------------------------------------------------------
    def _demo_search(self, ticker: str) -> ScoutResult:
        """Synthetic headlines for offline demos. Every record is labeled
        `"demo": true` and no spend or revenue is ever booked for it."""
        rng = random.Random(f"{ticker}-{today_key()}-{random.random()}")
        headlines = [
            f"Two institutional desks reported accumulating {ticker} last week",
            f"Fund filings show {ticker} positions trimmed into strength",
            f"Options desks flag unusual bullish flow in {ticker}",
            f"Analysts split on {ticker} after a volatile session",
            f"Insider Form 4 filings show routine {ticker} activity",
        ]
        bias = rng.choice(["bullish", "bearish"])
        snippet = rng.choice(headlines)
        results = [
            {
                "title": f"[DEMO] Synthetic headline: {ticker}",
                "url": "about:demo",
                "content": (
                    f"[DEMO — synthetic data, not a real headline] {snippet}. "
                    f"Sentiment leans {bias}."
                ),
                "score": round(rng.uniform(0.6, 0.95), 2),
                "demo": True,
            }
        ]
        self.db.add(
            LogEvent(
                level="INFO",
                category="SCOUT",
                ticker=ticker,
                message=f"DEMO MODE: synthetic scout data for {ticker} (no spend)",
                amount_usdc=0.0,
            )
        )
        self.db.commit()
        return ScoutResult(
            ticker=ticker,
            paid=True,
            amount_usdc=0.0,
            results=results,
            raw_text=json.dumps(results),
            tx_hash="",
            source="demo",
            demo=True,
        )

    @staticmethod
    def _safe_json(text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
        return {}

    @staticmethod
    def _extract_results(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        body = data.get("body") if isinstance(data.get("body"), dict) else data
        results = body.get("results") if isinstance(body, dict) else None
        return results if isinstance(results, list) else []

    def _log_error(self, ticker: str, message: str, category: str = "X402") -> None:
        self.db.add(
            LogEvent(level="ERROR", category=category, ticker=ticker, message=message)
        )
        self.db.commit()


def _merge_results(base: ScoutResult, extra: Optional[ScoutResult]) -> ScoutResult:
    """Fold an optional news result into the market-data result."""
    if extra is None or not extra.paid or not extra.results:
        return base
    if not base.paid:
        return extra
    base.results = list(base.results) + list(extra.results)
    base.raw_text = json.dumps(base.results)[:4000]
    base.source = f"{base.source}+{extra.source}"
    base.amount_usdc += extra.amount_usdc
    base.tx_hash = base.tx_hash or extra.tx_hash
    return base
