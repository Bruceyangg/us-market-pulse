"""Resolve holding/search queries: local catalog + Yahoo US market search."""

from __future__ import annotations

import re
import time
from functools import lru_cache
from typing import Any

import httpx

from us_market_pulse.market_map import MARKET_MAP
from us_market_pulse.sectors import SECTOR_ETFS, VALUE_CHAIN

_SYMBOL_RE = re.compile(r"^[A-Za-z0-9.\-^]{1,12}$")
_WS_RE = re.compile(r"[\s\-_/·•]+")
_YAHOO_SEARCH_CACHE: dict[str, dict[str, Any]] = {}
_YAHOO_SEARCH_TTL = 600.0

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


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
    if key not in index:
        index[key] = {"symbol": symbol, "name": name or symbol}


def looks_like_us_ticker(text: str) -> bool:
    """True for ticker-shaped tokens (AAPL, BRK.B) — not long English words."""
    upper = str(text or "").strip().upper()
    if not upper or not _SYMBOL_RE.match(upper):
        return False
    if "^" in upper or upper.startswith("="):
        return False
    # Common US equity/ETF tickers are short; longer alpha-only tokens are names.
    if len(upper) > 5 and "." not in upper and not any(ch.isdigit() for ch in upper):
        return False
    return True


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
        "星巴克": ("SBUX", "星巴克"),
        "starbucks": ("SBUX", "星巴克"),
        "可口可乐": ("KO", "可口可乐"),
        "coca-cola": ("KO", "可口可乐"),
        "可口": ("KO", "可口可乐"),
        "百事": ("PEP", "百事"),
        "迪士尼": ("DIS", "迪士尼"),
        "disney": ("DIS", "迪士尼"),
    }
    for alias, (sym, name) in extras.items():
        _add_alias(index, alias, sym, name)

    return index


def _yahoo_headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/",
    }


def _row(
    symbol: str,
    name: str,
    *,
    source: str = "local",
    exchange: str = "",
) -> dict[str, str]:
    sym = str(symbol or "").upper()
    nm = str(name or sym)
    out = {
        "symbol": sym,
        "name": nm,
        "label": f"{nm} · {sym}",
        "source": source,
    }
    if exchange:
        out["exchange"] = exchange
    return out


async def yahoo_search_us_quotes(
    query: str,
    *,
    limit: int = 8,
) -> list[dict[str, str]]:
    """Yahoo finance search — full US equity/ETF universe (not just desk catalog)."""
    q = (query or "").strip()
    if not q:
        return []
    cache_key = f"{q.casefold()}|{limit}"
    hit = _YAHOO_SEARCH_CACHE.get(cache_key)
    if (
        isinstance(hit, dict)
        and time.time() - float(hit.get("at") or 0) < _YAHOO_SEARCH_TTL
        and isinstance(hit.get("rows"), list)
    ):
        return [dict(r) for r in hit["rows"][:limit]]

    url = "https://query1.finance.yahoo.com/v1/finance/search"
    params = {
        "q": q,
        "lang": "en-US",
        "region": "US",
        "quotesCount": str(max(limit, 12)),
        "newsCount": "0",
        "listsCount": "0",
        "enableFuzzyQuery": "true",
        "quotesQueryId": "tss_match_phrase_query",
    }
    payload: dict[str, Any] = {}
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            trust_env=False,
            timeout=httpx.Timeout(8.0, connect=3.0),
        ) as client:
            resp = await client.get(url, params=params, headers=_yahoo_headers())
            if resp.status_code in {403, 429}:
                alt = url.replace("://query1.", "://query2.")
                resp = await client.get(alt, params=params, headers=_yahoo_headers())
            if resp.status_code >= 400:
                return []
            payload = resp.json() or {}
    except Exception:  # noqa: BLE001
        return []

    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in payload.get("quotes") or []:
        if not isinstance(row, dict):
            continue
        qtype = str(row.get("quoteType") or "").upper()
        if qtype not in {"EQUITY", "ETF", "MUTUALFUND"}:
            continue
        sym = str(row.get("symbol") or "").upper().strip()
        if not sym or "^" in sym or "=" in sym or sym in seen:
            continue
        # Prefer US-listed style tickers / ADRs.
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", sym):
            continue
        exch = str(row.get("exchDisp") or row.get("exchange") or "")
        # Soft prefer US venues when Yahoo returns many international hits.
        exch_u = exch.upper()
        if exch_u and not any(
            token in exch_u
            for token in ("NYSE", "NASDAQ", "AMEX", "NYQ", "NMS", "NGM", "PCX", "BATS", "CBOE", "OTC")
        ):
            # Keep plain short US-looking tickers even if exchDisp is empty/odd.
            if len(sym) > 5 or "." in sym:
                continue
        name = str(row.get("shortname") or row.get("longname") or sym)
        seen.add(sym)
        out.append(_row(sym, name, source="yahoo", exchange=exch))
        if len(out) >= limit:
            break

    _YAHOO_SEARCH_CACHE[cache_key] = {"at": time.time(), "rows": out}
    return [dict(r) for r in out]


