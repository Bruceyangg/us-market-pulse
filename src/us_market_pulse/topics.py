"""Topic desks for geopolitics — war progress columns + bearish analysis."""

from __future__ import annotations

import re
from typing import Any

from us_market_pulse.feeds import sort_items

TOPICS: dict[str, dict[str, Any]] = {
    "us_iran": {
        "id": "us_iran",
        "label": "美伊战争",
        "blurb": "美国、伊朗及相关中东军事与制裁进展",
        "query": "伊朗 OR Iran OR 霍尔木兹",
        "patterns": [
            re.compile(
                r"\b(iran|tehran|irgc|hormuz|hezbollah|houthi|strait of hormuz|"
                r"persian gulf|israel[- ]iran|us[- ]iran|american[- ]iran)\b",
                re.I,
            ),
            re.compile(r"(伊朗|德黑兰|霍尔木兹|真主党|胡塞|美伊|以伊)"),
        ],
    },
    "ukraine": {
        "id": "ukraine",
        "label": "俄乌战争",
        "blurb": "俄罗斯—乌克兰战事、谈判与能源地缘进展",
        "query": "乌克兰 OR Ukraine OR 俄乌",
        "patterns": [
            re.compile(
                r"\b(ukraine|ukrainian|kyiv|kiev|zelensky|zelenskyy|putin|"
                r"moscow|kremlin|crimea|donbas|donetsk|russia[- ]ukraine|"
                r"russian invasion)\b",
                re.I,
            ),
            re.compile(r"(乌克兰|基辅|泽连斯基|普京|克里米亚|顿巴斯|俄乌|莫斯科)"),
        ],
    },
}


def item_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(k) or "")
        for k in (
            "title",
            "title_zh",
            "summary",
            "brief_zh",
            "theme",
            "source",
            "sentiment_logic",
        )
    )


def match_topic(item: dict[str, Any], topic_id: str) -> bool:
    topic = TOPICS.get(topic_id)
    if not topic:
        return False
    text = item_text(item)
    return any(p.search(text) for p in topic["patterns"])


def filter_topic_items(
    items: list[dict[str, Any]],
    topic_id: str,
    *,
    sort: str = "latest",
    sentiment: str | None = None,
) -> list[dict[str, Any]]:
    rows = [i for i in items if match_topic(i, topic_id)]
    if sentiment and sentiment != "all":
        rows = [i for i in rows if i.get("sentiment") == sentiment]
    return sort_items(rows, sort=sort)


def event_matches_topic(event: dict[str, Any], topic_id: str) -> bool:
    topic = TOPICS.get(topic_id)
    if not topic:
        return False
    blob = " ".join(
        [
            str(event.get("title") or ""),
            str(event.get("title_zh") or ""),
            " ".join(str(k) for k in (event.get("keywords") or [])),
            " ".join(
                str(i.get("title") or "")
                for i in (event.get("items") or event.get("timeline") or [])[:6]
            ),
        ]
    )
    return any(p.search(blob) for p in topic["patterns"])


def topic_bearish_analysis(
    items: list[dict[str, Any]], topic_id: str
) -> dict[str, Any]:
    topic = TOPICS.get(topic_id) or {"label": topic_id, "blurb": ""}
    matched = filter_topic_items(items, topic_id, sort="latest")
    bears = [i for i in matched if i.get("sentiment") == "bearish"]
    bulls = [i for i in matched if i.get("sentiment") == "bullish"]
    neutrals = [i for i in matched if i.get("sentiment") == "neutral"]
    bears_sorted = sort_items(bears, sort="bearish")
    scores = [float(i.get("sentiment_score") or 0) for i in matched]
    avg = sum(scores) / len(scores) if scores else 0.0

    factor_counts: dict[str, int] = {}
    for item in bears_sorted[:12]:
        for factor in item.get("bear_factors") or item.get("sentiment_factors") or []:
            key = str(factor).strip()
            if not key:
                continue
            factor_counts[key] = factor_counts.get(key, 0) + 1
    top_factors = sorted(factor_counts.items(), key=lambda x: (-x[1], x[0]))[:5]

    logics = [
        str(i.get("sentiment_logic") or i.get("sentiment_reason") or "").strip()
        for i in bears_sorted[:4]
    ]
    logics = [x for x in logics if x]

    if not matched:
        assessment = f"近端公开源暂未抓到足够的{topic['label']}相关报道，暂不做利空强弱结论。"
    elif not bears:
        assessment = (
            f"{topic['label']}相关更新以中性/偏多为主（共 {len(matched)} 条），"
            "暂未形成集中的利空压制叙事。"
        )
    else:
        lead = bears_sorted[0]
        lead_title = lead.get("title_zh") or lead.get("title") or "相关头条"
        assessment = (
            f"{topic['label']}近端共 {len(matched)} 条，其中利空 {len(bears)} 条"
            f"（均分 {avg:.2f}）。主导压制线索：{lead_title}。"
        )
        if logics:
            assessment += f" 评判要点：{logics[0]}"

    return {
        "topic_id": topic_id,
        "label": topic.get("label") or topic_id,
        "blurb": topic.get("blurb") or "",
        "query": topic.get("query") or "",
        "counts": {
            "total": len(matched),
            "bearish": len(bears),
            "bullish": len(bulls),
            "neutral": len(neutrals),
        },
        "avg_score": round(avg, 3),
        "assessment": assessment,
        "top_factors": [name for name, _ in top_factors],
        "spotlight": bears_sorted[:4],
        "latest": sort_items(matched, sort="latest")[:6],
    }


def build_war_desk(
    items: list[dict[str, Any]],
    event_threads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    threads = event_threads or []
    columns: dict[str, Any] = {}
    analyses: list[dict[str, Any]] = []

    for topic_id in ("us_iran", "ukraine"):
        topic = TOPICS[topic_id]
        analysis = topic_bearish_analysis(items, topic_id)
        latest = analysis["latest"]
        events = [e for e in threads if event_matches_topic(e, topic_id)][:3]
        columns[topic_id] = {
            "id": topic_id,
            "label": topic["label"],
            "blurb": topic["blurb"],
            "query": topic["query"],
            "latest": latest,
            "events": events,
            "counts": analysis["counts"],
        }
        analyses.append(analysis)

    return {
        "columns": columns,
        "bearish_analysis": analyses,
        "updated_hint": "与情报流同源，按标题/摘要/主题匹配地缘冲突线索",
    }
