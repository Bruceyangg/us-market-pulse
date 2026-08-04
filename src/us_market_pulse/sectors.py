"""Hot sector board: AI desk, ETF tape, stock picks, value-chain blurbs."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from us_market_pulse.markets import PORTFOLIO_TIMEFRAMES, fetch_symbol_bundle
from us_market_pulse.topics import TOPICS, filter_topic_items, topic_bearish_analysis

USER_AGENT = "Mozilla/5.0 (compatible; PulseDesk/1.0)"

# Lightweight frames for sector tape (fewer Yahoo calls than full board)
SECTOR_TIMEFRAMES = [
    tf
    for tf in PORTFOLIO_TIMEFRAMES
    if tf["id"] in {"intraday", "day", "month", "quarter"}
]

SECTOR_ETFS: list[dict[str, Any]] = [
    {
        "id": "ai",
        "symbol": "BOTZ",
        "label": "AI / 机器人",
        "short": "AI",
        "topic_id": "ai",
        "blurb": "人工智能、机器人与自动化主题",
        "picks": ["NVDA", "AMD", "AVGO", "PLTR", "SMCI"],
    },
    {
        "id": "semis",
        "symbol": "SMH",
        "label": "半导体",
        "short": "Semis",
        "topic_id": "semis",
        "blurb": "芯片设计、制造与设备周期",
        "picks": ["NVDA", "TSM", "ASML", "AVGO", "AMAT"],
    },
    {
        "id": "tech",
        "symbol": "XLK",
        "label": "科技",
        "short": "Tech",
        "topic_id": "tech",
        "blurb": "广义科技板块（软件 + 硬件）",
        "picks": ["MSFT", "AAPL", "NVDA", "AVGO", "CRM"],
    },
    {
        "id": "nasdaq",
        "symbol": "QQQ",
        "label": "纳指百强",
        "short": "QQQ",
        "topic_id": "tech",
        "blurb": "纳斯达克 100 成长与流动性风向标",
        "picks": ["NVDA", "MSFT", "META", "AMZN", "GOOGL"],
    },
    {
        "id": "cloud",
        "symbol": "SKYY",
        "label": "云计算",
        "short": "Cloud",
        "topic_id": "cloud",
        "blurb": "云基础设施与软件即服务",
        "picks": ["MSFT", "AMZN", "GOOGL", "ORCL", "SNOW"],
    },
    {
        "id": "energy",
        "symbol": "XLE",
        "label": "能源",
        "short": "Energy",
        "topic_id": "energy",
        "blurb": "原油、天然气与油气产业链",
        "picks": ["XOM", "CVX", "COP", "SLB", "EOG"],
    },
    {
        "id": "finance",
        "symbol": "XLF",
        "label": "金融",
        "short": "Finance",
        "topic_id": "finance",
        "blurb": "银行、券商与保险利率敏感板块",
        "picks": ["JPM", "BAC", "GS", "MS", "V"],
    },
    {
        "id": "health",
        "symbol": "XLV",
        "label": "医疗",
        "short": "Health",
        "topic_id": "health",
        "blurb": "制药、器械与医疗保健防御板块",
        "picks": ["LLY", "UNH", "JNJ", "ABBV", "MRK"],
    },
]

# Extend topics locally for sector news matching (AI is also in topics.TOPICS if present)
SECTOR_TOPIC_PATTERNS: dict[str, dict[str, Any]] = {
    "ai": {
        "id": "ai",
        "label": "AI 板块",
        "blurb": "人工智能、算力、大模型与 AI 基础设施",
        "query": "人工智能 OR AI OR Nvidia",
    },
    "semis": {
        "id": "semis",
        "label": "半导体",
        "blurb": "芯片、代工、设备与存储周期",
        "query": "半导体 OR chip OR semiconductor",
    },
    "tech": {
        "id": "tech",
        "label": "科技",
        "blurb": "科技巨头与软件硬件联动",
        "query": "科技股 OR Big Tech OR Nasdaq",
    },
    "cloud": {
        "id": "cloud",
        "label": "云计算",
        "blurb": "云资本开支、SaaS 与数据中心",
        "query": "云计算 OR cloud OR data center",
    },
    "energy": {
        "id": "energy",
        "label": "能源",
        "blurb": "油价、天然气与能源股",
        "query": "原油 OR oil OR energy stocks",
    },
    "finance": {
        "id": "finance",
        "label": "金融",
        "blurb": "银行、利率与金融监管",
        "query": "银行 OR banks OR financials",
    },
    "health": {
        "id": "health",
        "label": "医疗",
        "blurb": "制药、医保与生物科技",
        "query": "制药 OR biotech OR healthcare",
    },
}

VALUE_CHAIN: dict[str, dict[str, Any]] = {
    "NVDA": {
        "name": "英伟达",
        "business": "以 GPU 与 CUDA 生态为核心，向数据中心、游戏与汽车提供 AI 加速计算平台。",
        "industry": "半导体（无晶圆设计）+ AI 基础设施软件栈。",
        "chain_position": "产业链上游核心算力提供商：设计 GPU → 台积电先进制程代工 → HBM 存储配套 → 服务器 OEM/ODM → 云厂商训练/推理。",
        "upstream": ["台积电 (TSM)", "SK 海力士 / 美光 HBM", "封装与基板供应商"],
        "downstream": ["微软 / 谷歌 / 亚马逊云", "超微 / 戴尔服务器", "企业 AI 应用层"],
        "bear_risks": ["出口管制", "云资本开支周期回落", "自研 ASIC 替代", "估值波动"],
    },
    "AMD": {
        "name": "超威",
        "business": "CPU/GPU/加速卡并行布局，在数据中心与 PC 端与英伟达、英特尔竞争。",
        "industry": "半导体设计，覆盖高性能计算与客户端。",
        "chain_position": "算力层挑战者：服务器 CPU + AI GPU，依赖台积电先进制程，面向云与企业客户。",
        "upstream": ["台积电", "封装与内存"],
        "downstream": ["云厂商", "OEM PC/服务器", "游戏与工作站"],
        "bear_risks": ["CUDA 生态粘性", "制程产能分配", "价格竞争"],
    },
    "AVGO": {
        "name": "博通",
        "business": "定制 ASIC、网络芯片与企业软件（含 VMware）组合，吃云资本开支与企业 IT。",
        "industry": "半导体 + 企业基础设施软件。",
        "chain_position": "云侧定制算力与网络互联关键环节，介于通用 GPU 与超大规模自研芯片之间。",
        "upstream": ["代工厂与封装"],
        "downstream": ["超大规模云厂商", "电信与企业网络"],
        "bear_risks": ["大客户订单波动", "反垄断/整合风险", "利率敏感估值"],
    },
    "TSM": {
        "name": "台积电",
        "business": "全球领先晶圆代工，掌握先进制程产能，为 AI GPU/ASIC 提供制造底座。",
        "industry": "半导体制造（Foundry）。",
        "chain_position": "制造中枢：承接设计公司订单，向上连接设备材料，向下决定先进芯片供给。",
        "upstream": ["ASML 光刻", "应用材料等设备", "硅片与化学品"],
        "downstream": ["NVDA / AMD / AVGO / 苹果等设计公司"],
        "bear_risks": ["地缘政治", "产能扩张节奏", "客户库存周期"],
    },
    "ASML": {
        "name": "阿斯麦",
        "business": "EUV/DUV 光刻机几乎独家供应，是先进制程扩张的瓶颈设备商。",
        "industry": "半导体设备。",
        "chain_position": "设备最上游：没有 EUV 则先进制程无法扩张，直接影响台积电/三星/英特尔产能。",
        "upstream": ["光学与精密零部件供应链"],
        "downstream": ["台积电、三星、英特尔等晶圆厂"],
        "bear_risks": ["出口许可", "晶圆厂资本开支放缓", "交期与维护合同波动"],
    },
    "MSFT": {
        "name": "微软",
        "business": "云（Azure）+ 办公软件 + OpenAI 合作，把 AI 嵌入企业工作流与云收入。",
        "industry": "软件与云计算。",
        "chain_position": "应用与云分发层：采购 GPU/定制芯片建设数据中心，向企业出售 AI 功能与云算力。",
        "upstream": ["NVDA / 定制 ASIC", "服务器与电力"],
        "downstream": ["全球企业客户", "开发者与 Copilot 用户"],
        "bear_risks": ["云增速放缓", "AI 变现进度", "监管与反垄断"],
    },
    "GOOGL": {
        "name": "谷歌",
        "business": "搜索广告现金牛 + Google Cloud + 自研 TPU/Gemini 模型矩阵。",
        "industry": "互联网广告与云计算。",
        "chain_position": "既是 AI 模型与云服务提供方，也是自研芯片降低对通用 GPU 依赖的垂直整合者。",
        "upstream": ["自研 TPU + 部分 GPU", "数据中心基建"],
        "downstream": ["广告主", "云企业客户", "Android/Workspace 用户"],
        "bear_risks": ["搜索被 AI 分流", "反垄断", "云竞争加剧"],
    },
    "AMZN": {
        "name": "亚马逊",
        "business": "电商物流网络 + AWS 云基础设施，AI 训练/推理重要算力买家与卖家。",
        "industry": "电商零售 + 云计算。",
        "chain_position": "云基础设施分发层：大规模采购芯片建设数据中心，并向客户出租算力与模型服务。",
        "upstream": ["GPU/ASIC 供应商", "能源与地产"],
        "downstream": ["云租户", "电商消费者与第三方卖家"],
        "bear_risks": ["零售利润波动", "云资本开支回报", "监管"],
    },
    "META": {
        "name": "Meta",
        "business": "社交广告平台，大力投入开源模型与 AI 推荐系统以提升广告效率。",
        "industry": "互联网社交与数字广告。",
        "chain_position": "应用侧算力消耗大户：采购 GPU 训练推荐/生成模型，变现回到广告投放。",
        "upstream": ["GPU 与数据中心"],
        "downstream": ["广告主与创作者"],
        "bear_risks": ["广告周期", "监管隐私", "元宇宙投入争议"],
    },
    "PLTR": {
        "name": "Palantir",
        "business": "面向政府与企业的数据平台与 AIP 应用编排，卖“可落地的 AI 工作流”。",
        "industry": "企业软件 / 数据分析。",
        "chain_position": "应用层：不造芯片，把底层模型与客户数据系统连接成可运营解决方案。",
        "upstream": ["云与 GPU 资源", "开源/闭源模型"],
        "downstream": ["政府机构", "大型企业客户"],
        "bear_risks": ["估值过高", "政府预算", "客户集中度"],
    },
    "SMCI": {
        "name": "超微电脑",
        "business": "AI 服务器与机柜解决方案，连接 GPU 与数据中心交付。",
        "industry": "服务器硬件 / ODM。",
        "chain_position": "中游组装集成：把 GPU、主板、液冷与机柜打包给云与企业客户。",
        "upstream": ["NVDA GPU", "存储与电源散热"],
        "downstream": ["云厂商与企业数据中心"],
        "bear_risks": ["订单波动", "竞争加剧", "会计与治理争议余波"],
    },
    "ORCL": {
        "name": "甲骨文",
        "business": "数据库与云基础设施，承接大模型训练集群与企业 AI 数据栈。",
        "industry": "企业软件与云计算。",
        "chain_position": "数据与云层：向上游采购算力，向企业提供数据库/云资源承载 AI 负载。",
        "upstream": ["GPU 服务器供应链"],
        "downstream": ["企业数据库与云客户"],
        "bear_risks": ["云份额竞争", "大客户集中", "杠杆与资本开支"],
    },
    "SNOW": {
        "name": "Snowflake",
        "business": "云数据仓库与数据云平台，承接分析与 AI 特征/数据管道。",
        "industry": "云数据基础设施软件。",
        "chain_position": "数据层：位于云存储/计算之上、应用模型之下，做跨云数据共享与分析。",
        "upstream": ["AWS / Azure / GCP"],
        "downstream": ["分析师、数据团队、AI 应用"],
        "bear_risks": ["增长放缓", "云厂商自研替代", "消费优化"],
    },
    "AAPL": {
        "name": "苹果",
        "business": "硬件 + 服务闭环，端侧 AI（Apple Intelligence）强化换机与服务粘性。",
        "industry": "消费电子与服务。",
        "chain_position": "终端入口：自研芯片 + 代工制造，把 AI 能力嵌进设备与服务。",
        "upstream": ["台积电等代工", "零部件供应链"],
        "downstream": ["全球消费者与开发者"],
        "bear_risks": ["换机周期", "中国区风险", "AI 功能差异化不足"],
    },
    "CRM": {
        "name": "Salesforce",
        "business": "CRM 与 Agentforce 企业 AI 代理，把生成式 AI 卖进销售/服务流程。",
        "industry": "企业 SaaS。",
        "chain_position": "企业应用层：调用底层模型 API，嵌入 CRM 工作流变现。",
        "upstream": ["云与模型 API"],
        "downstream": ["企业销售/客服组织"],
        "bear_risks": ["IT 预算", "AI 功能同质化", "整合执行"],
    },
    "AMAT": {
        "name": "应用材料",
        "business": "晶圆制造设备与材料工程，覆盖沉积、刻蚀等关键工艺步骤。",
        "industry": "半导体设备。",
        "chain_position": "设备上游：晶圆厂扩产时的资本开支受益环节。",
        "upstream": ["精密零部件"],
        "downstream": ["台积电、三星、英特尔等晶圆厂"],
        "bear_risks": ["资本开支下行", "对华出口限制", "竞争"],
    },
}

_CACHE: dict[str, Any] = {"fetched_at": 0.0, "payload": None}
_CACHE_TTL = 90.0


def _etf_by_id(sector_id: str) -> dict[str, Any] | None:
    for row in SECTOR_ETFS:
        if row["id"] == sector_id:
            return row
    return None


def _value_chain_for(symbol: str) -> dict[str, Any]:
    sym = (symbol or "").upper()
    base = VALUE_CHAIN.get(sym)
    if base:
        return {"symbol": sym, **base}
    return {
        "symbol": sym,
        "name": sym,
        "business": "暂无内置业务档案；可结合财报与主营构成自行补充。",
        "industry": "待补充行业归类。",
        "chain_position": "暂未标注在产业链中的明确位置。",
        "upstream": [],
        "downstream": [],
        "bear_risks": ["信息不足，避免仅凭短线涨幅下结论"],
    }


def _match_sector_news(items: list[dict[str, Any]], topic_id: str) -> list[dict[str, Any]]:
    if topic_id in TOPICS:
        return filter_topic_items(items, topic_id, sort="latest")[:8]
    # Fallback keyword filter for sector topics not in war TOPICS
    meta = SECTOR_TOPIC_PATTERNS.get(topic_id) or {}
    query = str(meta.get("query") or "")
    needles = [n.strip().casefold() for n in query.replace("OR", " ").split() if n.strip()]
    if not needles:
        return []
    rows = []
    for item in items:
        blob = " ".join(
            str(item.get(k) or "")
            for k in ("title", "title_zh", "summary", "theme", "brief_zh")
        ).casefold()
        if any(n in blob for n in needles):
            rows.append(item)
    rows.sort(key=lambda x: x.get("published_ts") or 0.0, reverse=True)
    return rows[:8]


async def _fetch_quote(
    client: httpx.AsyncClient, symbol: str, label: str | None = None
) -> tuple[dict[str, Any] | None, list[str]]:
    return await fetch_symbol_bundle(
        client,
        symbol=symbol,
        label=label or symbol,
        short=symbol,
        timeframes=SECTOR_TIMEFRAMES,
        include_yearly=False,
    )


def _relative_strength(stock: dict[str, Any], etf: dict[str, Any] | None) -> float | None:
    s = stock.get("change_pct")
    e = (etf or {}).get("change_pct")
    if s is None or e is None:
        return None
    try:
        return round(float(s) - float(e), 3)
    except (TypeError, ValueError):
        return None


def _bar_close(point: dict[str, Any] | None) -> float | None:
    if not point:
        return None
    for key in ("c", "v", "o"):
        if point.get(key) is None:
            continue
        try:
            return float(point[key])
        except (TypeError, ValueError):
            return None
    return None


def _window_change_pct(points: list[dict[str, Any]] | None, bars: int) -> float | None:
    """Percent change over the last N bars (from day/intraday series)."""
    rows = list(points or [])
    if len(rows) < 2:
        return None
    window = rows[-bars:] if len(rows) >= bars else rows
    first = _bar_close(window[0])
    last = _bar_close(window[-1])
    if first in (None, 0) or last is None:
        return None
    return round((last - first) / first * 100.0, 3)


def _series_points(bundle: dict[str, Any] | None, tf: str) -> list[dict[str, Any]]:
    series = ((bundle or {}).get("series") or {}).get(tf) or {}
    return list(series.get("points") or bundle.get("points") or [])


def _momentum_fields(bundle: dict[str, Any] | None) -> dict[str, Any]:
    """Derive near-term wave metrics from 1y daily bars (not all-time monthly)."""
    day_points = _series_points(bundle, "day")
    m1 = _window_change_pct(day_points, 22)
    m3 = _window_change_pct(day_points, 66)
    day_pct = (bundle or {}).get("change_pct")
    try:
        d = float(day_pct) if day_pct is not None else 0.0
    except (TypeError, ValueError):
        d = 0.0
    try:
        m = float(m1) if m1 is not None else 0.0
    except (TypeError, ValueError):
        m = 0.0
    try:
        q = float(m3) if m3 is not None else 0.0
    except (TypeError, ValueError):
        q = 0.0
    momentum = round(d * 0.25 + m * 0.45 + q * 0.30, 3)
    is_wave = m >= 6.0 and q >= 8.0 and d >= -2.0
    return {
        "month_change_pct": m1,
        "quarter_change_pct": m3,
        "momentum": momentum,
        "is_wave": is_wave,
    }


def _momentum_score(day_pct: Any, month_pct: Any) -> float:
    """Legacy helper kept for call sites that only have scalars."""
    fields = _momentum_fields(
        {
            "change_pct": day_pct,
            "series": {"day": {"points": []}},
        }
    )
    # If no points, fall back to weighted scalars
    try:
        d = float(day_pct or 0)
    except (TypeError, ValueError):
        d = 0.0
    try:
        m = float(month_pct or 0)
    except (TypeError, ValueError):
        m = 0.0
    return round(d * 0.35 + m * 0.65, 3)


def _is_wave_up(day_pct: Any, month_pct: Any) -> bool:
    try:
        d = float(day_pct if day_pct is not None else 0)
        m = float(month_pct if month_pct is not None else 0)
    except (TypeError, ValueError):
        return False
    return m >= 6.0 and d >= -2.0


async def _fetch_earnings(
    client: httpx.AsyncClient, symbol: str
) -> dict[str, Any] | None:
    sym = (symbol or "").strip().upper()
    if not sym:
        return None
    url = (
        f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{sym}"
        f"?modules=calendarEvents,earnings"
    )
    try:
        resp = await client.get(
            url,
            timeout=20.0,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        result = (((resp.json() or {}).get("quoteSummary") or {}).get("result") or [None])[0]
        if not result:
            return None
        cal = (result.get("calendarEvents") or {}).get("earnings") or {}
        dates_raw = cal.get("earningsDate") or []
        dates: list[dict[str, Any]] = []
        for entry in dates_raw:
            if isinstance(entry, dict):
                raw = entry.get("raw")
                fmt = entry.get("fmt")
            else:
                raw, fmt = entry, None
            if raw is None and not fmt:
                continue
            dates.append({"ts": int(raw) if raw is not None else None, "label": fmt or ""})
        earn = result.get("earnings") or {}
        chart = (earn.get("earningsChart") or {})
        quarterly = []
        for row in chart.get("quarterly") or []:
            quarterly.append(
                {
                    "date": row.get("date"),
                    "actual": (row.get("actual") or {}).get("raw")
                    if isinstance(row.get("actual"), dict)
                    else row.get("actual"),
                    "estimate": (row.get("estimate") or {}).get("raw")
                    if isinstance(row.get("estimate"), dict)
                    else row.get("estimate"),
                }
            )
        next_ts = dates[0]["ts"] if dates else None
        days_to = None
        if next_ts:
            days_to = int((next_ts - time.time()) / 86400)
        return {
            "symbol": sym,
            "earnings_dates": dates[:3],
            "next_earnings_ts": next_ts,
            "next_earnings_label": (dates[0].get("label") if dates else "") or "",
            "days_to_earnings": days_to,
            "is_estimate": bool(cal.get("isEarningsDateEstimate")),
            "eps_avg": (cal.get("earningsAverage") or {}).get("raw")
            if isinstance(cal.get("earningsAverage"), dict)
            else cal.get("earningsAverage"),
            "revenue_avg": (cal.get("revenueAverage") or {}).get("raw")
            if isinstance(cal.get("revenueAverage"), dict)
            else cal.get("revenueAverage"),
            "quarterly": quarterly[-4:],
            "current_quarter_estimate": chart.get("currentQuarterEstimate"),
        }
    except Exception:  # noqa: BLE001
        return None


async def build_sector_desk(
    items: list[dict[str, Any]] | None = None,
    *,
    force: bool = False,
    selected_sector: str | None = None,
    selected_symbol: str | None = None,
) -> dict[str, Any]:
    now = time.time()
    if (
        not force
        and _CACHE["payload"]
        and now - float(_CACHE["fetched_at"]) < _CACHE_TTL
    ):
        payload = dict(_CACHE["payload"])
    else:
        errors: list[str] = []
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=True,
        ) as client:
            etf_results = await asyncio.gather(
                *[
                    _fetch_quote(client, row["symbol"], row["label"])
                    for row in SECTOR_ETFS
                ]
            )

            sectors: list[dict[str, Any]] = []
            for spec, (bundle, errs) in zip(SECTOR_ETFS, etf_results, strict=True):
                errors.extend(errs)
                if not bundle:
                    continue
                wave = _momentum_fields(bundle)
                sectors.append(
                    {
                        "id": spec["id"],
                        "symbol": spec["symbol"],
                        "label": spec["label"],
                        "short": spec["short"],
                        "blurb": spec["blurb"],
                        "topic_id": spec["topic_id"],
                        "picks": list(spec["picks"]),
                        "price": bundle.get("price"),
                        "change": bundle.get("change"),
                        "change_pct": bundle.get("change_pct"),
                        "month_change_pct": wave["month_change_pct"],
                        "quarter_change_pct": wave["quarter_change_pct"],
                        "momentum": wave["momentum"],
                        "is_wave": wave["is_wave"],
                        "points": bundle.get("points") or [],
                        "series": bundle.get("series") or {},
                        "url": bundle.get("url"),
                        "as_of": bundle.get("as_of"),
                    }
                )

            # Hot rank: near-term wave score, then 1M / 1D tape
            sectors.sort(
                key=lambda r: (
                    float(r.get("momentum") or -999),
                    float(r.get("month_change_pct") or -999),
                    float(r.get("change_pct") or -999),
                ),
                reverse=True,
            )
            for idx, row in enumerate(sectors):
                row["rank"] = idx + 1
                row["is_hot"] = idx < 3 or bool(row.get("is_wave"))

            payload = {
                "sectors": sectors,
                "errors": errors[-30:],
                "fetched_at": now,
                "source": "Yahoo Finance + 情报源关键词",
                "cached": False,
            }
            _CACHE["payload"] = payload
            _CACHE["fetched_at"] = now

        payload = dict(payload)
        payload["cached"] = False

    news_items = items or []
    sectors = list(payload.get("sectors") or [])

    # Default to current hottest sector (not hard-coded AI)
    sector_id = (selected_sector or "").strip().lower()
    if not sector_id or not any(s["id"] == sector_id for s in sectors):
        sector_id = sectors[0]["id"] if sectors else "ai"
    active = next((s for s in sectors if s["id"] == sector_id), None)
    if active is None and sectors:
        active = sectors[0]
        sector_id = active["id"]

    # Universe: active sector picks + leaders from other hot sectors
    hot = [s for s in sectors if s.get("is_hot")][:3]
    pick_symbols: list[str] = []
    for sym in list((active or {}).get("picks") or [])[:5]:
        if sym not in pick_symbols:
            pick_symbols.append(sym)
    for hot_sec in hot:
        if hot_sec.get("id") == sector_id:
            continue
        for sym in list(hot_sec.get("picks") or [])[:2]:
            if sym not in pick_symbols:
                pick_symbols.append(sym)
        if len(pick_symbols) >= 10:
            break

    pick_rows: list[dict[str, Any]] = []
    pick_errors: list[str] = []
    earnings_by_symbol: dict[str, Any] = {}
    if pick_symbols:
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=True,
        ) as client:
            pick_results, earnings_results = await asyncio.gather(
                asyncio.gather(*[_fetch_quote(client, sym, sym) for sym in pick_symbols]),
                asyncio.gather(*[_fetch_earnings(client, sym) for sym in pick_symbols]),
            )
        sector_by_sym: dict[str, dict[str, Any]] = {}
        for sec in SECTOR_ETFS:
            for sym in sec.get("picks") or []:
                sector_by_sym.setdefault(sym, sec)

        for sym, (bundle, errs), earnings in zip(
            pick_symbols, pick_results, earnings_results, strict=True
        ):
            pick_errors.extend(errs)
            if earnings:
                earnings_by_symbol[sym] = earnings
            if not bundle:
                continue
            vc = _value_chain_for(sym)
            home = sector_by_sym.get(sym) or {}
            home_etf = next(
                (s for s in sectors if s.get("id") == home.get("id")), active
            )
            rs = _relative_strength(bundle, home_etf)
            wave = _momentum_fields(bundle)
            day_pct = bundle.get("change_pct")
            pick_rows.append(
                {
                    **bundle,
                    "name": vc.get("name") or sym,
                    "month_change_pct": wave["month_change_pct"],
                    "quarter_change_pct": wave["quarter_change_pct"],
                    "vs_sector_pct": rs,
                    "momentum": wave["momentum"],
                    "is_wave": wave["is_wave"],
                    "is_strong": wave["is_wave"]
                    or (rs is not None and rs > 0)
                    or float(day_pct or 0)
                    > float((home_etf or {}).get("change_pct") or 0),
                    "sector_id": home.get("id") or sector_id,
                    "sector_label": home.get("label")
                    or (active or {}).get("label")
                    or "",
                    "earnings": earnings,
                    "value_chain": vc,
                }
            )
        pick_rows.sort(
            key=lambda r: (
                1 if r.get("is_wave") else 0,
                float(r.get("momentum") or -999),
                float(r.get("month_change_pct") or -999),
                float(r.get("change_pct") or -999),
            ),
            reverse=True,
        )

    selected = (selected_symbol or "").strip().upper()
    if not selected or not any(p.get("symbol") == selected for p in pick_rows):
        selected = pick_rows[0]["symbol"] if pick_rows else ""
    selected_pick = next((p for p in pick_rows if p.get("symbol") == selected), None)

    sector_news = _match_sector_news(
        news_items, (active or {}).get("topic_id") or sector_id
    )
    topic_key = (active or {}).get("topic_id")
    if topic_key in TOPICS:
        sector_bear = topic_bearish_analysis(news_items, topic_key)
    else:
        sector_bear = {
            "label": (active or {}).get("label") or sector_id,
            "counts": {
                "total": len(sector_news),
                "bearish": sum(1 for i in sector_news if i.get("sentiment") == "bearish"),
                "bullish": sum(1 for i in sector_news if i.get("sentiment") == "bullish"),
                "neutral": sum(1 for i in sector_news if i.get("sentiment") == "neutral"),
            },
            "avg_score": 0,
            "assessment": (
                f"{(active or {}).get('label') or '该板块'}近端匹配 "
                f"{len(sector_news)} 条相关报道。"
            ),
            "top_factors": [],
            "spotlight": [i for i in sector_news if i.get("sentiment") == "bearish"][:3],
            "latest": sector_news,
        }

    # Keep AI desk payload for backward-compatible front-end, but fill with active hot sector
    hot_desk = {
        "label": (active or {}).get("label") or "热点板块",
        "blurb": (active or {}).get("blurb")
        or "当前热点板块利空与相关新闻（不限于 AI）",
        "analysis": sector_bear,
        "latest": sector_news[:6] or sector_bear.get("latest") or [],
        "spotlight": sector_bear.get("spotlight") or [],
    }

    earnings_calendar = sorted(
        [
            {
                **(earnings_by_symbol.get(p["symbol"]) or {}),
                "symbol": p["symbol"],
                "name": p.get("name") or p["symbol"],
                "sector_label": p.get("sector_label") or "",
                "change_pct": p.get("change_pct"),
                "month_change_pct": p.get("month_change_pct"),
            }
            for p in pick_rows
            if earnings_by_symbol.get(p["symbol"], {}).get("next_earnings_ts")
        ],
        key=lambda r: (
            r.get("days_to_earnings")
            if r.get("days_to_earnings") is not None
            else 10_000
        ),
    )

    return {
        **payload,
        "cached": bool(_CACHE["payload"]) and not force,
        "ai_desk": hot_desk,
        "hot_desk": hot_desk,
        "hot_sectors": [s for s in sectors if s.get("is_hot")][:4],
        "active_sector_id": sector_id,
        "active_sector": active,
        "sector_news": sector_news,
        "sector_bearish": sector_bear,
        "picks": pick_rows,
        "wave_leaders": [p for p in pick_rows if p.get("is_wave")][:6],
        "selected_symbol": selected,
        "selected_pick": selected_pick,
        "value_chain": (selected_pick or {}).get("value_chain")
        or _value_chain_for(selected),
        "earnings_calendar": earnings_calendar,
        "selected_earnings": earnings_by_symbol.get(selected)
        or (selected_pick or {}).get("earnings"),
        "timeframes": [
            {
                "id": tf["id"],
                "label": tf["label"],
                "blurb": tf["blurb"],
                "chart": tf["chart"],
            }
            for tf in SECTOR_TIMEFRAMES
        ],
        "errors": list(payload.get("errors") or []) + pick_errors[-20:],
    }
