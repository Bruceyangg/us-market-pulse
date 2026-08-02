"""Rolling multi-hour market briefing: event overview first, then bearish assessment."""

from __future__ import annotations

import time
from collections import Counter
from typing import Any


def _hours_ago(item: dict[str, Any], now_ts: float) -> float | None:
    ts = item.get("published_ts") or 0.0
    if not ts:
        return None
    return max(0.0, (now_ts - float(ts)) / 3600.0)


def _pick_recent(items: list[dict[str, Any]], *, within_hours: float, now_ts: float) -> list[dict[str, Any]]:
    rows = []
    for item in items:
        age = _hours_ago(item, now_ts)
        if age is None:
            continue
        if age <= within_hours:
            rows.append(item)
    rows.sort(key=lambda x: x.get("published_ts") or 0.0, reverse=True)
    return rows


def _avg_score(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    return round(sum(float(i.get("sentiment_score") or 0) for i in items) / len(items), 3)


def _tilt(score: float) -> tuple[str, str]:
    if score <= -0.35:
        return "bearish", "利空升温"
    if score <= -0.15:
        return "bearish", "偏空走强"
    if score >= 0.22:
        return "bullish", "偏多回暖"
    if score >= 0.08:
        return "bullish", "略偏多"
    return "neutral", "中性观望"


def _short_title(item: dict[str, Any], *, limit: int = 42) -> str:
    title = (item.get("title_zh") or item.get("title") or "").strip()
    if len(title) <= limit:
        return title
    return title[: limit - 1] + "…"


def _event_in_window(event: dict[str, Any], *, within_hours: float, now_ts: float) -> bool:
    last_ts = float(event.get("last_seen_ts") or 0)
    if last_ts and (now_ts - last_ts) / 3600.0 <= within_hours:
        return True
    # Fallback: any timeline node in window
    for node in event.get("timeline") or []:
        # timeline nodes may only have published ISO; match via title against items later
        if node.get("published_ts"):
            age = (now_ts - float(node["published_ts"])) / 3600.0
            if age <= within_hours:
                return True
    return bool(last_ts)  # if no ts, keep for caller filter


def _build_event_bullets(
    recent: list[dict[str, Any]],
    events: list[dict[str, Any]] | None,
    *,
    window: float,
    now_ts: float,
) -> list[dict[str, Any]]:
    """Pick main storylines for the overview section."""
    bullets: list[dict[str, Any]] = []
    used_titles: set[str] = set()

    # Prefer clustered event threads that touched the window
    for event in events or []:
        if not _event_in_window(event, within_hours=window, now_ts=now_ts):
            # Also accept if any recent item shares event_id
            eid = event.get("id")
            if not eid or not any(i.get("event_id") == eid for i in recent):
                continue
        title = (event.get("title_zh") or event.get("title") or "").strip()
        if not title:
            continue
        key = title.casefold()
        if key in used_titles:
            continue
        used_titles.add(key)
        sources = event.get("sources") or []
        bullets.append(
            {
                "title": event.get("title") or "",
                "title_zh": title,
                "kind": "event",
                "count": event.get("count") or 1,
                "sources": sources[:4],
                "keywords": (event.get("keywords") or [])[:4],
                "sentiment_label": event.get("sentiment_label") or "",
                "event_id": event.get("id"),
            }
        )
        if len(bullets) >= 4:
            break

    # Fill with distinct recent headlines by theme
    if len(bullets) < 4:
        theme_seen: set[str] = set()
        for item in recent:
            title = (item.get("title_zh") or item.get("title") or "").strip()
            if not title or title.casefold() in used_titles:
                continue
            theme = item.get("theme") or item.get("category") or "其他"
            # allow one extra per theme after first pass
            theme_key = str(theme)
            if theme_key in theme_seen and len(bullets) >= 2:
                continue
            theme_seen.add(theme_key)
            used_titles.add(title.casefold())
            bullets.append(
                {
                    "title": item.get("title") or "",
                    "title_zh": title,
                    "kind": "headline",
                    "count": 1,
                    "sources": [item.get("source") or ""] if item.get("source") else [],
                    "keywords": [],
                    "sentiment_label": item.get("sentiment_label") or "",
                    "theme": theme_key,
                    "url": item.get("url") or "",
                    "event_id": item.get("event_id"),
                }
            )
            if len(bullets) >= 4:
                break

    return bullets


def _compose_overview(
    recent: list[dict[str, Any]],
    bullets: list[dict[str, Any]],
    *,
    window: float,
    top_themes: list[str],
) -> str:
    if not recent:
        return f"近 {window:g} 小时公开源更新偏少，暂未形成可概述的主线事件。"

    theme_text = "、".join(top_themes[:3]) if top_themes else "主题较分散"
    parts = [
        f"近 {window:g} 小时共捕捉 {len(recent)} 条更新，主线集中在{theme_text}。"
    ]

    if bullets:
        narr = []
        for i, b in enumerate(bullets[:3], 1):
            title = b.get("title_zh") or b.get("title") or ""
            if b.get("kind") == "event" and (b.get("count") or 1) >= 2:
                narr.append(f"{i}）{title}（相关报道 {b['count']} 条）")
            else:
                narr.append(f"{i}）{title}")
        parts.append("事件脉络：" + "；".join(narr) + "。")
    else:
        # fallback to newest titles
        tops = [_short_title(i) for i in recent[:3] if _short_title(i)]
        if tops:
            parts.append("主要动态：" + "；".join(tops) + "。")

    return "".join(parts)


def _compose_assessment(
    *,
    window: float,
    recent_score: float,
    delta: float,
    change_zh: str,
    tilt_zh: str,
    bear: list[dict[str, Any]],
    bull: list[dict[str, Any]],
    neut: list[dict[str, Any]],
    top_factors: list[str],
    drivers: list[dict[str, Any]],
) -> str:
    total = len(bear) + len(bull) + len(neut)
    if total == 0:
        return "样本不足，暂不做利空强弱结论。"

    factor_text = "、".join(top_factors[:3]) if top_factors else "尚未形成集中利空因子"
    parts = [
        f"利空评判：窗口内利空 {len(bear)} / 利多 {len(bull)} / 中性 {len(neut)}，"
        f"情绪均分 {recent_score:+.2f}，较前一窗口 {delta:+.2f}，"
        f"综合判定为「{change_zh}」，当前偏向「{tilt_zh}」。",
        f"压制因子侧重：{factor_text}。",
    ]
    if drivers:
        lead = drivers[0].get("title_zh") or drivers[0].get("title") or ""
        logic = drivers[0].get("logic") or ""
        parts.append(f"最需关注的压制线索：{lead}。")
        if logic:
            parts.append(f"判定依据：{logic}")
    else:
        parts.append("本窗口暂无显著偏空/利空头条，风险更多来自不确定与观望情绪。")
    return "".join(parts)


def build_live_briefing(
    items: list[dict[str, Any]],
    *,
    hours: float = 12.0,
    compare_hours: float = 24.0,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build overview-then-assessment briefing for the recent window."""
    now_ts = time.time()
    recent = _pick_recent(items, within_hours=hours, now_ts=now_ts)
    window = hours
    # If sparse, widen once to 24h
    if len(recent) < 4 and hours < 24:
        window = 24.0
        recent = _pick_recent(items, within_hours=window, now_ts=now_ts)

    prior = [
        i
        for i in items
        if (_hours_ago(i, now_ts) or 999) > window
        and (_hours_ago(i, now_ts) or 999) <= max(compare_hours, window + 12)
    ]

    recent_score = _avg_score(recent)
    prior_score = _avg_score(prior) if prior else recent_score
    delta = round(recent_score - prior_score, 3)
    tilt, tilt_zh = _tilt(recent_score)

    if delta <= -0.12:
        change_zh = "利空显著升温"
        change = "deteriorating"
    elif delta <= -0.04:
        change_zh = "利空小幅加重"
        change = "softening"
    elif delta >= 0.12:
        change_zh = "利空明显缓和"
        change = "improving"
    elif delta >= 0.04:
        change_zh = "利空略有缓和"
        change = "stabilizing"
    else:
        change_zh = "利空水平大致持平"
        change = "steady"

    bear = [i for i in recent if i.get("sentiment") == "bearish"]
    bull = [i for i in recent if i.get("sentiment") == "bullish"]
    neut = [i for i in recent if i.get("sentiment") == "neutral"]

    factor_counter: Counter[str] = Counter()
    for item in bear:
        for f in item.get("bear_factors") or item.get("sentiment_factors") or []:
            factor_counter[str(f)] += 1
    top_factors = [name for name, _ in factor_counter.most_common(5)]

    theme_counter: Counter[str] = Counter()
    for item in recent:
        theme = item.get("theme") or item.get("category") or "其他"
        theme_counter[str(theme)] += 1
    top_themes = [name for name, _ in theme_counter.most_common(4)]

    drivers_src = sorted(
        bear,
        key=lambda x: (
            float(x.get("sentiment_score") or 0),
            -(x.get("published_ts") or 0),
        ),
    )[:5]

    driver_rows = [
        {
            "title": d.get("title") or "",
            "title_zh": d.get("title_zh") or d.get("title") or "",
            "url": d.get("url") or "",
            "source": d.get("source") or "",
            "published": d.get("published"),
            "sentiment_label": d.get("sentiment_label") or "利空",
            "sentiment_score": d.get("sentiment_score") or 0,
            "factors": (d.get("bear_factors") or d.get("sentiment_factors") or [])[:3],
            "logic": d.get("sentiment_logic") or "",
            "event_id": d.get("event_id"),
            "event_count": d.get("event_count") or 1,
        }
        for d in drivers_src
    ]

    event_pool = list(events or [])
    # Also include threads already stamped on items via unique event ids
    bullets = _build_event_bullets(recent, event_pool, window=window, now_ts=now_ts)
    overview = _compose_overview(recent, bullets, window=window, top_themes=top_themes)
    assessment = _compose_assessment(
        window=window,
        recent_score=recent_score,
        delta=delta,
        change_zh=change_zh,
        tilt_zh=tilt_zh,
        bear=bear,
        bull=bull,
        neut=neut,
        top_factors=top_factors,
        drivers=driver_rows,
    )

    # Back-compat single summary: overview then assessment
    summary = f"{overview} {assessment}".strip()

    direction = {
        "bias": tilt,
        "bias_zh": tilt_zh,
        "change": change,
        "change_zh": change_zh,
        "score": recent_score,
        "prior_score": prior_score,
        "delta": delta,
    }

    return {
        "window_hours": window,
        "compare_hours": compare_hours,
        "as_of": now_ts,
        "counts": {
            "total": len(recent),
            "bearish": len(bear),
            "bullish": len(bull),
            "neutral": len(neut),
            "prior_sample": len(prior),
        },
        "direction": direction,
        "top_factors": top_factors,
        "top_themes": top_themes,
        "event_bullets": bullets,
        "overview": overview,
        "assessment": assessment,
        "summary": summary,
        "drivers": driver_rows,
        "recent_ids": [i.get("id") for i in recent[:12]],
    }
