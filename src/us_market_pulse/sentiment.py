"""Rule-based equity market bias with per-item logic verdict for every headline."""

from __future__ import annotations

import re
from typing import Any

BULLISH_RULES: list[tuple[re.Pattern[str], float, str]] = [
    (re.compile(r"\b(rate cut|cuts rates|cutting rates|easing cycle|dovish)\b", re.I), 0.55, "降息/鸽派"),
    (re.compile(r"\b(soft landing|risk-?on|rally|soar|record high)\b", re.I), 0.4, "风险偏好回升"),
    (re.compile(r"\b(cooling inflation|inflation cools|disinflation|lower than expected)\b", re.I), 0.45, "通胀降温"),
    (
        re.compile(
            r"\b(stimulus|tax cut|peace deal|de-?escalat(?:ion|es|ed|ing)?|"
            r"(?:agree(?:s|d)?|reach(?:es|ed)?|broker(?:s|ed)?)\s+(?:a\s+)?ceasefire)\b",
            re.I,
        ),
        0.35,
        "宽松/缓和",
    ),
    (re.compile(r"\b(beat estimates|earnings beat|strong jobs|solid growth)\b", re.I), 0.3, "基本面超预期"),
    (re.compile(r"\b(debt ceiling (deal|agreement)|government reopens)\b", re.I), 0.35, "财政风险解除"),
    (re.compile(r"\b(buyback|dividend hike|upgrade to (buy|overweight))\b", re.I), 0.25, "股东回报/上调"),
]

BEARISH_RULES: list[tuple[re.Pattern[str], float, str]] = [
    (re.compile(r"\b(rate hike|hikes rates|hawkish|higher for longer|no cut)\b", re.I), -0.6, "加息/鹰派"),
    (re.compile(r"\b(recession|stagflation|hard landing|risk-?off)\b", re.I), -0.55, "衰退/避险"),
    (re.compile(r"\b(sell-?off|selloff|plunge|crash|collapse|rout|tumble)\b", re.I), -0.55, "下跌/崩盘叙事"),
    (
        re.compile(
            r"\b(hot(?:ter)? inflation|inflation (surges?|jumps?|accelerat\w*)|"
            r"sticky inflation|above[- ]expected inflation)\b",
            re.I,
        ),
        -0.5,
        "通胀升温",
    ),
    (re.compile(r"\b(tariff|tariffs|trade war|trade tensions?|import duty|retaliat\w*)\b", re.I), -0.45, "关税/贸易摩擦"),
    (
        re.compile(
            r"\b(sanctions?|military (action|strike|attack)|airstrike|missile|"
            r"geopolitical (risk|tensions?)|war risk|invasion|escalat(?:e|ion|ing))\b",
            re.I,
        ),
        -0.5,
        "地缘/军事风险",
    ),
    (
        re.compile(
            r"\b(travel (risk|warning|advisory)|embassy|embassies warn|evacuate|conflict zone)\b",
            re.I,
        ),
        -0.35,
        "安全/旅行预警",
    ),
    (
        re.compile(
            r"\b(bank (stress|failure|run)|credit crunch|default|insolvency|"
            r"liquidity crisis|contagion)\b",
            re.I,
        ),
        -0.55,
        "金融压力",
    ),
    (
        re.compile(
            r"\b(government shutdown|debt ceiling (standoff|crisis|breach)|"
            r"fiscal cliff|credit downgrade|downgrade)\b",
            re.I,
        ),
        -0.45,
        "财政/评级风险",
    ),
    (
        re.compile(
            r"\b(yields? (rise|jump|surge|spike)|bond sell-?off|higher yields|soaring yields)\b",
            re.I,
        ),
        -0.4,
        "收益率上行",
    ),
    (
        re.compile(
            r"\b(miss(?:es|ed)? estimates|profit warning|guidance cut|"
            r"cuts outlook|weak(er)? demand|margin pressure)\b",
            re.I,
        ),
        -0.4,
        "盈利不及预期",
    ),
    (
        re.compile(
            r"\b(layoff|layoffs|job cuts|weak(er)? jobs|unemployment (rises?|jumps?)|"
            r"hiring freeze)\b",
            re.I,
        ),
        -0.35,
        "就业走弱",
    ),
    (
        re.compile(
            r"\b(probe|investigation|antitrust|lawsuit|enforcement action|"
            r"fraud|indict(?:ment|ed)|ban on|export ban)\b",
            re.I,
        ),
        -0.3,
        "监管/诉讼冲击",
    ),
    (
        re.compile(
            r"\b(oil (spike|surges?|jumps?)|energy shock|supply shock|"
            r"dollar (surge|strength)|strong(er)? dollar)\b",
            re.I,
        ),
        -0.3,
        "大宗/美元冲击",
    ),
    (
        re.compile(r"\b(volatility spike|vix (surges?|jumps?)|flight to safety|safe[- ]haven)\b", re.I),
        -0.35,
        "波动率上升",
    ),
]

