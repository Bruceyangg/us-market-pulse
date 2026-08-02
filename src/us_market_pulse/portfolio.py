"""Personalized holdings list persisted per logged-in user."""

from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from us_market_pulse.config import DATA_DIR
from us_market_pulse.markets import PORTFOLIO_TIMEFRAMES, fetch_symbol_bundle

_LOCK = threading.Lock()
PORTFOLIOS_DIR = DATA_DIR / "portfolios"
LEGACY_PORTFOLIO_PATH = DATA_DIR / "portfolio.json"
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9.\-^]{1,12}$")
_USER_FILE_RE = re.compile(r"^[a-z0-9_]{3,24}$")
MAX_HOLDINGS = 20

_CACHE: dict[str, Any] = {
    "quotes_at": 0.0,
    "boards": {},  # symbol -> bundle
}
_QUOTE_TTL = 90


def _empty() -> dict[str, Any]:
    return {
        "updated_at": 0.0,
        "selected": "",
        "holdings": [],
    }


def portfolio_path(username: str) -> Path:
    user = str(username or "").strip().lower()
    if not _USER_FILE_RE.match(user):
        raise ValueError("无效用户")
    return PORTFOLIOS_DIR / f"{user}.json"


def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    holdings = []
    for row in data.get("holdings") or []:
        symbol = normalize_symbol(row.get("symbol"))
        if not symbol:
            continue
        holdings.append(
            {
                "symbol": symbol,
                "name": str(row.get("name") or symbol).strip()[:40],
                "note": str(row.get("note") or "").strip()[:80],
                "added_at": float(row.get("added_at") or 0) or time.time(),
            }
        )
    selected = normalize_symbol(data.get("selected")) or (
        holdings[0]["symbol"] if holdings else ""
    )
    return {
        "updated_at": float(data.get("updated_at") or 0),
        "selected": selected,
        "holdings": holdings[:MAX_HOLDINGS],
    }


def load_portfolio(username: str) -> dict[str, Any]:
    path = portfolio_path(username)
    PORTFOLIOS_DIR.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # One-time bridge: first account can inherit legacy shared file.
        if LEGACY_PORTFOLIO_PATH.exists() and not any(PORTFOLIOS_DIR.glob("*.json")):
            try:
                legacy = json.loads(LEGACY_PORTFOLIO_PATH.read_text(encoding="utf-8"))
                cleaned = _normalize_payload(legacy)
                save_portfolio(username, cleaned)
                return cleaned
            except (OSError, json.JSONDecodeError, ValueError):
                pass
        return _empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty()
    return _normalize_payload(data)


def save_portfolio(username: str, data: dict[str, Any]) -> dict[str, Any]:
    cleaned = {
        "updated_at": time.time(),
        "selected": normalize_symbol(data.get("selected")) or "",
        "holdings": [],
        "owner": str(username).strip().lower(),
    }
    seen: set[str] = set()
    for row in data.get("holdings") or []:
        symbol = normalize_symbol(row.get("symbol"))
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        cleaned["holdings"].append(
            {
                "symbol": symbol,
                "name": str(row.get("name") or symbol).strip()[:40],
                "note": str(row.get("note") or "").strip()[:80],
                "added_at": float(row.get("added_at") or time.time()),
            }
        )
        if len(cleaned["holdings"]) >= MAX_HOLDINGS:
            break
    if cleaned["selected"] not in {h["symbol"] for h in cleaned["holdings"]}:
        cleaned["selected"] = cleaned["holdings"][0]["symbol"] if cleaned["holdings"] else ""

    path = portfolio_path(username)
    with _LOCK:
        PORTFOLIOS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp.replace(path)
    return cleaned


def normalize_symbol(raw: Any) -> str:
    symbol = str(raw or "").strip().upper()
    if not symbol or not _SYMBOL_RE.match(symbol):
        return ""
    return symbol


def add_holding(
    username: str, symbol: str, *, name: str = "", note: str = ""
) -> dict[str, Any]:
    symbol = normalize_symbol(symbol)
    if not symbol:
        raise ValueError("代码无效。请输入美股代码，如 AAPL、NVDA、TSLA。")
    data = load_portfolio(username)
    holdings = data["holdings"]
    for row in holdings:
        if row["symbol"] == symbol:
            row["name"] = (name or row["name"] or symbol).strip()[:40]
            row["note"] = (note if note is not None else row.get("note") or "").strip()[
                :80
            ]
            data["selected"] = symbol
            return save_portfolio(username, data)
    if len(holdings) >= MAX_HOLDINGS:
        raise ValueError(f"最多添加 {MAX_HOLDINGS} 只持仓。")
    holdings.append(
        {
            "symbol": symbol,
            "name": (name or symbol).strip()[:40],
            "note": (note or "").strip()[:80],
            "added_at": time.time(),
        }
    )
    data["holdings"] = holdings
    data["selected"] = symbol
    return save_portfolio(username, data)


