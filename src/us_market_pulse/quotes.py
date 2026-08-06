"""Lightweight multi-source day quotes (CNBC batch primary, Yahoo fallback)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_ET = ZoneInfo("America/New_York")
_NUM_RE = re.compile(r"[^0-9+\-.]")
# Nasdaq intraday z.dateTime like "4:00 AM ET" / "7:59 PM ET"
_NASDAQ_TIME_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*(AM|PM)\s*ET\s*$", re.I)

# List quote fields for 收盘 / 实时 dual row (holdings + sectors)
LIST_QUOTE_RT_KEYS = (
    "rt_price",
    "rt_change",
    "rt_change_pct",
    "session",
    "session_label",
)

_CNBC_SESSION_MAP = {
    "PRE_MKT": ("pre", "盘前"),
    "PREMARKET": ("pre", "盘前"),
    "PRE": ("pre", "盘前"),
    "REG_MKT": ("regular", "盘中"),
    "REGULAR": ("regular", "盘中"),
    "OPEN": ("regular", "盘中"),
    "POST_MKT": ("post", "盘后"),
    "AFTER_HOURS": ("post", "盘后"),
    "AFTERHOURS": ("post", "盘后"),
    "POSTMARKET": ("post", "盘后"),
    "POST": ("post", "盘后"),
}


def _parse_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"—", "-", "N/A", "n/a"}:
        return None
    text = text.replace(",", "").replace("%", "").replace("+", "")
    text = _NUM_RE.sub("", text)
    if not text or text in {"+", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_pct(value: Any) -> float | None:
    return _parse_number(value)


_SESSION_LABELS = {
    "night": "夜盘",
    "pre": "盘前",
    "regular": "盘中",
    "post": "盘后",
}


def session_from_clock() -> tuple[str, str]:
    """ET clock → (session_id, 中文标签). Weekend counts as 夜盘."""
    now = datetime.now(tz=_ET)
    mins = now.hour * 60 + now.minute
    if now.weekday() >= 5:
        return "night", "夜盘"
    if mins >= 20 * 60 or mins < 4 * 60:
        return "night", "夜盘"
    if mins < 9 * 60 + 30:
        return "pre", "盘前"
    if mins < 16 * 60:
        return "regular", "盘中"
    return "post", "盘后"


def session_from_status(status: str | None = None) -> tuple[str, str]:
    """Map vendor market status / ET clock → (session_id, 中文标签)."""
    key = str(status or "").upper().strip().replace(" ", "_")
    if key in _CNBC_SESSION_MAP:
        return _CNBC_SESSION_MAP[key]
    return session_from_clock()


def resolve_list_session(
    status: str | None = None,
) -> tuple[str, str]:
    """List badge session: clock wins at 夜盘 so vendors don't stick on 盘后."""
    clock_sid, clock_label = session_from_clock()
    if clock_sid == "night":
        return clock_sid, clock_label
    key = str(status or "").upper().strip().replace(" ", "_")
    if key in _CNBC_SESSION_MAP:
        return _CNBC_SESSION_MAP[key]
    return clock_sid, clock_label


def _change_vs_basis(
    price: float | None, basis: float | None
) -> tuple[float | None, float | None]:
    if price is None or basis in (None, 0):
        return None, None
    try:
        px = float(price)
        base = float(basis)
    except (TypeError, ValueError):
        return None, None
    if base == 0:
        return None, None
    chg = px - base
    return chg, (chg / base) * 100.0


def _point_price(point: dict[str, Any] | None) -> float | None:
    if not isinstance(point, dict):
        return None
    for key in ("v", "c", "price"):
        val = _parse_number(point.get(key))
        if val is not None:
            return val
    return None


