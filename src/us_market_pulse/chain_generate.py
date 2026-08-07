"""Dynamic industry-chain generation from free-form keywords."""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from typing import Any

import httpx

from us_market_pulse.chains import CORE_SYMBOLS, _co, _panel, sort_companies


_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 30 * 60  # shorter: new IPOs (e.g. SPCX) should surface faster
_CACHE_VER = "v6"
_PANEL_CO_LIMIT = 28
_WS = re.compile(r"[\s\-_/·•,+]+")


def _norm(text: str) -> str:
    return _WS.sub("", (text or "").strip().lower())


# Extra English search seeds for common Chinese industry phrases.
QUERY_SEARCH_ALIASES: dict[str, list[str]] = {
    "太空ai": ["SPCX", "SpaceX", "Starlink", "space AI"],
    "太空": ["SPCX", "SpaceX", "Starlink", "space"],
    "航天": ["SPCX", "SpaceX", "aerospace"],
    "星链": ["SPCX", "Starlink", "SpaceX"],
    "spacex": ["SPCX", "SpaceX"],
    "飞机": ["aircraft", "airline", "aviation", "Boeing", "Airbus"],
    "航空": ["aviation", "airline", "aerospace", "Boeing"],
    "民航": ["airline", "commercial aviation"],
    "航司": ["airline stocks"],
    "军工": ["defense", "aerospace defense", "Lockheed", "Raytheon"],
    "国防": ["defense contractors", "Lockheed Martin"],
    "银行": ["bank", "banking", "JPMorgan"],
    "白酒": ["liquor", "spirits", "beverage"],
    "光伏": ["solar", "First Solar", "clean energy"],
    "芯片": ["semiconductor", "chip", "TSMC", "NVIDIA"],
    "半导体": ["semiconductor", "chip stocks"],
    "人工智能": ["NVDA", "artificial intelligence", "AI chip"],
    "新能源车": ["EV", "electric vehicle", "TSLA"],
    "网络安全": ["cybersecurity", "CRWD"],
    "人形机器人": ["humanoid robot", "robotics"],
    "医疗": ["healthcare", "biotech", "pharma"],
    "医药": ["pharmaceutical", "biotech"],
}


def resolve_search_aliases(query: str) -> list[str]:
    """Map free-form (esp. Chinese) keywords to English Yahoo search seeds."""
    qn = _norm(query)
    out: list[str] = []
    if qn in QUERY_SEARCH_ALIASES:
        out.extend(QUERY_SEARCH_ALIASES[qn])
    # Substring / containment match for compounds like「民用飞机」.
    for key, terms in QUERY_SEARCH_ALIASES.items():
        if key == qn:
            continue
        if key in qn or qn in key:
            out.extend(terms)
    # Dedup
    seen: set[str] = set()
    uniq: list[str] = []
    for t in out:
        k = t.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        uniq.append(t.strip())
    return uniq


