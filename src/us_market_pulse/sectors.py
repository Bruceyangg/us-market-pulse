"""Hot sector board: AI desk, ETF tape, stock picks, value-chain blurbs."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from us_market_pulse.markets import PORTFOLIO_TIMEFRAMES, fetch_symbol_bundle
from us_market_pulse.topics import TOPICS, filter_topic_items, topic_bearish_analysis

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

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
        "picks": [
            "NVDA",
            "AMD",
            "AVGO",
            "PLTR",
            "SMCI",
            "ARM",
            "META",
            "MSFT",
            "GOOGL",
            "SNOW",
        ],
    },
    {
        "id": "semis",
        "symbol": "SMH",
        "label": "半导体",
        "short": "Semis",
        "topic_id": "semis",
        "blurb": "芯片设计、制造与设备周期",
        "picks": [
            "NVDA",
            "TSM",
            "ASML",
            "AVGO",
            "AMAT",
            "MU",
            "LRCX",
            "KLAC",
            "QCOM",
            "AMD",
        ],
    },
    {
        "id": "tech",
        "symbol": "XLK",
        "label": "科技",
        "short": "Tech",
        "topic_id": "tech",
        "blurb": "广义科技板块（软件 + 硬件）",
        "picks": [
            "MSFT",
            "AAPL",
            "NVDA",
            "AVGO",
            "CRM",
            "ADBE",
            "ORCL",
            "NOW",
            "PANW",
            "IBM",
        ],
    },
    {
        "id": "nasdaq",
        "symbol": "QQQ",
        "label": "纳指百强",
        "short": "QQQ",
        "topic_id": "tech",
        "blurb": "纳斯达克 100 成长与流动性风向标",
        "picks": [
            "NVDA",
            "MSFT",
            "META",
            "AMZN",
            "GOOGL",
            "AVGO",
            "COST",
            "NFLX",
            "TSLA",
            "AMD",
        ],
    },
    {
        "id": "cloud",
        "symbol": "SKYY",
        "label": "云计算",
        "short": "Cloud",
        "topic_id": "cloud",
        "blurb": "云基础设施与软件即服务",
        "picks": [
            "MSFT",
            "AMZN",
            "GOOGL",
            "ORCL",
            "SNOW",
            "DDOG",
            "NET",
            "CRWD",
            "PANW",
            "NOW",
        ],
    },
    {
        "id": "energy",
        "symbol": "XLE",
        "label": "能源",
        "short": "Energy",
        "topic_id": "energy",
        "blurb": "原油、天然气与油气产业链",
        "picks": [
            "XOM",
            "CVX",
            "COP",
            "SLB",
            "EOG",
            "OXY",
            "MPC",
            "VLO",
            "WMB",
            "OKE",
        ],
    },
    {
        "id": "finance",
        "symbol": "XLF",
        "label": "金融",
        "short": "Finance",
        "topic_id": "finance",
        "blurb": "银行、券商与保险利率敏感板块",
        "picks": [
            "JPM",
            "BAC",
            "GS",
            "MS",
            "V",
            "MA",
            "SCHW",
            "C",
            "AXP",
            "BLK",
        ],
    },
    {
        "id": "health",
        "symbol": "XLV",
        "label": "医疗",
        "short": "Health",
        "topic_id": "health",
        "blurb": "制药、器械与医疗保健防御板块",
        "picks": [
            "LLY",
            "UNH",
            "JNJ",
            "ABBV",
            "MRK",
            "AMGN",
            "ISRG",
            "SYK",
            "PFE",
            "VRTX",
        ],
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
    "ARM": {
        "name": "Arm",
        "business": "CPU 架构授权与版税模式，覆盖手机、PC 与数据中心设计。",
        "industry": "半导体 IP。",
        "chain_position": "设计最上游 IP：不代工，向芯片公司授权架构。",
        "upstream": ["EDA 与研发人才"],
        "downstream": ["手机/PC/服务器芯片设计公司"],
        "bear_risks": ["客户自研架构", "版税增速波动", "估值"],
    },
    "MU": {
        "name": "美光",
        "business": "DRAM / HBM 存储，AI 服务器高带宽内存关键供应商之一。",
        "industry": "半导体存储。",
        "chain_position": "存储配套：与 GPU 出货共振，决定训练集群可交付规模。",
        "upstream": ["设备与晶圆材料"],
        "downstream": ["服务器 OEM、云厂商、消费电子"],
        "bear_risks": ["存储价格周期", "产能扩张", "竞争"],
    },
    "TSLA": {
        "name": "特斯拉",
        "business": "电动车、储能与自动驾驶软件，兼具科技成长与制造业属性。",
        "industry": "汽车 / 清洁能源。",
        "chain_position": "整车与能源系统集成商，向上游采购电池与芯片。",
        "upstream": ["电池与芯片供应链"],
        "downstream": ["消费者、电网储能客户"],
        "bear_risks": ["交付与价格战", "Robotaxi 预期差", "监管"],
    },
    "LLY": {
        "name": "礼来",
        "business": "减重与糖尿病等代谢药物管线驱动增长的大型制药公司。",
        "industry": "制药。",
        "chain_position": "创新药研发与商业化，产能与医保覆盖影响放量。",
        "upstream": ["原料药与代工产能"],
        "downstream": ["医保支付方、医院与患者"],
        "bear_risks": ["产能瓶颈", "定价与医保", "竞品进度"],
    },
    "JPM": {
        "name": "摩根大通",
        "business": "全能银行：零售、投行、交易与财富管理，利率与信贷周期敏感。",
        "industry": "银行。",
        "chain_position": "金融体系核心中介，连接储户、企业融资与资本市场。",
        "upstream": ["存款与批发融资"],
        "downstream": ["企业与零售客户、资本市场"],
        "bear_risks": ["净息差回落", "信贷质量", "监管资本"],
    },
    "XOM": {
        "name": "埃克森美孚",
        "business": "上下游一体化油气巨头，原油价格与炼化利润是主驱动。",
        "industry": "综合能源。",
        "chain_position": "勘探开采到炼化销售全链，油价与资本开支周期核心受益/承压方。",
        "upstream": ["油田服务与设备"],
        "downstream": ["炼厂、化工与终端燃料需求"],
        "bear_risks": ["油价回落", "能源转型政策", "项目执行"],
    },
}

_CACHE: dict[str, Any] = {"fetched_at": 0.0, "payload": None}
_CACHE_TTL = 90.0
# Per-sector pick boards (quotes + earnings) — avoids refetch on every symbol click
_PICKS_CACHE: dict[str, Any] = {}
_PICKS_TTL = 90.0
# Per-symbol Yahoo quote/earnings snippets shared across sectors
_SYM_CACHE: dict[str, Any] = {}
_SYM_TTL = 90.0


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
    client: httpx.AsyncClient,
    symbol: str,
    label: str | None = None,
    *,
    force: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    sym = (symbol or "").strip().upper()
    cache_key = f"quote:{sym}"
    cached = _SYM_CACHE.get(cache_key)
    if (
        not force
        and cached
        and time.time() - float(cached.get("fetched_at") or 0) < _SYM_TTL
    ):
        return cached.get("bundle"), []
    bundle, errs = await fetch_symbol_bundle(
        client,
        symbol=sym,
        label=label or sym,
        short=sym,
        timeframes=SECTOR_TIMEFRAMES,
        include_yearly=False,
    )
    if bundle:
        _SYM_CACHE[cache_key] = {"bundle": bundle, "fetched_at": time.time()}
    return bundle, errs


async def _fetch_earnings_cached(
    client: httpx.AsyncClient, symbol: str, *, force: bool = False
) -> dict[str, Any] | None:
    sym = (symbol or "").strip().upper()
    cache_key = f"earn:{sym}"
    cached = _SYM_CACHE.get(cache_key)
    if (
        not force
        and cached
        and time.time() - float(cached.get("fetched_at") or 0) < _SYM_TTL
    ):
        return cached.get("earnings")
    earnings = await _fetch_earnings(client, sym)
    _SYM_CACHE[cache_key] = {"earnings": earnings, "fetched_at": time.time()}
    return earnings


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


def _pct(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _move_analysis(
    *,
    day_pct: Any,
    month_pct: Any,
    quarter_pct: Any,
    vs_sector_pct: Any,
    is_wave: bool,
    sector_label: str,
    etf_day_pct: Any,
    earnings: dict[str, Any] | None,
    value_chain: dict[str, Any] | None,
    news: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Rule-based Chinese explanation for near-term stock move."""
    d = _pct(day_pct)
    m = _pct(month_pct)
    q = _pct(quarter_pct)
    rs = _pct(vs_sector_pct)
    etf_d = _pct(etf_day_pct)
    factors: list[str] = []

    if d is None and m is None:
        return {
            "bias": "neutral",
            "bias_zh": "中性",
            "summary": "行情数据不足，暂无法判断涨跌驱动。",
            "factors": ["等待报价刷新后再解读"],
        }

    score = 0.0
    if d is not None:
        score += d * 0.45
    if m is not None:
        score += m * 0.35
    if rs is not None:
        score += rs * 0.35

    if score >= 1.2:
        bias, bias_zh = "bullish", "偏多"
    elif score <= -1.2:
        bias, bias_zh = "bearish", "偏空"
    else:
        bias, bias_zh = "neutral", "震荡"

    if d is not None:
        if d >= 2:
            factors.append(f"今日大涨 {d:+.1f}%，短线资金推动明显")
        elif d >= 0.4:
            factors.append(f"今日上涨 {d:+.1f}%，盘面偏强")
        elif d <= -2:
            factors.append(f"今日大跌 {d:+.1f}%，短线抛压较重")
        elif d <= -0.4:
            factors.append(f"今日下跌 {d:+.1f}%，盘面偏弱")
        else:
            factors.append(f"今日涨跌有限（{d:+.1f}%），多为跟随波动")

    if m is not None:
        if m >= 10:
            factors.append(f"近 1 月走强约 {m:+.1f}%，一轮涨势仍在延续")
        elif m >= 4:
            factors.append(f"近 1 月累计 {m:+.1f}%，中期趋势偏多")
        elif m <= -8:
            factors.append(f"近 1 月回撤约 {m:+.1f}%，中期动能转弱")
        elif m <= -3:
            factors.append(f"近 1 月偏弱（{m:+.1f}%），反弹需看量能确认")

    if q is not None and abs(q) >= 8:
        factors.append(
            f"近一季约 {q:+.1f}%，{'趋势上行' if q > 0 else '趋势承压'}仍是主背景"
        )

    if is_wave:
        factors.append("同时满足近月/近季偏强条件，归入“一轮涨势”样本")

    sector = sector_label or "所属板块"
    if rs is not None and etf_d is not None:
        if rs >= 1.2:
            factors.append(
                f"强于 {sector}（相对板块约 {rs:+.1f}%），更偏个股逻辑"
            )
        elif rs <= -1.2:
            factors.append(
                f"弱于 {sector}（相对板块约 {rs:+.1f}%），注意个股拖累"
            )
        else:
            factors.append(
                f"与 {sector} 同步（板块日涨跌 {etf_d:+.1f}%），板块β为主"
            )
    elif etf_d is not None:
        factors.append(f"{sector} 今日 {etf_d:+.1f}%，提供板块方向参考")

    earn = earnings or {}
    days = earn.get("days_to_earnings")
    if isinstance(days, int) and 0 <= days <= 14:
        label = earn.get("next_earnings_label") or f"{days} 天后"
        factors.append(f"临近财报窗口（{label}），波动与预期差风险上升")

    vc = value_chain or {}
    risks = [str(x) for x in (vc.get("bear_risks") or []) if x][:2]
    if bias == "bearish" and risks:
        factors.append("关注既有风险：" + "、".join(risks))
    elif bias == "bullish" and vc.get("chain_position"):
        pos = str(vc.get("chain_position") or "")
        if pos and len(pos) > 8:
            factors.append(f"产业位置：{pos[:48]}{'…' if len(pos) > 48 else ''}")

    headlines: list[str] = []
    for item in (news or [])[:6]:
        title = str(item.get("title_zh") or item.get("title") or "").strip()
        if not title:
            continue
        sent = item.get("sentiment")
        if bias == "bearish" and sent == "bullish":
            continue
        if bias == "bullish" and sent == "bearish":
            continue
        headlines.append(title[:42] + ("…" if len(title) > 42 else ""))
        if len(headlines) >= 2:
            break
    if headlines:
        factors.append("相关报道：" + "；".join(headlines))

    day_bit = f"今日 {d:+.1f}%" if d is not None else "今日数据缺失"
    month_bit = f"近月 {m:+.1f}%" if m is not None else "近月待定"
    if bias == "bullish":
        summary = f"{day_bit}，{month_bit}，整体偏多；主要看动能与相对 {sector} 的强弱。"
    elif bias == "bearish":
        summary = f"{day_bit}，{month_bit}，整体偏空；优先核对板块拖累、风险事件与财报窗口。"
    else:
        summary = f"{day_bit}，{month_bit}，多空拉锯；更宜看相对 {sector} 是否走强/走弱。"

    return {
        "bias": bias,
        "bias_zh": bias_zh,
        "summary": summary,
        "factors": factors[:6],
    }


