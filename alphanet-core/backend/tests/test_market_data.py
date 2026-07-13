"""Pure yfinance-derivation functions — fully offline."""
from __future__ import annotations

import pytest

from app.modules.market_data import (
    MarketDataError,
    build_events,
    compute_features,
    estimate_prior,
)


def _uptrend(n=140):
    return [100 + i * 0.5 for i in range(n)]


def _downtrend(n=140):
    return [170 - i * 0.5 for i in range(n)]


def test_uptrend_features():
    f = compute_features(_uptrend(), [1_000_000] * 140)
    assert f["pct_vs_ma50"] > 0
    assert f["momentum_6m"] > 0
    assert f["up_day_ratio"] == 1.0
    assert f["sessions"] == 140


def test_downtrend_features():
    f = compute_features(_downtrend())
    assert f["pct_vs_ma50"] < 0
    assert f["momentum_6m"] < 0
    assert f["up_day_ratio"] == 0.0


def test_short_series_rejected():
    with pytest.raises(MarketDataError):
        compute_features([101.0])


def test_volume_spike_ratio():
    vols = [1_000_000.0] * 139 + [3_000_000.0]
    f = compute_features(_uptrend(), vols)
    assert f["volume_ratio"] == pytest.approx(3.0)


def test_prior_is_shrunk_and_clipped():
    assert estimate_prior(0.5) == pytest.approx(0.5)
    assert estimate_prior(1.0) == 0.65  # clipped
    assert estimate_prior(0.0) == 0.35  # clipped
    assert estimate_prior(0.6) == pytest.approx(0.56)
    assert estimate_prior(0.6) > estimate_prior(0.4)


def test_events_carry_real_numbers_and_qvm_tokens():
    f = compute_features(_uptrend(), [1e6] * 140)
    events = build_events(
        "TEST",
        f,
        {
            "returnOnEquity": 0.32,
            "enterpriseValue": 1e12,
            "ebitda": 5e10,
            "priceToBook": 40.0,
            "trailingPE": 30.0,
            "heldPercentInstitutions": 0.657,
        },
    )
    assert len(events) == 2
    tech, fund = events
    assert "bullish" in tech["content"]
    assert str(f["last_close"]) in tech["content"]
    low = fund["content"].lower()
    assert "roe" in low and "ev/ebitda" in low and "book-to-market" in low
    assert all(e["source"] == "yfinance" for e in events)
    assert not any(e.get("demo") for e in events)


def test_bearish_trend_labeled_in_events():
    f = compute_features(_downtrend())
    events = build_events("TEST", f, None)
    assert len(events) == 1  # no fundamentals -> single technical event
    assert "bearish" in events[0]["content"]