# Theme packs compose into a panorama when keywords hit.
THEME_PACKS: list[dict[str, Any]] = [
    {
        "id": "aviation",
        "label": "飞机 / 航空",
        "keywords": [
            "飞机",
            "航空",
            "民航",
            "航司",
            "客机",
            "airline",
            "aviation",
            "aircraft",
            "airplane",
            "波音",
            "空客",
        ],
        "search_terms": [
            "Boeing",
            "airline",
            "aviation",
            "aircraft",
            "aerospace defense",
        ],
        "must_include": [
            _co("BA", "波音", note="民用飞机 / 防务", core=True),
            _co("GE", "通用电气", note="航空发动机", core=True, sector="industrials"),
            _co("RTX", "RTX", note="发动机 / 航电", core=True, sector="industrials"),
        ],
        "support_nodes": ["航空材料", "发动机 / 航电"],
        "core_nodes": ["飞机制造", "航空公司"],
        "app_nodes": ["空港物流", "国防航空"],
        "panels": [
            _panel(
                "airframe",
                "飞机制造",
                tone="core",
                branch="airframe",
                blurb="整机与机体结构",
                companies=[
                    _co("BA", "波音", note="民用 / 军用飞机", core=True),
                    _co("SPR", "Spirit AeroSystems", note="机身结构件"),
                    _co("TXT", "德事隆", note="公务机 / 航空", sector="industrials"),
                    _co("HEI", "HEICO", note="航空零部件", sector="industrials"),
                ],
            ),
            _panel(
                "engines",
                "发动机 / 航电",
                tone="support",
                branch="engines",
                companies=[
                    _co("GE", "通用电气", note="GE Aerospace", core=True, sector="industrials"),
                    _co("RTX", "RTX", note="普惠发动机", core=True, sector="industrials"),
                    _co("HON", "霍尼韦尔", note="航电与系统", core=True),
                    _co("TDG", "TransDigm", note="航空零部件", sector="industrials"),
                    _co("CW", "Curtiss-Wright", note="航空系统", sector="industrials"),
                ],
            ),
            _panel(
                "materials_av",
                "航空材料 / 复材",
                tone="support",
                branch="materials_av",
                companies=[
                    _co("DD", "杜邦", note="特种材料"),
                    _co("ATI", "ATI", note="高温合金", sector="materials"),
                    _co("HXL", "Hexcel", note="航空复合材料", sector="industrials"),
                ],
            ),
            _panel(
                "airlines",
                "航空公司",
                tone="core",
                branch="airlines",
                companies=[
                    _co("DAL", "达美航空", note="全美航司", core=True, sector="industrials"),
                    _co("UAL", "美联航", note="全美航司", core=True, sector="industrials"),
                    _co("AAL", "美国航空", note="全美航司", sector="industrials"),
                    _co("LUV", "西南航空", note="低成本航司", sector="industrials"),
                    _co("ALK", "阿拉斯加航空", note="区域航司", sector="industrials"),
                    _co("RYAAY", "Ryanair", note="欧洲低成本", sector="industrials"),
                ],
            ),
            _panel(
                "defense_av",
                "国防航空",
                tone="app",
                branch="defense_av",
                companies=[
                    _co("LMT", "洛克希德马丁", note="战机 / 防务", core=True, sector="industrials"),
                    _co("NOC", "诺斯罗普格鲁曼", note="航空防务", core=True, sector="industrials"),
                    _co("GD", "通用动力", note="航电 / 防务", sector="industrials"),
                    _co("BA", "波音", note="军机与防务", core=True),
                    _co("HII", "亨廷顿英格尔斯", note="舰船 / 防务", sector="industrials"),
                ],
            ),
            _panel(
                "airport_logistics",
                "空港 / 物流",
                tone="app",
                branch="airport_logistics",
                companies=[
                    _co("FDX", "联邦快递", note="航空物流", sector="industrials"),
                    _co("UPS", "联合包裹", note="航空物流", sector="industrials"),
                    _co("BA", "波音", note="货机需求"),
                ],
            ),
        ],
    },
    {
        "id": "space",
        "label": "太空 / 航天",
        "keywords": [
            "太空",
            "航天",
            "卫星",
            "火箭",
            "宇航",
            "星链",
            "spacex",
            "spcx",
            "space",
            "satellite",
            "rocket",
            "aerospace",
            "orbit",
            "starlink",
        ],
        "search_terms": [
            "SPCX",
            "SpaceX",
            "Starlink",
            "space satellite",
            "aerospace",
            "rocket launch",
        ],
        # Always inject — covers mega-cap / fresh IPOs Yahoo search may miss.
        "must_include": [
            _co("SPCX", "SpaceX", note="发射 / Starlink / AI · Nasdaq", core=True),
            _co("RKLB", "Rocket Lab", note="小卫星发射", core=True),
            _co("ASTS", "AST SpaceMobile", note="太空手机直连", core=True),
        ],
        "support_nodes": ["发射与运载", "卫星制造"],
        "core_nodes": ["卫星通信", "对地观测"],
        "app_nodes": ["国防航天", "商业太空服务"],
        "panels": [
            _panel(
                "flagship",
                "太空龙头",
                tone="core",
                branch="flagship",
                blurb="链上核心上市公司（含新上市）",
                companies=[
                    _co("SPCX", "SpaceX", note="发射 / Starlink / AI"),
                    _co("RKLB", "Rocket Lab", note="小卫星发射"),
                    _co("ASTS", "AST SpaceMobile", note="太空蜂窝"),
                    _co("PL", "Planet Labs", note="对地观测"),
                ],
            ),
            _panel(
                "launch",
                "发射 / 运载",
                tone="support",
                branch="launch",
                blurb="火箭发射与可复用运载",
                companies=[
                    _co("SPCX", "SpaceX", note="可复用运载龙头"),
                    _co("RKLB", "Rocket Lab", note="小卫星发射"),
                    _co("BA", "波音", note="航天与防务"),
                    _co("LMT", "洛克希德马丁", note="运载与防务", sector="industrials"),
                    _co("NOC", "诺斯罗普格鲁曼", note="航天系统", sector="industrials"),
                    _co("RTX", "RTX", note="航空发动机 / 防务", sector="industrials"),
                ],
            ),
            _panel(
                "sat_mfg",
                "卫星制造",
                tone="support",
                branch="sat_mfg",
                blurb="卫星平台、载荷与组件",
                companies=[
                    _co("SPCX", "SpaceX", note="星链卫星量产"),
                    _co("ASTS", "AST SpaceMobile", note="太空手机直连"),
                    _co("PL", "Planet Labs", note="对地观测星座"),
                    _co("LUNR", "Intuitive Machines", note="月球着陆"),
                    _co("IRDM", "Iridium", note="卫星通信星座"),
                    _co("GSAT", "Globalstar", note="卫星物联网"),
                ],
            ),
            _panel(
                "satcom",
                "卫星通信",
                tone="core",
                branch="satcom",
                blurb="宽带、物联网与直连手机",
                companies=[
                    _co("SPCX", "SpaceX", note="Starlink 宽带", core=True),
                    _co("ASTS", "AST SpaceMobile", note="太空蜂窝", core=True),
                    _co("IRDM", "Iridium", note="全球卫星通信", core=True),
                    _co("GSAT", "Globalstar", note="物联网 / Apple 合作"),
                    _co("SATS", "EchoStar", note="卫星与宽带"),
                    _co("VSAT", "Viasat", note="卫星宽带"),
                    _co("GILT", "Gilat", note="卫星地面站 / 通信"),
                    _co("CMTL", "Comtech", note="卫星地面通信"),
                    _co("SPIR", "Spire Global", note="气象 / AIS 数据"),
                    _co("BKSY", "BlackSky", note="遥感数据服务"),
                ],
            ),
            _panel(
                "eo",
                "对地观测 / 遥感",
                tone="core",
                branch="eo",
                companies=[
                    _co("PL", "Planet Labs", note="每日成像"),
                    _co("BKSY", "BlackSky", note="实时遥感"),
                    _co("SPIR", "Spire Global", note="气象 / 船舶跟踪"),
                ],
            ),
            _panel(
                "defense_space",
                "国防航天",
                tone="app",
                branch="defense",
                companies=[
                    _co("SPCX", "SpaceX", note="国家安全发射 / 星盾"),
                    _co("LMT", "洛克希德马丁", note="导弹与航天", sector="industrials"),
                    _co("NOC", "诺斯罗普格鲁曼", note="太空系统", sector="industrials"),
                    _co("RTX", "RTX", note="传感器 / 防务", sector="industrials"),
                    _co("BA", "波音", note="航天防务"),
                    _co("GD", "通用动力", note="国防电子", sector="industrials"),
                ],
            ),
            _panel(
                "space_svc",
                "商业太空服务",
                tone="app",
                branch="space_svc",
                companies=[
                    _co("SPCX", "SpaceX", note="发射即服务 / 星链"),
                    _co("RKLB", "Rocket Lab", note="发射即服务"),
                    _co("SPCE", "维珍银河", note="太空旅游"),
                    _co("RDW", "Redwire", note="在轨基础设施"),
                ],
            ),
            _panel(
                "spacex_etf",
                "SpaceX 相关工具",
                tone="app",
                branch="spacex_etf",
                blurb="跟踪 / 杠杆工具（波动更大）",
                companies=[
                    _co("SPCH", "2x Long SPCX", note="2x 做多 SpaceX ETF"),
                    _co("SPAX", "T-REX 2X SPCX", note="2x 做多 SpaceX ETF"),
                ],
            ),
        ],
    },
    {
        "id": "defense",
        "label": "军工 / 国防",
        "keywords": ["军工", "国防", "防务", "defense", "military", "武器"],
        "search_terms": ["defense", "Lockheed", "Raytheon", "Northrop"],
        "must_include": [
            _co("LMT", "洛克希德马丁", note="防务龙头", core=True, sector="industrials"),
            _co("RTX", "RTX", note="导弹 / 航电", core=True, sector="industrials"),
            _co("NOC", "诺斯罗普格鲁曼", note="航空航天防务", core=True, sector="industrials"),
        ],
        "support_nodes": ["材料部件", "电子系统"],
        "core_nodes": ["主承包商", "导弹防空"],
        "app_nodes": ["海空军平台"],
        "panels": [
            _panel(
                "primes",
                "主承包商",
                tone="core",
                branch="primes",
                companies=[
                    _co("LMT", "洛克希德马丁", note="战机 / 导弹", core=True, sector="industrials"),
                    _co("RTX", "RTX", note="雷神业务", core=True, sector="industrials"),
                    _co("NOC", "诺斯罗普格鲁曼", note="B-21 / 太空", core=True, sector="industrials"),
                    _co("GD", "通用动力", note="潜艇 / 战车", sector="industrials"),
                    _co("BA", "波音", note="军机防务", core=True),
                ],
            ),
            _panel(
                "defense_electronics",
                "防务电子",
                tone="support",
                branch="defense_electronics",
                companies=[
                    _co("LHX", "L3Harris", note="通信与电子", sector="industrials"),
                    _co("HII", "亨廷顿英格尔斯", note="舰船", sector="industrials"),
                    _co("TDG", "TransDigm", note="航空部件", sector="industrials"),
                ],
            ),
        ],
    },
    {
        "id": "banks",
        "label": "银行 / 金融",
        "keywords": ["银行", "金融", "投行", "bank", "banking", "finance"],
        "search_terms": ["bank", "JPMorgan", "banking"],
        "must_include": [
            _co("JPM", "摩根大通", note="全能银行", core=True, sector="financials"),
            _co("BAC", "美国银行", note="零售 / 对公", core=True, sector="financials"),
            _co("GS", "高盛", note="投行", core=True, sector="financials"),
        ],
        "support_nodes": ["支付清算", "数据风控"],
        "core_nodes": ["全能银行", "投行券商"],
        "app_nodes": ["财富管理", "消费金融"],
        "panels": [
            _panel(
                "money_center",
                "全能银行",
                tone="core",
                branch="money_center",
                companies=[
                    _co("JPM", "摩根大通", note="美国银行龙头", core=True, sector="financials"),
                    _co("BAC", "美国银行", note="零售银行", core=True, sector="financials"),
                    _co("C", "花旗", note="跨境银行", sector="financials"),
                    _co("WFC", "富国银行", note="零售信贷", sector="financials"),
                    _co("USB", "美国合众银行", note="区域银行", sector="financials"),
                ],
            ),
            _panel(
                "ib_markets",
                "投行 / 市场",
                tone="core",
                branch="ib_markets",
                companies=[
                    _co("GS", "高盛", note="投行与交易", core=True, sector="financials"),
                    _co("MS", "摩根士丹利", note="财富 + 投行", core=True, sector="financials"),
                    _co("SCHW", "嘉信理财", note="经纪平台", sector="financials"),
                ],
            ),
            _panel(
                "payments",
                "支付",
                tone="app",
                branch="payments",
                companies=[
                    _co("V", "Visa", note="卡组织", core=True, sector="financials"),
                    _co("MA", "万事达", note="卡组织", core=True, sector="financials"),
                    _co("AXP", "美国运通", note="卡与消费", sector="financials"),
                ],
            ),
        ],
    },
    {
        "id": "ai",
        "label": "人工智能",
        "keywords": [
            "ai",
            "人工智能",
            "大模型",
            "算力",
            "机器学习",
            "智能",
            "llm",
            "gpt",
        ],
        "search_terms": ["artificial intelligence", "AI chip", "GPU"],
        "support_nodes": ["AI 芯片", "算力基础设施"],
        "core_nodes": ["云与模型", "数据平台"],
        "app_nodes": ["AI 应用", "智能终端"],
        "panels": [
            _panel(
                "ai_chip",
                "AI 芯片",
                tone="support",
                branch="ai_chip",
                companies=[
                    _co("NVDA", "英伟达", note="训练 / 推理 GPU"),
                    _co("AMD", "超威", note="AI 加速"),
                    _co("AVGO", "博通", note="定制 ASIC"),
                    _co("TSM", "台积电", note="先进制程"),
                    _co("ASML", "阿斯麦", note="先进光刻"),
                    _co("MU", "美光", note="HBM"),
                ],
            ),
            _panel(
                "ai_infra",
                "算力基础设施",
                tone="support",
                branch="ai_infra",
                companies=[
                    _co("SMCI", "超微电脑", note="AI 服务器"),
                    _co("ANET", "Arista", note="数据中心网络"),
                    _co("DELL", "戴尔", note="企业服务器"),
                    _co("EQIX", "Equinix", note="数据中心", sector="realestate"),
                ],
            ),
            _panel(
                "ai_cloud",
                "云与模型",
                tone="core",
                branch="ai_cloud",
                companies=[
                    _co("MSFT", "微软", note="Azure / OpenAI"),
                    _co("AMZN", "亚马逊", note="AWS"),
                    _co("GOOGL", "谷歌", note="GCP / Gemini"),
                    _co("META", "Meta", note="开源模型"),
                    _co("ORCL", "甲骨文", note="云数据库"),
                ],
            ),
            _panel(
                "ai_data",
                "数据平台",
                tone="core",
                branch="ai_data",
                companies=[
                    _co("SNOW", "Snowflake", note="数据云"),
                    _co("PLTR", "Palantir", note="企业 AI 平台"),
                    _co("DDOG", "Datadog", note="可观测性"),
                    _co("MDB", "MongoDB", note="开发者数据平台"),
                ],
            ),
            _panel(
                "ai_apps",
                "AI 应用",
                tone="app",
                branch="ai_apps",
                companies=[
                    _co("CRM", "Salesforce", note="Agentforce"),
                    _co("NOW", "ServiceNow", note="工作流 AI"),
                    _co("ADBE", "Adobe", note="创意生成"),
                    _co("PATH", "UiPath", note="自动化"),
                ],
            ),
            _panel(
                "ai_device",
                "智能终端",
                tone="app",
                branch="ai_device",
                companies=[
                    _co("AAPL", "苹果", note="端侧 AI"),
                    _co("TSLA", "特斯拉", note="车端算力", sector="consumer"),
                ],
            ),
        ],
    },
    {
        "id": "robotics",
        "label": "机器人 / 自动化",
        "keywords": ["机器人", "人形", "自动化", "robot", "robotics", "automation"],
        "search_terms": ["robotics", "automation"],
        "support_nodes": ["传感器", "执行器"],
        "core_nodes": ["机器人本体", "工业自动化"],
        "app_nodes": ["制造落地", "服务机器人"],
        "panels": [
            _panel(
                "sensors",
                "传感 / 视觉",
                tone="support",
                branch="sensors",
                companies=[
                    _co("KEYS", "是德科技", note="测试测量"),
                    _co("CGNX", "康耐视", note="机器视觉"),
                    _co("TER", "泰瑞达", note="自动化测试"),
                ],
            ),
            _panel(
                "robot_core",
                "机器人 / 自动化",
                tone="core",
                branch="robot_core",
                companies=[
                    _co("ISRG", "直觉外科", note="手术机器人", sector="healthcare"),
                    _co("ROK", "罗克韦尔", note="工业自动化", sector="industrials"),
                    _co("EMR", "艾默生", note="过程自动化", sector="industrials"),
                    _co("PATH", "UiPath", note="软件自动化"),
                ],
            ),
            _panel(
                "robot_apps",
                "应用落地",
                tone="app",
                branch="robot_apps",
                companies=[
                    _co("TSLA", "特斯拉", note="Optimus", sector="consumer"),
                    _co("AMZN", "亚马逊", note="仓储机器人"),
                ],
            ),
        ],
    },
    {
        "id": "cyber",
        "label": "网络安全",
        "keywords": ["网络安全", "网安", "cyber", "security", "信息安全"],
        "search_terms": ["cybersecurity"],
        "support_nodes": ["安全芯片", "身份认证"],
        "core_nodes": ["云安全", "终端安全"],
        "app_nodes": ["企业安全运营"],
        "panels": [
            _panel(
                "cyber_core",
                "网络安全平台",
                tone="core",
                branch="cyber_core",
                companies=[
                    _co("CRWD", "CrowdStrike", note="终端安全"),
                    _co("PANW", "Palo Alto", note="网络安全"),
                    _co("ZS", "Zscaler", note="零信任"),
                    _co("S", "SentinelOne", note="端点防护"),
                    _co("FTNT", "Fortinet", note="防火墙"),
                ],
            ),
            _panel(
                "cyber_apps",
                "安全运营",
                tone="app",
                branch="cyber_apps",
                companies=[
                    _co("OKTA", "Okta", note="身份认证"),
                    _co("NET", "Cloudflare", note="边缘安全"),
                ],
            ),
        ],
    },
    {
        "id": "biotech",
        "label": "生物医药",
        "keywords": ["生物", "医药", "制药", "biotech", "pharma", "医疗"],
        "search_terms": ["biotech", "pharmaceutical"],
        "support_nodes": ["科研工具", "CXO"],
        "core_nodes": ["创新药", "医疗器械"],
        "app_nodes": ["医院与支付"],
        "panels": [
            _panel(
                "bio_tools",
                "科研工具 / CXO",
                tone="support",
                branch="bio_tools",
                companies=[
                    _co("TMO", "赛默飞", note="生命科学工具", sector="healthcare"),
                    _co("DHR", "丹纳赫", note="诊断与生命科学", sector="healthcare"),
                    _co("IQV", "IQVIA", note="临床研究", sector="healthcare"),
                ],
            ),
            _panel(
                "pharma",
                "创新药 / 巨头",
                tone="core",
                branch="pharma",
                companies=[
                    _co("LLY", "礼来", note="代谢 / 神经", sector="healthcare"),
                    _co("NVO", "诺和诺德", note="减重 / 糖尿病", sector="healthcare"),
                    _co("MRK", "默沙东", note="肿瘤免疫", sector="healthcare"),
                    _co("PFE", "辉瑞", note="多元制药", sector="healthcare"),
                    _co("JNJ", "强生", note="制药 + 器械", sector="healthcare"),
                ],
            ),
            _panel(
                "devices",
                "医疗器械",
                tone="app",
                branch="devices",
                companies=[
                    _co("ISRG", "直觉外科", note="手术机器人", sector="healthcare"),
                    _co("ABT", "雅培", note="诊断与器械", sector="healthcare"),
                    _co("MDT", "美敦力", note="器械巨头", sector="healthcare"),
                ],
            ),
        ],
    },
    {
        "id": "energy",
        "label": "能源 / 电力",
        "keywords": ["能源", "电力", "光伏", "核电", "储能", "energy", "solar", "nuclear"],
        "search_terms": ["clean energy", "solar", "nuclear energy"],
        "support_nodes": ["材料设备", "发电"],
        "core_nodes": ["电网储能", "电力运营"],
        "app_nodes": ["用电侧"],
        "panels": [
            _panel(
                "gen",
                "发电 / 清洁能源",
                tone="support",
                branch="gen",
                companies=[
                    _co("FSLR", "First Solar", note="光伏", sector="energy"),
                    _co("ENPH", "Enphase", note="微逆", sector="energy"),
                    _co("CEG", "Constellation", note="核电运营", sector="utilities"),
                    _co("VST", "Vistra", note="发电 / AI 用电", sector="utilities"),
                ],
            ),
            _panel(
                "grid",
                "电网 / 储能",
                tone="core",
                branch="grid",
                companies=[
                    _co("ETN", "伊顿", note="电气设备", sector="industrials"),
                    _co("PWR", "Quanta", note="电网工程", sector="industrials"),
                    _co("TSLA", "特斯拉", note="Megapack", sector="consumer"),
                ],
            ),
        ],
    },
]