def derive_list_realtime(
    *,
    session: str,
    day_price: float | None = None,
    day_change: float | None = None,
    day_change_pct: float | None = None,
    previous_close: float | None = None,
    rt_price: float | None = None,
    rt_change: float | None = None,
    rt_change_pct: float | None = None,
    tape_points: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Dual-row 实时 fields by session.

    - 盘中: same as day quote
    - 盘前: last pre print vs previous close
    - 盘后/夜盘: last post print vs regular close (not full-day % vs prev close)
    - 夜盘 has no free overnight tape — freeze last 盘后; never invent ticks
    """
    sid = session if session in _SESSION_LABELS else "regular"
    pts = [p for p in (tape_points or []) if isinstance(p, dict)]
    pre_pts = [p for p in pts if p.get("session") == "pre"]
    reg_pts = [p for p in pts if p.get("session") == "regular"]
    post_pts = [p for p in pts if p.get("session") == "post"]

    regular_close = _point_price(reg_pts[-1]) if reg_pts else None
    if regular_close is None and sid in {"post", "night", "regular"}:
        regular_close = _parse_number(day_price)

    out_price = _parse_number(rt_price)
    out_change = _parse_number(rt_change)
    out_pct = _parse_pct(rt_change_pct)

    if sid == "regular":
        if out_price is None:
            out_price = _parse_number(day_price)
            if out_price is None and pts:
                out_price = _point_price(pts[-1])
        if out_change is None:
            out_change = _parse_number(day_change)
        if out_pct is None:
            out_pct = _parse_pct(day_change_pct)
        if out_pct is None:
            out_change, out_pct = _change_vs_basis(out_price, previous_close)
    elif sid == "pre":
        if out_price is None and pre_pts:
            out_price = _point_price(pre_pts[-1])
        if out_price is not None and (out_pct is None or out_change is None):
            chg, pct = _change_vs_basis(out_price, previous_close)
            if out_change is None:
                out_change = chg
            if out_pct is None:
                out_pct = pct
    elif sid == "post":
        if out_price is None and post_pts:
            out_price = _point_price(post_pts[-1])
        if out_price is not None and (out_pct is None or out_change is None):
            basis = regular_close if regular_close not in (None, 0) else previous_close
            chg, pct = _change_vs_basis(out_price, basis)
            if out_change is None:
                out_change = chg
            if out_pct is None:
                out_pct = pct
    else:  # night — Yahoo overnight is quote-only; never reuse 盘后 tape as 夜盘
        if out_price is not None and (out_pct is None or out_change is None):
            basis = regular_close if regular_close not in (None, 0) else previous_close
            if basis is None:
                basis = _parse_number(day_price)
            chg, pct = _change_vs_basis(out_price, basis)
            if out_change is None:
                out_change = chg
            if out_pct is None:
                out_pct = pct
        # Drop fake clones of the day line when Yahoo overnight is unavailable.
        if (
            out_price is not None
            and day_price is not None
            and abs(float(out_price) - float(day_price)) < 1e-6
            and out_pct is not None
            and day_change_pct is not None
            and abs(float(out_pct) - float(day_change_pct)) < 1e-6
        ):
            out_price = out_change = out_pct = None

    result: dict[str, Any] = {}
    if out_price is not None:
        result["rt_price"] = round(float(out_price), 2)
    if out_change is not None:
        result["rt_change"] = round(float(out_change), 4)
    if out_pct is not None:
        result["rt_change_pct"] = round(float(out_pct), 3)
    return result


def _yahoo_chart_headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/",
    }


def _yahoo_meta_extended(
    meta: dict[str, Any], *, session: str
) -> dict[str, Any] | None:
    """Map Yahoo chart/quote meta → extended tape fields for list RT."""
    if not isinstance(meta, dict):
        return None
    if session == "pre":
        px = _parse_number(meta.get("preMarketPrice"))
        if px is None:
            return None
        return {
            "last": px,
            "change": meta.get("preMarketChange"),
            "change_pct": meta.get("preMarketChangePercent"),
            "type": "PRE_MKT",
        }
    # post + night both use postMarket* on Yahoo; night/PREPRE is quote-only.
    px = _parse_number(meta.get("postMarketPrice"))
    if px is None:
        return None
    return {
        "last": px,
        "change": meta.get("postMarketChange"),
        "change_pct": meta.get("postMarketChangePercent"),
        "type": "AFTER_HOURS" if session == "post" else None,
    }


# Yahoo quote page shows Overnight as a numeric box (no tape), e.g.
#   220.29 +1.07 (+0.49%)
#   Overnight: 10:44:05 PM EDT
_YAHOO_OVERNIGHT_RE = re.compile(
    r"(?P<price>\d+(?:\.\d+)?)\s+"
    r"(?P<change>[+\-]?\d+(?:\.\d+)?)\s+"
    r"\((?P<pct>[+\-]?\d+(?:\.\d+)?)%\)\s*"
    r"(?:Overnight|夜盘)\s*:",
    re.I,
)
_YAHOO_CLOSE_RE = re.compile(
    r"(?P<price>\d+(?:\.\d+)?)\s+"
    r"(?P<change>[+\-]?\d+(?:\.\d+)?)\s+"
    r"\((?P<pct>[+\-]?\d+(?:\.\d+)?)%\)\s*"
    r"(?:At close|收盘)",
    re.I,
)
_YAHOO_JSON_RAW_RE = re.compile(
    r'"(?P<key>overnightMarketPrice|overnightMarketChange|'
    r'overnightMarketChangePercent|regularMarketPrice|'
    r'regularMarketChange|regularMarketChangePercent)"\s*:\s*'
    r'(?:\{[^}]*?"raw"\s*:\s*(?P<raw>-?\d+(?:\.\d+)?)[^}]*?\}|(?P<num>-?\d+(?:\.\d+)?))',
    re.I,
)


def _overnight_from_yahoo_html(html: str) -> dict[str, float | None] | None:
    if not html:
        return None
    text = (
        html.replace("\u2212", "-")
        .replace("&nbsp;", " ")
        .replace("\xa0", " ")
    )
    overnight_px = overnight_chg = overnight_pct = None
    close_px = close_chg = close_pct = None

    # Structured quoteSummary / Store blobs (preferred when present).
    blob: dict[str, float] = {}
    for m in _YAHOO_JSON_RAW_RE.finditer(text):
        key = m.group("key")
        raw = m.group("raw") if m.group("raw") is not None else m.group("num")
        num = _parse_number(raw)
        if num is not None and key not in blob:
            blob[key] = num
    if "overnightMarketPrice" in blob:
        overnight_px = blob.get("overnightMarketPrice")
        overnight_chg = blob.get("overnightMarketChange")
        overnight_pct = blob.get("overnightMarketChangePercent")
        # Yahoo sometimes stores percent as fraction (0.0049).
        if overnight_pct is not None and abs(overnight_pct) < 1:
            overnight_pct *= 100.0
        close_px = blob.get("regularMarketPrice")
        close_chg = blob.get("regularMarketChange")
        close_pct = blob.get("regularMarketChangePercent")
        if close_pct is not None and abs(close_pct) < 1:
            close_pct *= 100.0

    if overnight_px is None:
        m_on = _YAHOO_OVERNIGHT_RE.search(text)
        if not m_on:
            return None
        overnight_px = _parse_number(m_on.group("price"))
        overnight_chg = _parse_number(m_on.group("change"))
        overnight_pct = _parse_pct(m_on.group("pct"))
        m_close = _YAHOO_CLOSE_RE.search(text)
        if m_close:
            close_px = _parse_number(m_close.group("price"))
            close_chg = _parse_number(m_close.group("change"))
            close_pct = _parse_pct(m_close.group("pct"))

    if overnight_px is None:
        return None
    if overnight_pct is None and close_px not in (None, 0):
        overnight_chg, overnight_pct = _change_vs_basis(overnight_px, close_px)
    return {
        "rt_price": overnight_px,
        "rt_change": overnight_chg,
        "rt_change_pct": overnight_pct,
        "price": close_px,
        "change": close_chg,
        "change_pct": close_pct,
    }


async def fetch_yahoo_overnight_quote(
    client: httpx.AsyncClient,
    symbol: str,
    *,
    allow_page: bool = True,
    page_timeout: float = 6.0,
    chart_timeout: float = 3.5,
) -> dict[str, Any] | None:
    """
    Yahoo overnight is numeric only (no 夜盘 tape).

    Only accept true Overnight fields (page box / overnightMarket*).
    Never reuse postMarket* — that is 盘后 and mismatches Yahoo Overnight.
    Page scrape is optional: batch list loads should keep allow_page=False.
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return None
    enc = quote(sym, safe="")
    headers = {
        **_yahoo_chart_headers(),
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    }
    overnight_px = overnight_chg = overnight_pct = None
    price = change = change_pct = prev = None
    market_state = None

    # Quote page — source of truth for Yahoo "Overnight" numbers (selected only).
    if allow_page:
        page_urls = (
            f"https://finance.yahoo.com/quote/{enc}/",
            f"https://finance.yahoo.com/quote/{enc}",
        )
        for page_url in page_urls:
            try:
                page = await client.get(
                    page_url, timeout=page_timeout, headers=headers
                )
                if page.status_code >= 400 or not page.text:
                    continue
                parsed = _overnight_from_yahoo_html(page.text)
                if not parsed:
                    continue
                overnight_px = parsed.get("rt_price")
                overnight_chg = parsed.get("rt_change")
                overnight_pct = parsed.get("rt_change_pct")
                price = parsed.get("price")
                change = parsed.get("change")
                change_pct = parsed.get("change_pct")
                if overnight_px is not None:
                    break
            except Exception:  # noqa: BLE001
                continue

    # Chart meta: close/prev + rare overnightMarket* (never postMarket*).
    if overnight_px is None or price is None or prev is None:
        for host in ("query1", "query2"):
            url = (
                f"https://{host}.finance.yahoo.com/v8/finance/chart/{enc}"
                f"?range=1d&interval=1m&includePrePost=false"
            )
            try:
                resp = await client.get(
                    url, timeout=chart_timeout, headers=_yahoo_chart_headers()
                )
                if resp.status_code >= 400:
                    continue
                result = ((resp.json().get("chart") or {}).get("result") or [None])[0]
                if not result:
                    continue
                meta = result.get("meta") or {}
                market_state = meta.get("marketState")
                price = price or _parse_number(meta.get("regularMarketPrice"))
                prev = prev or _parse_number(
                    meta.get("chartPreviousClose") or meta.get("previousClose")
                )
                change = change or _parse_number(meta.get("regularMarketChange"))
                change_pct = change_pct or _parse_pct(
                    meta.get("regularMarketChangePercent")
                )
                if overnight_px is None:
                    overnight_px = _parse_number(meta.get("overnightMarketPrice"))
                    overnight_chg = _parse_number(meta.get("overnightMarketChange"))
                    overnight_pct = _parse_pct(
                        meta.get("overnightMarketChangePercent")
                    )
                    if overnight_px is not None and overnight_pct is None:
                        basis = price if price not in (None, 0) else prev
                        overnight_chg, overnight_pct = _change_vs_basis(
                            overnight_px, basis
                        )
                break
            except Exception:  # noqa: BLE001
                continue

    if change_pct is None and price is not None and prev not in (None, 0):
        change, change_pct = _change_vs_basis(price, prev)
    if overnight_px is None:
        return None
    out: dict[str, Any] = {
        "symbol": sym,
        "price": round(float(price), 2) if price is not None else None,
        "change": round(float(change), 4) if change is not None else None,
        "change_pct": round(float(change_pct), 3) if change_pct is not None else None,
        "previous_close": round(float(prev), 6) if prev not in (None, 0) else None,
        "source": "yahoo",
        "session": "night",
        "session_label": "夜盘",
        "market_state": market_state,
        "rt_price": round(float(overnight_px), 2),
    }
    if overnight_chg is not None:
        out["rt_change"] = round(float(overnight_chg), 4)
    if overnight_pct is not None:
        out["rt_change_pct"] = round(float(overnight_pct), 3)
    return out


def _stamp_night_session(quotes: dict[str, dict[str, Any]]) -> None:
    """Force 夜盘 badge and drop leftover 盘后 RT when Yahoo Overnight is absent."""
    for sym, row in list(quotes.items()):
        if not isinstance(row, dict):
            continue
        base = dict(row)
        base["session"] = "night"
        base["session_label"] = "夜盘"
        # Keep only explicit Yahoo overnight stamps (source yahoo + rt_*).
        if base.get("source") != "yahoo" or base.get("rt_price") is None:
            base.pop("rt_price", None)
            base.pop("rt_change", None)
            base.pop("rt_change_pct", None)
        quotes[sym] = base


async def overlay_yahoo_overnight_quotes(
    client: httpx.AsyncClient,
    quotes: dict[str, dict[str, Any]],
    symbols: list[str],
    *,
    concurrency: int = 3,
    limit: int | None = 2,
    deadline_s: float = 5.0,
    allow_page: bool = True,
) -> dict[str, dict[str, Any]]:
    """Stamp Yahoo Overnight onto a small priority set (never block the desk)."""
    import asyncio

    sem = asyncio.Semaphore(max(1, concurrency))
    uniq: list[str] = []
    seen: set[str] = set()
    for raw in symbols:
        sym = str(raw or "").upper().strip()
        if sym and sym not in seen:
            seen.add(sym)
            uniq.append(sym)
    if limit is not None:
        uniq = uniq[: max(0, int(limit))]

    async def one(sym: str) -> None:
        async with sem:
            row = await fetch_yahoo_overnight_quote(
                client,
                sym,
                allow_page=allow_page,
                page_timeout=min(6.0, max(2.0, deadline_s)),
                chart_timeout=min(3.5, max(1.5, deadline_s / 2)),
            )
            base = dict(quotes.get(sym) or {})
            base["session"] = "night"
            base["session_label"] = "夜盘"
            if not row or row.get("rt_price") is None:
                base.pop("rt_price", None)
                base.pop("rt_change", None)
                base.pop("rt_change_pct", None)
                quotes[sym] = base
                return
            if base.get("price") is None and row.get("price") is not None:
                base["price"] = row["price"]
                base["change"] = row.get("change")
                base["change_pct"] = row.get("change_pct")
                base["previous_close"] = row.get("previous_close")
            for key in ("rt_price", "rt_change", "rt_change_pct"):
                if row.get(key) is not None:
                    base[key] = row[key]
            base["source"] = "yahoo"
            quotes[sym] = base

    if not uniq:
        return quotes
    try:
        await asyncio.wait_for(
            asyncio.gather(*(one(s) for s in uniq)),
            timeout=max(1.0, float(deadline_s)),
        )
    except asyncio.TimeoutError:
        pass
    return quotes


def apply_list_quote_fields(
    row: dict[str, Any], quote: dict[str, Any] | None
) -> dict[str, Any]:
    """Copy 收盘 + 实时 list fields from a day quote onto a pick/holding card."""
    if not isinstance(row, dict) or not isinstance(quote, dict):
        return row
    for key in ("price", "change", "change_pct", "as_of", "previous_close"):
        if quote.get(key) is not None:
            row[key] = quote[key]
    for key in ("session", "session_label"):
        if quote.get(key) is not None:
            row[key] = quote[key]
    night = str(quote.get("session") or row.get("session") or "") == "night"
    has_night_rt = any(quote.get(k) is not None for k in ("rt_price", "rt_change", "rt_change_pct"))
    for key in ("rt_price", "rt_change", "rt_change_pct"):
        if quote.get(key) is not None:
            row[key] = quote[key]
        elif night and not has_night_rt:
            # Propagate "no Yahoo Overnight" so cards never keep CNBC 盘后 %.
            row.pop(key, None)
    return row


def _with_session_and_realtime(
    base: dict[str, Any],
    *,
    curmktstatus: str | None = None,
    extended: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach session badge + realtime (pre/post/night) quote onto a day-quote row."""
    status = curmktstatus
    if isinstance(extended, dict) and extended.get("type"):
        status = str(extended.get("type") or status or "")
    sid, label = resolve_list_session(status)
    base["session"] = sid
    base["session_label"] = label

    # CNBC ExtendedMktQuote is 盘前/盘后 only — never treat POST_MKT as Yahoo 夜盘.
    use_extended = isinstance(extended, dict) and sid in {"pre", "post"}
    rt_price = _parse_number(extended.get("last")) if use_extended else None
    rt_change = _parse_number(extended.get("change")) if use_extended else None
    rt_pct = _parse_pct(extended.get("change_pct")) if use_extended else None

    # Normalize extended % to the session basis so vendors never leak full-day %.
    if rt_price is not None:
        if sid == "pre":
            chg, pct = _change_vs_basis(rt_price, base.get("previous_close"))
        elif sid == "post":
            chg, pct = _change_vs_basis(rt_price, base.get("price"))
        else:
            chg, pct = None, None
        if chg is not None:
            rt_change = chg
        if pct is not None:
            rt_pct = pct

    rt_fields = derive_list_realtime(
        session=sid,
        day_price=base.get("price"),
        day_change=base.get("change"),
        day_change_pct=base.get("change_pct"),
        previous_close=base.get("previous_close"),
        rt_price=rt_price,
        rt_change=rt_change,
        rt_change_pct=rt_pct,
    )
    # Explicitly drop stale rt_* when night has no Yahoo overnight yet.
    if sid == "night":
        for key in ("rt_price", "rt_change", "rt_change_pct"):
            if key not in rt_fields:
                base.pop(key, None)
    base.update(rt_fields)
    return base


async def fetch_cnbc_quotes(
    client: httpx.AsyncClient, symbols: list[str]
) -> dict[str, dict[str, Any]]:
    """Batch day quotes from CNBC (works when Yahoo returns 403/429)."""
    out: dict[str, dict[str, Any]] = {}
    uniq = []
    seen: set[str] = set()
    for raw in symbols:
        sym = str(raw or "").upper().strip()
        if sym and sym not in seen:
            seen.add(sym)
            uniq.append(sym)
    if not uniq:
        return out

    # CNBC accepts pipe-joined symbols; keep batches modest.
    chunk_size = 60
    for i in range(0, len(uniq), chunk_size):
        chunk = uniq[i : i + chunk_size]
        joined = "|".join(chunk)
        url = (
            "https://quote.cnbc.com/quote-html-webservice/restQuote/"
            "symbolType/symbol"
            f"?symbols={quote(joined, safe='')}"
            "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1"
        )
        try:
            resp = await client.get(
                url,
                timeout=25.0,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json,text/plain,*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.cnbc.com/",
                    "Origin": "https://www.cnbc.com",
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            rows = (
                (payload.get("FormattedQuoteResult") or {}).get("FormattedQuote") or []
            )
            if isinstance(rows, dict):
                rows = [rows]
            for row in rows:
                if not isinstance(row, dict):
                    continue
                # code 0 / missing = ok; anything else is unknown symbol
                if row.get("code") not in (0, "0", None):
                    continue
                sym = str(row.get("symbol") or "").upper().strip()
                if not sym:
                    continue
                price = _parse_number(row.get("last"))
                change = _parse_number(row.get("change"))
                change_pct = _parse_pct(row.get("change_pct"))
                prev = _parse_number(row.get("previous_day_closing"))
                if change_pct is None and price is not None and prev not in (None, 0):
                    change = price - prev
                    change_pct = (change / prev) * 100.0
                if price is None and change_pct is None:
                    continue
                quote_row = {
                    "symbol": sym,
                    "price": round(price, 2) if price is not None else None,
                    "change": round(change, 4) if change is not None else None,
                    "change_pct": round(change_pct, 3)
                    if change_pct is not None
                    else None,
                    "previous_close": round(float(prev), 6)
                    if prev not in (None, 0)
                    else None,
                    "source": "cnbc",
                }
                ext = row.get("ExtendedMktQuote")
                if not isinstance(ext, dict):
                    ext = None
                out[sym] = _with_session_and_realtime(
                    quote_row,
                    curmktstatus=str(row.get("curmktstatus") or "") or None,
                    extended=ext,
                )
        except Exception:  # noqa: BLE001
            continue
    return out


async def fetch_yahoo_light_quotes(
    client: httpx.AsyncClient, symbols: list[str], *, concurrency: int = 4
) -> dict[str, dict[str, Any]]:
    """Per-symbol Yahoo chart fallback (rate-limit friendly)."""
    import asyncio

    out: dict[str, dict[str, Any]] = {}
    sem = asyncio.Semaphore(max(1, concurrency))

    async def one(sym: str) -> None:
        async with sem:
            enc = quote(sym, safe="")
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}"
                f"?range=5d&interval=1d&includePrePost=false"
            )
            try:
                headers = {
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Origin": "https://finance.yahoo.com",
                    "Referer": "https://finance.yahoo.com/",
                }
                resp = await client.get(url, timeout=18.0, headers=headers)
                if resp.status_code in {403, 429}:
                    alt = url.replace("://query1.", "://query2.")
                    if alt != url:
                        resp2 = await client.get(alt, timeout=18.0, headers=headers)
                        if resp2.status_code < 400:
                            resp = resp2
                if resp.status_code >= 400:
                    return
                result = ((resp.json().get("chart") or {}).get("result") or [None])[0]
                if not result:
                    return
                meta = result.get("meta") or {}
                price = meta.get("regularMarketPrice")
                prev = meta.get("chartPreviousClose") or meta.get("previousClose")
                change_pct = meta.get("regularMarketChangePercent")
                change = meta.get("regularMarketChange")
                if change_pct is None and price is not None and prev not in (None, 0):
                    change = float(price) - float(prev)
                    change_pct = (change / float(prev)) * 100.0
                if price is None and change_pct is None:
                    return
                quote_row = {
                    "symbol": sym,
                    "price": round(float(price), 2) if price is not None else None,
                    "change": round(float(change), 4) if change is not None else None,
                    "change_pct": round(float(change_pct), 3)
                    if change_pct is not None
                    else None,
                    "previous_close": round(float(prev), 6)
                    if prev not in (None, 0)
                    else None,
                    "source": "yahoo",
                }
                clock_sid, _ = session_from_clock()
                extended = _yahoo_meta_extended(meta, session=clock_sid)
                out[sym] = _with_session_and_realtime(
                    quote_row, extended=extended
                )
            except Exception:  # noqa: BLE001
                return

    await asyncio.gather(*[one(s.upper().strip()) for s in symbols if s])
    return out


async def fetch_day_quotes(
    symbols: list[str],
    *,
    overnight_priority: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """CNBC first, Yahoo fallback; at 夜盘 stamp session + best-effort Overnight.

    Full Yahoo page scrapes are limited to overnight_priority (selected / top
    holdings). Batch lists must stay fast — never scrape every constituent.
    """
    async with httpx.AsyncClient(follow_redirects=True, trust_env=False) as client:
        quotes = await fetch_cnbc_quotes(client, symbols)
        missing = [s for s in symbols if s.upper().strip() not in quotes]
        if missing:
            yahoo = await fetch_yahoo_light_quotes(client, missing, concurrency=3)
            quotes.update(yahoo)
        if session_from_clock()[0] == "night":
            _stamp_night_session(quotes)
            # None → try first symbols; [] → skip page scrapes (ETF strip).
            candidates = (
                list(symbols or [])
                if overnight_priority is None
                else list(overnight_priority)
            )
            pri: list[str] = []
            seen: set[str] = set()
            for raw in candidates:
                sym = str(raw or "").upper().strip()
                if sym and sym not in seen and sym in quotes:
                    seen.add(sym)
                    pri.append(sym)
            # At most 2 page scrapes so sector/holdings desks stay under ~5s.
            if pri:
                await overlay_yahoo_overnight_quotes(
                    client,
                    quotes,
                    pri,
                    concurrency=2,
                    limit=2,
                    deadline_s=5.0,
                    allow_page=True,
                )
                _stamp_night_session(quotes)
        return quotes


def _nasdaq_path_symbol(symbol: str) -> str:
    """Nasdaq API uses BRK/B style for dotted tickers."""
    sym = (symbol or "").strip().upper()
    if not sym:
        return ""
    return sym.replace(".", "/")


def _parse_pct_text(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("%", "").replace(",", "").replace("+", "")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_nasdaq_intraday_ts(row: dict[str, Any], day: date) -> int | None:
    """
    Nasdaq chart `x` is ~4h behind real ET during EDT; prefer z.dateTime
    ("4:00 AM ET") which matches the exchange tape.
    """
    z = row.get("z") if isinstance(row.get("z"), dict) else {}
    text = str((z or {}).get("dateTime") or "").strip()
    m = _NASDAQ_TIME_RE.match(text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2))
        ampm = m.group(3).upper()
        if ampm == "PM" and hour != 12:
            hour += 12
        elif ampm == "AM" and hour == 12:
            hour = 0
        try:
            return int(
                datetime(
                    day.year, day.month, day.day, hour, minute, tzinfo=_ET
                ).timestamp()
            )
        except ValueError:
            pass
    x = row.get("x")
    try:
        return int(x) // 1000 if x is not None else None
    except (TypeError, ValueError):
        return None


async def fetch_nasdaq_intraday(
    client: httpx.AsyncClient,
    symbol: str,
    *,
    max_points: int = 120,
) -> dict[str, Any] | None:
    """
    Intraday line points from Nasdaq official chart API.
    Works when Yahoo chart returns 403/429. Covers ~4:00–20:00 ET extended hours.
    """
    sym = (symbol or "").strip().upper()
    path_sym = _nasdaq_path_symbol(sym)
    if not path_sym:
        return None
    url = f"https://api.nasdaq.com/api/quote/{quote(path_sym, safe='/')}/chart?assetclass=stocks"
    try:
        resp = await client.get(
            url,
            timeout=18.0,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://www.nasdaq.com",
                "Referer": f"https://www.nasdaq.com/market-activity/stocks/{path_sym.lower()}",
            },
        )
        if resp.status_code >= 400:
            return None
        data = (resp.json() or {}).get("data") or {}
        raw = data.get("chart") or []
        if not isinstance(raw, list) or len(raw) < 2:
            return None
        # Stamp onto the active trading day (盘前 open of the 20:00 cycle),
        # NOT calendar "today". After midnight ET the Nasdaq tape is still
        # the prior session day's 盘前…盘后; using date.today() pushes every
        # point into tomorrow and the desk session filter drops the series.
        try:
            from us_market_pulse.markets import trading_day_et

            day = trading_day_et().date()
        except Exception:  # noqa: BLE001
            now_et = datetime.now(tz=_ET)
            day = (
                now_et.date()
                if (now_et.hour * 60 + now_et.minute) >= 4 * 60
                else (now_et.date() - timedelta(days=1))
            )
        points: list[dict[str, Any]] = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            z = row.get("z") if isinstance(row.get("z"), dict) else {}
            y = row.get("y")
            if y is None:
                y = (z or {}).get("value")
            try:
                price = float(y)
            except (TypeError, ValueError):
                continue
            ts = _parse_nasdaq_intraday_ts(row, day)
            if not ts or price <= 0:
                continue
            points.append({"t": int(ts), "v": round(price, 6)})
        if len(points) < 2:
            return None
        points.sort(key=lambda p: p["t"])
        # Drop duplicate timestamps (keep last)
        dedup: list[dict[str, Any]] = []
        for p in points:
            if dedup and dedup[-1]["t"] == p["t"]:
                dedup[-1] = p
            else:
                dedup.append(p)
        points = dedup
        if len(points) > max_points:
            # Session-aware sample — never truncate the 盘后 tail with [:max].
            from us_market_pulse.markets import sample_session_points

            points = sample_session_points(points, max_points)
        change_pct = _parse_pct_text(data.get("percentageChange"))
        price = _parse_number(data.get("lastSalePrice"))
        if price is None:
            price = points[-1]["v"]
        prev = _parse_number(data.get("previousClose"))
        change = _parse_number(data.get("netChange"))
        if change_pct is None and price is not None and prev not in (None, 0):
            change = float(price) - float(prev)
            change_pct = (change / float(prev)) * 100.0
        return {
            "symbol": sym,
            "points": points,
            "price": round(float(price), 2) if price is not None else None,
            "change": round(float(change), 4) if change is not None else None,
            "change_pct": round(float(change_pct), 3) if change_pct is not None else None,
            "previous_close": round(float(prev), 6) if prev not in (None, 0) else None,
            "source": "nasdaq",
        }
    except Exception:  # noqa: BLE001
        return None


async def fetch_nasdaq_intraday_many(
    symbols: list[str],
    *,
    concurrency: int = 4,
    max_points: int = 96,
) -> dict[str, dict[str, Any]]:
    """Parallel Nasdaq intraday charts for list sparklines."""
    import asyncio

    out: dict[str, dict[str, Any]] = {}
    sem = asyncio.Semaphore(max(1, concurrency))
    uniq = []
    seen: set[str] = set()
    for raw in symbols:
        sym = str(raw or "").upper().strip()
        if sym and sym not in seen:
            seen.add(sym)
            uniq.append(sym)
    if not uniq:
        return out

    async with httpx.AsyncClient(follow_redirects=True, trust_env=False) as client:

        async def one(sym: str) -> None:
            async with sem:
                row = await fetch_nasdaq_intraday(
                    client, sym, max_points=max_points
                )
                if row and row.get("points"):
                    out[sym] = row

        await asyncio.gather(*(one(s) for s in uniq))
    return out


def _nasdaq_headers(path_sym: str) -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.nasdaq.com",
        "Referer": f"https://www.nasdaq.com/market-activity/stocks/{path_sym.lower()}",
    }


def _candle_change(points: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    if len(points) < 2:
        return None, None
    first = float(points[0]["o"] if points[0].get("o") is not None else points[0]["c"])
    last = float(points[-1]["c"])
    if first == 0:
        return round(last - first, 4), None
    return round(last - first, 4), round((last - first) / first * 100.0, 3)


def _aggregate_ohlc_bars(
    bars: list[dict[str, Any]],
    *,
    period: str,
) -> list[dict[str, Any]]:
    """Aggregate daily OHLC into month or quarter candles."""
    if not bars:
        return []
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    order: list[tuple[int, int]] = []
    for bar in bars:
        dt = datetime.fromtimestamp(int(bar["t"]), tz=timezone.utc)
        if period == "quarter":
            key = (dt.year, (dt.month - 1) // 3)
        else:
            key = (dt.year, dt.month)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(bar)

    out: list[dict[str, Any]] = []
    for key in order:
        rows = groups[key]
        if not rows:
            continue
        o = float(rows[0]["o"])
        c = float(rows[-1]["c"])
        h = max(float(r["h"]) for r in rows)
        l = min(float(r["l"]) for r in rows)
        vols = [float(r["v"]) for r in rows if r.get("v") is not None]
        out.append(
            {
                "t": int(rows[0]["t"]),
                "o": round(o, 6),
                "h": round(h, 6),
                "l": round(l, 6),
                "c": round(c, 6),
                "v": round(sum(vols), 2) if vols else None,
            }
        )
    return out


async def fetch_nasdaq_daily_bars(
    client: httpx.AsyncClient,
    symbol: str,
    *,
    fromdate: date | str | None = None,
    todate: date | str | None = None,
) -> list[dict[str, Any]]:
    """
    Daily OHLC from Nasdaq chart API (fromdate/todate).
    Used when Yahoo day/month/quarter charts are blocked (403/429).
    """
    sym = (symbol or "").strip().upper()
    path_sym = _nasdaq_path_symbol(sym)
    if not path_sym:
        return []
    to_d = todate or date.today()
    from_d = fromdate or date(to_d.year - 25, 1, 1)
    url = (
        f"https://api.nasdaq.com/api/quote/{quote(path_sym, safe='/')}/chart"
        f"?assetclass=stocks&fromdate={from_d}&todate={to_d}"
    )
    try:
        resp = await client.get(url, timeout=22.0, headers=_nasdaq_headers(path_sym))
        if resp.status_code >= 400:
            return []
        data = (resp.json() or {}).get("data") or {}
        raw = data.get("chart") or []
        if not isinstance(raw, list) or len(raw) < 2:
            return []
        bars: list[dict[str, Any]] = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            z = row.get("z") if isinstance(row.get("z"), dict) else {}
            close = _parse_number(z.get("close") if z else None)
            if close is None:
                close = _parse_number(row.get("y"))
            if close is None or close <= 0:
                continue
            open_ = _parse_number(z.get("open")) if z else None
            high = _parse_number(z.get("high")) if z else None
            low = _parse_number(z.get("low")) if z else None
            vol = _parse_number(z.get("volume")) if z else None
            if open_ is None:
                open_ = close
            if high is None:
                high = max(open_, close)
            if low is None:
                low = min(open_, close)
            x = row.get("x")
            try:
                ts = int(x) // 1000 if x is not None else 0
            except (TypeError, ValueError):
                ts = 0
            if not ts:
                continue
            bars.append(
                {
                    "t": ts,
                    "o": round(float(open_), 6),
                    "h": round(float(high), 6),
                    "l": round(float(low), 6),
                    "c": round(float(close), 6),
                    "v": round(float(vol), 2) if vol is not None else None,
                }
            )
        return bars
    except Exception:  # noqa: BLE001
        return []


def build_nasdaq_ohlc_series(
    daily_bars: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build day / month / quarter candle series from Nasdaq daily bars."""
    if len(daily_bars) < 2:
        return {}
    day_pts = daily_bars[-560:] if len(daily_bars) > 560 else list(daily_bars)
    month_pts = _aggregate_ohlc_bars(daily_bars, period="month")
    if len(month_pts) > 360:
        month_pts = month_pts[-360:]
    quarter_pts = _aggregate_ohlc_bars(daily_bars, period="quarter")
    if len(quarter_pts) > 200:
        quarter_pts = quarter_pts[-200:]

    out: dict[str, dict[str, Any]] = {}
    specs = (
        (
            "day",
            "日图",
            "近 2 年日 K · MA5/10/30/60/120/250（红涨绿跌）",
            "2y",
            "1d",
            day_pts,
        ),
        (
            "month",
            "月图",
            "历史月 K · MA5/10/30/60/120/250（红涨绿跌）",
            "max",
            "1mo",
            month_pts,
        ),
        (
            "quarter",
            "季图",
            "历史季 K · 均线叠加（红涨绿跌）",
            "max",
            "3mo",
            quarter_pts,
        ),
    )
    for tf_id, label, blurb, range_, interval, points in specs:
        if len(points) < 2:
            continue
        change, change_pct = _candle_change(points)
        out[tf_id] = {
            "tf": tf_id,
            "label": label,
            "blurb": blurb + "（Nasdaq）",
            "range": range_,
            "interval": interval,
            "chart": "candle",
            "points": points,
            "change": change,
            "change_pct": change_pct,
        }
    return out
