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
                out[sym] = {
                    "symbol": sym,
                    "price": round(price, 2) if price is not None else None,
                    "change": round(change, 4) if change is not None else None,
                    "change_pct": round(change_pct, 3)
                    if change_pct is not None
                    else None,
                    "source": "cnbc",
                }
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
                resp = await client.get(
                    url,
                    timeout=18.0,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/json",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Origin": "https://finance.yahoo.com",
                        "Referer": "https://finance.yahoo.com/",
                    },
                )
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
                out[sym] = {
                    "symbol": sym,
                    "price": round(float(price), 2) if price is not None else None,
                    "change": round(float(change), 4) if change is not None else None,
                    "change_pct": round(float(change_pct), 3)
                    if change_pct is not None
                    else None,
                    "source": "yahoo",
                }
            except Exception:  # noqa: BLE001
                return

    await asyncio.gather(*[one(s.upper().strip()) for s in symbols if s])
    return out


async def fetch_day_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """CNBC first, then Yahoo for any remaining symbols."""
    async with httpx.AsyncClient(follow_redirects=True, trust_env=False) as client:
        quotes = await fetch_cnbc_quotes(client, symbols)
        missing = [s for s in symbols if s.upper().strip() not in quotes]
        if missing:
            yahoo = await fetch_yahoo_light_quotes(client, missing, concurrency=3)
            quotes.update(yahoo)
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
        # Stamp onto the active trading day (04:00 ET cycle), NOT calendar
        # "today". After midnight ET the Nasdaq tape is still yesterday's
        # 盘前…盘后; using date.today() pushes every point into tomorrow and
        # the desk session filter then drops the entire series.
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
            step = max(1, len(points) // max_points)
            trimmed = points[::step]
            if trimmed[-1] is not points[-1]:
                trimmed.append(points[-1])
            points = trimmed[:max_points]
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
