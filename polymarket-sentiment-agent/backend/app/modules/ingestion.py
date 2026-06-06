"""The Scout — pulls news from free, public sources.

Sources:
  1. RSS feeds (CoinDesk, Cointelegraph, Decrypt by default — no auth)
  2. CryptoPanic free API (optional, set CRYPTOPANIC_API_KEY)

The Scout is intentionally I/O-bound and stateless: it pulls items,
dedupes by URL (DB UNIQUE constraint), and hands raw text downstream.
NO interpretation happens here.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import feedparser
import httpx
from sqlalchemy.exc import IntegrityError

from ..config import settings
from ..database import session_scope
from ..models import NewsItem

log = logging.getLogger("scout")


@dataclass
class RawNews:
    source: str
    url: str
    title: str
    summary: str
    published_at: Optional[datetime]


def _parse_dt(struct_time) -> Optional[datetime]:
    if not struct_time:
        return None
    try:
        return datetime(*struct_time[:6], tzinfo=timezone.utc)
    except Exception:
        return None


async def _fetch_rss(url: str) -> List[RawNews]:
    """feedparser is sync but cheap; offload to thread pool."""
    def _parse() -> List[RawNews]:
        feed = feedparser.parse(url)
        out: List[RawNews] = []
        host = (feed.feed.get("title") if feed.feed else None) or url
        for entry in feed.entries[:25]:
            out.append(
                RawNews(
                    source=str(host)[:64],
                    url=entry.get("link", ""),
                    title=entry.get("title", "")[:1024],
                    summary=(entry.get("summary", "") or entry.get("description", ""))[:4000],
                    published_at=_parse_dt(entry.get("published_parsed") or entry.get("updated_parsed")),
                )
            )
        return [r for r in out if r.url and r.title]

    try:
        return await asyncio.to_thread(_parse)
    except Exception as e:
        log.warning("RSS fetch failed %s: %s", url, e)
        return []


async def _fetch_cryptopanic(client: httpx.AsyncClient) -> List[RawNews]:
    if not settings.cryptopanic_api_key:
        return []
    try:
        r = await client.get(
            "https://cryptopanic.com/api/v1/posts/",
            params={
                "auth_token": settings.cryptopanic_api_key,
                "kind": "news",
                "public": "true",
            },
            timeout=10.0,
        )
        r.raise_for_status()
        data = r.json()
        out: List[RawNews] = []
        for p in data.get("results", [])[:50]:
            out.append(
                RawNews(
                    source="cryptopanic",
                    url=p.get("url", ""),
                    title=(p.get("title") or "")[:1024],
                    summary=(p.get("title") or "")[:4000],
                    published_at=datetime.fromisoformat(p["published_at"].replace("Z", "+00:00"))
                    if p.get("published_at")
                    else None,
                )
            )
        return [r for r in out if r.url and r.title]
    except Exception as e:
        log.warning("CryptoPanic fetch failed: %s", e)
        return []


async def ingest_once() -> List[NewsItem]:
    """Run one ingestion pass. Returns persisted (newly inserted) items."""
    async with httpx.AsyncClient() as client:
        tasks = [_fetch_rss(u) for u in settings.rss_list]
        tasks.append(_fetch_cryptopanic(client))
        groups = await asyncio.gather(*tasks, return_exceptions=False)

    items: List[RawNews] = [it for grp in groups for it in grp]
    if not items:
        return []

    # Filter by keyword relevance to keep DB tight on the MVP.
    kws = settings.keyword_list
    if kws:
        def is_relevant(n: RawNews) -> bool:
            blob = f"{n.title} {n.summary}".lower()
            return any(k in blob for k in kws)
        items = [n for n in items if is_relevant(n)]

    inserted: List[NewsItem] = []
    with session_scope() as s:
        for n in items:
            row = NewsItem(
                source=n.source,
                url=n.url,
                title=n.title,
                summary=n.summary,
                published_at=n.published_at,
            )
            s.add(row)
            try:
                s.flush()  # surfaces UNIQUE violation per-row
                inserted.append(row)
            except IntegrityError:
                s.rollback()
                # already ingested — fine.
                continue
        # commit handled by session_scope
    if inserted:
        log.info("Scout: %d new items ingested", len(inserted))
    return inserted
