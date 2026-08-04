"""Resolve holding queries: ticker symbols or Chinese/English company names."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from us_market_pulse.market_map import MARKET_MAP
from us_market_pulse.sectors import SECTOR_ETFS, VALUE_CHAIN

_SYMBOL_RE = re.compile(r"^[A-Za-z0-9.\-^]{1,12}$")
_WS_RE = re.compile(r"[\s\-_/·•]+")


def _norm_key(text: str) -> str:
    raw = str(text or "").strip().casefold()
    if not raw:
        return ""
    return _WS_RE.sub("", raw)


def _add_alias(
    index: dict[str, dict[str, str]],
    alias: str,
    symbol: str,
    name: str,
) -> None:
    key = _norm_key(alias)
    if not key or len(key) < 1:
        return
    # Prefer longer / more specific Chinese names already stored; first write wins
    # for exact keys, but allow symbol keys to always map to themselves.
    if key not in index:
        index[key] = {"symbol": symbol, "name": name or symbol}


@lru_cache(maxsize=1)
def _build_index() -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}

    for sym, meta in VALUE_CHAIN.items():
        symbol = str(sym or "").upper()
        if not symbol:
            continue
        name = str(meta.get("name") or symbol)
        _add_alias(index, symbol, symbol, name)
        _add_alias(index, name, symbol, name)
        # Common English stubs from name if ASCII
        if re.fullmatch(r"[A-Za-z0-9 .&\-]+", name):
            _add_alias(index, name, symbol, name)

    for sector in MARKET_MAP:
        for group in sector.get("groups") or []:
            for stock in group.get("stocks") or []:
                symbol = str(stock.get("symbol") or "").upper()
                if not symbol:
                    continue
                name = str(stock.get("name") or symbol)
                _add_alias(index, symbol, symbol, name)
                _add_alias(index, name, symbol, name)

    for etf in SECTOR_ETFS:
        symbol = str(etf.get("symbol") or "").upper()
        if not symbol:
            continue
        name = str(etf.get("label") or etf.get("short") or symbol)
        _add_alias(index, symbol, symbol, name)
        _add_alias(index, name, symbol, name)
        _add_alias(index, str(etf.get("short") or ""), symbol, name)

    # Extra everyday aliases (beyond archive names)
    extras = {
        "苹果": ("AAPL", "苹果"),
        "apple": ("AAPL", "苹果"),
        "微软": ("MSFT", "微软"),
        "microsoft": ("MSFT", "微软"),
        "谷歌": ("GOOGL", "谷歌"),
        "google": ("GOOGL", "谷歌"),
        "alphabet": ("GOOGL", "谷歌"),
        "亚马逊": ("AMZN", "亚马逊"),
        "amazon": ("AMZN", "亚马逊"),
        "脸书": ("META", "Meta"),
        "meta": ("META", "Meta"),
        "特斯拉": ("TSLA", "特斯拉"),
        "tesla": ("TSLA", "特斯拉"),
        "英伟达": ("NVDA", "英伟达"),
        "nvidia": ("NVDA", "英伟达"),
        "台积电": ("TSM", "台积电"),
        "博通": ("AVGO", "博通"),
        "超威": ("AMD", "超威"),
        "美光": ("MU", "美光"),
        "高通": ("QCOM", "高通"),
        "阿斯麦": ("ASML", "阿斯麦"),
        "应用材料": ("AMAT", "应用材料"),
        "拉姆研究": ("LRCX", "拉姆研究"),
        "科磊": ("KLAC", "科磊"),
        "奈飞": ("NFLX", "奈飞"),
        "netflix": ("NFLX", "奈飞"),
        "成本高": ("COST", "好市多"),
        "好市多": ("COST", "好市多"),
        "costco": ("COST", "好市多"),
        "摩根大通": ("JPM", "摩根大通"),
        "埃克森": ("XOM", "埃克森美孚"),
        "埃克森美孚": ("XOM", "埃克森美孚"),
        "雪佛龙": ("CVX", "雪佛龙"),
        "礼来": ("LLY", "礼来"),
        "辉瑞": ("PFE", "辉瑞"),
        "强生": ("JNJ", "强生"),
        "甲骨文": ("ORCL", "甲骨文"),
        "salesforce": ("CRM", "Salesforce"),
        "雪花": ("SNOW", "Snowflake"),
        "snowflake": ("SNOW", "Snowflake"),
    }
    for alias, (sym, name) in extras.items():
        _add_alias(index, alias, sym, name)

    return index


def resolve_holding_query(raw: str) -> dict[str, str] | None:
    """
    Resolve user input to {symbol, name}.
    Accepts tickers (AAPL) or Chinese/English names (苹果 / Apple / 亚马逊).
    """
    text = str(raw or "").strip()
    if not text:
        return None

    index = _build_index()
    key = _norm_key(text)

    # Alias / Chinese / English name first (so "nvidia" → NVDA, not ticker NVIDIA)
    exact = index.get(key)
    if exact:
        return {"symbol": exact["symbol"], "name": exact["name"]}

    # Direct ticker for unknown or known codes
    upper = text.upper()
    if _SYMBOL_RE.match(upper):
        hit = index.get(_norm_key(upper))
        return {
            "symbol": upper,
            "name": (hit or {}).get("name") or upper,
        }

    # Prefix / contains match for Chinese names (prefer shortest alias length)
    candidates: list[tuple[int, dict[str, str]]] = []
    for alias, row in index.items():
        if alias == row["symbol"].casefold():
            continue
        if key in alias or alias in key:
            candidates.append((len(alias), row))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]["symbol"]))
    best = candidates[0][1]
    return {"symbol": best["symbol"], "name": best["name"]}


def suggest_holdings(raw: str, *, limit: int = 8) -> list[dict[str, str]]:
    """Autocomplete suggestions for the add-holding input."""
    text = str(raw or "").strip()
    if not text:
        return []
    key = _norm_key(text)
    upper = text.upper()
    seen: set[str] = set()
    out: list[dict[str, str]] = []

    def push(symbol: str, name: str, score: int) -> None:
        if symbol in seen:
            return
        seen.add(symbol)
        out.append({"symbol": symbol, "name": name, "label": f"{name} · {symbol}"})

    scored: list[tuple[int, str, str]] = []
    for alias, row in _build_index().items():
        symbol = row["symbol"]
        name = row["name"]
        if _SYMBOL_RE.match(upper) and symbol.startswith(upper):
            scored.append((0, symbol, name))
        elif alias.startswith(key):
            scored.append((1, symbol, name))
        elif key in alias:
            scored.append((2 + len(alias), symbol, name))

    scored.sort(key=lambda x: (x[0], x[1]))
    for _score, symbol, name in scored:
        push(symbol, name, _score)
        if len(out) >= limit:
            break
    return out


def catalog_snapshot(limit: int = 120) -> list[dict[str, str]]:
    """Compact catalog for client-side datalist (unique symbols)."""
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in _build_index().values():
        sym = row["symbol"]
        if sym in seen:
            continue
        seen.add(sym)
        rows.append({"symbol": sym, "name": row["name"], "label": f"{row['name']} · {sym}"})
        if len(rows) >= limit:
            break
    rows.sort(key=lambda r: r["symbol"])
    return rows