def match_themes(query: str) -> list[dict[str, Any]]:
    q = _norm(query)
    if not q:
        return []
    hits: list[tuple[int, dict[str, Any]]] = []
    for theme in THEME_PACKS:
        score = 0
        for kw in theme.get("keywords") or []:
            k = _norm(kw)
            if not k:
                continue
            if q == k:
                score += 100
            elif k in q or q in k:
                score += 80
        if score:
            hits.append((score, theme))
    hits.sort(key=lambda x: x[0], reverse=True)
    # Keep top themes; allow multi-theme composition (e.g. 太空AI).
    return [t for _, t in hits[:3]]


def _merge_unique_companies(
    items: list[dict[str, Any]], *, limit: int = _PANEL_CO_LIMIT
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for c in items:
        sym = str(c.get("symbol") or "").upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        row = dict(c)
        row["symbol"] = sym
        if row.get("core") is None:
            row["core"] = sym in CORE_SYMBOLS
        out.append(row)
        if len(out) >= limit:
            break
    return sort_companies(out)


def clear_chain_cache() -> None:
    _CACHE.clear()


def _yahoo_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/",
    }


async def _yahoo_search(term: str, *, limit: int = 20) -> list[dict[str, Any]]:
    q = (term or "").strip()
    if not q:
        return []
    url = "https://query1.finance.yahoo.com/v1/finance/search"
    params = {
        "q": q,
        "lang": "en-US",
        "region": "US",
        "quotesCount": str(limit),
        "newsCount": "0",
        "listsCount": "0",
        "enableFuzzyQuery": "true",
    }
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, trust_env=False, timeout=httpx.Timeout(8.0, connect=3.0)
        ) as client:
            res = await client.get(url, params=params, headers=_yahoo_headers())
            if res.status_code != 200:
                return []
            payload = res.json()
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for row in payload.get("quotes") or []:
        if str(row.get("quoteType") or "").upper() not in {"EQUITY", "ETF"}:
            continue
        sym = str(row.get("symbol") or "").upper()
        if not sym or "^" in sym or "=" in sym:
            continue
        # Prefer US listings: plain tickers / common ADRs.
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", sym):
            continue
        name = str(row.get("shortname") or row.get("longname") or sym)
        out.append(
            _co(
                sym,
                name,
                note=str(row.get("exchDisp") or row.get("typeDisp") or "Yahoo 检索"),
            )
        )
    return out


