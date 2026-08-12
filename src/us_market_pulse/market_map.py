"""US market sector treemap: nested groups with live day change (红涨绿跌)."""

from __future__ import annotations

import asyncio
import copy
import time
from datetime import date, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from us_market_pulse.quotes import (
    USER_AGENT,
    fetch_day_quotes,
    fetch_nasdaq_daily_bars,
)

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
_MAP_TTL = 180.0


def peek_cached_market_map() -> dict[str, Any] | None:
    """Return last warm map payload for timeout / cold-start fallbacks."""
    payload = _MAP_CACHE.get("payload")
    if not isinstance(payload, dict) or not payload:
        return None
    out = copy.deepcopy(payload)
    out["cached"] = True
    out["stale"] = True
    return out


# Multi-week stock returns (Nasdaq daily bars) — longer TTL; day quotes refresh separately.
_MAP_RET_CACHE: dict[str, dict[str, Any]] = {}
_MAP_RET_TTL = 1800.0
_HORIZON_FILL_BUSY = False
_HORIZON_FILL_PENDING: list[str] | None = None


def _pct_from_closes(closes: list[float], sessions: int) -> float | None:
    """Return % change from close[-sessions-1] → close[-1] (sessions trading days)."""
    if sessions < 1 or len(closes) < sessions + 1:
        return None
    last = closes[-1]
    base = closes[-(sessions + 1)]
    if not isinstance(last, (int, float)) or not isinstance(base, (int, float)):
        return None
    if abs(base) < 1e-12:
        return None
    try:
        return round((last - base) / abs(base) * 100.0, 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _closes_to_horizon_row(closes: list[float]) -> dict[str, Any] | None:
    if len(closes) < 6:
        return None
    return {
        "at": time.time(),
        "week5_pct": _pct_from_closes(closes, 5),
        "week10_pct": _pct_from_closes(closes, 10),
        "week15_pct": _pct_from_closes(closes, 15),
        "week20_pct": _pct_from_closes(closes, 20),
    }


async def _yahoo_daily_closes(
    client: httpx.AsyncClient, symbol: str
) -> list[float]:
    """Yahoo 3mo daily closes — faster bulk path for map week returns."""
    sym = (symbol or "").strip().upper()
    if not sym:
        return []
    enc = quote(sym, safe="")
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/",
    }
    for host in ("query1", "query2"):
        url = (
            f"https://{host}.finance.yahoo.com/v8/finance/chart/{enc}"
            f"?range=3mo&interval=1d&includePrePost=false"
        )
        try:
            resp = await client.get(url, timeout=3.5, headers=headers)
            if resp.status_code >= 400:
                continue
            result = ((resp.json().get("chart") or {}).get("result") or [None])[0]
            if not result:
                continue
            quote_rows = (result.get("indicators") or {}).get("quote") or []
            if not quote_rows:
                continue
            raw = (quote_rows[0] or {}).get("close") or []
            closes = [
                float(v)
                for v in raw
                if isinstance(v, (int, float)) and float(v) > 0
            ]
            if len(closes) >= 6:
                return closes
        except Exception:  # noqa: BLE001
            continue
    return []


def _horizon_row_usable(hit: dict[str, Any] | None, *, now: float | None = None) -> bool:
    """Partial week row is OK to paint (at least 1w)."""
    if not isinstance(hit, dict):
        return False
    ts = now if now is not None else time.time()
    if ts - float(hit.get("at") or 0) >= _MAP_RET_TTL:
        return False
    return hit.get("week5_pct") is not None


def _horizon_row_complete(hit: dict[str, Any] | None, *, now: float | None = None) -> bool:
    """Full 1w–4w row — stop refetching until TTL expires."""
    if not _horizon_row_usable(hit, now=now):
        return False
    return hit.get("week20_pct") is not None  # type: ignore[union-attr]


def _cached_horizon_rets(symbols: list[str]) -> dict[str, dict[str, Any]]:
    now = time.time()
    out: dict[str, dict[str, Any]] = {}
    for sym in symbols:
        hit = _MAP_RET_CACHE.get(str(sym or "").upper())
        if _horizon_row_usable(hit, now=now):
            out[str(sym).upper()] = hit  # type: ignore[assignment]
    return out


