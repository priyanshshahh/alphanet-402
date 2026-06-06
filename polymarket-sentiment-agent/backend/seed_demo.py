"""Seed one coherent demo trade so /api/trade/{id}/rationale returns rich data.

Creates: NewsItem -> Signal (Bayesian) -> MarketSnapshot -> Trade, all linked.
Safe to run repeatedly (uses a fixed idem_key).
"""
from __future__ import annotations

import datetime as dt

from app.database import session_scope
from app.models import NewsItem, Signal, MarketSnapshot, Trade
from app.modules import intelligence

IDEM = "demo-seed-fed-rate-cut-001"


def main() -> None:
    with session_scope() as s:
        existing = s.query(Trade).filter(Trade.idem_key == IDEM).first()
        if existing:
            print(f"Demo trade already exists: id={existing.id}")
            return

        news = NewsItem(
            source="coindesk",
            url="https://www.coindesk.com/markets/demo/fed-rate-cut-signal",
            title="Fed officials signal openness to a 25bps rate cut after June meeting",
            summary=(
                "Multiple FOMC members indicated softening inflation data has opened the "
                "door to a 25 basis point cut, a dovish shift markets read as risk-on."
            ),
            published_at=dt.datetime.utcnow(),
        )
        s.add(news)
        s.flush()

        prior = 0.62  # Polymarket implied probability (market prior)
        posterior, lr = intelligence.bayesian_update(prior, "bullish", 0.78)
        sig = Signal(
            news_item_id=news.id,
            sentiment="bullish",
            confidence=0.78,
            topic="FED",
            entities='["FED", "FOMC", "RATES"]',
            rationale="Dovish FOMC commentary increases probability of a June rate cut.",
            llm_provider="heuristic",
            prior=prior,
            posterior=posterior,
            likelihood_ratio=lr,
        )
        s.add(sig)
        s.flush()

        snap = MarketSnapshot(
            condition_id="0xdde06286a7b9464d344f410ab0b3d2ebc6469904e72c27fd982f65fdbf78768d",
            slug="will-the-fed-decrease-interest-rates-by-25-bps-after-the-june-2026-meeting",
            question="Will the Fed decrease interest rates by 25 bps after the June 2026 meeting?",
            outcome="YES",
            token_id="11019686559003253359318459636510036787281809199165975947920974072245914352862",
            price=prior,
            best_bid=0.61,
            best_ask=0.63,
            liquidity=125000.0,
            volume_24h=480000.0,
        )
        s.add(snap)
        s.flush()

        edge = round(posterior - prior, 4)
        size = 8.0
        trade = Trade(
            idem_key=IDEM,
            mode="PAPER",
            status="FILLED",
            condition_id=snap.condition_id,
            market_question=snap.question,
            outcome="YES",
            side="BUY",
            price=prior,
            size_usdc=size,
            shares=round(size / prior, 4),
            fees_usdc=0.0,
            model_probability=posterior,
            edge=edge,
            signal_id=sig.id,
            snapshot_id=snap.id,
            notes="Seeded demo trade for x402 rationale endpoint.",
        )
        s.add(trade)
        s.flush()
        print(f"Seeded demo trade: id={trade.id}  edge={edge}  posterior={posterior} prior={prior}")


if __name__ == "__main__":
    main()
