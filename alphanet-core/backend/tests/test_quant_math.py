"""Bayesian update math, leakage guards, and the heuristic NLP parser."""
from __future__ import annotations

import datetime as dt
import math

import pytest

from app.modules.ingestion import ScoutResult
from app.modules.quant_pipeline import (
    _LOG_LIKELIHOOD,
    LeakageError,
    _heuristic_extract,
    bayesian_update,
    calculate_chf_leakage_safe_edge,
    run_quant,
    verify_no_leakage,
)

NOW = dt.datetime.now(dt.timezone.utc)


def _scout(text="AAPL rallied.", results=None, **kw):
    results = (
        results
        if results is not None
        else [{"title": "t", "url": "u", "content": text, "score": 0.9}]
    )
    return ScoutResult(
        ticker="AAPL",
        paid=True,
        amount_usdc=0.0,
        results=results,
        raw_text=text,
        source="yfinance",
        **kw,
    )


# --- bayesian_update (sentiment channel) -----------------------------------
def test_bullish_sentiment_raises_posterior():
    assert bayesian_update(0.5, "bullish", 0.8) > 0.5


def test_bearish_sentiment_lowers_posterior():
    assert bayesian_update(0.5, "bearish", 0.8) < 0.5


def test_neutral_sentiment_keeps_prior():
    assert bayesian_update(0.5, "neutral", 0.9) == pytest.approx(0.5)


def test_zero_confidence_is_a_noop():
    assert bayesian_update(0.42, "bullish", 0.0) == pytest.approx(0.42)


def test_posterior_stays_in_open_unit_interval():
    assert 0.0 < bayesian_update(0.999999, "bullish", 1.0) < 1.0
    assert 0.0 < bayesian_update(0.000001, "bearish", 1.0) < 1.0


def test_update_matches_log_odds_formula():
    prior, conf = 0.6, 0.7
    expected = 1 / (1 + math.exp(-(math.log(prior / (1 - prior)) + 2.2 * conf)))
    assert bayesian_update(prior, "bullish", conf) == pytest.approx(expected)


# --- evidence-weight log-odds table ------------------------------------------
def test_ceo_buy_weight_applied_exactly():
    post, edge, ll = calculate_chf_leakage_safe_edge(
        0.5, {"has_recent_ceo_buying": True}
    )
    assert ll == pytest.approx(_LOG_LIKELIHOOD["ceo_buy"])
    assert post == pytest.approx(1 / (1 + math.exp(-_LOG_LIKELIHOOD["ceo_buy"])))
    assert edge == pytest.approx(post - 0.5)


def test_regulatory_risk_pushes_down():
    post, edge, _ = calculate_chf_leakage_safe_edge(
        0.5, {"regulatory_risk_mentioned": True}
    )
    assert post < 0.5 and edge < 0


def test_institutional_trend_is_symmetric():
    up, _, _ = calculate_chf_leakage_safe_edge(
        0.5, {"institutional_accumulation_trend": "bullish"}
    )
    down, _, _ = calculate_chf_leakage_safe_edge(
        0.5, {"institutional_accumulation_trend": "bearish"}
    )
    assert up - 0.5 == pytest.approx(0.5 - down, abs=1e-9)


def test_qvm_quality_needs_two_metrics():
    _, _, ll_one = calculate_chf_leakage_safe_edge(0.5, {"qvm_metrics_mentioned": ["roe"]})
    _, _, ll_two = calculate_chf_leakage_safe_edge(
        0.5, {"qvm_metrics_mentioned": ["roe", "ev_ebit"]}
    )
    assert ll_one == 0.0
    assert ll_two == pytest.approx(_LOG_LIKELIHOOD["qvm_quality"])


def test_no_evidence_means_no_edge():
    post, edge, ll = calculate_chf_leakage_safe_edge(0.55, {})
    assert post == pytest.approx(0.55) and edge == pytest.approx(0.0) and ll == 0.0


# --- leakage guards -----------------------------------------------------------
def test_leakage_ok_for_clean_evidence():
    assert verify_no_leakage(
        prior_captured_at=NOW, scout=_scout(), decision_at=NOW + dt.timedelta(seconds=1)
    )


def test_leakage_rejects_lookahead_prior():
    with pytest.raises(LeakageError):
        verify_no_leakage(
            prior_captured_at=NOW + dt.timedelta(minutes=5),
            scout=_scout(),
            decision_at=NOW,
        )


def test_leakage_rejects_empty_evidence():
    empty = ScoutResult(ticker="AAPL", paid=True, amount_usdc=0.0)
    with pytest.raises(LeakageError):
        verify_no_leakage(prior_captured_at=NOW, scout=empty, decision_at=NOW)


def test_leakage_rejects_future_year_reference():
    text = f"Guidance for {NOW.year + 1} looks strong"
    with pytest.raises(LeakageError):
        verify_no_leakage(prior_captured_at=NOW, scout=_scout(text), decision_at=NOW)


# --- heuristic parser (keyless path) ------------------------------------------
def test_heuristic_reads_bullish_equities_language():
    out = _heuristic_extract(
        "Technical read: bullish. AAPL closed 4.0% above its 50-day moving average."
    )
    assert out["sentiment"] == "bullish" and out["confidence"] > 0.4


def test_heuristic_reads_bearish_equities_language():
    out = _heuristic_extract(
        "Technical read: bearish. MSFT slid below its 50-day moving average after a downgrade."
    )
    assert out["sentiment"] == "bearish"


def test_heuristic_detects_qvm_metrics():
    out = _heuristic_extract("Fundamentals: ROE 32.0%, EV/EBITDA 20.1, 6-month momentum +5%.")
    assert {"roe", "ev_ebit", "momentum_6m"} <= set(out["qvm_metrics_mentioned"])


def test_heuristic_static_ownership_is_not_a_trend():
    out = _heuristic_extract("Fundamentals for AAPL: institutional ownership 65.7%.")
    assert out["institutional_accumulation_trend"] == "neutral"


def test_coerce_rejects_garbage_values():
    out = _heuristic_extract("")
    assert out["sentiment"] == "neutral"
    assert 0.0 <= out["confidence"] <= 1.0
    assert out["qvm_metrics_mentioned"] == []


# --- run_quant ------------------------------------------------------------------
def test_run_quant_uses_real_market_prior():
    sig = run_quant(_scout("Technical read: neutral.", market_prior=0.61))
    assert sig.prior == pytest.approx(0.61, abs=1e-3)


def test_run_quant_hold_when_no_edge():
    sig = run_quant(_scout("Nothing notable happened today.", market_prior=0.5))
    assert sig.decision == "HOLD"