async def _fetch_map_horizon_returns(
    symbols: list[str],
    *,
    concurrency: int = 20,
) -> dict[str, dict[str, Any]]:
    """Batch ~1–4 week % returns (Yahoo daily first, Nasdaq fallback)."""
    now = time.time()
    out: dict[str, dict[str, Any]] = {}
    need: list[str] = []
    for sym in symbols:
        key = str(sym or "").upper()
        if not key:
            continue
        hit = _MAP_RET_CACHE.get(key)
        if _horizon_row_usable(hit, now=now):
            out[key] = hit  # type: ignore[assignment]
        # Keep fetching until 4w lands (or TTL expires).
        if not _horizon_row_complete(hit, now=now):
            need.append(key)
    if not need:
        return out

    uniq = list(dict.fromkeys(need))
    from_d = date.today() - timedelta(days=90)

    async def _one(
        client: httpx.AsyncClient, sym: str, sem: asyncio.Semaphore
    ) -> None:
        async with sem:
            closes = await _yahoo_daily_closes(client, sym)
            if len(closes) < 6:
                try:
                    bars = await fetch_nasdaq_daily_bars(
                        client,
                        sym,
                        fromdate=from_d,
                        todate=date.today(),
                        assetclass="stocks",
                    )
                except Exception:  # noqa: BLE001
                    bars = []
                closes = [
                    float(b["c"])
                    for b in bars
                    if isinstance(b, dict) and isinstance(b.get("c"), (int, float))
                ]
            row = _closes_to_horizon_row(closes)
            if not row:
                return
            _MAP_RET_CACHE[sym] = row
            out[sym] = row

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            trust_env=False,
            timeout=httpx.Timeout(6.0, connect=2.5),
        ) as client:
            # Finished symbols stay in _MAP_RET_CACHE even if the caller times out.
            sem = asyncio.Semaphore(max(4, int(concurrency)))
            await asyncio.gather(
                *[_one(client, s, sem) for s in uniq],
                return_exceptions=True,
            )
    except Exception:  # noqa: BLE001
        pass
    return out


async def _background_horizon_fill(symbols: list[str]) -> None:
    """Continue filling week returns after the map response is already out."""
    global _HORIZON_FILL_BUSY, _HORIZON_FILL_PENDING
    if _HORIZON_FILL_BUSY:
        _HORIZON_FILL_PENDING = list(symbols or [])
        return
    _HORIZON_FILL_BUSY = True
    batch = list(symbols or [])
    try:
        while batch:
            await _fetch_map_horizon_returns(batch, concurrency=18)
            cached = _MAP_CACHE.get("payload")
            if isinstance(cached, dict) and cached.get("sectors"):
                payload = copy.deepcopy(cached)
                stamped = _stamp_returns_on_payload(
                    payload, _cached_horizon_rets(batch)
                )
                if stamped:
                    _MAP_CACHE["payload"] = payload
            batch = list(_HORIZON_FILL_PENDING or [])
            _HORIZON_FILL_PENDING = None
    except Exception:  # noqa: BLE001
        pass
    finally:
        _HORIZON_FILL_BUSY = False
        pending = _HORIZON_FILL_PENDING
        _HORIZON_FILL_PENDING = None
        if pending:
            _schedule_horizon_fill(pending)


def _horizon_coverage(payload: dict[str, Any], key: str = "1w") -> float:
    total = 0
    hit = 0
    for sec in payload.get("sectors") or []:
        for grp in sec.get("groups") or []:
            for st in grp.get("children") or []:
                total += 1
                rets = st.get("returns") if isinstance(st.get("returns"), dict) else {}
                val = rets.get(key)
                if val is None and key == "1w":
                    val = st.get("week5_pct")
                if isinstance(val, (int, float)):
                    hit += 1
    if total <= 0:
        return 0.0
    return hit / total


