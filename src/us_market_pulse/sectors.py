"""Hot sector board: AI desk, ETF tape, stock picks, value-chain blurbs."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from us_market_pulse.earnings_calendar import (
    _parse_money,
    get_upcoming_earnings_map,
    lookup_upcoming_earnings,
    peek_upcoming_earnings_map,
)
from us_market_pulse.market_map import symbols_for_desk
from us_market_pulse.markets import (
    PORTFOLIO_TIMEFRAMES,
    _session_id_for_ts,
    _session_segments,
    fetch_symbol_bundle,
)
from us_market_pulse.feeds import fetch_google_news
from us_market_pulse.feeds import fetch_google_news
from us_market_pulse.portfolio_intel import match_portfolio_intel
from us_market_pulse.sentiment import enrich_sentiment
from us_market_pulse.translate import enrich_titles
from us_market_pulse.quotes import (
    apply_list_quote_fields,
    build_nasdaq_ohlc_series,
    derive_list_realtime,
    fetch_day_quotes,
    fetch_nasdaq_daily_bars,
    fetch_nasdaq_intraday,
    fetch_nasdaq_intraday_many,
    peek_overnight_quote,
    resolve_list_session,
    restamp_list_session,
    session_from_clock,
)
from us_market_pulse.topics import TOPICS, filter_topic_items, topic_bearish_analysis

# Cap concurrent Yahoo chart fetches per sector switch
_MAX_SECTOR_PICKS = 28
_INTRADAY_TF = next(
    (tf for tf in PORTFOLIO_TIMEFRAMES if tf["id"] == "intraday"),
    {
        "id": "intraday",
        "label": "分时",
        "blurb": "Yahoo 1D 分时 · 含盘前/盘后",
        "range": "1d",
        "interval": "1m",
        "max_points": 480,
        "chart": "line",
        "prepost": True,
        "session_window": False,
    },
)
# Left-list sparklines: classic same-day 分时 only (not the desk session window).
_LIST_SPARK_TF: dict[str, Any] = {
    "id": "intraday",
    "label": "分时",
    "blurb": "当日分时",
    "range": "1d",
    "interval": "5m",
    "max_points": 96,
    "chart": "line",
    "prepost": True,
    "session_window": False,
}
_pick_fetch_sem: asyncio.Semaphore | None = None


def _get_pick_sem() -> asyncio.Semaphore:
    global _pick_fetch_sem
    if _pick_fetch_sem is None:
        _pick_fetch_sem = asyncio.Semaphore(6)
    return _pick_fetch_sem


def _universe_for_sector(sector_id: str, curated: list[str] | None = None) -> list[str]:
    """Full constituent list: market-map stocks ∪ curated picks."""
    out: list[str] = []
    for sym in symbols_for_desk(sector_id):
        if sym not in out:
            out.append(sym)
    for sym in curated or []:
        up = str(sym or "").upper()
        if up and up not in out:
            out.append(up)
    return out[:_MAX_SECTOR_PICKS]

_ET = ZoneInfo("America/New_York")

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
        "gn_query": (
            '("artificial intelligence" OR Nvidia OR OpenAI OR "data center" OR GPU) '
            "when:7d"
        ),
    },
    "semis": {
        "id": "semis",
        "label": "半导体",
        "blurb": "芯片、代工、设备与存储周期",
        "query": "半导体 OR chip OR semiconductor",
        "gn_query": (
            "(semiconductor OR chip OR TSMC OR ASML OR Nvidia OR AMD) stock when:7d"
        ),
    },
    "tech": {
        "id": "tech",
        "label": "科技",
        "blurb": "科技巨头与软件硬件联动",
        "query": "科技股 OR Big Tech OR Nasdaq",
        "gn_query": (
            '("Big Tech" OR Apple OR Microsoft OR Google OR Meta OR Nasdaq) '
            "stock when:7d"
        ),
    },
    "cloud": {
        "id": "cloud",
        "label": "云计算",
        "blurb": "云资本开支、SaaS 与数据中心",
        "query": "云计算 OR cloud OR data center",
        "gn_query": (
            '("cloud computing" OR AWS OR Azure OR "data center" OR SaaS) '
            "stock when:7d"
        ),
    },
    "energy": {
        "id": "energy",
        "label": "能源",
        "blurb": "油价、天然气与能源股",
        "query": "原油 OR oil OR energy stocks",
        "gn_query": (
            "(crude OR oil OR energy stocks OR Exxon OR Chevron) when:7d"
        ),
    },
    "finance": {
        "id": "finance",
        "label": "金融",
        "blurb": "银行、利率与金融监管",
        "query": "银行 OR banks OR financials",
        "gn_query": (
            "(banks OR financials OR Wall Street OR JPMorgan OR Fed rate) "
            "stock when:7d"
        ),
    },
    "health": {
        "id": "health",
        "label": "医疗",
        "blurb": "制药、医保与生物科技",
        "query": "制药 OR biotech OR healthcare",
        "gn_query": (
            "(biotech OR healthcare OR pharma OR Eli Lilly OR FDA) stock when:7d"
        ),
    },
}

# Ticker → English name for Google News queries (VALUE_CHAIN names are often CN).
_SYMBOL_GN_ALIAS: dict[str, str] = {
    "NVDA": "Nvidia",
    "AMD": "AMD",
    "AVGO": "Broadcom",
    "ARM": "Arm Holdings",
    "SMCI": "Super Micro",
    "PLTR": "Palantir",
    "SNOW": "Snowflake",
    "META": "Meta",
    "GOOGL": "Google",
    "GOOG": "Google",
    "MSFT": "Microsoft",
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
    "JPM": "JPMorgan",
    "BAC": "Bank of America",
    "GS": "Goldman Sachs",
    "XOM": "Exxon",
    "CVX": "Chevron",
    "LLY": "Eli Lilly",
    "JNJ": "Johnson & Johnson",
    "PFE": "Pfizer",
    "MRK": "Merck",
    "ABBV": "AbbVie",
    "ORCL": "Oracle",
    "DDOG": "Datadog",
    "NFLX": "Netflix",
    "ISRG": "Intuitive Surgical",
    "PATH": "UiPath",
    "QCOM": "Qualcomm",
    "TSM": "TSMC",
    "ASML": "ASML",
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
    "LRCX": {
        "name": "拉姆研究",
        "business": "刻蚀与沉积设备龙头，先进制程与存储扩产核心供应商。",
        "industry": "半导体设备。",
        "chain_position": "晶圆厂前端设备：与资本开支和先进节点导入强相关。",
        "upstream": ["真空泵、射频电源、精密零部件"],
        "downstream": ["台积电、三星、美光、SK 海力士等晶圆厂"],
        "bear_risks": ["晶圆厂资本开支下滑", "对华出口管制", "竞争加剧"],
    },
    "KLAC": {
        "name": "科磊",
        "business": "制程控制与检测设备，监控良率与缺陷的关键量测环节。",
        "industry": "半导体检测设备。",
        "chain_position": "量测/检测：先进制程必备，随节点升级提升单厂价值量。",
        "upstream": ["光学与传感器组件"],
        "downstream": ["逻辑与存储晶圆厂"],
        "bear_risks": ["扩产节奏", "出口限制", "客户自研检测"],
    },
    "QCOM": {
        "name": "高通",
        "business": "手机与汽车 SoC、射频与许可收入，连接与端侧 AI 芯片平台。",
        "industry": "半导体设计。",
        "chain_position": "无晶圆设计：依赖台积电等代工，面向手机/汽车/IoT 终端。",
        "upstream": ["台积电等代工", "EDA / IP"],
        "downstream": ["手机制造商、汽车与 IoT 客户"],
        "bear_risks": ["安卓周期", "大客户自研芯片", "许可纠纷"],
    },
    "TXN": {
        "name": "德州仪器",
        "business": "模拟与嵌入式芯片，工业、汽车与电子系统广泛基础件。",
        "industry": "模拟半导体。",
        "chain_position": "模拟/嵌入式：偏周期与库存，自有制造产能占比高。",
        "upstream": ["硅片与制造设备"],
        "downstream": ["工业自动化、汽车电子、消费电子"],
        "bear_risks": ["工业去库存", "汽车需求波动", "自建产能利用率"],
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
_CACHE_TTL = 180.0
# Per-sector pick boards (quotes + earnings) — avoids refetch on every symbol click
_PICKS_CACHE: dict[str, Any] = {}
_PICKS_TTL = 180.0
# Serve slightly stale pick boards with a soft quote refresh (SWR).
_PICKS_STALE_TTL = 900.0
# Per-symbol Yahoo quote/earnings snippets shared across sectors
_SYM_CACHE: dict[str, Any] = {}
_SYM_TTL = 180.0
# Shared holdings/sectors 分时 poll — short TTL so Yahoo-like tape stays fresh
_INTRADAY_SNAP_CACHE: dict[str, Any] = {}
# Match FE 分时 poll (~0.5–1s); still coalesces bursts.
_INTRADAY_SNAP_TTL = 0.75


def _pick_has_chart(row: dict[str, Any] | None) -> bool:
    """True when the row has a full desk chart (day+), not only a 24h list spark."""
    if not row:
        return False
    series = row.get("series") or {}
    day = series.get("day") if isinstance(series.get("day"), dict) else {}
    if len(day.get("points") or []) >= 2:
        return True
    month = series.get("month") if isinstance(series.get("month"), dict) else {}
    return len(month.get("points") or []) >= 2


def _pick_has_intraday(row: dict[str, Any] | None) -> bool:
    return len(_spark_points_from_row(row)) >= 2


def _bundle_has_full_chart(bundle: dict[str, Any] | None) -> bool:
    return _pick_has_chart(bundle)


def _series_intraday_ok(row: dict[str, Any] | None) -> bool:
    """True when series.intraday has a usable line (≥2 points)."""
    if not row:
        return False
    series = row.get("series") or {}
    intra = series.get("intraday") if isinstance(series.get("intraday"), dict) else {}
    return len(intra.get("points") or []) >= 2


def _annotate_intraday_sessions(series_row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep Yahoo/Nasdaq 1D tape as-is; only tag session ids for metadata."""
    if not isinstance(series_row, dict):
        return series_row
    pts: list[dict[str, Any]] = []
    for p in list(series_row.get("points") or []):
        if not isinstance(p, dict) or not p.get("t"):
            continue
        row = dict(p)
        try:
            row["session"] = _session_id_for_ts(int(row["t"]))
        except (TypeError, ValueError):
            row["session"] = "regular"
        pts.append(row)
    pts.sort(key=lambda p: int(p["t"]))
    series_row["points"] = pts
    series_row["chart"] = "line"
    series_row["blurb"] = series_row.get("blurb") or "Yahoo 1D 分时 · 含盘前/盘后"
    series_row["session_labels"] = ["盘前", "盘中", "盘后"]
    # Preserve previous_close for Yahoo-style 昨收 guide (holdings + sectors).
    if series_row.get("previous_close") is None and series_row.get("prev_close") is not None:
        series_row["previous_close"] = series_row.get("prev_close")
    if len(pts) >= 2:
        series_row["sessions"] = _session_segments(pts)
    return series_row


