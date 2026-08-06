"""US market sector treemap: nested groups with live day change (红涨绿跌)."""

from __future__ import annotations

import time
from typing import Any

from us_market_pulse.quotes import fetch_day_quotes

# Nested market map (sector → subgroup → stocks). Weights are relative tile sizes.
MARKET_MAP: list[dict[str, Any]] = [
    {
        "id": "semis",
        "label": "半导体",
        "desk_id": "semis",
        "weight": 18,
        "groups": [
            {
                "id": "ic-design",
                "label": "芯片设计",
                "weight": 9,
                "stocks": [
                    {"symbol": "NVDA", "name": "英伟达", "weight": 36},
                    {"symbol": "AVGO", "name": "博通", "weight": 16},
                    {"symbol": "AMD", "name": "超威", "weight": 12},
                    {"symbol": "QCOM", "name": "高通", "weight": 8},
                    {"symbol": "ARM", "name": "安谋", "weight": 6},
                    {"symbol": "TXN", "name": "德州仪器", "weight": 6},
                ],
            },
            {
                "id": "foundry-equip",
                "label": "代工设备",
                "weight": 9,
                "stocks": [
                    {"symbol": "TSM", "name": "台积电", "weight": 22},
                    {"symbol": "ASML", "name": "阿斯麦", "weight": 14},
                    {"symbol": "AMAT", "name": "应用材料", "weight": 8},
                    {"symbol": "LRCX", "name": "拉姆研究", "weight": 6},
                    {"symbol": "KLAC", "name": "科磊", "weight": 5},
                    {"symbol": "MU", "name": "美光", "weight": 7},
                ],
            },
        ],
    },
    {
        "id": "tech",
        "label": "科技软件",
        "desk_id": "tech",
        "weight": 16,
        "groups": [
            {
                "id": "mega-tech",
                "label": "科技巨头",
                "weight": 9,
                "stocks": [
                    {"symbol": "MSFT", "name": "微软", "weight": 24},
                    {"symbol": "AAPL", "name": "苹果", "weight": 22},
                    {"symbol": "GOOGL", "name": "谷歌", "weight": 14},
                    {"symbol": "META", "name": "Meta", "weight": 12},
                    {"symbol": "ORCL", "name": "甲骨文", "weight": 6},
                    {"symbol": "IBM", "name": "IBM", "weight": 4},
                ],
            },
            {
                "id": "software",
                "label": "企业软件",
                "weight": 7,
                "stocks": [
                    {"symbol": "CRM", "name": "赛富时", "weight": 6},
                    {"symbol": "ADBE", "name": "Adobe", "weight": 5},
                    {"symbol": "NOW", "name": "ServiceNow", "weight": 5},
                    {"symbol": "INTU", "name": "Intuit", "weight": 4},
                    {"symbol": "PANW", "name": "Palo Alto", "weight": 4},
                    {"symbol": "PLTR", "name": "Palantir", "weight": 5},
                ],
            },
        ],
    },
    {
        "id": "cloud",
        "label": "云计算",
        "desk_id": "cloud",
        "weight": 10,
        "groups": [
            {
                "id": "cloud-infra",
                "label": "云基建",
                "weight": 6,
                "stocks": [
                    {"symbol": "AMZN", "name": "亚马逊", "weight": 16},
                    {"symbol": "MSFT", "name": "微软云", "weight": 12},
                    {"symbol": "GOOGL", "name": "谷歌云", "weight": 8},
                    {"symbol": "SNOW", "name": "Snowflake", "weight": 5},
                    {"symbol": "DDOG", "name": "Datadog", "weight": 3},
                    {"symbol": "NET", "name": "Cloudflare", "weight": 3},
                ],
            },
            {
                "id": "cyber-saas",
                "label": "安全SaaS",
                "weight": 4,
                "stocks": [
                    {"symbol": "CRWD", "name": "CrowdStrike", "weight": 5},
                    {"symbol": "ZS", "name": "Zscaler", "weight": 3},
                    {"symbol": "OKTA", "name": "Okta", "weight": 2},
                    {"symbol": "MDB", "name": "MongoDB", "weight": 3},
                ],
            },
        ],
    },
    {
        "id": "ai",
        "label": "AI / 机器人",
        "desk_id": "ai",
        "weight": 8,
        "groups": [
            {
                "id": "ai-platform",
                "label": "AI平台",
                "weight": 8,
                "stocks": [
                    {"symbol": "NVDA", "name": "英伟达", "weight": 20},
                    {"symbol": "PLTR", "name": "Palantir", "weight": 6},
                    {"symbol": "SMCI", "name": "超微电脑", "weight": 4},
                    {"symbol": "ARM", "name": "安谋", "weight": 4},
                    {"symbol": "SNOW", "name": "Snowflake", "weight": 4},
                    {"symbol": "PATH", "name": "UiPath", "weight": 2},
                    {"symbol": "ISRG", "name": "直觉外科", "weight": 5},
                ],
            },
        ],
    },
    {
        "id": "comms",
        "label": "通信传媒",
        "desk_id": "nasdaq",
        "weight": 9,
        "groups": [
            {
                "id": "internet",
                "label": "互联网",
                "weight": 5,
                "stocks": [
                    {"symbol": "META", "name": "Meta", "weight": 10},
                    {"symbol": "GOOGL", "name": "谷歌", "weight": 9},
                    {"symbol": "NFLX", "name": "奈飞", "weight": 5},
                    {"symbol": "DIS", "name": "迪士尼", "weight": 4},
                    {"symbol": "SPOT", "name": "Spotify", "weight": 2},
                ],
            },
            {
                "id": "telecom",
                "label": "电信",
                "weight": 4,
                "stocks": [
                    {"symbol": "T", "name": "AT&T", "weight": 4},
                    {"symbol": "VZ", "name": "Verizon", "weight": 4},
                    {"symbol": "TMUS", "name": "T-Mobile", "weight": 5},
                    {"symbol": "CMCSA", "name": "康卡斯特", "weight": 3},
                ],
            },
        ],
    },
    {
        "id": "consumer",
        "label": "可选消费",
        "desk_id": "nasdaq",
        "weight": 10,
        "groups": [
            {
                "id": "retail",
                "label": "零售电商",
                "weight": 5,
                "stocks": [
                    {"symbol": "AMZN", "name": "亚马逊", "weight": 12},
                    {"symbol": "TSLA", "name": "特斯拉", "weight": 8},
                    {"symbol": "HD", "name": "家得宝", "weight": 5},
                    {"symbol": "MCD", "name": "麦当劳", "weight": 4},
                    {"symbol": "NKE", "name": "耐克", "weight": 3},
                    {"symbol": "SBUX", "name": "星巴克", "weight": 3},
                ],
            },
            {
                "id": "auto",
                "label": "汽车出行",
                "weight": 5,
                "stocks": [
                    {"symbol": "TSLA", "name": "特斯拉", "weight": 10},
                    {"symbol": "F", "name": "福特", "weight": 3},
                    {"symbol": "GM", "name": "通用", "weight": 3},
                    {"symbol": "RIVN", "name": "Rivian", "weight": 2},
                    {"symbol": "UBER", "name": "Uber", "weight": 4},
                ],
            },
        ],
    },
    {
        "id": "finance",
        "label": "金融",
        "desk_id": "finance",
        "weight": 12,
        "groups": [
            {
                "id": "banks",
                "label": "银行券商",
                "weight": 7,
                "stocks": [
                    {"symbol": "JPM", "name": "摩根大通", "weight": 10},
                    {"symbol": "BAC", "name": "美银", "weight": 6},
                    {"symbol": "GS", "name": "高盛", "weight": 5},
                    {"symbol": "MS", "name": "摩士", "weight": 5},
                    {"symbol": "C", "name": "花旗", "weight": 4},
                    {"symbol": "WFC", "name": "富国", "weight": 5},
                ],
            },
            {
                "id": "payments",
                "label": "支付资管",
                "weight": 5,
                "stocks": [
                    {"symbol": "V", "name": "Visa", "weight": 8},
                    {"symbol": "MA", "name": "万事达", "weight": 7},
                    {"symbol": "AXP", "name": "运通", "weight": 4},
                    {"symbol": "BLK", "name": "贝莱德", "weight": 4},
                    {"symbol": "SCHW", "name": "嘉信", "weight": 3},
                ],
            },
        ],
    },
    {
        "id": "health",
        "label": "医疗",
        "desk_id": "health",
        "weight": 10,
        "groups": [
            {
                "id": "pharma",
                "label": "制药生物",
                "weight": 6,
                "stocks": [
                    {"symbol": "LLY", "name": "礼来", "weight": 10},
                    {"symbol": "JNJ", "name": "强生", "weight": 6},
                    {"symbol": "ABBV", "name": "艾伯维", "weight": 5},
                    {"symbol": "MRK", "name": "默沙东", "weight": 5},
                    {"symbol": "PFE", "name": "辉瑞", "weight": 3},
                    {"symbol": "AMGN", "name": "安进", "weight": 4},
                    {"symbol": "VRTX", "name": "福泰", "weight": 4},
                ],
            },
            {
                "id": "medtech",
                "label": "器械服务",
                "weight": 4,
                "stocks": [
                    {"symbol": "UNH", "name": "联合健康", "weight": 7},
                    {"symbol": "ISRG", "name": "直觉外科", "weight": 4},
                    {"symbol": "SYK", "name": "史赛克", "weight": 3},
                    {"symbol": "TMO", "name": "赛默飞", "weight": 4},
                ],
            },
        ],
    },
    {
        "id": "energy",
        "label": "能源",
        "desk_id": "energy",
        "weight": 8,
        "groups": [
            {
                "id": "oil-gas",
                "label": "油气",
                "weight": 5,
                "stocks": [
                    {"symbol": "XOM", "name": "埃克森", "weight": 8},
                    {"symbol": "CVX", "name": "雪佛龙", "weight": 6},
                    {"symbol": "COP", "name": "康菲", "weight": 4},
                    {"symbol": "EOG", "name": "EOG", "weight": 3},
                    {"symbol": "OXY", "name": "西方石油", "weight": 3},
                    {"symbol": "SLB", "name": "斯伦贝谢", "weight": 3},
                ],
            },
            {
                "id": "midstream",
                "label": "中游炼化",
                "weight": 3,
                "stocks": [
                    {"symbol": "MPC", "name": "马拉松石油", "weight": 3},
                    {"symbol": "VLO", "name": "瓦莱罗", "weight": 2},
                    {"symbol": "WMB", "name": "Williams", "weight": 3},
                    {"symbol": "OKE", "name": "ONEOK", "weight": 3},
                ],
            },
        ],
    },
    {
        "id": "industrial",
        "label": "工业",
        "desk_id": "tech",
        "weight": 7,
        "groups": [
            {
                "id": "industrials",
                "label": "制造航空",
                "weight": 7,
                "stocks": [
                    {"symbol": "GE", "name": "通用电气", "weight": 5},
                    {"symbol": "CAT", "name": "卡特彼勒", "weight": 5},
                    {"symbol": "BA", "name": "波音", "weight": 4},
                    {"symbol": "HON", "name": "霍尼韦尔", "weight": 4},
                    {"symbol": "UPS", "name": "UPS", "weight": 3},
                    {"symbol": "RTX", "name": "雷神", "weight": 4},
                    {"symbol": "DE", "name": "迪尔", "weight": 3},
                ],
            },
        ],
    },
    {
        "id": "staples",
        "label": "必需消费",
        "desk_id": "health",
        "weight": 5,
        "groups": [
            {
                "id": "staples-core",
                "label": "零售日用品",
                "weight": 5,
                "stocks": [
                    {"symbol": "WMT", "name": "沃尔玛", "weight": 8},
                    {"symbol": "COST", "name": "好市多", "weight": 6},
                    {"symbol": "PG", "name": "宝洁", "weight": 5},
                    {"symbol": "KO", "name": "可口可乐", "weight": 4},
                    {"symbol": "PEP", "name": "百事", "weight": 4},
                    {"symbol": "PM", "name": "菲莫国际", "weight": 3},
                ],
            },
        ],
    },
    {
        "id": "defensive",
        "label": "公用地产",
        "desk_id": "finance",
        "weight": 5,
        "groups": [
            {
                "id": "utilities",
                "label": "公用事业",
                "weight": 2.5,
                "stocks": [
                    {"symbol": "NEE", "name": "NextEra", "weight": 4},
                    {"symbol": "DUK", "name": "杜克能源", "weight": 3},
                    {"symbol": "SO", "name": "南方公司", "weight": 3},
                    {"symbol": "AEP", "name": "美国电力", "weight": 2},
                ],
            },
            {
                "id": "reit",
                "label": "房地产",
                "weight": 2.5,
                "stocks": [
                    {"symbol": "AMT", "name": "美国铁塔", "weight": 3},
                    {"symbol": "PLD", "name": "普洛斯", "weight": 3},
                    {"symbol": "EQIX", "name": "Equinix", "weight": 3},
                    {"symbol": "SPG", "name": "西蒙地产", "weight": 2},
                ],
            },
        ],
    },
    {
        "id": "materials",
        "label": "原材料",
        "desk_id": "energy",
        "weight": 4,
        "groups": [
            {
                "id": "materials-core",
                "label": "化工金属",
                "weight": 4,
                "stocks": [
                    {"symbol": "LIN", "name": "林德", "weight": 5},
                    {"symbol": "FCX", "name": "自由港", "weight": 3},
                    {"symbol": "NEM", "name": "纽蒙特", "weight": 3},
                    {"symbol": "APD", "name": "空气产品", "weight": 3},
                    {"symbol": "SHW", "name": "宣伟", "weight": 3},
                ],
            },
        ],
    },
]