def resolve_holding_query(raw: str) -> dict[str, str] | None:
    """
    Sync local resolve (catalog / Chinese aliases).
    For full-market Yahoo resolution use `resolve_market_query`.
    """
    text = str(raw or "").strip()
    if not text:
        return None

    index = _build_index()
    key = _norm_key(text)

    exact = index.get(key)
    if exact:
        return _row(exact["symbol"], exact["name"], source="local")

    upper = text.upper()
    if looks_like_us_ticker(upper):
        hit = index.get(_norm_key(upper))
        return _row(upper, (hit or {}).get("name") or upper, source="local")

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
    return _row(best["symbol"], best["name"], source="local")


async def resolve_market_query(raw: str) -> dict[str, str] | None:
    """Local catalog first, then Yahoo US search for any listed equity/ETF."""
    text = str(raw or "").strip()
    if not text:
        return None

    index = _build_index()
    key = _norm_key(text)
    if key in index:
        row = index[key]
        return _row(row["symbol"], row["name"], source="local")

    # Ticker-shaped input → confirm on Yahoo (full US tape).
    if looks_like_us_ticker(text):
        upper = text.upper()
        yrows = await yahoo_search_us_quotes(upper, limit=10)
        exact = next((r for r in yrows if r.get("symbol") == upper), None)
        if exact:
            return exact
        if yrows and str(yrows[0].get("symbol") or "").startswith(upper):
            return yrows[0]
        # Allow short unknown tickers through; chart path will validate.
        if len(upper) <= 5:
            return _row(upper, upper, source="ticker")
        return None

    # Company name / Chinese alias fuzzy → Yahoo, then local contains match.
    yrows = await yahoo_search_us_quotes(text, limit=8)
    if yrows:
        return yrows[0]
    return resolve_holding_query(text)


def suggest_holdings(raw: str, *, limit: int = 8) -> list[dict[str, str]]:
    """Sync local autocomplete (catalog only)."""
    text = str(raw or "").strip()
    if not text:
        return []
    key = _norm_key(text)
    upper = text.upper()
    seen: set[str] = set()
    out: list[dict[str, str]] = []

    def push(symbol: str, name: str) -> None:
        if symbol in seen:
            return
        seen.add(symbol)
        out.append(_row(symbol, name, source="local"))

    scored: list[tuple[int, str, str]] = []
    for alias, row in _build_index().items():
        symbol = row["symbol"]
        name = row["name"]
        if looks_like_us_ticker(upper) and symbol.startswith(upper):
            scored.append((0, symbol, name))
        elif alias.startswith(key):
            scored.append((1, symbol, name))
        elif key in alias:
            scored.append((2 + len(alias), symbol, name))

    scored.sort(key=lambda x: (x[0], x[1]))
    for _score, symbol, name in scored:
        push(symbol, name)
        if len(out) >= limit:
            break
    return out


async def suggest_market_holdings(raw: str, *, limit: int = 8) -> list[dict[str, str]]:
    """Local suggestions + Yahoo US market search merged."""
    local = suggest_holdings(raw, limit=limit)
    yrows = await yahoo_search_us_quotes(raw, limit=limit)
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for row in local + yrows:
        sym = str(row.get("symbol") or "").upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(row)
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
        rows.append(_row(sym, row["name"], source="local"))
        if len(rows) >= limit:
            break
    rows.sort(key=lambda r: r["symbol"])
    return rows