def _ensure_bundle_intraday_sessions(bundle: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(bundle, dict):
        return bundle
    series = dict(bundle.get("series") or {})
    intra = series.get("intraday")
    if isinstance(intra, dict) and (intra.get("points") or []):
        series["intraday"] = _annotate_intraday_sessions(dict(intra))
        bundle["series"] = series
    return bundle


async def fetch_intraday_snapshot(
    symbol: str,
    *,
    force: bool = False,
) -> dict[str, Any] | None:
    """Fast 1D 分时 snapshot for holdings + sectors auto-refresh.

    Nasdaq-first (sub-second) so 1s client polls stay responsive; Yahoo is only
    a short fallback when Nasdaq is empty.
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return None
    cache_key = f"intraday_snap:{sym}"
    cached = _INTRADAY_SNAP_CACHE.get(cache_key)
    if (
        not force
        and isinstance(cached, dict)
        and time.time() - float(cached.get("at") or 0) < _INTRADAY_SNAP_TTL
        and isinstance(cached.get("data"), dict)
        and _series_intraday_ok(cached.get("data"))
    ):
        return dict(cached["data"])

    yahoo_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/",
    }
    series_row: dict[str, Any] | None = None
    price: Any = None
    change: Any = None
    change_pct: Any = None
    source = "none"

    async with httpx.AsyncClient(
        headers=yahoo_headers,
        follow_redirects=True,
        trust_env=False,
        timeout=httpx.Timeout(4.0, connect=2.0),
    ) as client:
        # Fast path: Nasdaq only (typical 200–800ms; allow more in 盘前).
        nd = None
        try:
            nd = await asyncio.wait_for(
                fetch_nasdaq_intraday(client, sym, max_points=480),
                timeout=3.5,
            )
        except Exception:  # noqa: BLE001
            nd = None

        if nd and len(nd.get("points") or []) >= 2:
            raw_pts = [
                {"t": int(p["t"]), "v": float(p["v"])}
                for p in (nd.get("points") or [])
                if p.get("t") and p.get("v") is not None
            ]
            series_row = _annotate_intraday_sessions(
                {
                    "tf": "intraday",
                    "label": "分时",
                    "blurb": "Yahoo 1D 分时 · 含盘前/盘后",
                    "range": "1d",
                    "interval": "1m",
                    "chart": "line",
                    "points": raw_pts,
                    "change": nd.get("change"),
                    "change_pct": nd.get("change_pct"),
                    "previous_close": nd.get("previous_close"),
                }
            )
            price = nd.get("price")
            change = nd.get("change")
            change_pct = nd.get("change_pct")
            source = "nasdaq"
        else:
            # Short Yahoo fallback only when Nasdaq fails.
            try:
                bundle, _errs = await asyncio.wait_for(
                    fetch_symbol_bundle(
                        client,
                        symbol=sym,
                        label=sym,
                        short=sym,
                        timeframes=[_INTRADAY_TF],
                        include_yearly=False,
                    ),
                    timeout=1.8,
                )
            except Exception:  # noqa: BLE001
                bundle = None
            if bundle and _series_intraday_ok(bundle):
                _ensure_bundle_intraday_sessions(bundle)
                intra = (bundle.get("series") or {}).get("intraday")
                if isinstance(intra, dict):
                    series_row = dict(intra)
                price = bundle.get("price")
                change = bundle.get("change")
                change_pct = bundle.get("change_pct")
                source = "yahoo"

    if not series_row or len(series_row.get("points") or []) < 2:
        # Serve last good snapshot rather than blank the chart on a blip.
        if isinstance(cached, dict) and isinstance(cached.get("data"), dict):
            return dict(cached["data"])
        return None

    # Badge: ET clock is authoritative (vendors/tape lag stick on 盘前).
    last_pts = list(series_row.get("points") or [])
    clock_sid, clock_label = session_from_clock()
    sid, _label = clock_sid, clock_label

    prev_close = series_row.get("previous_close")
    day_price = price if isinstance(price, (int, float)) else None
    day_change = change if isinstance(change, (int, float)) else None
    day_change_pct = change_pct if isinstance(change_pct, (int, float)) else None
    prev_num = prev_close if isinstance(prev_close, (int, float)) else None

    # During 盘前/盘后, Nasdaq lastSale is the extended print — pull the day
    # quote so 收盘 + 盘前% match Yahoo (vs last regular close).
    day_q: dict[str, Any] | None = None
    if sid in {"pre", "post", "night"}:
        try:
            from us_market_pulse.quotes import fetch_day_quotes

            day_map = await fetch_day_quotes([sym])
            day_q = day_map.get(sym) if isinstance(day_map, dict) else None
        except Exception:  # noqa: BLE001
            day_q = None
        if isinstance(day_q, dict):
            if day_q.get("price") is not None:
                price = day_q.get("price")
                day_price = price if isinstance(price, (int, float)) else day_price
            if day_q.get("change") is not None:
                change = day_q.get("change")
                day_change = change if isinstance(change, (int, float)) else day_change
            if day_q.get("change_pct") is not None:
                change_pct = day_q.get("change_pct")
                day_change_pct = (
                    change_pct
                    if isinstance(change_pct, (int, float))
                    else day_change_pct
                )
            if day_q.get("previous_close") is not None:
                prev_close = day_q.get("previous_close")
                prev_num = (
                    prev_close if isinstance(prev_close, (int, float)) else prev_num
                )
            # Chart 昨收 guide = last regular close during 盘前 (Yahoo At close).
            if sid == "pre" and day_q.get("price") is not None:
                series_row["previous_close"] = day_q.get("price")
            elif day_q.get("previous_close") is not None:
                series_row["previous_close"] = day_q.get("previous_close")

    # 夜盘: Yahoo Overnight only (distinct from 盘后). No tape invented.
    if sid == "night":
        rt_fields: dict[str, Any] = {}
        try:
            # Cache-only on the request path (see PULSE_OVERNIGHT_FETCH).
            y_night = peek_overnight_quote(sym)
        except Exception:  # noqa: BLE001
            y_night = None
        if isinstance(y_night, dict) and y_night.get("overnight"):
            if day_price is None and y_night.get("price") is not None:
                price = y_night.get("price")
                change = y_night.get("change")
                change_pct = y_night.get("change_pct")
                day_price = price if isinstance(price, (int, float)) else day_price
                day_change = change if isinstance(change, (int, float)) else day_change
                day_change_pct = (
                    change_pct
                    if isinstance(change_pct, (int, float))
                    else day_change_pct
                )
            if y_night.get("previous_close") is not None:
                prev_close = y_night.get("previous_close")
                prev_num = (
                    prev_close if isinstance(prev_close, (int, float)) else prev_num
                )
            for key in ("rt_price", "rt_change", "rt_change_pct"):
                if y_night.get(key) is not None:
                    rt_fields[key] = y_night[key]
        # No overnight → leave rt_* empty (show 夜盘: --), never use 盘后.
        if not rt_fields:
            rt_fields = {}
    elif sid in {"pre", "post"} and isinstance(day_q, dict) and day_q.get("rt_price") is not None:
        # Trust CNBC/Yahoo extended quote for list RT (synced with Yahoo page).
        rt_fields = {
            k: day_q[k]
            for k in ("rt_price", "rt_change", "rt_change_pct")
            if day_q.get(k) is not None
        }
    else:
        rt_fields = derive_list_realtime(
            session=sid,
            day_price=day_price,
            day_change=day_change,
            day_change_pct=day_change_pct,
            previous_close=prev_num,
            tape_points=last_pts,
        )
    data = {
        "symbol": sym,
        "price": price,
        "change": change,
        "change_pct": change_pct,
        "previous_close": prev_close,
        "series": {"intraday": series_row},
        "source": source,
        "session": sid,
        "session_label": _label,
        "fetched_at": time.time(),
        **rt_fields,
    }
    _INTRADAY_SNAP_CACHE[cache_key] = {"at": time.time(), "data": data}
    return dict(data)


def _spark_points_from_row(row: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Prefer full-session intraday line points for list sparklines (same as desk 分时)."""
    if not row:
        return []
    series = row.get("series") or {}
    intra = series.get("intraday") if isinstance(series.get("intraday"), dict) else {}
    pts = list((intra or {}).get("points") or [])
    if not pts:
        pts = list(row.get("points") or [])
    out: list[dict[str, Any]] = []
    for p in pts:
        if not isinstance(p, dict):
            continue
        # Candle bars carry volume in `v` — always prefer close for price sparks
        if p.get("c") is not None and (
            p.get("o") is not None or p.get("h") is not None or p.get("l") is not None
        ):
            out.append({"t": p.get("t"), "v": p.get("c")})
        elif p.get("v") is not None and p.get("c") is None:
            out.append({"t": p.get("t"), "v": p.get("v")})
        elif p.get("c") is not None:
            out.append({"t": p.get("t"), "v": p.get("c")})
    return out


def _apply_intraday_spark(
    row: dict[str, Any],
    points: list[dict[str, Any]],
    *,
    change_pct: float | None = None,
) -> None:
    spark = list(points or [])
    if not spark:
        return
    existing = (row.get("series") or {}).get("intraday")
    existing_pts = (
        list(existing.get("points") or []) if isinstance(existing, dict) else []
    )
    # Never replace a fuller desk intraday series with a truncated list spark
    if len(existing_pts) > len(spark):
        return
    row["points"] = spark[-48:]
    series = dict(row.get("series") or {})
    base = dict(existing) if isinstance(existing, dict) else {}
    pct = change_pct
    if pct is None and isinstance(existing, dict):
        pct = existing.get("change_pct")
    if pct is None:
        pct = row.get("change_pct")
    series["intraday"] = {
        **base,
        "chart": "line",
        "points": spark,
        "change_pct": pct,
    }
    row["series"] = series


def _slim_pick_row(row: dict[str, Any], selected: str) -> dict[str, Any]:
    """Strip heavy multi-TF series from list rows; keep 24h spark + full selected chart."""
    out = dict(row)
    sym = str(out.get("symbol") or "").upper()
    if sym == selected and (_pick_has_chart(out) or _pick_has_intraday(out)):
        return out
    spark = _spark_points_from_row(out)
    intra = (out.get("series") or {}).get("intraday")
    intra_pct = (
        intra.get("change_pct")
        if isinstance(intra, dict) and intra.get("change_pct") is not None
        else out.get("change_pct")
    )
    out["series"] = {}
    if spark:
        _apply_intraday_spark(out, spark, change_pct=intra_pct)
    else:
        out["points"] = []
    out["lite"] = True
    # Drop bulky nested blobs from wire payload
    earn = out.get("earnings")
    if isinstance(earn, dict):
        out["earnings"] = {
            k: earn.get(k)
            for k in (
                "symbol",
                "next_earnings_label",
                "prev_earnings_label",
                "days_to_earnings",
                "next_earnings_ts",
                "expect_eps",
                "eps_avg",
                "last_eps_actual",
            )
            if earn.get(k) is not None
        } or None
    return out


def _slim_sector_etf(row: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in row.items() if k != "series"}
    out["points"] = list(row.get("points") or [])[:64]
    return out


def _hydrate_sparks_from_cache(pick_rows: list[dict[str, Any]]) -> None:
    for row in pick_rows:
        # Even day/month-ready rows may lack 分时 — still restore from cache.
        if _spark_points_from_row(row):
            continue
        sym = str(row.get("symbol") or "").upper()
        cached = _SYM_CACHE.get(f"spark:{sym}") or _SYM_CACHE.get(f"quote:{sym}") or {}
        bundle = cached.get("bundle")
        spark = _spark_points_from_row(bundle if isinstance(bundle, dict) else None)
        if spark:
            _apply_intraday_spark(
                row,
                spark,
                change_pct=(bundle or {}).get("change_pct")
                if isinstance(bundle, dict)
                else row.get("change_pct"),
            )


async def _fetch_intraday_spark(
    client: httpx.AsyncClient,
    symbol: str,
    *,
    force: bool = False,
) -> list[dict[str, Any]]:
    sym = (symbol or "").strip().upper()
    if not sym:
        return []
    # Prefer spark cache, then quote cache — never poison quote/desk session series
    spark_cached = _SYM_CACHE.get(f"spark:{sym}") or {}
    quote_cached = _SYM_CACHE.get(f"quote:{sym}") or {}
    if not force:
        if time.time() - float(spark_cached.get("fetched_at") or 0) < _SYM_TTL:
            spark = _spark_points_from_row(spark_cached.get("bundle") or spark_cached)
            if spark:
                return spark
        if time.time() - float(quote_cached.get("fetched_at") or 0) < _SYM_TTL:
            spark = _spark_points_from_row(quote_cached.get("bundle"))
            if spark:
                return spark

    spark: list[dict[str, Any]] = []
    change_pct: float | None = None

    # 1) Yahoo 1d (classic list spark) — may 429
    async with _get_pick_sem():
        bundle, _errs = await fetch_symbol_bundle(
            client,
            symbol=sym,
            label=sym,
            short=sym,
            timeframes=[dict(_LIST_SPARK_TF)],
            include_yearly=False,
        )
    if bundle:
        spark = _spark_points_from_row(bundle)
        spark = [
            {"t": p.get("t"), "v": p.get("v")}
            for p in spark
            if p.get("v") is not None
        ]
        change_pct = bundle.get("change_pct")

    # 2) Nasdaq official chart — reliable when Yahoo is blocked
    if len(spark) < 2:
        nd = await fetch_nasdaq_intraday(client, sym, max_points=96)
        if nd and len(nd.get("points") or []) >= 2:
            spark = [
                {"t": p.get("t"), "v": p.get("v")}
                for p in (nd.get("points") or [])
                if p.get("v") is not None
            ]
            change_pct = nd.get("change_pct")

    if len(spark) < 2:
        # Keep last good list spark when all live sources fail
        return _spark_points_from_row(spark_cached.get("bundle") or spark_cached)

    _SYM_CACHE[f"spark:{sym}"] = {
        "bundle": {
            "symbol": sym,
            "points": spark,
            "change_pct": change_pct,
            "series": {
                "intraday": {
                    "chart": "line",
                    "points": spark,
                    "change_pct": change_pct,
                }
            },
        },
        "fetched_at": time.time(),
    }
    return spark


async def _hydrate_list_intraday_sparks(
    client: httpx.AsyncClient,
    pick_rows: list[dict[str, Any]],
    *,
    force: bool = False,
    limit: int = 18,
) -> None:
    """Fill same-day list sparklines via Nasdaq (Yahoo often 429).

    Also fills selected rows that already have day/month candles but lost
    their 分时 series — otherwise the desk chart goes blank after upgrade.
    """
    _hydrate_sparks_from_cache(pick_rows)
    missing = [
        str(r.get("symbol") or "").upper()
        for r in pick_rows
        if str(r.get("symbol") or "") and not _spark_points_from_row(r)
    ][: max(1, min(limit, _MAX_SECTOR_PICKS))]
    if not missing:
        return

    try:
        nd_map = await asyncio.wait_for(
            fetch_nasdaq_intraday_many(missing, concurrency=8, max_points=64),
            timeout=6.0,
        )
    except (asyncio.TimeoutError, httpx.HTTPError):
        nd_map = {}

    for sym, row_nd in nd_map.items():
        pts = [
            {"t": p.get("t"), "v": p.get("v")}
            for p in (row_nd.get("points") or [])
            if p.get("v") is not None
        ]
        if len(pts) < 2:
            continue
        _SYM_CACHE[f"spark:{sym}"] = {
            "bundle": {
                "symbol": sym,
                "points": pts,
                "change_pct": row_nd.get("change_pct"),
                "series": {
                    "intraday": {
                        "chart": "line",
                        "points": pts,
                        "change_pct": row_nd.get("change_pct"),
                    }
                },
            },
            "fetched_at": time.time(),
        }
        for row in pick_rows:
            if str(row.get("symbol") or "").upper() != sym:
                continue
            if _spark_points_from_row(row):
                break
            _apply_intraday_spark(
                row,
                pts,
                change_pct=row_nd.get("change_pct")
                if row_nd.get("change_pct") is not None
                else row.get("change_pct"),
            )
            break

    # Optional Yahoo fill only for a few stragglers (hard budget).
    still = [
        str(r.get("symbol") or "").upper()
        for r in pick_rows
        if str(r.get("symbol") or "") and not _spark_points_from_row(r)
    ][:4]
    if not still:
        return

    async def one(sym: str) -> tuple[str, list[dict[str, Any]]]:
        try:
            pts = await asyncio.wait_for(
                _fetch_intraday_spark(client, sym, force=force),
                timeout=1.6,
            )
            return sym, pts
        except (asyncio.TimeoutError, httpx.HTTPError):
            return sym, []

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(one(sym) for sym in still)),
            timeout=2.0,
        )
    except asyncio.TimeoutError:
        results = []
    by_sym = {sym: pts for sym, pts in results if pts}
    for row in pick_rows:
        sym = str(row.get("symbol") or "").upper()
        if sym in by_sym and not _spark_points_from_row(row):
            _apply_intraday_spark(row, by_sym[sym], change_pct=row.get("change_pct"))


