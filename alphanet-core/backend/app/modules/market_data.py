"""Real equities data via yfinance (keyless, free).

This is the default scout source: daily price history and fundamental
ratios pulled from Yahoo Finance, distilled into small factual "event"
snippets that the NLP/Bayes pipeline consumes exactly like paid news.

Design: everything that touches the network lives in `fetch_equity_events`;
`compute_features`, `estimate_prior`, and `build_events` are pure functions
over plain Python lists/dicts so the pipeline is testable fully offline.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple


class MarketDataError(Exception):
    """Raised when no usable market data could be fetched for a ticker."""


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def compute_features(
    closes: Sequence[float], volumes: Optional[Sequence[float]] = None
) -> Dict[str, Any]:
    """Derive technical features from a daily close series (oldest first)."""
    closes = [float(c) for c in closes if c is not None]
    if len(closes) < 2:
        raise MarketDataError("Need at least 2 closes to derive features")

    last = closes[-1]
    ma_window = min(50, len(closes))
    ma50 = _mean(closes[-ma_window:])
    pct_vs_ma50 = (last - ma50) / ma50 if ma50 else 0.0

    mom_window = min(126, len(closes) - 1)  # ~6 months of sessions
    base = closes[-(mom_window + 1)]
    momentum_6m = (last - base) / base if base else 0.0

    up_window = min(60, len(closes) - 1)
    diffs = [
        closes[i] - closes[i - 1]
        for i in range(len(closes) - up_window, len(closes))
    ]
    up_day_ratio = sum(1 for d in diffs if d > 0) / len(diffs)

    volume_ratio = None
    if volumes:
        vols = [float(v) for v in volumes if v is not None]
        if len(vols) >= 2:
            avg_window = min(20, len(vols) - 1)
            avg = _mean(vols[-(avg_window + 1) : -1])
            if avg > 0:
                volume_ratio = vols[-1] / avg

    return {
        "last_close": round(last, 4),
        "pct_vs_ma50": round(pct_vs_ma50, 4),
        "momentum_6m": round(momentum_6m, 4),
        "up_day_ratio": round(up_day_ratio, 4),
        "volume_ratio": round(volume_ratio, 4) if volume_ratio is not None else None,
        "sessions": len(closes),
    }


def estimate_prior(up_day_ratio: float) -> float:
    """Base-rate prior for "next move is up" from the observed up-day
    frequency, shrunk toward 0.5 and clipped so a short window can never
    dominate the Bayesian update."""
    shrunk = 0.5 + (float(up_day_ratio) - 0.5) * 0.6
    return max(0.35, min(0.65, shrunk))


def _trend_label(feats: Dict[str, Any]) -> str:
    above = feats["pct_vs_ma50"] > 0.01
    below = feats["pct_vs_ma50"] < -0.01
    mom_up = feats["momentum_6m"] > 0.02
    mom_down = feats["momentum_6m"] < -0.02
    if above and mom_up:
        return "bullish"
    if below and mom_down:
        return "bearish"
    return "neutral"


def build_events(
    ticker: str, feats: Dict[str, Any], fundamentals: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Turn derived numbers into factual text snippets for the NLP stage."""
    url = f"https://finance.yahoo.com/quote/{ticker}"
    label = _trend_label(feats)
    side = "above" if feats["pct_vs_ma50"] >= 0 else "below"
    parts = [
        f"Technical read: {label}.",
        f"{ticker} closed at {feats['last_close']} — "
        f"{abs(feats['pct_vs_ma50']) * 100:.1f}% {side} its 50-day moving average;",
        f"6-month momentum {feats['momentum_6m'] * 100:+.1f}%;",
        f"up-day ratio over the last {min(60, feats['sessions'] - 1)} sessions: "
        f"{feats['up_day_ratio'] * 100:.0f}%.",
    ]
    if feats.get("volume_ratio") is not None:
        parts.append(
            f"Latest session volume was {feats['volume_ratio']:.2f}x its 20-day average."
        )
    events = [
        {
            "title": f"{ticker} price/trend snapshot (yfinance)",
            "url": url,
            "content": " ".join(parts),
            "score": None,
            "source": "yfinance",
        }
    ]

    fparts: List[str] = []
    f = fundamentals or {}
    if f.get("returnOnEquity") is not None:
        fparts.append(f"ROE {float(f['returnOnEquity']) * 100:.1f}%")
    ev, ebitda = f.get("enterpriseValue"), f.get("ebitda")
    if ev and ebitda:
        fparts.append(f"EV/EBITDA {float(ev) / float(ebitda):.1f}")
    if f.get("priceToBook"):
        try:
            fparts.append(f"book-to-market {1.0 / float(f['priceToBook']):.3f}")
        except ZeroDivisionError:
            pass
    if f.get("trailingPE") is not None:
        fparts.append(f"trailing P/E {float(f['trailingPE']):.1f}")
    if f.get("heldPercentInstitutions") is not None:
        fparts.append(
            f"institutional ownership {float(f['heldPercentInstitutions']) * 100:.1f}%"
        )
    if fparts:
        events.append(
            {
                "title": f"{ticker} fundamentals snapshot (yfinance)",
                "url": url,
                "content": f"Fundamentals for {ticker}: " + ", ".join(fparts) + ".",
                "score": None,
                "source": "yfinance",
            }
        )
    return events


def fetch_equity_events(ticker: str) -> Tuple[List[Dict[str, Any]], float]:
    """Network path: pull ~7 months of daily bars + fundamentals from Yahoo.

    Returns (events, prior). Raises MarketDataError when Yahoo returns
    nothing usable — callers must surface that instead of inventing data.
    """
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover
        raise MarketDataError(f"yfinance not installed: {exc}") from exc

    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="7mo", interval="1d", auto_adjust=True)
    except Exception as exc:
        raise MarketDataError(f"yfinance history failed for {ticker}: {exc}") from exc

    if hist is None or getattr(hist, "empty", True):
        raise MarketDataError(f"No price history returned for {ticker}")

    closes = list(hist["Close"].dropna())
    volumes = list(hist["Volume"].dropna()) if "Volume" in hist else None
    feats = compute_features(closes, volumes)

    fundamentals: Dict[str, Any] = {}
    try:
        info = t.info or {}
        fundamentals = {
            k: info.get(k)
            for k in (
                "returnOnEquity",
                "enterpriseValue",
                "ebitda",
                "priceToBook",
                "trailingPE",
                "heldPercentInstitutions",
            )
        }
    except Exception:
        # Fundamentals are best-effort; price/trend events alone are fine.
        fundamentals = {}

    return build_events(ticker, feats, fundamentals), estimate_prior(
        feats["up_day_ratio"]
    )