def remove_holding(username: str, symbol: str) -> dict[str, Any]:
    symbol = normalize_symbol(symbol)
    data = load_portfolio(username)
    data["holdings"] = [h for h in data["holdings"] if h["symbol"] != symbol]
    if data.get("selected") == symbol:
        data["selected"] = data["holdings"][0]["symbol"] if data["holdings"] else ""
    _CACHE["boards"].pop(symbol, None)
    return save_portfolio(username, data)


def select_holding(username: str, symbol: str) -> dict[str, Any]:
    symbol = normalize_symbol(symbol)
    data = load_portfolio(username)
    symbols = {h["symbol"] for h in data["holdings"]}
    if symbol and symbol not in symbols:
        raise ValueError("该代码不在持仓列表中")
    data["selected"] = symbol
    return save_portfolio(username, data)


def replace_holdings(
    username: str, holdings: list[dict[str, Any]], *, selected: str = ""
) -> dict[str, Any]:
    return save_portfolio(username, {"holdings": holdings, "selected": selected})


async def build_portfolio_view(
    username: str,
    *,
    force_refresh: bool = False,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    data = load_portfolio(username)
    holdings = data["holdings"]
    now = time.time()
    boards: dict[str, Any] = dict(_CACHE.get("boards") or {})
    stale = force_refresh or (now - float(_CACHE.get("quotes_at") or 0) >= _QUOTE_TTL)

    symbols = [h["symbol"] for h in holdings]
    need = [s for s in symbols if stale or s not in boards]
    errors: list[str] = []

    async def _load(http: httpx.AsyncClient) -> None:
        nonlocal boards, errors
        if not need:
            return
        name_map = {h["symbol"]: h.get("name") or h["symbol"] for h in holdings}
        tasks = [
            fetch_symbol_bundle(
                http,
                symbol=sym,
                label=name_map.get(sym),
                short=sym,
                timeframes=PORTFOLIO_TIMEFRAMES,
                include_yearly=True,
            )
            for sym in need
        ]
        results = await asyncio.gather(*tasks)
        for sym, (bundle, errs) in zip(need, results, strict=True):
            errors.extend(errs)
            if bundle:
                boards[sym] = bundle

    if need:
        if client is None:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; PulseDesk/1.0)",
                    "Accept": "application/json",
                },
                follow_redirects=True,
            ) as http:
                await _load(http)
        else:
            await _load(client)
        merged = dict(_CACHE.get("boards") or {})
        merged.update({s: boards[s] for s in symbols if s in boards})
        _CACHE["boards"] = merged
        _CACHE["quotes_at"] = now
    else:
        # keep shared quote cache; ensure selected symbols present
        _CACHE["boards"] = {**(_CACHE.get("boards") or {}), **{s: boards[s] for s in symbols if s in boards}}

    boards = _CACHE.get("boards") or {}
    selected = data.get("selected") or (symbols[0] if symbols else "")
    selected_board = boards.get(selected)

    timeframes = [
        {
            "id": tf["id"],
            "label": tf["label"],
            "blurb": tf["blurb"],
            "chart": tf["chart"],
        }
        for tf in PORTFOLIO_TIMEFRAMES
    ] + [
        {
            "id": "year",
            "label": "年图",
            "blurb": "按年聚合 K 线（红涨绿跌）",
            "chart": "candle",
        }
    ]

    cards = []
    for h in holdings:
        board = boards.get(h["symbol"]) or {}
        cards.append(
            {
                **h,
                "price": board.get("price"),
                "change": board.get("change"),
                "change_pct": board.get("change_pct"),
                "as_of": board.get("as_of"),
                "points": board.get("points") or [],
                "series": board.get("series") or {},
                "label": board.get("label") or h.get("name") or h["symbol"],
                "url": board.get("url")
                or f"https://finance.yahoo.com/quote/{h['symbol']}",
            }
        )

    return {
        "updated_at": data.get("updated_at") or 0,
        "selected": selected,
        "holdings": cards,
        "selected_board": selected_board,
        "timeframes": timeframes,
        "default_tf": "intraday",
        "max_holdings": MAX_HOLDINGS,
        "owner": str(username).strip().lower(),
        "errors": errors,
        "note": "持仓绑定当前登录账户；换设备用同一账号登录即可同步。部署重建后请用导出备份恢复。",
        "style": {"up": "red", "down": "green"},
    }