async def _fetch_quote_limited(
    client: httpx.AsyncClient,
    symbol: str,
    label: str | None = None,
    *,
    force: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    async with _get_pick_sem():
        return await _fetch_quote(client, symbol, label, force=force)


def _lite_pick_from_quote(
    sym: str,
    quote: dict[str, Any] | None,
    *,
    active: dict[str, Any] | None,
    home_etf: dict[str, Any] | None,
    sector_id: str,
) -> dict[str, Any]:
    vc = _value_chain_for(sym)
    day_pct = (quote or {}).get("change_pct")
    price = (quote or {}).get("price")
    change = (quote or {}).get("change")
    etf_day = (home_etf or {}).get("change_pct")
    rs = None
    if day_pct is not None and etf_day is not None:
        try:
            rs = round(float(day_pct) - float(etf_day), 3)
        except (TypeError, ValueError):
            rs = None
    sector_label = (active or {}).get("label") or ""
    is_strong = (rs is not None and rs > 0) or (
        day_pct is not None
        and etf_day is not None
        and float(day_pct) > float(etf_day)
    )
    row = {
        "symbol": sym,
        "name": vc.get("name") or sym,
        "label": vc.get("name") or sym,
        "price": price,
        "change": change,
        "change_pct": day_pct,
        "month_change_pct": day_pct,
        "quarter_change_pct": None,
        "vs_sector_pct": rs,
        "momentum": float(day_pct or 0),
        "is_wave": bool(is_strong and float(day_pct or 0) > 1.5),
        "is_strong": bool(is_strong),
        "sector_id": (active or {}).get("id") or sector_id,
        "sector_label": sector_label,
        "points": [],
        "series": {},
        "lite": True,
        "earnings": None,
        "value_chain": vc,
        "move_analysis": None,
        "url": f"https://finance.yahoo.com/quote/{sym}",
    }
    apply_list_quote_fields(row, quote)
    return row


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


def _slim_news_item(item: dict[str, Any]) -> dict[str, Any]:
    """Keep feed cards light for sector / symbol news lists."""
    keys = (
        "id",
        "url",
        "title",
        "title_zh",
        "summary",
        "brief_zh",
        "source",
        "theme",
        "published",
        "published_ts",
        "sentiment",
        "sentiment_label",
        "sentiment_score",
        "sentiment_strength",
        "sentiment_logic",
        "sentiment_reason",
        "sentiment_factors",
        "holding_matches",
    )
    return {k: item.get(k) for k in keys if item.get(k) is not None}


def _match_sector_news(items: list[dict[str, Any]], topic_id: str) -> list[dict[str, Any]]:
    if topic_id in TOPICS:
        return filter_topic_items(items, topic_id, sort="latest")[:12]
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
    return rows[:12]


def _news_dedupe_key(item: dict[str, Any]) -> str:
    url = str(item.get("url") or "").strip().casefold()
    if url:
        return f"u:{url}"
    title = str(item.get("title") or "").strip().casefold()
    return f"t:{title}" if title else f"id:{item.get('id')}"


def _merge_news_latest(
    *buckets: list[dict[str, Any]],
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Merge news buckets, prefer fresher published_ts, dedupe by url/title."""
    best: dict[str, dict[str, Any]] = {}
    for bucket in buckets:
        for raw in bucket or []:
            if not isinstance(raw, dict):
                continue
            key = _news_dedupe_key(raw)
            if not key or key in {"u:", "t:", "id:"}:
                continue
            prev = best.get(key)
            if prev is None or float(raw.get("published_ts") or 0) >= float(
                prev.get("published_ts") or 0
            ):
                best[key] = dict(raw)
    rows = sorted(
        best.values(),
        key=lambda x: float(x.get("published_ts") or 0),
        reverse=True,
    )
    return [_slim_news_item(r) for r in rows[: max(1, min(int(limit), 16))]]


def _symbol_google_query(symbol: str, name: str | None = None) -> str:
    sym = (symbol or "").strip().upper()
    if not sym:
        return ""
    alias = _SYMBOL_GN_ALIAS.get(sym)
    if not alias:
        # Prefer ASCII / Latin company names from the pick row.
        raw = (name or "").strip()
        if raw and all(ord(ch) < 128 for ch in raw) and raw.upper() != sym:
            alias = raw
    if alias:
        return f'({sym} OR "{alias}") stock when:7d'
    return f"{sym} stock when:7d"


def _sector_google_query(topic_id: str, label: str | None = None) -> str:
    meta = SECTOR_TOPIC_PATTERNS.get(topic_id) or {}
    q = str(meta.get("gn_query") or "").strip()
    if q:
        return q
    label_en = (label or topic_id or "US stocks").strip()
    return f"({label_en}) stock when:7d"


def _match_symbol_news(
    items: list[dict[str, Any]],
    symbol: str,
    *,
    name: str | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Match intel / news mentioning a constituent ticker or company name."""
    sym = (symbol or "").strip().upper()
    if not sym:
        return []
    hits = match_portfolio_intel(
        items,
        [{"symbol": sym, "name": (name or "").strip() or sym}],
    )
    return [_slim_news_item(dict(i)) for i in hits[: max(1, min(limit, 16))]]


async def _hydrate_sector_symbol_news(
    news_items: list[dict[str, Any]],
    *,
    topic_id: str,
    sector_label: str,
    selected_symbol: str,
    selected_name: str | None,
    force: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Google News–first latest headlines for sector + selected ticker."""
    sector_matched = _match_sector_news(news_items, topic_id)
    symbol_matched = _match_symbol_news(
        news_items,
        selected_symbol,
        name=selected_name,
        limit=8,
    )
    sector_q = _sector_google_query(topic_id, sector_label)
    symbol_q = _symbol_google_query(selected_symbol, selected_name)
    async def _empty_news() -> list[dict[str, Any]]:
        return []

    sector_gn_task = fetch_google_news(
        sector_q,
        limit=12,
        source_name="Google News",
        source_id=f"gn-sector-{topic_id or 'hot'}",
        force=force,
    )
    symbol_gn_task = (
        fetch_google_news(
            symbol_q,
            limit=10,
            source_name="Google News",
            source_id=f"gn-sym-{(selected_symbol or 'x').lower()}",
            force=force,
        )
        if symbol_q
        else _empty_news()
    )
    try:
        sector_gn, symbol_gn = await asyncio.wait_for(
            asyncio.gather(sector_gn_task, symbol_gn_task),
            timeout=4.5,
        )
    except asyncio.TimeoutError:
        sector_gn, symbol_gn = [], []
    sector_news = _merge_news_latest(sector_gn, sector_matched, limit=12)
    symbol_news = (
        _merge_news_latest(symbol_gn, symbol_matched, limit=8) if symbol_q else []
    )
    try:
        sector_news, symbol_news = await asyncio.wait_for(
            asyncio.gather(
                _polish_desk_news(sector_news, online_limit=8),
                _polish_desk_news(symbol_news, online_limit=6),
            ),
            timeout=3.5,
        )
    except asyncio.TimeoutError:
        # Keep headlines without waiting on translation.
        sector_news = [_slim_news_item(dict(r)) for r in enrich_sentiment(sector_news)]
        symbol_news = [_slim_news_item(dict(r)) for r in enrich_sentiment(symbol_news)]
    return sector_news, symbol_news


async def _polish_desk_news(
    rows: list[dict[str, Any]] | None,
    *,
    online_limit: int = 12,
) -> list[dict[str, Any]]:
    """Translate headlines to Chinese + score 多/空 for sector desk cards."""
    items = [dict(r) for r in (rows or []) if isinstance(r, dict)]
    if not items:
        return []
    titled = await enrich_titles(items, online=True, online_limit=online_limit)
    scored = enrich_sentiment(titled)
    return [_slim_news_item(dict(r)) for r in scored]


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
    # Require both multi-TF candles AND usable 分时 — otherwise a Yahoo-only
    # cache hit would blank the intraday desk after a successful spark paint.
    if (
        not force
        and cached
        and time.time() - float(cached.get("fetched_at") or 0) < _SYM_TTL
        and _bundle_has_full_chart(cached.get("bundle"))
        and _series_intraday_ok(cached.get("bundle"))
    ):
        bundle = cached.get("bundle")
        _ensure_bundle_intraday_sessions(bundle)
        return bundle, []

    # Start Nasdaq immediately — Yahoo 429s often burn the desk budget alone.
    nd_intra_task = asyncio.create_task(
        fetch_nasdaq_intraday(client, sym, max_points=480)
    )
    nd_ohlc_task = asyncio.create_task(fetch_nasdaq_daily_bars(client, sym))

    bundle: dict[str, Any] | None = None
    errs: list[str] = []
    try:
        bundle, errs = await asyncio.wait_for(
            fetch_symbol_bundle(
                client,
                symbol=sym,
                label=label or sym,
                short=sym,
                timeframes=SECTOR_TIMEFRAMES,
                include_yearly=False,
            ),
            timeout=5.0,
        )
    except asyncio.TimeoutError:
        errs = [f"{sym}: Yahoo chart slow/timeout"]
    except Exception as exc:  # noqa: BLE001
        errs = [f"{sym}: Yahoo bundle failed ({exc.__class__.__name__})"]

    series = dict((bundle or {}).get("series") or {})
    need_intra = not _series_intraday_ok({"series": series})
    need_day = len((series.get("day") or {}).get("points") or []) < 2
    need_month = len((series.get("month") or {}).get("points") or []) < 2
    need_quarter = len((series.get("quarter") or {}).get("points") or []) < 2

    # Yahoo day/month alone is not enough — keep Nasdaq 分时 when intraday missing.
    if bundle and _bundle_has_full_chart(bundle) and not need_intra:
        nd_intra_task.cancel()
        nd_ohlc_task.cancel()
        _ensure_bundle_intraday_sessions(bundle)
        _SYM_CACHE[cache_key] = {"bundle": bundle, "fetched_at": time.time()}
        return bundle, errs

    if bundle and _bundle_has_full_chart(bundle):
        # Candles are fine; only wait on Nasdaq intraday (cancel daily OHLC).
        nd_ohlc_task.cancel()
        need_day = need_month = need_quarter = False

    extra_errs = list(errs or [])

    nd = None
    ohlc_series: dict[str, Any] = {}
    try:
        nd = await nd_intra_task
    except Exception as exc:  # noqa: BLE001
        extra_errs.append(f"{sym}: Nasdaq intra failed ({exc.__class__.__name__})")
    if need_day or need_month or need_quarter:
        try:
            daily_res = await nd_ohlc_task
            if isinstance(daily_res, list):
                ohlc_series = build_nasdaq_ohlc_series(daily_res)
        except Exception as exc:  # noqa: BLE001
            extra_errs.append(f"{sym}: Nasdaq OHLC failed ({exc.__class__.__name__})")
    else:
        nd_ohlc_task.cancel()

    if nd and len(nd.get("points") or []) >= 2 and need_intra:
        raw_pts = [
            {"t": int(p["t"]), "v": float(p["v"])}
            for p in (nd.get("points") or [])
            if p.get("t") and p.get("v") is not None
        ]
        series["intraday"] = _annotate_intraday_sessions(
            {
                "tf": "intraday",
                "label": "分时",
                "blurb": "当日分时 · 含盘前/盘后（Nasdaq）",
                "range": "1d",
                "interval": "1m",
                "chart": "line",
                "points": raw_pts,
                "change": nd.get("change"),
                "change_pct": nd.get("change_pct"),
                "previous_close": nd.get("previous_close"),
            }
        )

    for tf_id, row in ohlc_series.items():
        if tf_id == "day" and not need_day:
            continue
        if tf_id == "month" and not need_month:
            continue
        if tf_id == "quarter" and not need_quarter:
            continue
        if len((series.get(tf_id) or {}).get("points") or []) >= 2:
            continue
        series[tf_id] = row

    if not series:
        return bundle, extra_errs

    if isinstance(series.get("intraday"), dict):
        series["intraday"] = _annotate_intraday_sessions(dict(series["intraday"]))

    intra_pts = list((series.get("intraday") or {}).get("points") or [])
    spark_pts = (
        intra_pts[-64:]
        if intra_pts
        else list(((series.get("day") or {}).get("points") or [])[-64:])
    )
    if spark_pts and spark_pts[0].get("c") is not None and spark_pts[0].get("v") is None:
        spark_pts = [
            {"t": p["t"], "v": p["c"]} for p in spark_pts if p.get("c") is not None
        ]

    price = (bundle or {}).get("price")
    change = (bundle or {}).get("change")
    change_pct = (bundle or {}).get("change_pct")
    if nd:
        price = nd.get("price") if nd.get("price") is not None else price
        change = nd.get("change") if nd.get("change") is not None else change
        change_pct = (
            nd.get("change_pct") if nd.get("change_pct") is not None else change_pct
        )
    if price is None and series.get("day", {}).get("points"):
        price = series["day"]["points"][-1].get("c")

    fallback = {
        "id": ((bundle or {}).get("id") or sym.lower()),
        "symbol": sym,
        "label": (bundle or {}).get("label") or label or sym,
        "short": (bundle or {}).get("short") or sym,
        "price": price,
        "change": change,
        "change_pct": change_pct,
        "points": spark_pts,
        "series": series,
        "url": (bundle or {}).get("url") or f"https://finance.yahoo.com/quote/{sym}",
        "source": "nasdaq" if (nd or ohlc_series) else (bundle or {}).get("source"),
    }
    if _bundle_has_full_chart(fallback) and _series_intraday_ok(fallback):
        _SYM_CACHE[cache_key] = {"bundle": fallback, "fetched_at": time.time()}
        note = (
            f"{sym}: Yahoo chart incomplete; filled from Nasdaq"
            if need_intra or ohlc_series
            else f"{sym}: chart ready"
        )
        return fallback, extra_errs + ([note] if note else [])
    if _bundle_has_full_chart(fallback):
        # Candles ok but 分时 still missing — short TTL so we retry Nasdaq soon
        _SYM_CACHE[cache_key] = {
            "bundle": fallback,
            "fetched_at": time.time() - max(0, _SYM_TTL - 45),
        }
        return fallback, extra_errs + [f"{sym}: 日/月就绪，分时待补"]
    if _pick_has_intraday(fallback):
        # Intraday-only: short TTL so we retry OHLC soon
        _SYM_CACHE[cache_key] = {
            "bundle": fallback,
            "fetched_at": time.time() - max(0, _SYM_TTL - 45),
        }
        return fallback, extra_errs + [f"{sym}: using Nasdaq 分时 (日/月/季 pending)"]
    return bundle, extra_errs


def _session_id_et(ts: int) -> str:
    dt = datetime.fromtimestamp(int(ts), tz=_ET)
    mins = dt.hour * 60 + dt.minute
    if mins >= 20 * 60 or mins < 4 * 60:
        return "night"
    if mins < 9 * 60 + 30:
        return "pre"
    if mins < 16 * 60:
        return "regular"
    return "post"


def _session_segments_local(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not points:
        return []
    label_map = {
        "night": "夜盘",
        "pre": "盘前",
        "regular": "盘中",
        "post": "盘后",
    }
    segs: list[dict[str, Any]] = []
    cur = points[0].get("session") or "regular"
    start_i = 0
    for i, p in enumerate(points):
        sid = p.get("session") or "regular"
        if sid != cur:
            segs.append(
                {
                    "id": cur,
                    "label": label_map.get(cur, cur),
                    "i0": start_i,
                    "i1": i - 1,
                    "t0": points[start_i].get("t"),
                    "t1": points[i - 1].get("t"),
                }
            )
            cur = sid
            start_i = i
    segs.append(
        {
            "id": cur,
            "label": label_map.get(cur, cur),
            "i0": start_i,
            "i1": len(points) - 1,
            "t0": points[start_i].get("t"),
            "t1": points[-1].get("t"),
        }
    )
    return segs


async def _fetch_earnings_cached(
    client: httpx.AsyncClient,
    symbol: str,
    *,
    force: bool = False,
    upcoming_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    sym = (symbol or "").strip().upper()
    cache_key = f"earn:{sym}"
    cached = _SYM_CACHE.get(cache_key)
    if (
        not force
        and cached
        and time.time() - float(cached.get("fetched_at") or 0) < _SYM_TTL
        and _earnings_has_core(cached.get("earnings"))
    ):
        return cached.get("earnings")
    earnings = await _fetch_earnings(
        client, sym, upcoming_map=upcoming_map
    )
    # Avoid caching empty results during Yahoo outages — retry next time.
    if _earnings_has_core(earnings):
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
    b = bundle or {}
    series = (b.get("series") or {}).get(tf) or {}
    return list(series.get("points") or b.get("points") or [])


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


def _parse_us_date(text: str | None) -> datetime | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(raw[:10] if fmt == "%Y-%m-%d" else raw, fmt)
        except ValueError:
            continue
    return None


def _day_ts(day: datetime | None) -> int | None:
    if day is None:
        return None
    stamp = day.replace(hour=12, minute=0, second=0, microsecond=0, tzinfo=_ET)
    return int(stamp.timestamp())


def _earnings_has_core(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    return bool(
        payload.get("next_earnings_label")
        or payload.get("prev_earnings_label")
        or payload.get("expect_eps") is not None
        or payload.get("eps_avg") is not None
        or payload.get("last_eps_actual") is not None
        or payload.get("history")
    )


async def _fetch_earnings_yahoo(
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
            "source": "yahoo",
        }
        return _enrich_earnings_comparisons(payload)
    except Exception:  # noqa: BLE001
        return None


def _earnings_from_calendar_row(
    symbol: str, row: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Build a minimal earnings payload from a Nasdaq calendar row (no network)."""
    if not isinstance(row, dict):
        return None
    sym = (symbol or "").strip().upper()
    next_label = str(row.get("next_earnings_label") or row.get("date") or "")
    if not next_label and row.get("eps_forecast") is None:
        return None
    next_day = _parse_us_date(next_label) if next_label else None
    next_ts = _day_ts(next_day) if next_day else None
    days_to = None
    if next_ts:
        days_to = int((next_ts - time.time()) / 86400)
    eps_avg = row.get("eps_forecast")
    if eps_avg is None:
        eps_avg = _parse_money(row.get("eps"))
    return {
        "symbol": sym,
        "earnings_dates": (
            [{"ts": next_ts, "label": next_label}] if next_label else []
        ),
        "next_earnings_ts": next_ts,
        "next_earnings_label": next_label,
        "days_to_earnings": days_to,
        "prev_earnings_ts": None,
        "prev_earnings_label": "",
        "is_estimate": True,
        "eps_avg": eps_avg,
        "next_eps_estimate": eps_avg,
        "expect_eps": eps_avg,
        "analyst_count": row.get("estimate_count") or row.get("noOfEsts"),
        "last_eps_actual": None,
        "last_eps_estimate": None,
        "beat_pct": row.get("surprise_pct"),
        "source": "nasdaq-calendar",
    }


async def _fetch_earnings_nasdaq(
    client: httpx.AsyncClient,
    symbol: str,
    *,
    upcoming: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Nasdaq earnings-surprise + calendar (works when Yahoo quoteSummary is blocked)."""
    sym = (symbol or "").strip().upper()
    if not sym:
        return None
    history_rows: list[dict[str, Any]] = []
    try:
        resp = await client.get(
            f"https://api.nasdaq.com/api/company/{sym}/earnings-surprise",
            timeout=25.0,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.nasdaq.com",
                "Referer": f"https://www.nasdaq.com/market-activity/stocks/{sym.lower()}/earnings",
            },
        )
        resp.raise_for_status()
        table = (
            ((resp.json() or {}).get("data") or {}).get("earningsSurpriseTable") or {}
        )
        for row in table.get("rows") or []:
            reported = _parse_us_date(str(row.get("dateReported") or ""))
            actual = _parse_money(row.get("eps"))
            if actual is None and isinstance(row.get("eps"), (int, float)):
                actual = float(row.get("eps"))
            estimate = _parse_money(row.get("consensusForecast"))
            surprise = _parse_money(row.get("percentageSurprise"))
            history_rows.append(
                {
                    "period": str(row.get("fiscalQtrEnd") or ""),
                    "quarter_ts": _day_ts(reported),
                    "label": reported.date().isoformat() if reported else str(
                        row.get("dateReported") or ""
                    ),
                    "actual": actual,
                    "estimate": estimate,
                    "surprise_pct": surprise,
                }
            )
        history_rows.sort(
            key=lambda r: float(r.get("quarter_ts") or 0),
            reverse=True,
        )
    except Exception:  # noqa: BLE001
        history_rows = []

    up = upcoming
    if up is None:
        up = await lookup_upcoming_earnings(sym)
    elif isinstance(up, dict) and "symbol" not in up and sym in up:
        # full map passed in
        up = up.get(sym)

    next_label = ""
    next_ts = None
    days_to = None
    eps_avg = None
    analyst_count = None
    if isinstance(up, dict) and up.get("date"):
        next_label = str(up.get("next_earnings_label") or up.get("date") or "")
        next_day = _parse_us_date(next_label)
        next_ts = _day_ts(next_day)
        if next_ts:
            days_to = int((next_ts - time.time()) / 86400)
        eps_avg = up.get("eps_forecast")
        analyst_count = up.get("estimate_count")

    # If calendar miss, estimate next print ~90d after last report
    if not next_label and history_rows:
        prev_ts = history_rows[0].get("quarter_ts")
        if isinstance(prev_ts, (int, float)) and prev_ts > 0:
            est_day = datetime.fromtimestamp(float(prev_ts), tz=_ET) + timedelta(days=91)
            if est_day.timestamp() > time.time():
                next_ts = _day_ts(est_day)
                next_label = est_day.date().isoformat()
                days_to = int((float(next_ts) - time.time()) / 86400)

    prev = history_rows[0] if history_rows else None
    if not history_rows and not next_label:
        return None

    payload = {
        "symbol": sym,
        "earnings_dates": (
            [{"ts": next_ts, "label": next_label}] if next_label else []
        ),
        "next_earnings_ts": next_ts,
        "next_earnings_label": next_label,
        "days_to_earnings": days_to,
        "prev_earnings_ts": (prev or {}).get("quarter_ts"),
        "prev_earnings_label": (prev or {}).get("label") or "",
        "is_estimate": bool(next_label and not (isinstance(up, dict) and up.get("date"))),
        "eps_avg": eps_avg,
        "next_eps_estimate": eps_avg,
        "next_eps_low": None,
        "next_eps_high": None,
        "next_eps_growth": None,
        "analyst_count": analyst_count,
        "revenue_avg": None,
        "quarterly": [
            {
                "date": r.get("label"),
                "label": r.get("label"),
                "actual": r.get("actual"),
                "estimate": r.get("estimate"),
            }
            for r in reversed(history_rows[:6])
        ],
        "history": history_rows[:6],
        "current_quarter_estimate": eps_avg,
        "trend": {},
        "source": "nasdaq",
    }
    return _enrich_earnings_comparisons(payload)


async def _fetch_earnings(
    client: httpx.AsyncClient,
    symbol: str,
    *,
    upcoming_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    yahoo = await _fetch_earnings_yahoo(client, symbol)
    if _earnings_has_core(yahoo) and yahoo and yahoo.get("next_earnings_label"):
        return yahoo
    nasdaq = await _fetch_earnings_nasdaq(
        client,
        symbol,
        upcoming=(upcoming_map or {}).get(symbol.upper()) if upcoming_map else None,
    )
    if _earnings_has_core(nasdaq):
        return nasdaq
    return yahoo if _earnings_has_core(yahoo) else nasdaq


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
        # Fast ETF strip via CNBC/Yahoo light quotes (avoid 8× multi-TF Yahoo charts)
        errors: list[str] = []
        etf_symbols = [row["symbol"] for row in SECTOR_ETFS]
        # ETF strip: skip Yahoo Overnight page scrapes (keep desk cold-start fast).
        etf_quotes = await fetch_day_quotes(etf_symbols, overnight_priority=[])
        sectors: list[dict[str, Any]] = []
        for spec in SECTOR_ETFS:
            quote = etf_quotes.get(str(spec["symbol"]).upper())
            if not quote:
                errors.append(f"{spec['symbol']}: quote failed")
                # Keep the card even without a live quote so navigation still works
                quote = {}
            day_pct = quote.get("change_pct")
            universe = _universe_for_sector(spec["id"], list(spec["picks"]))
            sectors.append(
                {
                    "id": spec["id"],
                    "symbol": spec["symbol"],
                    "label": spec["label"],
                    "short": spec["short"],
                    "blurb": spec["blurb"],
                    "topic_id": spec["topic_id"],
                    "picks": list(spec["picks"]),
                    "universe": universe,
                    "pick_count": len(universe),
                    "pick_preview": universe[:6],
                    "price": quote.get("price"),
                    "change": quote.get("change"),
                    "change_pct": day_pct,
                    "month_change_pct": day_pct,
                    "quarter_change_pct": None,
                    "momentum": float(day_pct or 0),
                    "is_wave": bool(day_pct is not None and float(day_pct) > 1.2),
                    "points": [],
                    "series": {},
                    "url": f"https://finance.yahoo.com/quote/{spec['symbol']}",
                    "as_of": None,
                }
            )

        # Hot rank: day tape first (month spark optional / filled later)
        sectors.sort(
            key=lambda r: (
                float(r.get("momentum") or -999),
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
            "source": "CNBC / Yahoo light quotes + 情报源",
            "cached": False,
        }
        _CACHE["payload"] = payload
        _CACHE["fetched_at"] = now

        payload = dict(payload)
        payload["cached"] = False

    news_items = items or []
    sectors = list(payload.get("sectors") or [])
    # Backfill universe metadata for cached ETF rows
    for row in sectors:
        if row.get("universe"):
            continue
        universe = _universe_for_sector(row.get("id") or "", list(row.get("picks") or []))
        row["universe"] = universe
        row["pick_count"] = len(universe)
        row["pick_preview"] = universe[:6]

    # Default to current hottest sector (not hard-coded AI)
    sector_id = (selected_sector or "").strip().lower()
    if not sector_id or not any(s["id"] == sector_id for s in sectors):
        sector_id = sectors[0]["id"] if sectors else "ai"
    active = next((s for s in sectors if s["id"] == sector_id), None)
    if active is None and sectors:
        active = sectors[0]
        sector_id = active["id"]

    # Universe: all market-map constituents for this desk sector ∪ curated picks
    pick_symbols = list((active or {}).get("universe") or [])
    if not pick_symbols:
        pick_symbols = _universe_for_sector(
            sector_id, list((active or {}).get("picks") or [])
        )

    pick_rows: list[dict[str, Any]] = []
    pick_errors: list[str] = []
    earnings_by_symbol: dict[str, Any] = {}
    picks_key = f"v2:{sector_id}:{'|'.join(pick_symbols)}"
    picks_cached = _PICKS_CACHE.get(sector_id) or {}
    picks_age = time.time() - float(picks_cached.get("fetched_at") or 0)
    picks_key_ok = picks_cached.get("key") == picks_key and bool(
        picks_cached.get("pick_rows")
    )
    picks_fresh = not force and picks_key_ok and picks_age < _PICKS_TTL
    picks_stale_ok = (
        not force and picks_key_ok and picks_age < _PICKS_STALE_TTL
    )
    picks_from_cache = False
    if picks_fresh or picks_stale_ok:
        pick_rows = [dict(r) for r in picks_cached["pick_rows"]]
        earnings_by_symbol = dict(picks_cached.get("earnings_by_symbol") or {})
        picks_from_cache = True

    selected = (selected_symbol or "").strip().upper()
    universe = {str(s).strip().upper() for s in pick_symbols if str(s).strip()}
    in_rows = any(p.get("symbol") == selected for p in pick_rows)
    # Keep an explicit ?symbol= even on cold refresh (pick_rows empty before quotes).
    # Only fall back when the request has no symbol or it's outside this sector universe.
    if not selected or (not in_rows and selected not in universe):
        selected = (
            pick_rows[0]["symbol"]
            if pick_rows
            else (pick_symbols[0] if pick_symbols else "")
        )

    home_etf = active
    yahoo_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/",
    }

    # Fast path: batch day quotes for the whole list; full multi-TF chart only
    # for the selected symbol (biggest latency win on sector switch).
    if not picks_from_cache and pick_symbols:
        # Overnight page scrape only for the selected symbol — never N× Yahoo HTML.
        # At 夜盘 hydrate Overnight for the visible list (not only selected).
        if session_from_clock()[0] == "night":
            night_pri = []
            if selected:
                night_pri.append(selected)
            for sym in pick_symbols:
                if sym not in night_pri:
                    night_pri.append(sym)
                if len(night_pri) >= 3:
                    break
        else:
            night_pri = [selected] if selected else []
        try:
            day_quotes = await asyncio.wait_for(
                fetch_day_quotes(
                    pick_symbols,
                    overnight_priority=night_pri,
                    bypass_cache=force,
                ),
                timeout=3.5,
            )
        except asyncio.TimeoutError:
            day_quotes = {}
        for sym in pick_symbols:
            quote = day_quotes.get(sym)
            pick_rows.append(
                _lite_pick_from_quote(
                    sym,
                    quote,
                    active=active,
                    home_etf=home_etf,
                    sector_id=sector_id,
                )
            )
        pick_rows.sort(
            key=lambda r: (
                1 if r.get("is_wave") else 0,
                float(r.get("momentum") or -999),
                float(r.get("change_pct") or -999),
            ),
            reverse=True,
        )
        # Do not drop an in-universe ?symbol= if its lite row failed to build.
        if not selected or (
            not any(p.get("symbol") == selected for p in pick_rows)
            and selected not in universe
        ):
            selected = pick_rows[0]["symbol"] if pick_rows else selected
    elif picks_from_cache and pick_symbols and (
        not picks_fresh or session_from_clock()[0] in {"night", "pre", "post"}
    ):
        # Soft-refresh day tape with a hard budget — never stall the list paint.
        if session_from_clock()[0] == "night":
            night_pri = []
            if selected:
                night_pri.append(selected)
            for sym in pick_symbols:
                if sym not in night_pri:
                    night_pri.append(sym)
                if len(night_pri) >= 3:
                    break
        else:
            night_pri = [selected] if selected else []
        try:
            day_quotes = await asyncio.wait_for(
                fetch_day_quotes(
                    pick_symbols,
                    overnight_priority=night_pri,
                ),
                timeout=1.4,
            )
        except asyncio.TimeoutError:
            day_quotes = {}
        for row in pick_rows:
            sym = str(row.get("symbol") or "").upper()
            quote = day_quotes.get(sym)
            if not quote:
                continue
            apply_list_quote_fields(row, quote)
            if quote.get("price") is not None:
                row["price"] = quote.get("price")
            if quote.get("change") is not None:
                row["change"] = quote.get("change")
            if quote.get("change_pct") is not None:
                row["change_pct"] = quote.get("change_pct")
                row["momentum"] = float(quote["change_pct"] or 0)

    # List first: sparks from cache. Selected chart races briefly (≤2s), then
    # continues in background so 成分股 never waits on a full multi-TF fetch.
    selected_pick = next((p for p in pick_rows if p.get("symbol") == selected), None)
    need_selected_chart = bool(selected) and not _pick_has_chart(selected_pick)
    _hydrate_sparks_from_cache(pick_rows)

    async def _apply_selected_bundle(bundle: dict[str, Any]) -> None:
        nonlocal selected_pick
        if not bundle or not (
            _bundle_has_full_chart(bundle) or _pick_has_intraday(bundle)
        ):
            return
        vc = _value_chain_for(selected)
        rs = _relative_strength(bundle, home_etf)
        wave = _momentum_fields(bundle)
        day_pct = bundle.get("change_pct")
        sector_label = (active or {}).get("label") or ""
        prev_row = next((p for p in pick_rows if p.get("symbol") == selected), None)
        rich = {
            **bundle,
            "name": vc.get("name") or selected,
            "month_change_pct": wave["month_change_pct"],
            "quarter_change_pct": wave["quarter_change_pct"],
            "vs_sector_pct": rs,
            "momentum": wave["momentum"],
            "is_wave": wave["is_wave"],
            "is_strong": wave["is_wave"]
            or (rs is not None and rs > 0)
            or float(day_pct or 0) > float((home_etf or {}).get("change_pct") or 0),
            "sector_id": sector_id,
            "sector_label": sector_label,
            "earnings": earnings_by_symbol.get(selected),
            "value_chain": vc,
            "move_analysis": None,
            "lite": False,
            "chart_attempted": True,
        }
        apply_list_quote_fields(rich, prev_row)
        for idx, row in enumerate(pick_rows):
            if row.get("symbol") == selected:
                pick_rows[idx] = rich
                break
        else:
            pick_rows.insert(0, rich)
        selected_pick = rich

    async def _upgrade_selected_chart() -> None:
        if not (selected and need_selected_chart):
            return
        try:
            async with httpx.AsyncClient(
                headers=yahoo_headers,
                follow_redirects=True,
                trust_env=False,
                timeout=httpx.Timeout(16.0, connect=3.0),
            ) as client:
                bundle, errs = await asyncio.wait_for(
                    _fetch_quote_limited(client, selected, selected, force=force),
                    timeout=14.0,
                )
        except (asyncio.TimeoutError, httpx.HTTPError) as exc:
            pick_errors.append(f"{selected}: chart timeout ({exc.__class__.__name__})")
            return
        pick_errors.extend(errs or [])
        await _apply_selected_bundle(bundle or {})
        # Persist into picks cache even if the HTTP response already left.
        if selected_pick and not selected_pick.get("lite"):
            cached = _PICKS_CACHE.get(sector_id) or {}
            rows = [dict(r) for r in (cached.get("pick_rows") or pick_rows)]
            for idx, row in enumerate(rows):
                if row.get("symbol") == selected:
                    rows[idx] = dict(selected_pick)
                    break
            else:
                rows.insert(0, dict(selected_pick))
            _PICKS_CACHE[sector_id] = {
                "key": picks_key,
                "pick_rows": rows,
                "earnings_by_symbol": dict(
                    cached.get("earnings_by_symbol") or earnings_by_symbol
                ),
                "fetched_at": cached.get("fetched_at") or time.time(),
            }

    # Chart + list sparks in parallel. Prefer finishing sparks before reply
    # so the left column isn't blank; chart may continue warming cache.
    sparked = sum(1 for r in pick_rows[:12] if _spark_points_from_row(r))
    need_sparks = bool(pick_rows) and sparked < min(8, len(pick_rows))
    chart_task = (
        asyncio.create_task(_upgrade_selected_chart())
        if need_selected_chart and selected
        else None
    )
    sparks_task = None
    if need_sparks:

        async def _sparks_job() -> None:
            try:
                async with httpx.AsyncClient(
                    headers=yahoo_headers,
                    follow_redirects=True,
                    trust_env=False,
                    timeout=httpx.Timeout(4.0, connect=2.0),
                ) as spark_client:
                    await _hydrate_list_intraday_sparks(
                        spark_client,
                        pick_rows,
                        force=False,
                        limit=min(12, len(pick_rows) or 1),
                    )
            except (asyncio.TimeoutError, httpx.HTTPError):
                _hydrate_sparks_from_cache(pick_rows)

        sparks_task = asyncio.create_task(_sparks_job())

    waiters = []
    if chart_task is not None:
        waiters.append(asyncio.shield(chart_task))
    if sparks_task is not None:
        waiters.append(asyncio.shield(sparks_task))
    if waiters:
        try:
            await asyncio.wait_for(
                asyncio.gather(*waiters, return_exceptions=True),
                timeout=8.0,
            )
        except asyncio.TimeoutError:
            pass
    # If sparks still thin, give them a short extra beat before we freeze the list.
    if sparks_task is not None and not sparks_task.done():
        sparked_now = sum(1 for r in pick_rows[:12] if _spark_points_from_row(r))
        if sparked_now < min(6, len(pick_rows)):
            try:
                await asyncio.wait_for(asyncio.shield(sparks_task), timeout=3.5)
            except asyncio.TimeoutError:
                pass
    # Selected chart is more important than a perfect spark fill — wait briefly
    # if the desk still has no multi-TF / 分时 for the clicked symbol.
    if chart_task is not None and not chart_task.done():
        selected_pick = next(
            (p for p in pick_rows if p.get("symbol") == selected), selected_pick
        )
        if not (
            _pick_has_chart(selected_pick) or _pick_has_intraday(selected_pick)
        ):
            try:
                await asyncio.wait_for(asyncio.shield(chart_task), timeout=4.0)
            except asyncio.TimeoutError:
                pass
            selected_pick = next(
                (p for p in pick_rows if p.get("symbol") == selected), selected_pick
            )
    _hydrate_sparks_from_cache(pick_rows)

    async def _persist_sparks_later() -> None:
        if sparks_task is None:
            return
        try:
            await sparks_task
        except Exception:  # noqa: BLE001
            return
        cached = _PICKS_CACHE.get(sector_id) or {}
        if not cached.get("pick_rows"):
            return
        rows = [dict(r) for r in cached["pick_rows"]]
        by = {str(r.get("symbol") or "").upper(): r for r in pick_rows}
        for row in rows:
            src = by.get(str(row.get("symbol") or "").upper())
            if not src:
                continue
            pts = _spark_points_from_row(src)
            if pts and not _spark_points_from_row(row):
                _apply_intraday_spark(row, pts, change_pct=src.get("change_pct"))
        _PICKS_CACHE[sector_id] = {
            **cached,
            "pick_rows": rows,
        }

    if sparks_task is not None and not sparks_task.done():
        try:
            asyncio.get_running_loop().create_task(_persist_sparks_later())
        except RuntimeError:
            pass

    if pick_rows:
        pick_rows.sort(
            key=lambda r: (
                1 if r.get("is_wave") else 0,
                float(r.get("momentum") or -999),
                float(r.get("month_change_pct") or r.get("change_pct") or -999),
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

    if not selected or not any(p.get("symbol") == selected for p in pick_rows):
        if selected and selected in {
            str(s).strip().upper() for s in pick_symbols if str(s).strip()
        }:
            pass
        else:
            selected = pick_rows[0]["symbol"] if pick_rows else ""
    selected_pick = next((p for p in pick_rows if p.get("symbol") == selected), None)

    # Refresh value-chain blurbs (covers newly added archive entries even on warm cache)
    for row in pick_rows:
        vc = _value_chain_for(str(row.get("symbol") or ""))
        row["value_chain"] = vc
        if not row.get("name") or row.get("name") == row.get("symbol"):
            row["name"] = vc.get("name") or row.get("symbol")

    # Fast earnings: cached Nasdaq calendar first (no network), then a short
    # surprise-API fetch only for the selected symbol.
    upcoming_peek = peek_upcoming_earnings_map()
    for row in pick_rows:
        sym = str(row.get("symbol") or "").upper()
        if not sym:
            continue
        earn = row.get("earnings") if isinstance(row.get("earnings"), dict) else None
        if not _earnings_has_core(earn):
            earn = earnings_by_symbol.get(sym) or _earnings_from_calendar_row(
                sym, upcoming_peek.get(sym)
            )
        if earn:
            row["earnings"] = earn
            earnings_by_symbol[sym] = earn

    # Earnings surprise API is slow — warm it in the background only.
    if (
        selected
        and not picks_from_cache
        and not _earnings_has_core(earnings_by_symbol.get(selected))
    ):

        async def _earn_bg() -> None:
            try:
                async with httpx.AsyncClient(
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/json, text/plain, */*",
                    },
                    follow_redirects=True,
                    trust_env=False,
                    timeout=httpx.Timeout(2.0, connect=1.2),
                ) as client:
                    earn = await asyncio.wait_for(
                        _fetch_earnings_nasdaq(
                            client,
                            selected,
                            upcoming=upcoming_peek.get(selected),
                        ),
                        timeout=2.0,
                    )
            except (asyncio.TimeoutError, httpx.HTTPError):
                return
            if not earn:
                return
            cached = _PICKS_CACHE.get(sector_id) or {}
            earn_map = dict(cached.get("earnings_by_symbol") or {})
            earn_map[selected] = earn
            rows = [dict(r) for r in (cached.get("pick_rows") or [])]
            for row in rows:
                if row.get("symbol") == selected:
                    row["earnings"] = earn
            if rows:
                _PICKS_CACHE[sector_id] = {
                    "key": cached.get("key") or picks_key,
                    "pick_rows": rows,
                    "earnings_by_symbol": earn_map,
                    "fetched_at": cached.get("fetched_at") or time.time(),
                }

        try:
            asyncio.get_running_loop().create_task(_earn_bg())
        except RuntimeError:
            pass

    if selected_pick is not None:
        selected_pick = next(
            (p for p in pick_rows if p.get("symbol") == selected), selected_pick
        )
        selected_pick["earnings"] = earnings_by_symbol.get(selected) or selected_pick.get(
            "earnings"
        )
        selected_pick["value_chain"] = _value_chain_for(selected)

    # Persist enriched earnings / value-chain back into the sector cache
    if pick_rows:
        _PICKS_CACHE[sector_id] = {
            "key": picks_key,
            "pick_rows": [dict(r) for r in pick_rows],
            "earnings_by_symbol": dict(earnings_by_symbol),
            "fetched_at": (_PICKS_CACHE.get(sector_id) or {}).get("fetched_at")
            or time.time(),
        }

    # Warm the upcoming calendar in the background for next sector click (non-blocking)
    if not upcoming_peek:
        try:
            asyncio.get_running_loop().create_task(get_upcoming_earnings_map(force=False))
        except RuntimeError:
            pass

    topic_key = str((active or {}).get("topic_id") or sector_id or "")
    selected_name = None
    for row in pick_rows:
        if str(row.get("symbol") or "").upper() == str(selected or "").upper():
            selected_name = str(row.get("name") or "") or None
            break
    # Instant news from in-memory intel; GN hydrate warms cache in background.
    sector_news_slim = [
        _slim_news_item(dict(i))
        for i in _match_sector_news(news_items, topic_key)[:12]
    ]
    selected_symbol_news = [
        _slim_news_item(dict(i))
        for i in _match_symbol_news(
            news_items,
            str(selected or ""),
            name=selected_name,
            limit=8,
        )
    ]

    def _stash_news(
        sector_gn: list[dict[str, Any]],
        symbol_gn: list[dict[str, Any]],
    ) -> None:
        cached = _PICKS_CACHE.get(sector_id) or {}
        meta = dict(cached) if cached else {
            "key": picks_key,
            "pick_rows": [dict(r) for r in pick_rows],
            "earnings_by_symbol": dict(earnings_by_symbol),
            "fetched_at": time.time(),
        }
        if sector_gn:
            meta["sector_news"] = sector_gn
        sym_map = dict(meta.get("symbol_news") or {})
        if symbol_gn and selected:
            sym_map[str(selected).upper()] = symbol_gn
            meta["symbol_news"] = sym_map
        if sector_gn or symbol_gn:
            meta["news_at"] = time.time()
            _PICKS_CACHE[sector_id] = meta

    async def _news_bg() -> None:
        try:
            sector_gn, symbol_gn = await _hydrate_sector_symbol_news(
                news_items,
                topic_id=topic_key,
                sector_label=str((active or {}).get("label") or sector_id or ""),
                selected_symbol=str(selected or ""),
                selected_name=selected_name,
                force=force,
            )
        except Exception:  # noqa: BLE001
            return
        _stash_news(sector_gn, symbol_gn)

    # Prefer previously warmed GN headlines when available (< 3 min).
    news_cached = _PICKS_CACHE.get(sector_id) or {}
    news_age = time.time() - float(news_cached.get("news_at") or 0)
    warm_sector = list(news_cached.get("sector_news") or [])
    warm_sym = (news_cached.get("symbol_news") or {}).get(
        str(selected or "").upper()
    )
    if news_age < 180 and (warm_sector or warm_sym):
        if warm_sector:
            sector_news_slim = warm_sector
        if warm_sym:
            selected_symbol_news = list(warm_sym)
    else:
        # Brief inline hydrate so 个股信息流 isn't empty on first paint.
        # Finish in background if Yahoo/GN is slow.
        try:
            sector_gn, symbol_gn = await asyncio.wait_for(
                _hydrate_sector_symbol_news(
                    news_items,
                    topic_id=topic_key,
                    sector_label=str((active or {}).get("label") or sector_id or ""),
                    selected_symbol=str(selected or ""),
                    selected_name=selected_name,
                    force=force,
                ),
                timeout=3.2,
            )
            if sector_gn:
                sector_news_slim = list(sector_gn)
            if symbol_gn:
                selected_symbol_news = list(symbol_gn)
            _stash_news(sector_gn or [], symbol_gn or [])
        except asyncio.TimeoutError:
            try:
                asyncio.get_running_loop().create_task(_news_bg())
            except RuntimeError:
                pass
        except Exception:  # noqa: BLE001
            try:
                asyncio.get_running_loop().create_task(_news_bg())
            except RuntimeError:
                pass
    sector_news = sector_news_slim
    # Enrich move analysis + per-symbol news once news is available
    for row in pick_rows:
        home_etf = next(
            (s for s in sectors if s.get("id") == row.get("sector_id")), active
        )
        sym = str(row.get("symbol") or "").upper()
        if sym and sym == str(selected or "").upper() and selected_symbol_news:
            row["symbol_news"] = list(selected_symbol_news)
        else:
            row["symbol_news"] = _match_symbol_news(
                news_items,
                sym,
                name=str(row.get("name") or "") or None,
                limit=8,
            )
        # Prefer symbol-matched headlines for move factors; fall back to sector
        move_news = row["symbol_news"] or sector_news_slim
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
            news=move_news,
        )

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
                f"{(active or {}).get('label') or '该板块'}近端汇总 "
                f"{len(sector_news)} 条最新报道（Google News）。"
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
        "latest": sector_news_slim[:6]
        or [_slim_news_item(dict(i)) for i in (sector_bear.get("latest") or [])[:6]],
        "spotlight": [
            _slim_news_item(dict(i)) for i in (sector_bear.get("spotlight") or [])[:6]
        ],
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

    # Clock-authoritative session badges (盘前→盘中→盘后→夜盘) on every response.
    for row in pick_rows:
        restamp_list_session(row)
    if selected_pick is not None:
        restamp_list_session(selected_pick)

    wire_picks = [_slim_pick_row(dict(p), selected) for p in pick_rows]
    for row in wire_picks:
        restamp_list_session(row)
    wire_selected = next((p for p in wire_picks if p.get("symbol") == selected), None)
    # Always expose the selected desk chart (full multi-TF or Nasdaq 分时 fallback)
    if selected_pick and (
        _pick_has_chart(selected_pick) or _pick_has_intraday(selected_pick)
    ):
        wire_selected = dict(selected_pick)
        restamp_list_session(wire_selected)
        wire_picks = [
            wire_selected if p.get("symbol") == selected else p for p in wire_picks
        ]

    return {
        **payload,
        "sectors": [_slim_sector_etf(dict(s)) for s in sectors],
        "cached": bool(picks_fresh) and not force,
        "market_session": session_from_clock()[0],
        "market_session_label": session_from_clock()[1],
        "ai_desk": hot_desk,
        "hot_desk": hot_desk,
        "hot_sectors": [s for s in sectors if s.get("is_hot")][:4],
        "active_sector_id": sector_id,
        "active_sector": _slim_sector_etf(dict(active)) if active else active,
        "sector_news": sector_news_slim,
        "sector_bearish": sector_bear,
        "picks": wire_picks,
        "wave_leaders": [p for p in wire_picks if p.get("is_wave")][:10],
        "selected_symbol": selected,
        "selected_pick": wire_selected,
        "symbol_news": list((wire_selected or {}).get("symbol_news") or []),
        "value_chain": (wire_selected or {}).get("value_chain")
        or _value_chain_for(selected),
        "earnings_calendar": earnings_calendar[:12],
        "selected_earnings": earnings_by_symbol.get(selected)
        or (wire_selected or {}).get("earnings"),
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