def compose_from_themes(query: str, themes: list[dict[str, Any]]) -> dict[str, Any]:
    label_bits = [t.get("label") or t.get("id") for t in themes]
    label = " × ".join([str(x) for x in label_bits if x]) or query
    if len(themes) == 1:
        title = f"{label}产业链"
    else:
        title = f"{query.strip()}产业链"

    support_nodes: list[dict[str, str]] = []
    core_nodes: list[dict[str, str]] = []
    app_nodes: list[dict[str, str]] = []
    panels: list[dict[str, Any]] = []
    seen_panel: set[str] = set()

    must_include: list[dict[str, Any]] = []
    for theme in themes:
        must_include.extend(theme.get("must_include") or [])
        for i, name in enumerate(theme.get("support_nodes") or []):
            support_nodes.append({"id": f"{theme['id']}_s{i}", "label": name})
        for i, name in enumerate(theme.get("core_nodes") or []):
            core_nodes.append({"id": f"{theme['id']}_c{i}", "label": name})
        for i, name in enumerate(theme.get("app_nodes") or []):
            app_nodes.append({"id": f"{theme['id']}_a{i}", "label": name})
        for panel in theme.get("panels") or []:
            pid = str(panel.get("id") or "")
            if not pid or pid in seen_panel:
                # Same id across themes — merge companies.
                if pid in seen_panel:
                    for existing in panels:
                        if existing.get("id") == pid:
                            existing["companies"] = _merge_unique_companies(
                                (existing.get("companies") or [])
                                + (panel.get("companies") or []),
                                limit=_PANEL_CO_LIMIT,
                            )
                            break
                continue
            seen_panel.add(pid)
            panels.append(
                {
                    **panel,
                    "companies": list(panel.get("companies") or []),
                }
            )

    # Pin must-include names (fresh IPOs / mega names) into the first panels.
    if must_include and panels:
        pinned = _merge_unique_companies(
            [{**c, "core": True} for c in must_include], limit=12
        )
        panels[0]["companies"] = _merge_unique_companies(
            pinned + (panels[0].get("companies") or []), limit=_PANEL_CO_LIMIT
        )
        # Also ensure they appear in any panel already listing peers.
        for panel in panels[1:]:
            have = {
                str(c.get("symbol") or "").upper()
                for c in (panel.get("companies") or [])
            }
            inject = [
                c
                for c in pinned
                if c["symbol"] not in have
                and c["symbol"] in {"SPCX", "NVDA", "TSM", "TSLA"}
            ]
            if inject:
                panel["companies"] = _merge_unique_companies(
                    inject + (panel.get("companies") or []), limit=_PANEL_CO_LIMIT
                )
    for panel in panels:
        panel["companies"] = sort_companies(panel.get("companies") or [])

    # Cap node pills for readable UI.
    support_nodes = support_nodes[:4] or [{"id": "support_generic", "label": "上游支撑"}]
    core_nodes = core_nodes[:4] or [{"id": "core_generic", "label": "中游核心"}]
    app_nodes = app_nodes[:5] or [{"id": "app_generic", "label": "下游应用"}]

    slug = hashlib.md5(_norm(query).encode("utf-8")).hexdigest()[:10]
    return {
        "id": f"gen_{slug}",
        "label": title,
        "blurb": (
            f"根据「{query.strip()}」自动组合主题包并检索美股生成；"
            "含新上市龙头时会优先置顶，但并非交易所全量行情库。"
        ),
        "generated": True,
        "themes": [t.get("id") for t in themes],
        "top_flow": [
            {"id": "support", "label": "上游支撑", "tone": "support"},
            {"id": "core", "label": "中游核心", "tone": "core"},
            {"id": "downstream", "label": "下游应用", "tone": "app"},
        ],
        "branches": [
            {"parent": "support", "tone": "support", "nodes": support_nodes},
            {"parent": "core", "tone": "core", "nodes": core_nodes},
            {"parent": "downstream", "tone": "app", "nodes": app_nodes},
        ],
        "panels": panels,
        "keywords": [query],
    }


