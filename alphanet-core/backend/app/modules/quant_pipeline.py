"""Quant engine.

Responsibilities:
  1. LLM parsing — Groq turns Tavily text into strict JSON (sentiment and structured
     boolean/trend features). The LLM never performs portfolio math.
  2. Pure math — Bayesian log-odds update with leakage-aware edge calculation.
  3. Leakage guard — verify_no_leakage() rejects forward-looking evidence.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.modules.ingestion import ScoutResult


@dataclass
class QuantSignal:
    ticker: str
    sentiment: str
    confidence: float
    whale_action: str
    prior: float
    posterior: float
    edge: float
    decision: str
    leakage_ok: bool
    source_snippet: str
    nlp_features: Dict[str, Any] = field(default_factory=dict)
    log_likelihood_sum: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)


class LeakageError(Exception):
    """Raised when forward-looking data would contaminate a decision."""


# Log-likelihood weights log Λ(E) for evidence features → log-odds update.
_LOG_LIKELIHOOD: Dict[str, float] = {
    "ceo_buy": 0.45,
    "inst_bull": 0.22,
    "inst_bear": -0.22,
    "reg_risk": -0.60,
    "insider_sell_spike": -0.35,
    "qvm_quality": 0.08,
}


_SYSTEM_PROMPT = (
    "You extract structured features from whale/institutional market research. "
    "Respond with STRICT minified JSON ONLY, no prose, keys exactly:\n"
    '{"sentiment":"bullish|bearish|neutral","confidence":0.0,'
    '"whale_action":"short phrase",'
    '"has_recent_ceo_buying":true|false,'
    '"institutional_accumulation_trend":"bullish|bearish|neutral",'
    '"regulatory_risk_mentioned":true|false,'
    '"insider_selling_spikes":true|false,'
    '"qvm_metrics_mentioned":["roe","roic","ev_ebit","book_to_market","momentum_6m"]}\n'
    "Use false/neutral/empty array when unknown. confidence in [0,1]. "
    "Never compute probabilities, prices, or portfolio math — extraction only."
)


def parse_sentiment(scout: ScoutResult) -> Dict[str, Any]:
    """Structured NLP features from Groq, else deterministic heuristic."""
    text = _flatten_results(scout.results) or scout.raw_text
    if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("your_"):
        parsed = _groq_extract(text)
        if parsed is not None:
            return parsed
    return _heuristic_extract(text)


def _flatten_results(results: List[Dict[str, Any]]) -> str:
    chunks = []
    for r in results or []:
        chunks.append(str(r.get("title", "")))
        chunks.append(str(r.get("content", "")))
        chunks.append(str(r.get("url", "")))
    return "\n".join(c for c in chunks if c).strip()


def _groq_extract(text: str) -> Optional[Dict[str, Any]]:
    try:
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)
        resp = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text[:6000]},
            ],
        )
        raw = resp.choices[0].message.content or "{}"
        return _coerce_extended(json.loads(raw))
    except Exception:
        return None


def _heuristic_extract(text: str) -> Dict[str, Any]:
    t = (text or "").lower()
    bull = len(re.findall(r"accumulat|inflow|outflow to cold|bullish|buy|long|ceo buy", t))
    bear = len(
        re.findall(r"distribut|de-risk|bearish|sell|rotated into stable|dump|sec charge|lawsuit", t)
    )
    if bull == bear:
        sentiment, conf = "neutral", 0.4
    elif bull > bear:
        sentiment, conf = "bullish", min(0.95, 0.5 + 0.1 * (bull - bear))
    else:
        sentiment, conf = "bearish", min(0.95, 0.5 + 0.1 * (bear - bull))

    action = text.split(".")[0][:160] if text else "no clear whale action"
    ceo_buy = bool(re.search(r"ceo|cfo|officer.*buy|insider buy", t))
    inst = "neutral"
    if re.search(r"13f|institution|fund|accumulation|whale inflow", t):
        inst = "bullish" if bull >= bear else "bearish"
    reg = bool(re.search(r"sec investigat|subpoena|lawsuit|sanction|regulatory risk|ofac", t))
    insider_sell = bool(re.search(r"insider sell|form 4 sell|officer sold", t))
    qvm = []
    for token, label in (
        ("roe", "roe"),
        ("roic", "roic"),
        ("ev/ebit", "ev_ebit"),
        ("book-to-market", "book_to_market"),
        ("6-month", "momentum_6m"),
    ):
        if token in t:
            qvm.append(label)

    return _coerce_extended(
        {
            "sentiment": sentiment,
            "confidence": round(conf, 2),
            "whale_action": action,
            "has_recent_ceo_buying": ceo_buy,
            "institutional_accumulation_trend": inst,
            "regulatory_risk_mentioned": reg,
            "insider_selling_spikes": insider_sell,
            "qvm_metrics_mentioned": qvm,
        }
    )


def _coerce_extended(d: Dict[str, Any]) -> Dict[str, Any]:
    sentiment = str(d.get("sentiment", "neutral")).lower()
    if sentiment not in {"bullish", "bearish", "neutral"}:
        sentiment = "neutral"
    try:
        confidence = max(0.0, min(1.0, float(d.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0

    inst = str(d.get("institutional_accumulation_trend", "neutral")).lower()
    if inst not in {"bullish", "bearish", "neutral"}:
        inst = "neutral"

    qvm = d.get("qvm_metrics_mentioned")
    if not isinstance(qvm, list):
        qvm = []

    return {
        "sentiment": sentiment,
        "confidence": confidence,
        "whale_action": str(d.get("whale_action", ""))[:200],
        "has_recent_ceo_buying": bool(d.get("has_recent_ceo_buying")),
        "institutional_accumulation_trend": inst,
        "regulatory_risk_mentioned": bool(d.get("regulatory_risk_mentioned")),
        "insider_selling_spikes": bool(d.get("insider_selling_spikes")),
        "qvm_metrics_mentioned": [str(x) for x in qvm][:12],
    }


def _clip(p: float, lo: float = 1e-4, hi: float = 1 - 1e-4) -> float:
    return max(lo, min(hi, p))


def calculate_chf_leakage_safe_edge(
    market_prior: float, institutional_signals: Dict[str, Any]
) -> tuple[float, float, float]:
    """Bayesian log-odds update from configured evidence weights.

    Returns (posterior_probability, edge_vs_prior, sum_log_likelihood).
    """
    p0 = _clip(float(market_prior))
    log_odds = math.log(p0 / (1.0 - p0))
    ll_sum = 0.0

    if institutional_signals.get("has_recent_ceo_buying"):
        ll_sum += _LOG_LIKELIHOOD["ceo_buy"]

    it = institutional_signals.get("institutional_accumulation_trend", "neutral")
    if it == "bullish":
        ll_sum += _LOG_LIKELIHOOD["inst_bull"]
    elif it == "bearish":
        ll_sum += _LOG_LIKELIHOOD["inst_bear"]

    if institutional_signals.get("regulatory_risk_mentioned"):
        ll_sum += _LOG_LIKELIHOOD["reg_risk"]

    if institutional_signals.get("insider_selling_spikes"):
        ll_sum += _LOG_LIKELIHOOD["insider_sell_spike"]

    qvm = institutional_signals.get("qvm_metrics_mentioned") or []
    if isinstance(qvm, list) and len(qvm) >= 2:
        ll_sum += _LOG_LIKELIHOOD["qvm_quality"]

    post_log_odds = log_odds + ll_sum
    posterior = _clip(1.0 / (1.0 + math.exp(-post_log_odds)))
    edge = posterior - p0
    return posterior, edge, ll_sum


def bayesian_update(prior: float, sentiment: str, confidence: float) -> float:
    """Legacy sentiment-only log-odds bump (used as fallback tie-break)."""
    prior = _clip(prior)
    prior_log_odds = math.log(prior / (1 - prior))
    strength = 2.2 * confidence
    if sentiment == "bullish":
        llr = strength
    elif sentiment == "bearish":
        llr = -strength
    else:
        llr = 0.0
    posterior_log_odds = prior_log_odds + llr
    posterior = 1 / (1 + math.exp(-posterior_log_odds))
    return _clip(posterior)


def verify_no_leakage(
    *, prior_captured_at: dt.datetime, scout: ScoutResult, decision_at: dt.datetime
) -> bool:
    """Reject look-ahead / empty evidence."""
    if prior_captured_at > decision_at:
        raise LeakageError("Prior captured after decision time (look-ahead).")

    if not scout.results and not scout.raw_text:
        raise LeakageError("No evidence available; refusing to act on a vacuum.")

    future_year = decision_at.year + 1
    if re.search(rf"\b{future_year}\b", scout.raw_text or ""):
        raise LeakageError("Evidence references a future year (look-ahead).")

    return True


def get_market_prior(ticker: str) -> float:
    """Pseudo market-implied prior near 0.5 (replace with live Polymarket feed)."""
    seed = sum(ord(c) for c in ticker)
    drift = ((seed % 21) - 10) / 200.0
    return _clip(0.5 + drift)


def _evidence_bundle(scout: ScoutResult) -> Dict[str, Any]:
    out: Dict[str, Any] = {"mode": scout.source, "tx_hash": scout.tx_hash, "urls": []}
    for r in scout.results or []:
        out["urls"].append(
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "score": r.get("score"),
            }
        )
    return out


def run_quant(scout: ScoutResult) -> QuantSignal:
    prior_captured_at = dt.datetime.now(dt.timezone.utc)
    prior = get_market_prior(scout.ticker)

    parsed = parse_sentiment(scout)
    feat_subset = {k: parsed[k] for k in parsed if k != "whale_action"}

    posterior_tbl, edge_tbl, ll_sum = calculate_chf_leakage_safe_edge(prior, feat_subset)
    # Blend: table-driven posterior slightly mixed with sentiment channel for demo stability.
    posterior_sent = bayesian_update(prior, parsed["sentiment"], parsed["confidence"])
    posterior = _clip(0.65 * posterior_tbl + 0.35 * posterior_sent)
    edge = posterior - prior

    decision_at = dt.datetime.now(dt.timezone.utc)
    leakage_ok = True
    try:
        verify_no_leakage(
            prior_captured_at=prior_captured_at, scout=scout, decision_at=decision_at
        )
    except LeakageError:
        leakage_ok = False

    if not leakage_ok:
        decision = "HOLD"
    elif edge >= settings.EDGE_THRESHOLD:
        decision = "BUY"
    elif edge <= -settings.EDGE_THRESHOLD:
        decision = "SELL"
    else:
        decision = "HOLD"

    snippet = (scout.results[0].get("content") if scout.results else scout.raw_text)[:280]
    return QuantSignal(
        ticker=scout.ticker,
        sentiment=parsed["sentiment"],
        confidence=parsed["confidence"],
        whale_action=parsed["whale_action"],
        prior=round(prior, 4),
        posterior=round(posterior, 4),
        edge=round(edge, 4),
        decision=decision,
        leakage_ok=leakage_ok,
        source_snippet=snippet or "",
        nlp_features=parsed,
        log_likelihood_sum=round(ll_sum, 4),
        evidence=_evidence_bundle(scout),
    )