def _stamp_returns_on_payload(
    payload: dict[str, Any], horizon_rets: dict[str, dict[str, Any]]
) -> int:
    """Merge week returns into an existing map payload; return #symbols updated."""
    if not horizon_rets:
        return 0
    updated = 0
    for sec in payload.get("sectors") or []:
        sector_bucket: dict[str, list[tuple[float | None, float]]] = {
            k: [] for k in ("day", "rt", "1w", "2w", "3w", "4w")
        }
        for grp in sec.get("groups") or []:
            group_bucket: dict[str, list[tuple[float | None, float]]] = {
                k: [] for k in ("day", "rt", "1w", "2w", "3w", "4w")
            }
            for st in grp.get("children") or []:
                sym = str(st.get("symbol") or "").upper()
                w = float(st.get("weight") or 1)
                hr = horizon_rets.get(sym) or {}
                rets = dict(st.get("returns") or {})
                day = rets.get("day", st.get("change_pct"))
                rt = rets.get("rt", st.get("rt_change_pct", day))

                def _keep(new: Any, *olds: Any) -> float | None:
                    if isinstance(new, (int, float)):
                        return float(new)
                    for old in olds:
                        if isinstance(old, (int, float)):
                            return float(old)
                    return None

                if hr:
                    rets = {
                        "day": day if isinstance(day, (int, float)) else None,
                        "rt": rt if isinstance(rt, (int, float)) else None,
                        "1w": _keep(hr.get("week5_pct"), rets.get("1w"), st.get("week5_pct")),
                        "2w": _keep(hr.get("week10_pct"), rets.get("2w"), st.get("week10_pct")),
                        "3w": _keep(hr.get("week15_pct"), rets.get("3w"), st.get("week15_pct")),
                        "4w": _keep(hr.get("week20_pct"), rets.get("4w"), st.get("week20_pct")),
                    }
                    st["returns"] = rets
                    st["week5_pct"] = rets["1w"]
                    st["week10_pct"] = rets["2w"]
                    st["week15_pct"] = rets["3w"]
                    st["week20_pct"] = rets["4w"]
                    updated += 1
                else:
                    rets = {
                        "day": day if isinstance(day, (int, float)) else None,
                        "rt": rt if isinstance(rt, (int, float)) else None,
                        "1w": _keep(rets.get("1w"), st.get("week5_pct")),
                        "2w": _keep(rets.get("2w"), st.get("week10_pct")),
                        "3w": _keep(rets.get("3w"), st.get("week15_pct")),
                        "4w": _keep(rets.get("4w"), st.get("week20_pct")),
                    }
                    st["returns"] = rets
                for key in ("day", "rt", "1w", "2w", "3w", "4w"):
                    group_bucket[key].append((rets.get(key), w))
                    sector_bucket[key].append((rets.get(key), w))
            grp["returns"] = {k: _weighted_avg(v) for k, v in group_bucket.items()}
        sec["returns"] = {k: _weighted_avg(v) for k, v in sector_bucket.items()}
    stats = payload.setdefault("stats", {})
    stats["horizon_quoted"] = sum(
        1
        for sec in payload.get("sectors") or []
        for grp in sec.get("groups") or []
        for st in grp.get("children") or []
        if isinstance((st.get("returns") or {}).get("1w"), (int, float))
    )
    return updated


def _weighted_avg(
    items: list[tuple[float | None, float]],
) -> float | None:
    num = 0.0
    den = 0.0
    for pct, w in items:
        if isinstance(pct, (int, float)) and w > 0:
            num += float(pct) * w
            den += w
    if den <= 0:
        return None
    return round(num / den, 3)


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


def _schedule_horizon_fill(symbols: list[str]) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if _HORIZON_FILL_BUSY:
        return
    loop.create_task(_background_horizon_fill(symbols))


