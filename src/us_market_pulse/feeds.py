"""Aggregate public RSS / data sources for US market intelligence."""

from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

_TAG_RE = re.compile(r"<[^>]+>")

import feedparser
import httpx

from us_market_pulse.briefs import daily_digest, enrich_items
from us_market_pulse.calendar import next_fomc, upcoming_calendar
from us_market_pulse.config import load_settings
from us_market_pulse.briefing import build_live_briefing
from us_market_pulse.events import build_event_bundle
from us_market_pulse.sentiment import enrich_sentiment, sentiment_summary
from us_market_pulse.translate import enrich_titles
from us_market_pulse.watch import match_watchlist

USER_AGENT = (
    "USMarketPulse/1.0 (+https://github.com/local/us-market-pulse; research aggregator)"
)

# Category taxonomy shown in the UI
CATEGORIES: dict[str, dict[str, str]] = {
    "all": {"label": "全部", "blurb": "跨市场情报总览"},
    "markets": {"label": "市场", "blurb": "美股行情与企业动态"},
    "fed": {"label": "美联储", "blurb": "利率决议、声明与官员讲话"},
    "treasury": {"label": "国债", "blurb": "收益率、拍卖与财政部动态"},
    "policy": {"label": "政策监管", "blurb": "SEC、白宫经济与监管政策"},
    "politics": {"label": "时政地缘", "blurb": "影响市场的政治与地缘事件"},
}