_MAP_CACHE: dict[str, Any] = {"fetched_at": 0.0, "payload": None}
_MAP_TTL = 120.0


def _map_symbols() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for sector in MARKET_MAP:
        for group in sector.get("groups") or []:
            for stock in group.get("stocks") or []:
                sym = str(stock.get("symbol") or "").upper()
                if sym and sym not in seen:
                    seen.add(sym)
                    out.append(sym)
    return out


def symbols_for_desk(desk_id: str) -> list[str]:
    """Unique stock symbols mapped to a sectors-desk id (e.g. cloud, energy)."""
    key = (desk_id or "").strip().lower()
    if not key:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for sector in MARKET_MAP:
        mapped = str(sector.get("desk_id") or sector.get("id") or "").lower()
        if mapped != key:
            continue
        for group in sector.get("groups") or []:
            for stock in group.get("stocks") or []:
                sym = str(stock.get("symbol") or "").upper()
                if sym and sym not in seen:
                    seen.add(sym)
                    out.append(sym)
    return out


async def build_market_map(*, force: bool = False) -> dict[str, Any]:
    now = time.time()
    cached_payload = _MAP_CACHE.get("payload")
    cached_quoted = int(((cached_payload or {}).get("stats") or {}).get("quoted") or 0)
    if (
        not force
        and cached_payload
        and cached_quoted > 0
        and now - float(_MAP_CACHE["fetched_at"]) < _MAP_TTL
    ):
        payload = dict(cached_payload)
        payload["cached"] = True
        return payload

    symbols = _map_symbols()
    # Map has dozens of tickers — never block on Yahoo Overnight HTML scrapes.
    quotes = await fetch_day_quotes(symbols, overnight_priority=[])
    errors = [f"{sym}: quote failed" for sym in symbols if sym not in quotes]

    sectors_out: list[dict[str, Any]] = []
    up = down = flat = 0
    for sector in MARKET_MAP:
        groups_out: list[dict[str, Any]] = []
        sector_weights = 0.0
        sector_weighted_pct = 0.0
        sector_pct_n = 0
        for group in sector.get("groups") or []:
            children: list[dict[str, Any]] = []
            group_weight = 0.0
            group_weighted_pct = 0.0
            group_pct_n = 0
            for stock in group.get("stocks") or []:
                sym = str(stock.get("symbol") or "").upper()
                q = quotes.get(sym) or {}
                pct = q.get("change_pct")
                w = float(stock.get("weight") or 1)
                if isinstance(pct, (int, float)):
                    if pct > 0.05:
                        up += 1
                    elif pct < -0.05:
                        down += 1
                    else:
                        flat += 1
                    group_weighted_pct += float(pct) * w
                    group_pct_n += w
                    sector_weighted_pct += float(pct) * w
                    sector_pct_n += w
                children.append(
                    {
                        "symbol": sym,
                        "name": stock.get("name") or sym,
                        "weight": w,
                        "change_pct": pct,
                        "price": q.get("price"),
                    }
                )
                group_weight += w
            if not children:
                continue
            g_pct = (
                round(group_weighted_pct / group_pct_n, 3) if group_pct_n else None
            )
            groups_out.append(
                {
                    "id": group["id"],
                    "label": group["label"],
                    "weight": float(group.get("weight") or group_weight or 1),
                    "change_pct": g_pct,
                    "children": children,
                }
            )
            sector_weights += float(group.get("weight") or group_weight or 1)
        if not groups_out:
            continue
        s_pct = (
            round(sector_weighted_pct / sector_pct_n, 3) if sector_pct_n else None
        )
        sectors_out.append(
            {
                "id": sector["id"],
                "label": sector["label"],
                "desk_id": sector.get("desk_id") or sector["id"],
                "weight": float(sector.get("weight") or sector_weights or 1),
                "change_pct": s_pct,
                "groups": groups_out,
            }
        )

    payload = {
        "sectors": sectors_out,
        "stats": {
            "symbols": len(symbols),
            "quoted": len(quotes),
            "up": up,
            "down": down,
            "flat": flat,
        },
        "errors": errors[-20:],
        "fetched_at": now,
        "cached": False,
        "source": "CNBC / Yahoo 日涨跌 · 权重为相对市值近似",
    }
    # Never cache an empty quote set — keeps UI stuck on "—" after Yahoo outages.
    if quotes:
        _MAP_CACHE["payload"] = payload
        _MAP_CACHE["fetched_at"] = now
    return dict(payload)