async def build_market_map(
    *, force: bool = False, fill_horizon: bool = False
) -> dict[str, Any]:
    now = time.time()
    symbols = _map_symbols()
    cached_payload = _MAP_CACHE.get("payload")
    cached_quoted = int(((cached_payload or {}).get("stats") or {}).get("quoted") or 0)
    cache_fresh = (
        not force
        and cached_payload
        and cached_quoted > 0
        and now - float(_MAP_CACHE["fetched_at"]) < _MAP_TTL
    )

    # Week-tab path: keep day shell, spend the budget filling 1w–4w returns.
    if fill_horizon and cached_payload and cached_quoted > 0:
        try:
            horizon_rets = await asyncio.wait_for(
                _fetch_map_horizon_returns(symbols, concurrency=22),
                timeout=14.0,
            )
        except TimeoutError:
            horizon_rets = {}
        horizon_rets = {**_cached_horizon_rets(symbols), **horizon_rets}
        payload = copy.deepcopy(cached_payload)
        _stamp_returns_on_payload(payload, horizon_rets)
        payload["cached"] = True
        payload["horizon_fill"] = True
        payload["fetched_at"] = cached_payload.get("fetched_at") or now
        _MAP_CACHE["payload"] = copy.deepcopy(payload)
        _schedule_horizon_fill(symbols)
        return payload

    # Horizon fills are best-effort — never block the map paint on a full gather.
    try:
        horizon_rets = await asyncio.wait_for(
            _fetch_map_horizon_returns(symbols, concurrency=18),
            timeout=5.0 if cache_fresh else 8.0,
        )
    except TimeoutError:
        horizon_rets = {}
    # Always merge warm cache — timeout must not drop already-fetched weeks.
    horizon_rets = {**_cached_horizon_rets(symbols), **horizon_rets}

    if cache_fresh:
        payload = copy.deepcopy(cached_payload)
        before = _horizon_coverage(payload, "1w")
        _stamp_returns_on_payload(payload, horizon_rets)
        after = _horizon_coverage(payload, "1w")
        payload["cached"] = True
        payload["fetched_at"] = cached_payload.get("fetched_at") or now
        # Persist improved week coverage so next clients see denser heatmaps.
        if after > before + 0.02 or after >= 0.55:
            _MAP_CACHE["payload"] = copy.deepcopy(payload)
        _schedule_horizon_fill(symbols)
        return payload

    # Map has dozens of tickers — never block on Yahoo Overnight HTML scrapes.
    try:
        quotes = await asyncio.wait_for(
            fetch_day_quotes(symbols, overnight_priority=[]),
            timeout=8.0,
        )
    except TimeoutError:
        if cached_payload and cached_quoted > 0:
            payload = copy.deepcopy(cached_payload)
            payload["cached"] = True
            payload["stale"] = True
            payload["note"] = "地图报价超时，已返回缓存。"
            return payload
        quotes = {}
    errors = [f"{sym}: quote failed" for sym in symbols if sym not in quotes]

    sectors_out: list[dict[str, Any]] = []
    up = down = flat = 0
    horizon_quoted = 0
    for sector in MARKET_MAP:
        groups_out: list[dict[str, Any]] = []
        sector_weights = 0.0
        sector_bucket: dict[str, list[tuple[float | None, float]]] = {
            k: [] for k in ("day", "rt", "1w", "2w", "3w", "4w")
        }
        for group in sector.get("groups") or []:
            children: list[dict[str, Any]] = []
            group_weight = 0.0
            group_bucket: dict[str, list[tuple[float | None, float]]] = {
                k: [] for k in ("day", "rt", "1w", "2w", "3w", "4w")
            }
            for stock in group.get("stocks") or []:
                sym = str(stock.get("symbol") or "").upper()
                q = quotes.get(sym) or {}
                pct = q.get("change_pct")
                rt_pct = q.get("rt_change_pct")
                if rt_pct is None:
                    rt_pct = pct
                hr = horizon_rets.get(sym) or _MAP_RET_CACHE.get(sym) or {}
                w = float(stock.get("weight") or 1)
                returns = {
                    "day": pct if isinstance(pct, (int, float)) else None,
                    "rt": rt_pct if isinstance(rt_pct, (int, float)) else None,
                    "1w": hr.get("week5_pct"),
                    "2w": hr.get("week10_pct"),
                    "3w": hr.get("week15_pct"),
                    "4w": hr.get("week20_pct"),
                }
                if isinstance(returns["1w"], (int, float)):
                    horizon_quoted += 1
                if isinstance(pct, (int, float)):
                    if pct > 0.05:
                        up += 1
                    elif pct < -0.05:
                        down += 1
                    else:
                        flat += 1
                for key in returns:
                    group_bucket[key].append((returns[key], w))
                    sector_bucket[key].append((returns[key], w))
                children.append(
                    {
                        "symbol": sym,
                        "name": stock.get("name") or sym,
                        "weight": w,
                        "change_pct": pct,
                        "rt_change_pct": rt_pct,
                        "week5_pct": returns["1w"],
                        "week10_pct": returns["2w"],
                        "week15_pct": returns["3w"],
                        "week20_pct": returns["4w"],
                        "returns": returns,
                        "price": q.get("price"),
                    }
                )
                group_weight += w
            if not children:
                continue
            g_returns = {k: _weighted_avg(v) for k, v in group_bucket.items()}
            g_pct = g_returns.get("day")
            groups_out.append(
                {
                    "id": group["id"],
                    "label": group["label"],
                    "weight": float(group.get("weight") or group_weight or 1),
                    "change_pct": g_pct,
                    "returns": g_returns,
                    "children": children,
                }
            )
            sector_weights += float(group.get("weight") or group_weight or 1)
        if not groups_out:
            continue
        s_returns = {k: _weighted_avg(v) for k, v in sector_bucket.items()}
        s_pct = s_returns.get("day")
        sectors_out.append(
            {
                "id": sector["id"],
                "label": sector["label"],
                "desk_id": sector.get("desk_id") or sector["id"],
                "weight": float(sector.get("weight") or sector_weights or 1),
                "change_pct": s_pct,
                "returns": s_returns,
                "groups": groups_out,
            }
        )

    payload = {
        "sectors": sectors_out,
        "horizons": ["day", "rt", "1w", "2w", "3w", "4w"],
        "default_horizon": "day",
        "stats": {
            "symbols": len(symbols),
            "quoted": len(quotes),
            "horizon_quoted": horizon_quoted,
            "up": up,
            "down": down,
            "flat": flat,
        },
        "errors": errors[-20:],
        "fetched_at": now,
        "cached": False,
        "source": "日/实时涨跌 + Yahoo/Nasdaq 日线周涨跌 · 权重为相对市值近似",
    }
    # Cache day quotes even if week coverage is still filling — next hits backfill.
    if quotes:
        _MAP_CACHE["payload"] = payload
        _MAP_CACHE["fetched_at"] = now
    _schedule_horizon_fill(symbols)
    return dict(payload)