FEED_SOURCES: list[dict[str, str]] = [
    {
        "id": "fed-press",
        "name": "美联储新闻稿",
        "category": "fed",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
    },
    {
        "id": "fed-speeches",
        "name": "美联储讲话",
        "category": "fed",
        "url": "https://www.federalreserve.gov/feeds/speeches.xml",
    },
    {
        "id": "fed-testimony",
        "name": "美联储证词",
        "category": "fed",
        "url": "https://www.federalreserve.gov/feeds/testimony.xml",
    },
    {
        "id": "fed-monetary",
        "name": "美联储货币政策",
        "category": "fed",
        "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
    },
    {
        "id": "treasury-news",
        "name": "国债与收益率",
        "category": "treasury",
        "url": "https://news.google.com/rss/search?q=US+Treasury+yield+OR+Treasury+auction+OR+%22bond+market%22&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "fiscal-policy",
        "name": "财政部与财政",
        "category": "treasury",
        "url": "https://news.google.com/rss/search?q=%22US+Treasury%22+OR+Yellen+OR+Bessent+debt+ceiling+OR+fiscal&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "sec-press",
        "name": "SEC 新闻",
        "category": "policy",
        "url": "https://www.sec.gov/news/pressreleases.rss",
    },
    {
        "id": "sec-speeches",
        "name": "SEC 讲话",
        "category": "policy",
        "url": "https://www.sec.gov/news/speeches-statements.rss",
    },
    {
        "id": "whitehouse",
        "name": "白宫新闻",
        "category": "politics",
        "url": "https://www.whitehouse.gov/news/feed/",
    },
    {
        "id": "cnbc-markets",
        "name": "CNBC Markets",
        "category": "markets",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
    },
    {
        "id": "cnbc-economy",
        "name": "CNBC Economy",
        "category": "policy",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    },
    {
        "id": "cnbc-politics",
        "name": "CNBC Politics",
        "category": "politics",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000113",
    },
    {
        "id": "marketwatch-top",
        "name": "MarketWatch",
        "category": "markets",
        "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    },
    {
        "id": "wsj-markets",
        "name": "WSJ Markets",
        "category": "markets",
        "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    },
    {
        "id": "bbc-business",
        "name": "BBC Business",
        "category": "markets",
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
    },
    {
        "id": "bbc-us",
        "name": "BBC US & Canada",
        "category": "politics",
        "url": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
    },
]

# FRED series (public CSV, no API key)
FRED_SERIES: list[dict[str, str]] = [
    {"id": "DFF", "label": "联邦基金利率", "unit": "%", "group": "fed"},
    {"id": "DGS2", "label": "2年期国债", "unit": "%", "group": "treasury"},
    {"id": "DGS10", "label": "10年期国债", "unit": "%", "group": "treasury"},
    {"id": "DGS30", "label": "30年期国债", "unit": "%", "group": "treasury"},
    {"id": "T10Y2Y", "label": "10Y-2Y 利差", "unit": "%", "group": "treasury"},
    {"id": "VIXCLS", "label": "VIX 波动率", "unit": "", "group": "markets"},
]

_CACHE: dict[str, Any] = {
    "items": [],
    "indicators": [],
    "calendar": [],
    "digest": {},
    "sentiment_summary": {},
    "watch_hits": [],
    "events": [],
    "event_threads": [],
    "timeline": [],
    "live_briefing": {},
    "next_fomc": None,
    "fetched_at": 0.0,
    "errors": [],
}
_CACHE_TTL = 300  # seconds


def _parse_date(entry: dict[str, Any]) -> datetime | None:
    for key in ("published", "updated", "created"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError, IndexError):
            pass
    for key in ("published_parsed", "updated_parsed"):
        struct = entry.get(key)
        if not struct:
            continue
        try:
            return datetime(*struct[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    return None


def _clean_text(value: str | None, limit: int = 280) -> str:
    if not value:
        return ""
    text = " ".join(value.split())
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


async def _fetch_feed(
    client: httpx.AsyncClient, source: dict[str, str]
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        resp = await client.get(source["url"], timeout=20.0)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:  # noqa: BLE001 — surface per-source failures
        return [], f"{source['name']}: {exc}"

    items: list[dict[str, Any]] = []
    for entry in parsed.entries[:12]:
        published = _parse_date(entry)
        link = entry.get("link") or entry.get("id") or ""
        summary = entry.get("summary") or entry.get("description") or ""
        if "<" in summary:
            summary = _TAG_RE.sub(" ", summary)
        items.append(
            {
                "id": f"{source['id']}:{entry.get('id') or link or entry.get('title')}",
                "title": _clean_text(entry.get("title"), 160),
                "summary": _clean_text(summary, 220),
                "url": link,
                "source": source["name"],
                "source_id": source["id"],
                "category": source["category"],
                "published": published.isoformat() if published else None,
                "published_ts": published.timestamp() if published else 0.0,
            }
        )
    return items, None


async def _fetch_fred_series(
    client: httpx.AsyncClient, series: dict[str, str]
) -> tuple[dict[str, Any] | None, str | None]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series['id']}"
    try:
        resp = await client.get(url, timeout=20.0)
        resp.raise_for_status()
        lines = [ln.strip() for ln in resp.text.splitlines() if ln.strip()]
        # Skip header; walk backwards for last numeric observation
        value = None
        date = None
        prev = None
        for line in reversed(lines[1:]):
            parts = line.split(",")
            if len(parts) < 2:
                continue
            raw = parts[1].strip()
            if raw in {"", "."}:
                continue
            try:
                value = float(raw)
                date = parts[0].strip()
                break
            except ValueError:
                continue
        if value is None:
            return None, f"FRED {series['id']}: no observation"

        # previous observation for delta
        for line in reversed(lines[1:]):
            parts = line.split(",")
            if len(parts) < 2:
                continue
            if parts[0].strip() == date:
                continue
            raw = parts[1].strip()
            if raw in {"", "."}:
                continue
            try:
                prev = float(raw)
                break
            except ValueError:
                continue

        delta = None if prev is None else round(value - prev, 4)
        return {
            "id": series["id"],
            "label": series["label"],
            "unit": series["unit"],
            "group": series["group"],
            "value": value,
            "date": date,
            "delta": delta,
            "url": f"https://fred.stlouisfed.org/series/{series['id']}",
        }, None
    except Exception as exc:  # noqa: BLE001
        return None, f"FRED {series['id']}: {exc}"


async def refresh_intel(force: bool = False) -> dict[str, Any]:
    now = time.time()
    if (
        not force
        and _CACHE["items"]
        and now - float(_CACHE["fetched_at"]) < _CACHE_TTL
    ):
        # Briefing is cheap; rebuild so copy/structure updates without full refresh
        live_briefing = build_live_briefing(
            _CACHE["items"],
            hours=12.0,
            compare_hours=24.0,
            events=(_CACHE.get("event_threads") or []) + (_CACHE.get("events") or []),
        )
        _CACHE["live_briefing"] = live_briefing
        return {
            "items": _CACHE["items"],
            "indicators": _CACHE["indicators"],
            "calendar": _CACHE["calendar"],
            "digest": _CACHE["digest"],
            "sentiment_summary": _CACHE["sentiment_summary"],
            "watch_hits": _CACHE["watch_hits"],
            "events": _CACHE["events"],
            "event_threads": _CACHE["event_threads"],
            "timeline": _CACHE["timeline"],
            "live_briefing": live_briefing,
            "next_fomc": _CACHE["next_fomc"],
            "fetched_at": _CACHE["fetched_at"],
            "errors": _CACHE["errors"],
            "cached": True,
        }

    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, */*"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        feed_tasks = [_fetch_feed(client, src) for src in FEED_SOURCES]
        fred_tasks = [_fetch_fred_series(client, s) for s in FRED_SERIES]
        feed_results, fred_results = await asyncio.gather(
            asyncio.gather(*feed_tasks),
            asyncio.gather(*fred_tasks),
        )

    items: list[dict[str, Any]] = []
    errors: list[str] = []
    for batch, err in feed_results:
        items.extend(batch)
        if err:
            errors.append(err)

    indicators: list[dict[str, Any]] = []
    for row, err in fred_results:
        if row:
            indicators.append(row)
        if err:
            errors.append(err)

    items.sort(key=lambda x: x.get("published_ts") or 0.0, reverse=True)
    # Deduplicate by normalized title
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = item["title"].casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    unique = enrich_sentiment(enrich_items(unique[:120]))
    unique = await enrich_titles(unique, online=True, online_limit=80)
    bundle = build_event_bundle(unique)
    unique = bundle["items"]
    settings = load_settings()
    watch_hits = match_watchlist(unique, settings.watch_keywords)
    calendar = upcoming_calendar(limit=8)
    digest = daily_digest(unique)
    mood = sentiment_summary(unique[:40])
    live_briefing = build_live_briefing(
        unique,
        hours=12.0,
        compare_hours=24.0,
        events=bundle["event_threads"] + bundle["events"],
    )

    _CACHE.update(
        {
            "items": unique,
            "indicators": indicators,
            "calendar": calendar,
            "digest": digest,
            "sentiment_summary": mood,
            "watch_hits": watch_hits[:20],
            "events": bundle["events"],
            "event_threads": bundle["event_threads"],
            "timeline": bundle["timeline"],
            "live_briefing": live_briefing,
            "next_fomc": next_fomc(),
            "fetched_at": now,
            "errors": errors,
        }
    )
    return {
        "items": unique,
        "indicators": indicators,
        "calendar": calendar,
        "digest": digest,
        "sentiment_summary": mood,
        "watch_hits": watch_hits[:20],
        "events": bundle["events"],
        "event_threads": bundle["event_threads"],
        "timeline": bundle["timeline"],
        "live_briefing": live_briefing,
        "next_fomc": next_fomc(),
        "fetched_at": now,
        "errors": errors,
        "cached": False,
    }


def get_event(event_id: str) -> dict[str, Any] | None:
    for event in _CACHE.get("events") or []:
        if event.get("id") == event_id:
            return event
    for event in _CACHE.get("event_threads") or []:
        if event.get("id") == event_id:
            return event
    return None


def clear_cache() -> None:
    _CACHE["fetched_at"] = 0.0
    _CACHE["items"] = []


def sort_items(items: list[dict[str, Any]], sort: str | None = None) -> list[dict[str, Any]]:
    mode = (sort or "bearish").strip().lower()
    rows = list(items)
    if mode == "latest":
        rows.sort(key=lambda x: x.get("published_ts") or 0.0, reverse=True)
    elif mode == "bullish":
        rows.sort(
            key=lambda x: (
                0 if x.get("sentiment") == "bullish" else 1 if x.get("sentiment") == "neutral" else 2,
                -float(x.get("sentiment_score") or 0),
                -(x.get("published_ts") or 0.0),
            )
        )
    else:  # bearish first (default)
        rows.sort(
            key=lambda x: (
                0 if x.get("sentiment") == "bearish" else 1 if x.get("sentiment") == "neutral" else 2,
                float(x.get("sentiment_score") or 0),
                -(x.get("published_ts") or 0.0),
            )
        )
    return rows


def filter_items(
    items: list[dict[str, Any]],
    category: str | None = None,
    q: str | None = None,
    sentiment: str | None = None,
    sort: str | None = "bearish",
) -> list[dict[str, Any]]:
    result = items
    if category and category != "all":
        result = [i for i in result if i.get("category") == category]
    if sentiment and sentiment != "all":
        result = [i for i in result if i.get("sentiment") == sentiment]
    if q:
        needle = q.strip().casefold()
        if needle:
            result = [
                i
                for i in result
                if needle in i.get("title", "").casefold()
                or needle in i.get("summary", "").casefold()
                or needle in i.get("source", "").casefold()
                or needle in i.get("brief_zh", "").casefold()
                or needle in i.get("theme", "").casefold()
                or needle in i.get("title_zh", "").casefold()
                or needle in i.get("sentiment_label", "").casefold()
                or needle in i.get("sentiment_logic", "").casefold()
            ]
    return sort_items(result, sort=sort)


def bearish_spotlight(items: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    bears = [i for i in items if i.get("sentiment") == "bearish"]
    bears.sort(key=lambda x: float(x.get("sentiment_score") or 0))
    return bears[:limit]
