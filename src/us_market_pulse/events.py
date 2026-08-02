"""Cluster related headlines into events and build chronological timelines."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "have",
    "has",
    "had",
    "are",
    "was",
    "were",
    "will",
    "would",
    "could",
    "should",
    "after",
    "before",
    "into",
    "over",
    "under",
    "about",
    "against",
    "their",
    "they",
    "them",
    "its",
    "his",
    "her",
    "who",
    "what",
    "when",
    "where",
    "why",
    "how",
    "not",
    "but",
    "out",
    "new",
    "says",
    "said",
    "amid",
    "near",
    "more",
    "than",
    "into",
    "just",
    "also",
    "been",
    "being",
    "can",
    "may",
    "might",
    "as",
    "of",
    "to",
    "in",
    "on",
    "at",
    "by",
    "an",
    "a",
    "or",
    "is",
    "it",
    "be",
}

# High-signal entities for event stitching
ENTITY_ALIASES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(federal reserve|fomc|powell|fed)\b", re.I), "美联储/FOMC"),
    (re.compile(r"\b(treasury|yield|bond market|dgs10)\b", re.I), "国债/收益率"),
    (re.compile(r"\b(tariff|tariffs|trade war|retaliat\w*)\b", re.I), "关税/贸易"),
    (re.compile(r"\b(iran|tehran)\b", re.I), "伊朗"),
    (re.compile(r"\b(israel|gaza|hamas|hezbollah)\b", re.I), "以巴/加沙"),
    (re.compile(r"\b(ukraine|zelensky|patriot missile)\b", re.I), "乌克兰"),
    (re.compile(r"\b(china|beijing|xi jinping)\b", re.I), "中国"),
    (re.compile(r"\b(russia|moscow|putin)\b", re.I), "俄罗斯"),
    (re.compile(r"\b(trump)\b", re.I), "特朗普"),
    (re.compile(r"\b(biden)\b", re.I), "拜登"),
    (re.compile(r"\b(sec|antitrust|enforcement)\b", re.I), "SEC/监管"),
    (re.compile(r"\b(inflation|cpi|ppi|pce)\b", re.I), "通胀"),
    (re.compile(r"\b(jobs|payroll|unemployment|nfp)\b", re.I), "就业"),
    (re.compile(r"\b(debt ceiling|shutdown|fiscal)\b", re.I), "财政/债务"),
    (re.compile(r"\b(oil|brent|wti|energy)\b", re.I), "原油/能源"),
    (re.compile(r"\b(sanctions?)\b", re.I), "制裁"),
    (re.compile(r"\b(military|airstrike|missile|war)\b", re.I), "军事冲突"),
]

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]{2,}|[\u4e00-\u9fff]{2,}")


def _extract_entities(text: str) -> list[str]:
    hits: list[str] = []
    for pattern, label in ENTITY_ALIASES:
        if pattern.search(text):
            if label not in hits:
                hits.append(label)
    return hits


def _tokens(text: str) -> set[str]:
    words = set()
    for raw in WORD_RE.findall(text or ""):
        w = raw.casefold()
        if w in STOPWORDS:
            continue
        if len(w) < 3 and not re.search(r"[\u4e00-\u9fff]", w):
            continue
        words.add(w)
    return words


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / len(a | b)


# Too common to stitch unrelated stories by themselves
BROAD_ENTITIES = {"特朗普", "拜登", "美联储/FOMC", "国债/收益率", "军事冲突", "制裁", "关税/贸易"}
GEO_ENTITIES = {"伊朗", "以巴/加沙", "乌克兰", "中国", "俄罗斯"}


def _item_signature(item: dict[str, Any]) -> dict[str, Any]:
    title = item.get("title") or ""
    title_zh = item.get("title_zh") or ""
    summary = item.get("summary") or ""
    text = f"{title} {title_zh} {summary}"
    entities = _extract_entities(text)
    tokens = _tokens(title) | _tokens(title_zh)
    # Only specific entities become matching tokens (avoid Trump linking everything)
    for ent in entities:
        if ent not in BROAD_ENTITIES:
            tokens.add(ent.casefold())
    return {"tokens": tokens, "entities": entities}


def _similarity(sig_a: dict[str, Any], sig_b: dict[str, Any]) -> float:
    base = _jaccard(sig_a["tokens"], sig_b["tokens"])
    ent_a = set(sig_a["entities"])
    ent_b = set(sig_b["entities"])
    shared = ent_a & ent_b
    shared_specific = shared - BROAD_ENTITIES
    shared_broad = shared & BROAD_ENTITIES

    if shared_specific:
        base += 0.22 * min(len(shared_specific), 3)
    elif shared_broad:
        # Broad-only overlap needs real lexical overlap
        base += 0.06 * min(len(shared_broad), 2)

    # Different country theaters should not merge without lexical overlap
    geo_a = ent_a & GEO_ENTITIES
    geo_b = ent_b & GEO_ENTITIES
    if geo_a and geo_b and not (geo_a & geo_b):
        if _jaccard(sig_a["tokens"], sig_b["tokens"]) < 0.35:
            return 0.0

    token_overlap = len(sig_a["tokens"] & sig_b["tokens"])
    if token_overlap == 0 and len(shared_specific) < 2:
        return 0.0
    if base < 0.28 and len(shared_specific) < 2:
        return 0.0
    return min(1.0, base)


def _event_id(seed: str) -> str:
    return "evt_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]


def _dominant_sentiment(items: list[dict[str, Any]]) -> tuple[str, str, float]:
    if not items:
        return "neutral", "中性", 0.0
    # Prefer strongest absolute score among clustered items
    ranked = sorted(
        items, key=lambda x: abs(float(x.get("sentiment_score") or 0)), reverse=True
    )
    top = ranked[0]
    return (
        top.get("sentiment") or "neutral",
        top.get("sentiment_label") or "中性",
        float(top.get("sentiment_score") or 0),
    )


def cluster_events(items: list[dict[str, Any]], *, min_size: int = 1) -> list[dict[str, Any]]:
    """Greedy clustering of headlines into event threads."""
    prepared: list[dict[str, Any]] = []
    for item in items:
        row = dict(item)
        sig = _item_signature(row)
        row["_sig"] = sig
        prepared.append(row)

    # Newest first helps attach updates to active stories
    prepared.sort(key=lambda x: x.get("published_ts") or 0.0, reverse=True)

    clusters: list[dict[str, Any]] = []
    for item in prepared:
        best_idx = -1
        best_score = 0.0
        for idx, cluster in enumerate(clusters):
            # Compare against up to 3 freshest members
            scores = [
                _similarity(item["_sig"], member["_sig"])
                for member in cluster["members"][:3]
            ]
            score = max(scores) if scores else 0.0
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_idx >= 0 and best_score >= 0.4:
            clusters[best_idx]["members"].append(item)
            clusters[best_idx]["entities"] = sorted(
                set(clusters[best_idx]["entities"]) | set(item["_sig"]["entities"])
            )
        else:
            clusters.append(
                {
                    "members": [item],
                    "entities": list(item["_sig"]["entities"]),
                    "seed": item.get("title") or item.get("id") or str(len(clusters)),
                }
            )

    events: list[dict[str, Any]] = []
    for cluster in clusters:
        members = cluster["members"]
        if len(members) < min_size:
            continue
        members_sorted = sorted(
            members, key=lambda x: x.get("published_ts") or 0.0
        )  # oldest -> newest for timeline
        latest = members_sorted[-1]
        earliest = members_sorted[0]
        sentiment, label, score = _dominant_sentiment(members)
        eid = _event_id(cluster["seed"])

        timeline = []
        for m in members_sorted:
            timeline.append(
                {
                    "id": m.get("id"),
                    "title": m.get("title") or "",
                    "title_zh": m.get("title_zh") or m.get("title") or "",
                    "source": m.get("source") or "",
                    "category": m.get("category") or "",
                    "url": m.get("url") or "",
                    "published": m.get("published"),
                    "published_ts": m.get("published_ts") or 0.0,
                    "sentiment": m.get("sentiment") or "neutral",
                    "sentiment_label": m.get("sentiment_label") or "中性",
                    "sentiment_score": m.get("sentiment_score") or 0.0,
                    "sentiment_logic": m.get("sentiment_logic") or "",
                }
            )

        events.append(
            {
                "id": eid,
                "title": latest.get("title") or "",
                "title_zh": latest.get("title_zh") or latest.get("title") or "",
                "keywords": cluster["entities"][:6],
                "count": len(members_sorted),
                "sentiment": sentiment,
                "sentiment_label": label,
                "sentiment_score": score,
                "first_seen": earliest.get("published"),
                "last_seen": latest.get("published"),
                "first_seen_ts": earliest.get("published_ts") or 0.0,
                "last_seen_ts": latest.get("published_ts") or 0.0,
                "sources": sorted({m.get("source") or "" for m in members_sorted if m.get("source")}),
                "timeline": timeline,
            }
        )

    # Active multi-item events first, then by recency
    events.sort(
        key=lambda e: (
            0 if e["count"] > 1 else 1,
            -e["last_seen_ts"],
            -e["count"],
        )
    )
    return events


def attach_event_ids(
    items: list[dict[str, Any]], events: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Stamp each item with its event_id and sibling count."""
    title_to_event: dict[str, dict[str, Any]] = {}
    for event in events:
        for node in event.get("timeline") or []:
            key = (node.get("title") or "").casefold()
            if key:
                title_to_event[key] = event

    out: list[dict[str, Any]] = []
    for item in items:
        row = dict(item)
        event = title_to_event.get((item.get("title") or "").casefold())
        if event:
            row["event_id"] = event["id"]
            row["event_count"] = event["count"]
            row["event_title_zh"] = event.get("title_zh") or ""
        else:
            row["event_id"] = None
            row["event_count"] = 1
            row["event_title_zh"] = item.get("title_zh") or item.get("title") or ""
        out.append(row)
    return out


