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
from us_market_pulse.earnings_calendar import get_upcoming_earnings_map
from us_market_pulse.markets import PORTFOLIO_TIMEFRAMES
from us_market_pulse.quotes import apply_list_quote_fields, fetch_day_quotes
from us_market_pulse.sectors import (
    USER_AGENT,
    _bundle_has_full_chart,
    _fetch_earnings_cached,
    _fetch_quote_limited,
    _hydrate_list_intraday_sparks,
    _hydrate_sparks_from_cache,
    _momentum_fields,
    _move_analysis,
    _pick_has_chart,
    _pick_has_intraday,
    _slim_pick_row,
    _value_chain_for,
)

_LOCK = threading.Lock()
PORTFOLIOS_DIR = DATA_DIR / "portfolios"
LEGACY_PORTFOLIO_PATH = DATA_DIR / "portfolio.json"
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9.\-^]{1,12}$")
_USER_FILE_RE = re.compile(r"^[a-z0-9_]{3,24}$")
MAX_HOLDINGS = 20

_CACHE: dict[str, Any] = {
    "quotes_at": 0.0,
    "boards": {},  # symbol -> selected chart bundle
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


def resolve_and_normalize(raw: Any) -> tuple[str, str]:
    """Return (symbol, canonical_name) from ticker or Chinese/English name."""
    from us_market_pulse.symbol_lookup import resolve_holding_query

    hit = resolve_holding_query(str(raw or ""))
    if not hit:
        return "", ""
    symbol = normalize_symbol(hit.get("symbol"))
    if not symbol:
        return "", ""
    return symbol, str(hit.get("name") or symbol)


def add_holding(
    username: str, symbol: str, *, name: str = "", note: str = ""
) -> dict[str, Any]:
    resolved_symbol, canonical_name = resolve_and_normalize(symbol)
    if not resolved_symbol:
        # Fall back to strict ticker-only for unknown ASCII codes
        resolved_symbol = normalize_symbol(symbol)
    if not resolved_symbol:
        raise ValueError(
            "无法识别。可输入美股代码（如 AAPL）或中文名（如 苹果 / 亚马逊 / 英伟达）。"
        )
    symbol = resolved_symbol
    display_name = (name or canonical_name or symbol).strip()[:40]
    data = load_portfolio(username)
    holdings = data["holdings"]
    for row in holdings:
        if row["symbol"] == symbol:
            row["name"] = display_name or row["name"] or symbol
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
            "name": display_name or symbol,
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


def _lite_holding_card(
    holding: dict[str, Any], quote: dict[str, Any] | None
) -> dict[str, Any]:
    """Sector-desk lite row: day quote + empty spark (hydrated later)."""
    sym = holding["symbol"]
    vc = _value_chain_for(sym)
    day_pct = (quote or {}).get("change_pct")
    name = holding.get("name") or vc.get("name") or sym
    try:
        momentum = float(day_pct or 0)
    except (TypeError, ValueError):
        momentum = 0.0
    is_strong = day_pct is not None and float(day_pct) > 0
    row = {
        **holding,
        "name": name,
        "label": name,
        "price": (quote or {}).get("price"),
        "change": (quote or {}).get("change"),
        "change_pct": day_pct,
        "as_of": (quote or {}).get("as_of"),
        "month_change_pct": day_pct,
        "quarter_change_pct": None,
        "momentum": momentum,
        "is_wave": bool(is_strong and momentum > 1.5),
        "is_strong": bool(is_strong),
        "points": [],
        "series": {},
        "lite": True,
        "earnings": None,
        "value_chain": vc,
        "move_analysis": None,
        "sector_label": str(vc.get("industry") or "持仓"),
        "url": f"https://finance.yahoo.com/quote/{sym}",
    }
    apply_list_quote_fields(row, quote)
    return row


def _empty_portfolio_view(username: str, data: dict[str, Any]) -> dict[str, Any]:
    timeframes = [
        {
            "id": tf["id"],
            "label": tf["label"],
            "blurb": tf["blurb"],
            "chart": tf["chart"],
        }
        for tf in PORTFOLIO_TIMEFRAMES
        if tf["id"] != "year"
    ]
    return {
        "updated_at": data.get("updated_at") or 0,
        "selected": "",
        "selected_symbol": "",
        "holdings": [],
        "selected_board": None,
        "board": None,
        "selected_earnings": None,
        "value_chain": None,
        "earnings_calendar": [],
        "timeframes": timeframes,
        "default_tf": "intraday",
        "max_holdings": MAX_HOLDINGS,
        "owner": str(username).strip().lower(),
        "errors": [],
        "note": "持仓绑定当前登录账户；换设备用同一账号登录即可同步。部署重建后请用导出备份恢复。",
        "style": {"up": "red", "down": "green"},
    }


async def upgrade_selected_board(
    username: str,
    symbol: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Fetch only the selected symbol's chart/earnings — used by fast /select."""
    sym = normalize_symbol(symbol)
    data = load_portfolio(username)
    holdings = data.get("holdings") or []
    holding_meta = next((h for h in holdings if h.get("symbol") == sym), None)
    if not holding_meta:
        raise ValueError("该代码不在持仓列表中")

    now = time.time()
    errors: list[str] = []
    boards: dict[str, Any] = dict(_CACHE.get("boards") or {})
    cached = boards.get(sym) if isinstance(boards.get(sym), dict) else None
    # Only treat multi-TF candles as "fresh". Intraday-only boards must still
    # upgrade so 日/月/季 tabs work without a full page reload.
    cache_fresh = (
        not force
        and cached
        and (now - float(_CACHE.get("quotes_at") or 0) < _QUOTE_TTL)
        and _pick_has_chart(cached)
    )
    vc = _value_chain_for(sym)

    def _rich_from_bundle(
        bundle: dict[str, Any],
        quote: dict[str, Any] | None = None,
        *,
        earn: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        wave = _momentum_fields(bundle)
        day_pct = bundle.get("change_pct")
        if day_pct is None and quote:
            day_pct = quote.get("change_pct")
        rich = {
            **holding_meta,
            **bundle,
            "name": holding_meta.get("name")
            or vc.get("name")
            or bundle.get("label")
            or sym,
            "label": holding_meta.get("name")
            or vc.get("name")
            or bundle.get("label")
            or sym,
            "month_change_pct": wave["month_change_pct"],
            "quarter_change_pct": wave["quarter_change_pct"],
            "momentum": wave["momentum"],
            "is_wave": wave["is_wave"],
            "is_strong": wave["is_wave"] or float(day_pct or 0) > 0,
            "sector_label": str(vc.get("industry") or "持仓"),
            "value_chain": vc,
            "lite": False,
            "chart_attempted": True,
            "url": bundle.get("url") or f"https://finance.yahoo.com/quote/{sym}",
        }
        if quote:
            apply_list_quote_fields(rich, quote)
        if earn:
            rich["earnings"] = earn
        elif isinstance(bundle.get("earnings"), dict):
            rich["earnings"] = bundle["earnings"]
        try:
            rich["move_analysis"] = _move_analysis(
                day_pct=rich.get("change_pct"),
                month_pct=wave["month_change_pct"]
                if _pick_has_chart(rich)
                else rich.get("month_change_pct"),
                quarter_pct=wave["quarter_change_pct"],
                vs_sector_pct=None,
                is_wave=bool(rich.get("is_wave")),
                sector_label=str(rich.get("sector_label") or ""),
                etf_day_pct=None,
                earnings=rich.get("earnings")
                if isinstance(rich.get("earnings"), dict)
                else None,
                value_chain=vc,
                news=None,
            )
        except Exception:  # noqa: BLE001
            rich["move_analysis"] = {
                "bias": "neutral",
                "bias_zh": "中性",
                "summary": "行情数据不足，暂无法判断涨跌驱动。",
                "factors": ["等待报价刷新后再解读"],
            }
        return rich

    # Warm cache: return immediately — skip day-quote / earnings network waits.
    if cache_fresh and cached:
        rich = _rich_from_bundle(cached)
        return {
            "selected": sym,
            "selected_symbol": sym,
            "selected_board": rich,
            "board": rich,
            "selected_earnings": rich.get("earnings"),
            "value_chain": rich.get("value_chain"),
            "errors": errors,
            "cache": "hit",
        }

    yahoo_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/",
    }

    bundle: dict[str, Any] | None = None
    try:
        async with httpx.AsyncClient(
            headers=yahoo_headers,
            follow_redirects=True,
            trust_env=False,
            timeout=httpx.Timeout(14.0, connect=3.0),
        ) as http:
            bundle, errs = await asyncio.wait_for(
                _fetch_quote_limited(http, sym, sym, force=force),
                timeout=14.0,
            )
        errors.extend(errs or [])
    except (asyncio.TimeoutError, httpx.HTTPError) as exc:
        bundle = None
        errors.append(f"{sym}: chart timeout ({exc.__class__.__name__})")

    day_quotes: dict[str, Any] = {}
    try:
        day_quotes = await asyncio.wait_for(fetch_day_quotes([sym]), timeout=4.0)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"day quote: {exc}")
    quote = day_quotes.get(sym)

    if bundle and (_bundle_has_full_chart(bundle) or _pick_has_intraday(bundle)):
        boards[sym] = bundle
        _CACHE["boards"] = boards
        _CACHE["quotes_at"] = now
        rich = _rich_from_bundle(bundle, quote)
    else:
        rich = _lite_holding_card(holding_meta, quote)
        rich["chart_attempted"] = True
        rich["value_chain"] = vc

    earn = rich.get("earnings") if isinstance(rich.get("earnings"), dict) else None
    if not earn:
        try:
            upcoming_map = await asyncio.wait_for(
                get_upcoming_earnings_map(force=False),
                timeout=4.0,
            )
        except Exception:  # noqa: BLE001
            upcoming_map = {}
        try:
            async with httpx.AsyncClient(
                headers=yahoo_headers,
                follow_redirects=True,
                trust_env=False,
                timeout=httpx.Timeout(5.0, connect=2.0),
            ) as earn_client:
                earn = await asyncio.wait_for(
                    _fetch_earnings_cached(
                        earn_client,
                        sym,
                        force=force,
                        upcoming_map=upcoming_map,
                    ),
                    timeout=5.0,
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{sym}: earnings {exc}")
        if earn:
            rich["earnings"] = earn
            # Rebuild move_analysis with earnings context
            rich = _rich_from_bundle(
                {**(bundle or {}), **rich, "earnings": earn},
                quote,
                earn=earn,
            )

    return {
        "selected": sym,
        "selected_symbol": sym,
        "selected_board": rich,
        "board": rich,
        "selected_earnings": rich.get("earnings"),
        "value_chain": rich.get("value_chain"),
        "errors": errors,
    }


async def build_portfolio_view(
    username: str,
    *,
    force_refresh: bool = False,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Build holdings desk using the same enrichment path as the sectors desk.

    Fast day quotes for the whole list + Nasdaq sparks; full multi-TF chart
    only for the selected symbol — avoids the Yahoo-per-holding timeout that
    left prices/sparks as "—".
    """
    data = load_portfolio(username)
    holdings = data["holdings"]
    if not holdings:
        return _empty_portfolio_view(username, data)

    symbols = [h["symbol"] for h in holdings]
    selected = data.get("selected") or symbols[0]
    if selected not in symbols:
        selected = symbols[0]
    errors: list[str] = []
    now = time.time()
    force = bool(force_refresh)

    # 1) Batch day quotes (CNBC → Yahoo light) — same as sector constituents
    day_quotes: dict[str, Any] = {}
    try:
        day_quotes = await asyncio.wait_for(
            fetch_day_quotes(symbols, overnight_priority=[selected]),
            timeout=10.0,
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"day quotes: {exc}")

    cards = [_lite_holding_card(h, day_quotes.get(h["symbol"])) for h in holdings]

    yahoo_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/",
    }

    # 2) Full multi-TF chart only for selected (reuse sector quote fetcher + cache)
    selected_card = next((c for c in cards if c.get("symbol") == selected), None)
    boards: dict[str, Any] = dict(_CACHE.get("boards") or {})
    cached = boards.get(selected) if isinstance(boards.get(selected), dict) else None
    cache_fresh = (
        not force
        and cached
        and (now - float(_CACHE.get("quotes_at") or 0) < _QUOTE_TTL)
        and _pick_has_chart(cached)
    )
    need_chart = bool(selected) and not cache_fresh and not _pick_has_chart(selected_card)

    if cache_fresh and cached:
        bundle = cached
        errs: list[str] = []
    elif need_chart:
        bundle, errs = None, []
        try:
            async with httpx.AsyncClient(
                headers=yahoo_headers,
                follow_redirects=True,
                trust_env=False,
                timeout=httpx.Timeout(16.0, connect=3.0),
            ) as http:
                if client is not None:
                    bundle, errs = await asyncio.wait_for(
                        _fetch_quote_limited(
                            client, selected, selected, force=force
                        ),
                        timeout=16.0,
                    )
                else:
                    bundle, errs = await asyncio.wait_for(
                        _fetch_quote_limited(http, selected, selected, force=force),
                        timeout=16.0,
                    )
        except (asyncio.TimeoutError, httpx.HTTPError) as exc:
            bundle, errs = None, [
                f"{selected}: chart timeout ({exc.__class__.__name__})"
            ]
        errors.extend(errs)
    else:
        bundle, errs = None, []

    if bundle and (_bundle_has_full_chart(bundle) or _pick_has_intraday(bundle)):
        vc = _value_chain_for(selected)
        wave = _momentum_fields(bundle)
        day_pct = bundle.get("change_pct")
        if day_pct is None:
            day_pct = (selected_card or {}).get("change_pct")
        holding_meta = next((h for h in holdings if h["symbol"] == selected), {})
        rich = {
            **holding_meta,
            **bundle,
            "name": holding_meta.get("name")
            or vc.get("name")
            or bundle.get("label")
            or selected,
            "label": holding_meta.get("name")
            or vc.get("name")
            or bundle.get("label")
            or selected,
            "month_change_pct": wave["month_change_pct"],
            "quarter_change_pct": wave["quarter_change_pct"],
            "momentum": wave["momentum"],
            "is_wave": wave["is_wave"],
            "is_strong": wave["is_wave"] or float(day_pct or 0) > 0,
            "sector_label": str(vc.get("industry") or "持仓"),
            "earnings": None,
            "value_chain": vc,
            "move_analysis": None,
            "lite": False,
            "chart_attempted": True,
            "url": bundle.get("url") or f"https://finance.yahoo.com/quote/{selected}",
        }
        # Keep list 收盘/实时 fields from day quote (don't let chart tape overwrite).
        apply_list_quote_fields(rich, day_quotes.get(selected) or selected_card)
        for idx, row in enumerate(cards):
            if row.get("symbol") == selected:
                cards[idx] = rich
                break
        boards[selected] = bundle
        _CACHE["boards"] = boards
        _CACHE["quotes_at"] = now
        selected_card = rich
    elif selected_card is not None:
        selected_card["chart_attempted"] = True

    # 3) List sparklines — Nasdaq-first, same as sector constituents
    try:
        async with httpx.AsyncClient(
            headers=yahoo_headers,
            follow_redirects=True,
            trust_env=False,
            timeout=httpx.Timeout(4.0, connect=2.0),
        ) as spark_client:
            await asyncio.wait_for(
                _hydrate_list_intraday_sparks(
                    spark_client,
                    cards,
                    force=force,
                    limit=min(18, len(cards) or 1),
                ),
                timeout=14.0,
            )
    except (asyncio.TimeoutError, httpx.HTTPError):
        _hydrate_sparks_from_cache(cards)

    # 4) Slim non-selected rows (keep spark + day tape; drop heavy multi-TF)
    cards = [_slim_pick_row(dict(c), selected) for c in cards]
    selected_card = next((c for c in cards if c.get("symbol") == selected), None)

    # 5) Earnings for selected + light calendar from upcoming map
    upcoming_map: dict[str, Any] = {}
    earnings_by_symbol: dict[str, Any] = {}
    try:
        upcoming_map = await asyncio.wait_for(
            get_upcoming_earnings_map(force=force),
            timeout=10.0,
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"earnings calendar: {exc}")
        upcoming_map = {}

    if selected:
        try:
            async with httpx.AsyncClient(
                headers=yahoo_headers,
                follow_redirects=True,
                trust_env=False,
                timeout=httpx.Timeout(8.0, connect=2.0),
            ) as earn_client:
                earn = await asyncio.wait_for(
                    _fetch_earnings_cached(
                        earn_client,
                        selected,
                        force=force,
                        upcoming_map=upcoming_map,
                    ),
                    timeout=8.0,
                )
            if earn:
                earnings_by_symbol[selected] = earn
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{selected}: earnings {exc}")

    # Fill calendar rows from upcoming map for all holdings (no per-symbol Yahoo)
    for c in cards:
        sym = str(c.get("symbol") or "")
        earn = earnings_by_symbol.get(sym) or upcoming_map.get(sym)
        if earn and not c.get("earnings"):
            c["earnings"] = earn if isinstance(earn, dict) else None
        vc = c.get("value_chain") or _value_chain_for(sym)
        c["value_chain"] = vc
        c["sector_label"] = c.get("sector_label") or vc.get("industry") or "持仓"
        wave = _momentum_fields(c if _pick_has_chart(c) else c)
        try:
            c["move_analysis"] = _move_analysis(
                day_pct=c.get("change_pct"),
                month_pct=wave["month_change_pct"]
                if _pick_has_chart(c)
                else c.get("month_change_pct"),
                quarter_pct=wave["quarter_change_pct"],
                vs_sector_pct=None,
                is_wave=bool(c.get("is_wave")),
                sector_label=str(c.get("sector_label") or ""),
                etf_day_pct=None,
                earnings=c.get("earnings") if isinstance(c.get("earnings"), dict) else None,
                value_chain=vc,
                news=None,
            )
        except Exception:  # noqa: BLE001
            c["move_analysis"] = {
                "bias": "neutral",
                "bias_zh": "中性",
                "summary": "行情数据不足，暂无法判断涨跌驱动。",
                "factors": ["等待报价刷新后再解读"],
            }

    selected_card = next((c for c in cards if c.get("symbol") == selected), None)
    if selected_card is None and cards:
        selected_card = cards[0]
        selected = selected_card["symbol"]

    earnings_calendar = sorted(
        [
            {
                **(c.get("earnings") or {}),
                "symbol": c["symbol"],
                "name": c.get("name") or c.get("label") or c["symbol"],
                "change_pct": c.get("change_pct"),
                "month_change_pct": c.get("month_change_pct"),
            }
            for c in cards
            if (c.get("earnings") or {}).get("next_earnings_ts")
            or (c.get("earnings") or {}).get("next_earnings_label")
        ],
        key=lambda r: (
            r.get("days_to_earnings")
            if r.get("days_to_earnings") is not None
            else 10_000
        ),
    )

    timeframes = [
        {
            "id": tf["id"],
            "label": tf["label"],
            "blurb": tf["blurb"],
            "chart": tf["chart"],
        }
        for tf in PORTFOLIO_TIMEFRAMES
        if tf["id"] != "year"
    ]

    return {
        "updated_at": data.get("updated_at") or 0,
        "selected": selected,
        "selected_symbol": selected,
        "holdings": cards,
        "selected_board": selected_card,
        "board": selected_card,
        "selected_earnings": (selected_card or {}).get("earnings"),
        "value_chain": (selected_card or {}).get("value_chain"),
        "earnings_calendar": earnings_calendar,
        "timeframes": timeframes,
        "default_tf": "intraday",
        "max_holdings": MAX_HOLDINGS,
        "owner": str(username).strip().lower(),
        "errors": errors,
        "note": "持仓列表与板块成分共用行情通道 · 云端同步 · 红涨绿跌",
        "style": {"up": "red", "down": "green"},
    }
