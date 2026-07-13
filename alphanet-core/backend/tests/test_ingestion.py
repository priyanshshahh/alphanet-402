"""Scout plumbing: mocked Tavily REST, budget caps, merging, demo labeling."""
from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import settings
from app.modules import ingestion
from app.modules.ingestion import (
    BudgetManager,
    EquityScout,
    ScoutResult,
    SpendLimitExceeded,
    _merge_results,
)


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class _FakeClient:
    """Stands in for httpx.Client(...) as a context manager."""

    response = _FakeResponse()
    raise_error = False

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, json=None):
        if _FakeClient.raise_error:
            raise httpx.ConnectError("no network in tests")
        return _FakeClient.response


@pytest.fixture(autouse=True)
def _mock_httpx(monkeypatch):
    _FakeClient.raise_error = False
    _FakeClient.response = _FakeResponse()
    monkeypatch.setattr(ingestion.httpx, "Client", _FakeClient)
    yield


# --- Tavily REST parsing --------------------------------------------------
def test_rest_search_normalizes_results(db):
    _FakeClient.response = _FakeResponse(
        200,
        {
            "results": [
                {"title": "A", "url": "https://x", "content": "AAPL upgrade", "score": 0.9},
                "not-a-dict",
            ]
        },
    )
    scout = EquityScout(db)
    r = scout._rest_search("AAPL", {"query": "q"})
    assert r.paid is True
    assert r.source == "tavily_rest"
    assert r.results == [
        {"title": "A", "url": "https://x", "content": "AAPL upgrade", "score": 0.9}
    ]
    assert json.loads(r.raw_text)[0]["title"] == "A"


def test_rest_search_http_error_status_is_unpaid(db):
    _FakeClient.response = _FakeResponse(429, text="rate limited")
    r = EquityScout(db)._rest_search("AAPL", {"query": "q"})
    assert r.paid is False and r.results == []


def test_rest_search_transport_error_is_unpaid(db):
    _FakeClient.raise_error = True
    r = EquityScout(db)._rest_search("AAPL", {"query": "q"})
    assert r.paid is False


# --- budget enforcement -----------------------------------------------------
def test_per_search_price_cap_enforced(db):
    with pytest.raises(SpendLimitExceeded):
        BudgetManager(db).assert_can_spend(settings.MAX_PRICE_PER_SEARCH_USDC * 2)


def test_daily_spend_cap_enforced(db):
    budget = BudgetManager(db)
    state = budget._state()
    state.daily_spend_usdc = settings.MAX_DAILY_SPEND_USDC
    db.commit()
    with pytest.raises(SpendLimitExceeded):
        budget.assert_can_spend(0.01)


def test_record_spend_accumulates_and_logs(db):
    from app.models import LogEvent

    budget = BudgetManager(db)
    budget.record_spend(0.01, "AAPL", "test spend")
    budget.record_spend(0.01, "AAPL", "test spend")
    assert budget.current_spend() == pytest.approx(0.02)
    spends = db.query(LogEvent).filter(LogEvent.level == "SPEND").all()
    assert len(spends) == 2 and spends[0].amount_usdc == -0.01


# --- merging ------------------------------------------------------------------
def _res(source, n=1, paid=True):
    return ScoutResult(
        ticker="AAPL",
        paid=paid,
        amount_usdc=0.0,
        results=[{"title": f"{source}-{i}", "url": "u", "content": "c"} for i in range(n)],
        raw_text="x",
        source=source,
    )


def test_merge_combines_market_data_and_news():
    merged = _merge_results(_res("yfinance", 2), _res("tavily_rest", 3))
    assert merged.source == "yfinance+tavily_rest"
    assert len(merged.results) == 5


def test_merge_keeps_base_when_news_failed():
    base = _res("yfinance", 2)
    assert _merge_results(base, _res("tavily_rest", 0, paid=False)) is base
    assert _merge_results(base, None) is base


def test_merge_uses_news_when_market_data_failed():
    news = _res("tavily_rest", 2)
    merged = _merge_results(_res("yfinance", 0, paid=False), news)
    assert merged is news


# --- scout orchestration ---------------------------------------------------
def test_scout_surfaces_market_data_failure_without_fake_fallback(db, monkeypatch):
    def _boom(ticker):
        raise ingestion.MarketDataError("offline")

    monkeypatch.setattr(ingestion, "fetch_equity_events", _boom)
    r = EquityScout(db).scout("AAPL")
    assert r.paid is False
    assert r.demo is False
    assert r.results == []


def test_scout_layers_tavily_news_on_yfinance(db, monkeypatch):
    monkeypatch.setattr(
        ingestion,
        "fetch_equity_events",
        lambda t: ([{"title": "tech", "url": "u", "content": "bullish"}], 0.55),
    )
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-real-key")
    _FakeClient.response = _FakeResponse(
        200, {"results": [{"title": "news", "url": "n", "content": "upgrade", "score": 0.8}]}
    )
    r = EquityScout(db).scout("AAPL")
    assert r.paid is True
    assert r.source == "yfinance+tavily_rest"
    assert r.market_prior == 0.55
    assert len(r.results) == 2
