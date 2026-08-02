"""Upcoming FOMC/macro calendar with equity risk interpretation."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# Official tentative FOMC schedule (Fed announcement, Aug 2024)
FOMC_MEETINGS: list[dict[str, Any]] = [
    {"start": date(2026, 1, 27), "end": date(2026, 1, 28), "sep": False},
    {"start": date(2026, 3, 17), "end": date(2026, 3, 18), "sep": True},
    {"start": date(2026, 4, 28), "end": date(2026, 4, 29), "sep": False},
    {"start": date(2026, 6, 16), "end": date(2026, 6, 17), "sep": True},
    {"start": date(2026, 7, 28), "end": date(2026, 7, 29), "sep": False},
    {"start": date(2026, 9, 15), "end": date(2026, 9, 16), "sep": True},
    {"start": date(2026, 10, 27), "end": date(2026, 10, 28), "sep": False},
    {"start": date(2026, 12, 8), "end": date(2026, 12, 9), "sep": True},
    {"start": date(2027, 1, 26), "end": date(2027, 1, 27), "sep": False},
]

MACRO_WATCH: list[dict[str, Any]] = [
    {
        "date": date(2026, 8, 1),
        "title": "非农就业报告 (NFP)",
        "kind": "labor",
        "note": "就业与薪资是联储反应函数核心变量之一",
    },
    {
        "date": date(2026, 8, 12),
        "title": "CPI 通胀数据",
        "kind": "inflation",
        "note": "关注核心 CPI 与服务业粘性",
    },
    {
        "date": date(2026, 8, 14),
        "title": "PPI 生产者物价",
        "kind": "inflation",
        "note": "成本端压力的领先观察",
    },
    {
        "date": date(2026, 8, 19),
        "title": "7 月 FOMC 会议纪要",
        "kind": "fed",
        "note": "通常在决议后约三周公布，读内部分歧",
    },
    {
        "date": date(2026, 9, 4),
        "title": "非农就业报告 (NFP)",
        "kind": "labor",
        "note": "9 月议息前最后一轮关键就业数据之一",
    },
    {
        "date": date(2026, 9, 10),
        "title": "CPI 通胀数据",
        "kind": "inflation",
        "note": "9 月 FOMC（含点阵图）前关键输入",
    },
    {
        "date": date(2026, 9, 15),
        "title": "国债关键拍卖窗口",
        "kind": "treasury",
        "note": "关注票息标售结果与尾部分布对收益率的影响",
    },
]

# Pre-event equity risk playbook by kind
KIND_PLAYBOOK: dict[str, dict[str, Any]] = {
    "fomc": {
        "pre_bias": "bearish",
        "pre_label": "偏空",
        "pre_score": -0.35,
        "pre_reason": "议息窗口事件风险上升，波动率与利率敏感板块常先承压。",
        "bull_case": "声明/点阵图偏鸽、暗示更快降息 → 风险资产利多。",
        "bear_case": "声明偏鹰、上修中性利率或推迟降息 → 股市利空。",
        "watch": ["政策利率", "点阵图", "经济预测", "主席措辞"],
    },
    "fed": {
        "pre_bias": "neutral",
        "pre_label": "中性偏空",
        "pre_score": -0.2,
        "pre_reason": "纪要/讲话重定价政策路径，分歧加大时常抬升不确定性溢价。",
        "bull_case": "纪要显示更多委员倾向宽松 → 偏多。",
        "bear_case": "纪要强调通胀风险或反对过早降息 → 偏空。",
        "watch": ["投票分歧", "通胀风险表述", "就业评估"],
    },
    "inflation": {
        "pre_bias": "bearish",
        "pre_label": "偏空",
        "pre_score": -0.4,
        "pre_reason": "通胀数据是当前最强定价因子之一，超预期上行对估值压制最直接。",
        "bull_case": "CPI/PPI 低于预期、核心回落 → 降息预期升温，利多。",
        "bear_case": "通胀黏性或再加速 → 实际利率上行预期，利空股市。",
        "watch": ["核心CPI", "服务通胀", "住房项", "环比动量"],
    },
    "labor": {
        "pre_bias": "neutral",
        "pre_label": "中性",
        "pre_score": -0.1,
        "pre_reason": "就业是“软着陆”关键变量：太强抑降息，太弱又触发衰退担忧。",
        "bull_case": "就业温和降温但非塌陷 → 利好降息叙事。",
        "bear_case": "薪资/就业过热，或失业骤升指向衰退 → 对股市偏空。",
        "watch": ["非农新增", "失业率", "时薪", "劳动参与率"],
    },
    "treasury": {
        "pre_bias": "bearish",
        "pre_label": "偏空",
        "pre_score": -0.28,
        "pre_reason": "供给拍卖若需求疲弱，易推升期限溢价并压制成长股估值。",
        "bull_case": "拍卖尾部分布紧、间接标购强 → 收益率稳定/回落，偏多。",
        "bear_case": "尾部偏宽、需求不足 → 收益率冲高，股市承压。",
        "watch": ["标售倍数", "间接标购", "尾部", "10Y/30Y 收益率"],
    },
}


def _fmt_range(start: date, end: date) -> str:
    if start == end:
        return start.strftime("%m/%d")
    if start.month == end.month:
        return f"{start.strftime('%m/%d')}–{end.strftime('%d')}"
    return f"{start.strftime('%m/%d')}–{end.strftime('%m/%d')}"


def assess_calendar_event(event: dict[str, Any]) -> dict[str, Any]:
    """Attach pre-event equity bias + bull/bear scenario logic."""
    kind = event.get("kind") or "fed"
    play = KIND_PLAYBOOK.get(kind, KIND_PLAYBOOK["fed"])
    days = int(event.get("days_until") or 0)
    sep = bool(event.get("sep"))

    score = float(play["pre_score"])
    # Closer events carry more near-term risk premium
    if days <= 1:
        score -= 0.12
    elif days <= 3:
        score -= 0.08
    elif days <= 7:
        score -= 0.04

    # SEP / dot-plot meetings are higher-impact
    if kind == "fomc" and (sep or "点阵图" in (event.get("title") or "")):
        score -= 0.1

    score = max(-1.0, min(1.0, round(score, 3)))
    if score <= -0.45:
        bias, label = "bearish", "利空"
    elif score <= -0.18:
        bias, label = "bearish", "偏空"
    elif score >= 0.22:
        bias, label = "bullish", "偏多"
    else:
        bias, label = "neutral", play.get("pre_label") or "中性"

    proximity = (
        "临近公布，事件风险溢价抬升。"
        if days <= 3
        else "仍有缓冲，但应提前关注预期差。"
        if days <= 10
        else "日程较远，作前瞻布局参考。"
    )

    logic = (
        f"结论：{label}（会前风险分 {score:+.2f}）。"
        f"{play['pre_reason']}{proximity}"
        f" 利空情景：{play['bear_case']}"
        f" 利多情景：{play['bull_case']}"
    )

    return {
        **event,
        "sentiment": bias,
        "sentiment_label": label,
        "sentiment_score": score,
        "sentiment_logic": logic,
        "bull_case": play["bull_case"],
        "bear_case": play["bear_case"],
        "watch_points": play["watch"],
        "pre_reason": play["pre_reason"],
    }


def upcoming_calendar(today: date | None = None, limit: int = 8) -> list[dict[str, Any]]:
    """Build a merged upcoming calendar of FOMC + macro watch items."""
    today = today or datetime.now(tz=ET).date()
    events: list[dict[str, Any]] = []

    for meeting in FOMC_MEETINGS:
        decision = meeting["end"]
        if decision < today:
            continue
        sep = bool(meeting["sep"])
        title = "FOMC 利率决议" + (" · 点阵图/SEP" if sep else "")
        events.append(
            {
                "date": decision.isoformat(),
                "sort_date": decision,
                "title": title,
                "subtitle": f"会议 {_fmt_range(meeting['start'], meeting['end'])} · 美东 14:00 声明",
                "kind": "fomc",
                "sep": sep,
                "note": "随后约 14:30 主席发布会" + ("，并更新经济预测摘要" if sep else ""),
                "url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
                "days_until": (decision - today).days,
            }
        )

    for item in MACRO_WATCH:
        d = item["date"]
        if d < today - timedelta(days=1):
            continue
        events.append(
            {
                "date": d.isoformat(),
                "sort_date": d,
                "title": item["title"],
                "subtitle": d.strftime("%Y-%m-%d"),
                "kind": item["kind"],
                "sep": False,
                "note": item.get("note", ""),
                "url": None,
                "days_until": (d - today).days,
            }
        )

    events.sort(key=lambda e: (e["sort_date"], e["title"]))
    trimmed = [assess_calendar_event(row) for row in events[:limit]]
    for row in trimmed:
        row.pop("sort_date", None)
    return trimmed


def next_fomc(today: date | None = None) -> dict[str, Any] | None:
    today = today or datetime.now(tz=ET).date()
    for meeting in FOMC_MEETINGS:
        if meeting["end"] >= today:
            base = {
                "start": meeting["start"].isoformat(),
                "end": meeting["end"].isoformat(),
                "sep": meeting["sep"],
                "days_until": (meeting["end"] - today).days,
                "label": "FOMC 利率决议"
                + ("（含点阵图）" if meeting["sep"] else ""),
                "kind": "fomc",
                "title": "FOMC 利率决议" + (" · 点阵图/SEP" if meeting["sep"] else ""),
            }
            assessed = assess_calendar_event(base)
            return {
                **base,
                "sentiment": assessed["sentiment"],
                "sentiment_label": assessed["sentiment_label"],
                "sentiment_score": assessed["sentiment_score"],
                "sentiment_logic": assessed["sentiment_logic"],
                "bull_case": assessed["bull_case"],
                "bear_case": assessed["bear_case"],
            }
    return None