def _generic_skeleton(query: str) -> dict[str, Any]:
    """Fallback skeleton when no theme pack hits — still returns a usable map."""
    q = query.strip()
    slug = hashlib.md5(_norm(q).encode("utf-8")).hexdigest()[:10]
    return {
        "id": f"gen_{slug}",
        "label": f"{q}产业链",
        "blurb": f"未命中预制主题包，已按「{q}」检索美股并搭建通用上中下游骨架。",
        "generated": True,
        "themes": [],
        "top_flow": [
            {"id": "support", "label": "上游支撑", "tone": "support"},
            {"id": "core", "label": "中游核心", "tone": "core"},
            {"id": "downstream", "label": "下游应用", "tone": "app"},
        ],
        "branches": [
            {
                "parent": "support",
                "tone": "support",
                "nodes": [
                    {"id": "materials", "label": "材料 / 设备"},
                    {"id": "infra", "label": "基础设施"},
                ],
            },
            {
                "parent": "core",
                "tone": "core",
                "nodes": [
                    {"id": "platform", "label": "平台 / 制造"},
                    {"id": "software", "label": "软件 / 服务"},
                ],
            },
            {
                "parent": "downstream",
                "tone": "app",
                "nodes": [
                    {"id": "enterprise", "label": "企业客户"},
                    {"id": "consumer", "label": "消费场景"},
                ],
            },
        ],
        "panels": [
            _panel(
                "upstream",
                "上游相关美股",
                tone="support",
                branch="materials",
                companies=[],
            ),
            _panel(
                "midstream",
                "中游相关美股",
                tone="core",
                branch="platform",
                companies=[],
            ),
            _panel(
                "downstream",
                "下游相关美股",
                tone="app",
                branch="enterprise",
                companies=[],
            ),
        ],
        "keywords": [q],
    }