# Soft context factors — always help explain logic even when score stays near 0
CONTEXT_RULES: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"\b(fed|fomc|powell|federal reserve)\b", re.I), "联储政策相关", -0.05),
    (re.compile(r"\b(treasury|yield|bond|auction)\b", re.I), "国债/利率相关", -0.04),
    (re.compile(r"\b(sec|regulation|compliance)\b", re.I), "监管政策相关", -0.04),
    (re.compile(r"\b(trump|biden|congress|white house|election)\b", re.I), "时政博弈相关", -0.06),
    (re.compile(r"\b(iran|israel|gaza|ukraine|china|russia|war|conflict)\b", re.I), "地缘叙事相关", -0.08),
    (re.compile(r"\b(earnings|revenue|guidance|ceo|company|stock|shares)\b", re.I), "公司/股市相关", 0.0),
    (re.compile(r"\b(inflation|cpi|ppi|pce)\b", re.I), "通胀数据相关", -0.03),
    (re.compile(r"\b(jobs|payroll|labor|unemployment)\b", re.I), "就业数据相关", 0.0),
    (re.compile(r"\b(dies?|obituar|celebrity|sopranos|girlfriend|sister|wedding)\b", re.I), "非宏观噪声", 0.02),
    (re.compile(r"\b(social security|medicare)\b", re.I), "社保民生话题", 0.0),
]

NEGATION_GEOPOLITICS = re.compile(
    r"\b(war|military|missile|strike|complicat|hostage|sanction|risk|conflict|attack)\b",
    re.I,
)

CATEGORY_PRIOR: dict[str, float] = {
    "politics": -0.1,
    "policy": -0.05,
    "fed": 0.0,
    "treasury": -0.03,
    "markets": 0.0,
}

CATEGORY_FACTOR: dict[str, str] = {
    "politics": "时政地缘频道",
    "policy": "政策监管频道",
    "fed": "美联储频道",
    "treasury": "国债频道",
    "markets": "市场新闻频道",
}


def _label(score: float) -> tuple[str, str, str]:
    if score >= 0.45:
        return "bullish", "利多", "强"
    if score >= 0.22:
        return "bullish", "偏多", "中"
    if score <= -0.5:
        return "bearish", "利空", "强"
    if score <= -0.2:
        return "bearish", "偏空", "中"
    return "neutral", "中性", "弱"


def _build_logic(
    *,
    bias: str,
    label_zh: str,
    score: float,
    factors: list[str],
    bull_factors: list[str],
    bear_factors: list[str],
    context_factors: list[str],
    category: str,
) -> str:
    """Always produce an explicit per-item logic explanation."""
    cat = CATEGORY_FACTOR.get(category, "综合资讯")
    parts = [f"结论：{label_zh}（得分 {score:+.2f}）"]

    if bear_factors:
        parts.append("利空依据：" + "、".join(bear_factors[:4]))
    if bull_factors:
        parts.append("利多依据：" + "、".join(bull_factors[:4]))
    if context_factors:
        parts.append("语境：" + "、".join(context_factors[:3]))
    else:
        parts.append(f"语境：{cat}")

    if bias == "bearish":
        parts.append("传导：压制风险偏好 / 抬升避险与波动溢价。")
    elif bias == "bullish":
        parts.append("传导：利好估值与风险资产弹性。")
    else:
        if bear_factors and bull_factors:
            parts.append("传导：多空线索并存，净影响接近中性。")
        elif bear_factors:
            parts.append("传导：存在压制因素但强度不足，暂标中性观察。")
        elif bull_factors:
            parts.append("传导：存在支撑因素但强度不足，暂标中性观察。")
        elif context_factors:
            parts.append("传导：仅有弱语境线索，短期对指数定价影响有限。")
        else:
            parts.append("传导：未识别明确定价因子，对指数影响有限。")

    return " ".join(parts)


