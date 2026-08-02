"""Rule-based Chinese briefs for English market headlines."""

from __future__ import annotations

import re
from typing import Any

THEME_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"\b(rate cut|cuts rates|cutting rates|easing)\b", re.I),
        "降息预期",
        "标题指向宽松/降息叙事，关注利率期货定价与风险资产弹性。",
    ),
    (
        re.compile(r"\b(rate hike|hikes rates|hawkish|tightening)\b", re.I),
        "鹰派/紧缩",
        "偏鹰或紧缩信号，短端利率与美元往往更敏感。",
    ),
    (
        re.compile(r"\b(inflation|cpi|ppi|pce)\b", re.I),
        "通胀数据",
        "通胀相关线索，影响联储反应函数与实际利率预期。",
    ),
    (
        re.compile(r"\b(treasury|yield|bond|auction|duration)\b", re.I),
        "国债/收益率",
        "债券市场动态，留意曲线形态与拍卖需求。",
    ),
    (
        re.compile(r"\b(fed|fomc|powell|governor|federal reserve)\b", re.I),
        "美联储",
        "官方或官员沟通，重点看政策路径措辞变化。",
    ),
    (
        re.compile(r"\b(tariff|trade war|sanctions|geopolit)\b", re.I),
        "贸易/地缘",
        "政策与地缘冲击，常通过风险溢价与供应链预期传导。",
    ),
    (
        re.compile(r"\b(sec|regulation|antitrust|probe|investigation)\b", re.I),
        "监管政策",
        "监管与执法动态，对板块估值与合规成本更直接。",
    ),
    (
        re.compile(r"\b(jobs|payroll|unemployment|labor)\b", re.I),
        "就业市场",
        "就业数据影响“软着陆”叙事与降息时点博弈。",
    ),
]

CATEGORY_FALLBACK: dict[str, tuple[str, str]] = {
    "fed": ("美联储动态", "来自联储体系的政策沟通，建议对照利率路径预期阅读。"),
    "treasury": ("国债与财政", "收益率或财政部相关消息，关注供给与期限溢价。"),
    "policy": ("政策监管", "政策/监管线索，评估对行业与风险偏好的影响。"),
    "politics": ("时政地缘", "政治或地缘事件，关注避险与波动率反应。"),
    "markets": ("市场动态", "市场层面新闻，结合指数与板块表现交叉验证。"),
}


def build_brief(item: dict[str, Any]) -> dict[str, str]:
    text = f"{item.get('title', '')} {item.get('summary', '')}"
    category = item.get("category") or "markets"

    theme = ""
    note = ""
    for pattern, theme_name, theme_note in THEME_RULES:
        if pattern.search(text):
            theme, note = theme_name, theme_note
            break
    if not theme:
        theme, note = CATEGORY_FALLBACK.get(
            category, ("市场观察", "建议结合利率、风险偏好与政策日程综合判断。")
        )

    brief = f"【{theme}】{note}"
    return {
        "theme": theme,
        "brief_zh": brief,
    }


def enrich_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in items:
        row = dict(item)
        row.update(build_brief(item))
        enriched.append(row)
    return enriched


def daily_digest(items: list[dict[str, Any]], limit: int = 5) -> dict[str, Any]:
    """Aggregate top themes from the freshest headlines."""
    counts: dict[str, int] = {}
    samples: dict[str, str] = {}
    for item in items[:40]:
        theme = item.get("theme") or build_brief(item)["theme"]
        counts[theme] = counts.get(theme, 0) + 1
        samples.setdefault(theme, item.get("title") or "")

    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    bullets = [
        {
            "theme": theme,
            "count": count,
            "example": samples.get(theme, ""),
        }
        for theme, count in ranked
    ]
    if not bullets:
        summary = "暂无足够头条可提炼简报。"
    else:
        parts = [f"{b['theme']}（{b['count']}）" for b in bullets[:4]]
        summary = "近端头条主题：" + "、".join(parts) + "。"
    return {"summary": summary, "themes": bullets}