def _yahoo_raw(value: Any) -> Any:
    if isinstance(value, dict):
        if "raw" in value:
            return value.get("raw")
        if "fmt" in value:
            return value.get("fmt")
    return value


def _yahoo_fmt(value: Any) -> str:
    if isinstance(value, dict):
        fmt = value.get("fmt")
        if fmt:
            return str(fmt)
        raw = value.get("raw")
        if raw is None:
            return ""
        return str(raw)
    if value is None:
        return ""
    return str(value)


def _pct_change(curr: Any, base: Any) -> float | None:
    try:
        c = float(curr)
        b = float(base)
    except (TypeError, ValueError):
        return None
    if b == 0:
        return None
    return round((c - b) / abs(b) * 100.0, 2)


def _enrich_earnings_comparisons(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach YoY / QoQ / expectation fields from quarterly + history rows."""
    quarterly = list(payload.get("quarterly") or [])
    history = list(payload.get("history") or [])

    # Prefer history (actual reported), fall back to chart quarterly
    latest = history[0] if history else (quarterly[-1] if quarterly else None)
    prev_q = history[1] if len(history) > 1 else (
        quarterly[-2] if len(quarterly) > 1 else None
    )
    yoy_base = history[3] if len(history) > 3 else (
        quarterly[-5] if len(quarterly) >= 5 else None
    )

    last_actual = (latest or {}).get("actual")
    last_estimate = (latest or {}).get("estimate")
    prev_actual = (prev_q or {}).get("actual")
    yoy_actual = (yoy_base or {}).get("actual")

    qoq_pct = _pct_change(last_actual, prev_actual)
    yoy_pct = _pct_change(last_actual, yoy_actual)
    beat_pct = None
    if last_actual is not None and last_estimate not in (None, 0):
        beat_pct = _pct_change(last_actual, last_estimate)
    elif latest and latest.get("surprise_pct") is not None:
        try:
            beat_pct = round(float(latest["surprise_pct"]), 2)
        except (TypeError, ValueError):
            beat_pct = None

    expect = payload.get("eps_avg")
    if expect is None:
        expect = payload.get("next_eps_estimate")
    expect_vs_last_yoy = _pct_change(expect, last_actual if yoy_actual is None else yoy_actual)
    # Expected YoY: consensus vs year-ago actual when available, else vs last print
    if yoy_actual is not None:
        expect_yoy_pct = _pct_change(expect, yoy_actual)
    else:
        expect_yoy_pct = _pct_change(expect, last_actual)

    payload.update(
        {
            "last_eps_actual": last_actual,
            "last_eps_estimate": last_estimate,
            "prev_eps_actual": prev_actual,
            "yoy_eps_actual": yoy_actual,
            "qoq_pct": qoq_pct,
            "yoy_pct": yoy_pct,
            "beat_pct": beat_pct,
            "expect_eps": expect,
            "expect_yoy_pct": expect_yoy_pct,
            "expect_vs_last_pct": expect_vs_last_yoy,
        }
    )
    return payload


async def _fetch_earnings(
    client: httpx.AsyncClient, symbol: str
) -> dict[str, Any] | None:
    sym = (symbol or "").strip().upper()
    if not sym:
        return None
    url = (
        f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{sym}"
        f"?modules=calendarEvents,earnings,earningsHistory,earningsTrend"
    )
    try:
        resp = await client.get(
            url,
            timeout=25.0,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://finance.yahoo.com",
                "Referer": f"https://finance.yahoo.com/quote/{sym}/analysis",
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
            try:
                ts = int(raw) if raw is not None else None
            except (TypeError, ValueError):
                ts = None
            dates.append({"ts": ts, "label": str(fmt or "")})

        earn = result.get("earnings") or {}
        chart = earn.get("earningsChart") or {}
        quarterly: list[dict[str, Any]] = []
        for row in chart.get("quarterly") or []:
            quarterly.append(
                {
                    "date": row.get("date"),
                    "label": str(row.get("date") or ""),
                    "actual": _yahoo_raw(row.get("actual")),
                    "estimate": _yahoo_raw(row.get("estimate")),
                }
            )

        history_rows: list[dict[str, Any]] = []
        for row in (result.get("earningsHistory") or {}).get("history") or []:
            q = row.get("quarter")
            history_rows.append(
                {
                    "period": row.get("period"),
                    "quarter_ts": _yahoo_raw(q),
                    "label": _yahoo_fmt(q),
                    "actual": _yahoo_raw(row.get("epsActual")),
                    "estimate": _yahoo_raw(row.get("epsEstimate")),
                    "surprise_pct": _yahoo_raw(row.get("surprisePercent")),
                }
            )
        # Newest first
        history_rows.sort(
            key=lambda r: float(r.get("quarter_ts") or 0),
            reverse=True,
        )

        trend_map: dict[str, dict[str, Any]] = {}
        for row in (result.get("earningsTrend") or {}).get("trend") or []:
            period = str(row.get("period") or "")
            est = row.get("earningsEstimate") or {}
            trend_map[period] = {
                "period": period,
                "avg": _yahoo_raw(est.get("avg")),
                "low": _yahoo_raw(est.get("low")),
                "high": _yahoo_raw(est.get("high")),
                "growth": _yahoo_raw(est.get("growth")),
                "number_of_analysts": _yahoo_raw(est.get("numberOfAnalysts")),
            }

        next_trend = trend_map.get("0q") or trend_map.get("+1q") or {}
        eps_avg = _yahoo_raw(cal.get("earningsAverage"))
        if eps_avg is None:
            eps_avg = next_trend.get("avg")

        next_ts = dates[0]["ts"] if dates else None
        days_to = None
        if next_ts:
            days_to = int((next_ts - time.time()) / 86400)

        prev = history_rows[0] if history_rows else None
        prev_ts = (prev or {}).get("quarter_ts")
        try:
            prev_ts_i = int(prev_ts) if prev_ts is not None else None
        except (TypeError, ValueError):
            prev_ts_i = None

        cq_est = chart.get("currentQuarterEstimate")
        payload = {
            "symbol": sym,
            "earnings_dates": dates[:3],
            "next_earnings_ts": next_ts,
            "next_earnings_label": (dates[0].get("label") if dates else "") or "",
            "days_to_earnings": days_to,
            "prev_earnings_ts": prev_ts_i,
            "prev_earnings_label": (prev or {}).get("label") or "",
            "is_estimate": bool(cal.get("isEarningsDateEstimate")),
            "eps_avg": eps_avg,
            "next_eps_estimate": next_trend.get("avg"),
            "next_eps_low": next_trend.get("low"),
            "next_eps_high": next_trend.get("high"),
            "next_eps_growth": next_trend.get("growth"),
            "analyst_count": next_trend.get("number_of_analysts"),
            "revenue_avg": _yahoo_raw(cal.get("revenueAverage")),
            "quarterly": quarterly[-6:],
            "history": history_rows[:6],
            "current_quarter_estimate": _yahoo_raw(cq_est),
            "trend": {
                k: v
                for k, v in trend_map.items()
                if k in {"0q", "+1q", "+1y", "0y"}
            },
        }
        return _enrich_earnings_comparisons(payload)
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

    # Universe: full active-sector picks + a few leaders from other hot sectors
    hot = [s for s in sectors if s.get("is_hot")][:3]
    pick_symbols: list[str] = []
    for sym in list((active or {}).get("picks") or [])[:12]:
        if sym not in pick_symbols:
            pick_symbols.append(sym)
    for hot_sec in hot:
        if hot_sec.get("id") == sector_id:
            continue
        for sym in list(hot_sec.get("picks") or [])[:3]:
            if sym not in pick_symbols:
                pick_symbols.append(sym)
        if len(pick_symbols) >= 16:
            break

    pick_rows: list[dict[str, Any]] = []
    pick_errors: list[str] = []
    earnings_by_symbol: dict[str, Any] = {}
    picks_key = f"{sector_id}:{'|'.join(pick_symbols)}"
    picks_cached = _PICKS_CACHE.get(sector_id) or {}
    picks_fresh = (
        not force
        and picks_cached.get("key") == picks_key
        and time.time() - float(picks_cached.get("fetched_at") or 0) < _PICKS_TTL
        and picks_cached.get("pick_rows")
    )
    if picks_fresh:
        pick_rows = [dict(r) for r in picks_cached["pick_rows"]]
        earnings_by_symbol = dict(picks_cached.get("earnings_by_symbol") or {})
    elif pick_symbols:
        async with httpx.AsyncClient(
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://finance.yahoo.com",
                "Referer": "https://finance.yahoo.com/",
            },
            follow_redirects=True,
            trust_env=False,
        ) as client:
            pick_results, earnings_results = await asyncio.gather(
                asyncio.gather(
                    *[_fetch_quote(client, sym, sym, force=force) for sym in pick_symbols]
                ),
                asyncio.gather(
                    *[
                        _fetch_earnings_cached(client, sym, force=force)
                        for sym in pick_symbols
                    ]
                ),
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
            home = sector_by_sym.get(sym) or active or {}
            # Prefer currently selected sector label when the symbol belongs there
            if sym in list((active or {}).get("picks") or []):
                home = active or home
            home_etf = next(
                (s for s in sectors if s.get("id") == home.get("id")), active
            )
            rs = _relative_strength(bundle, home_etf)
            wave = _momentum_fields(bundle)
            day_pct = bundle.get("change_pct")
            sector_label = (
                home.get("label") or (active or {}).get("label") or ""
            )
            analysis = _move_analysis(
                day_pct=day_pct,
                month_pct=wave["month_change_pct"],
                quarter_pct=wave["quarter_change_pct"],
                vs_sector_pct=rs,
                is_wave=bool(wave["is_wave"]),
                sector_label=sector_label,
                etf_day_pct=(home_etf or {}).get("change_pct"),
                earnings=earnings,
                value_chain=vc,
                news=None,  # filled after sector_news is ready
            )
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
                    "sector_label": sector_label,
                    "earnings": earnings,
                    "value_chain": vc,
                    "move_analysis": analysis,
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
        _PICKS_CACHE[sector_id] = {
            "key": picks_key,
            "pick_rows": [dict(r) for r in pick_rows],
            "earnings_by_symbol": dict(earnings_by_symbol),
            "fetched_at": time.time(),
        }

    selected = (selected_symbol or "").strip().upper()
    if not selected or not any(p.get("symbol") == selected for p in pick_rows):
        selected = pick_rows[0]["symbol"] if pick_rows else ""
    selected_pick = next((p for p in pick_rows if p.get("symbol") == selected), None)

    sector_news = _match_sector_news(
        news_items, (active or {}).get("topic_id") or sector_id
    )
    # Enrich move analysis with sector headlines once news is available
    for row in pick_rows:
        home_etf = next(
            (s for s in sectors if s.get("id") == row.get("sector_id")), active
        )
        row["move_analysis"] = _move_analysis(
            day_pct=row.get("change_pct"),
            month_pct=row.get("month_change_pct"),
            quarter_pct=row.get("quarter_change_pct"),
            vs_sector_pct=row.get("vs_sector_pct"),
            is_wave=bool(row.get("is_wave")),
            sector_label=str(row.get("sector_label") or ""),
            etf_day_pct=(home_etf or {}).get("change_pct"),
            earnings=row.get("earnings") if isinstance(row.get("earnings"), dict) else None,
            value_chain=row.get("value_chain")
            if isinstance(row.get("value_chain"), dict)
            else None,
            news=sector_news,
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
        "wave_leaders": [p for p in pick_rows if p.get("is_wave")][:10],
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