def score_sentiment(item: dict[str, Any]) -> dict[str, Any]:
    title = item.get("title") or ""
    summary = item.get("summary") or ""
    category = item.get("category") or "markets"
    text = f"{title} {summary}"

    score = CATEGORY_PRIOR.get(category, 0.0)
    bull_factors: list[str] = []
    bear_factors: list[str] = []
    context_factors: list[str] = []
    bearish_hits = 0
    bullish_hits = 0

    for pattern, weight, factor in BULLISH_RULES:
        t_hit = bool(pattern.search(title))
        s_hit = bool(pattern.search(summary))
        if not t_hit and not s_hit:
            continue
        w = weight
        if "ceasefire" in pattern.pattern and NEGATION_GEOPOLITICS.search(text):
            w *= 0.2
        contrib = w if t_hit else w * 0.45
        score += contrib
        if factor not in bull_factors:
            bull_factors.append(factor)
        bullish_hits += 1

    for pattern, weight, factor in BEARISH_RULES:
        t_hit = bool(pattern.search(title))
        s_hit = bool(pattern.search(summary))
        if not t_hit and not s_hit:
            continue
        contrib = weight * (1.15 if t_hit else 0.45)
        score += contrib
        if factor not in bear_factors:
            bear_factors.append(factor)
        bearish_hits += 1

    for pattern, factor, prior in CONTEXT_RULES:
        if pattern.search(text):
            if factor not in context_factors:
                context_factors.append(factor)
            # Only apply soft prior when hard rules didn't already fire heavily
            if bearish_hits == 0 and bullish_hits == 0:
                score += prior

    if bearish_hits >= 2:
        score -= 0.12
    if bearish_hits >= 3:
        score -= 0.1

    # Always keep at least one explaining factor
    factors = bear_factors + bull_factors
    if not factors:
        factors = context_factors[:2] or [CATEGORY_FACTOR.get(category, "综合资讯")]

    score = max(-1.0, min(1.0, round(score, 3)))
    bias, label_zh, strength = _label(score)
    logic = _build_logic(
        bias=bias,
        label_zh=label_zh,
        score=score,
        factors=factors,
        bull_factors=bull_factors,
        bear_factors=bear_factors,
        context_factors=context_factors,
        category=category,
    )

    reasons = {
        "bullish": "对风险资产偏友好。",
        "bearish": "对股市偏压制。",
        "neutral": "方向信号偏弱或噪声较高。",
    }

    return {
        "sentiment": bias,
        "sentiment_label": label_zh,
        "sentiment_score": score,
        "sentiment_strength": strength,
        "sentiment_reason": reasons[bias],
        "sentiment_logic": logic,
        "sentiment_factors": factors[:6],
        "bull_factors": bull_factors[:4],
        "bear_factors": bear_factors[:4],
        "sentiment_hits": bearish_hits + bullish_hits,
        "is_bearish": bias == "bearish",
        "is_bullish": bias == "bullish",
    }


def enrich_sentiment(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        row = dict(item)
        row.update(score_sentiment(item))
        out.append(row)
    return out


def sentiment_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    bull = [i for i in items if i.get("sentiment") == "bullish"]
    bear = [i for i in items if i.get("sentiment") == "bearish"]
    neut = [i for i in items if i.get("sentiment") == "neutral"]
    avg = 0.0
    if items:
        avg = round(sum(float(i.get("sentiment_score") or 0) for i in items) / len(items), 3)

    if avg >= 0.15:
        tilt, tilt_zh = "bullish", "偏多"
    elif avg <= -0.15:
        tilt, tilt_zh = "bearish", "偏空"
    else:
        tilt, tilt_zh = "neutral", "中性偏混"

    def top(rows: list[dict[str, Any]], n: int = 3) -> list[dict[str, str]]:
        ranked = sorted(
            rows, key=lambda x: abs(float(x.get("sentiment_score") or 0)), reverse=True
        )
        return [
            {
                "title": r.get("title_zh") or r.get("title") or "",
                "label": r.get("sentiment_label") or "",
                "score": str(r.get("sentiment_score")),
                "url": r.get("url") or "",
                "factors": "、".join(r.get("sentiment_factors") or []),
                "logic": r.get("sentiment_logic") or "",
            }
            for r in ranked[:n]
        ]

    return {
        "tilt": tilt,
        "tilt_zh": tilt_zh,
        "avg_score": avg,
        "counts": {
            "bullish": len(bull),
            "bearish": len(bear),
            "neutral": len(neut),
        },
        "top_bullish": top(bull),
        "top_bearish": top(bear),
        "blurb": (
            f"近端样本情绪：{tilt_zh}（利多 {len(bull)} / 利空 {len(bear)} / 中性 {len(neut)}，"
            f"均分 {avg:+.2f}）。每条均含利多/利空逻辑评判。"
        ),
    }