def build_feed_timeline(
    items: list[dict[str, Any]], *, limit_days: int = 7
) -> list[dict[str, Any]]:
    """Group feed items into day buckets for chronological browsing."""
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        published = item.get("published")
        ts = item.get("published_ts") or 0.0
        if published:
            try:
                day = published[:10]
            except Exception:  # noqa: BLE001
                day = datetime.fromtimestamp(ts or 0, tz=timezone.utc).date().isoformat()
        else:
            day = datetime.fromtimestamp(ts or 0, tz=timezone.utc).date().isoformat()
        buckets[day].append(
            {
                "id": item.get("id"),
                "title": item.get("title") or "",
                "title_zh": item.get("title_zh") or item.get("title") or "",
                "source": item.get("source") or "",
                "url": item.get("url") or "",
                "published": item.get("published"),
                "published_ts": ts,
                "sentiment": item.get("sentiment") or "neutral",
                "sentiment_label": item.get("sentiment_label") or "中性",
                "event_id": item.get("event_id"),
                "event_count": item.get("event_count") or 1,
                "category": item.get("category") or "",
            }
        )

    today = datetime.now(timezone.utc).date()
    timeline: list[dict[str, Any]] = []
    for day in sorted(buckets.keys(), reverse=True)[:limit_days]:
        rows = sorted(buckets[day], key=lambda x: x.get("published_ts") or 0.0, reverse=True)
        try:
            d = datetime.fromisoformat(day).date()
            delta = (today - d).days
            if delta == 0:
                label = "今天"
            elif delta == 1:
                label = "昨天"
            else:
                label = f"{delta} 天前"
        except ValueError:
            label = day
        timeline.append(
            {
                "date": day,
                "label": label,
                "count": len(rows),
                "bearish": sum(1 for r in rows if r.get("sentiment") == "bearish"),
                "bullish": sum(1 for r in rows if r.get("sentiment") == "bullish"),
                "items": rows,
            }
        )
    return timeline


def build_event_bundle(items: list[dict[str, Any]]) -> dict[str, Any]:
    events = cluster_events(items, min_size=1)
    stamped = attach_event_ids(items, events)
    # Keep multi-item threads prominent in the event rail
    multi = [e for e in events if e["count"] >= 2]
    singles_recent = [e for e in events if e["count"] == 1][:12]
    featured = (multi + singles_recent)[:24]
    timeline = build_feed_timeline(stamped, limit_days=8)
    return {
        "items": stamped,
        "events": featured,
        "event_threads": multi[:16],
        "timeline": timeline,
    }