async def enrich_with_yahoo(chain: dict[str, Any], query: str) -> dict[str, Any]:
    themes = chain.get("themes") or []
    terms: list[str] = []
    raw = query.strip()
    # Alias seeds first (e.g. 飞机 → aircraft / Boeing).
    terms.extend(resolve_search_aliases(raw))
    # Prefer English search terms from matched themes + original query.
    for theme in THEME_PACKS:
        if theme.get("id") in themes:
            terms.extend(theme.get("search_terms") or [])
            for co in theme.get("must_include") or []:
                sym = str(co.get("symbol") or "")
                if sym:
                    terms.append(sym)
    if re.search(r"[A-Za-z]", raw):
        terms.insert(0, raw)
    else:
        # Keep Chinese query as a last resort; Yahoo mainly hits English seeds.
        terms.append(raw)
    # Dedupe terms
    uniq_terms: list[str] = []
    seen_t: set[str] = set()
    for t in terms:
        key = t.strip().lower()
        if not key or key in seen_t:
            continue
        seen_t.add(key)
        uniq_terms.append(t.strip())
        if len(uniq_terms) >= 8:
            break

    results = await asyncio.gather(
        *[_yahoo_search(t, limit=16) for t in uniq_terms], return_exceptions=True
    )
    found: list[dict[str, Any]] = []
    for item in results:
        if isinstance(item, list):
            found.extend(item)

    if not found:
        return chain

    panels = list(chain.get("panels") or [])
    # Distribute Yahoo hits into tone buckets.
    buckets = {"support": [], "core": [], "app": []}
    for i, co in enumerate(found):
        tone = ("support", "core", "app")[i % 3]
        buckets[tone].append(co)

    # Merge into existing panels by tone; if empty generic panels, fill them.
    for panel in panels:
        tone = panel.get("tone") or "core"
        extra = buckets.get(tone) or []
        panel["companies"] = _merge_unique_companies(
            (panel.get("companies") or []) + extra, limit=_PANEL_CO_LIMIT
        )

    # If still thin, append a Yahoo hits panel.
    all_cos = _merge_unique_companies(
        [{**c, "core": c.get("symbol") in CORE_SYMBOLS} for c in found],
        limit=_PANEL_CO_LIMIT,
    )
    if all_cos:
        existing_ids = {p.get("id") for p in panels}
        if "yahoo_hits" not in existing_ids:
            panels.append(
                _panel(
                    "yahoo_hits",
                    "关键词检索补充",
                    tone="core",
                    branch="yahoo",
                    blurb="Yahoo Finance 检索到的相关美股",
                    companies=all_cos,
                )
            )
        chain["panels"] = panels
    return chain


async def generate_chain(query: str) -> dict[str, Any] | None:
    q = (query or "").strip()
    if not q:
        return None
    cache_key = f"{_CACHE_VER}:{_norm(q)}"
    now = time.time()
    cached = _CACHE.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    themes = match_themes(q)
    if themes:
        chain = compose_from_themes(q, themes)
    else:
        chain = _generic_skeleton(q)
    chain = await enrich_with_yahoo(chain, q)

    # Accept thin Yahoo-only maps — better than empty for long-tail keywords.
    total = sum(len(p.get("companies") or []) for p in chain.get("panels") or [])
    if total < 1 and not themes:
        return None

    _CACHE[cache_key] = (now, chain)
    return chain
