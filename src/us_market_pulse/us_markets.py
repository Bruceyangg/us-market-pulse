"""US markets strip + index futures charts for the sectors page.

Yahoo chart endpoints are often 403 from datacenter/residential IPs.
CNBC quote + ts-api bars cover futures (ES/NQ/YM); Yahoo is a fast fallback.
Build always finishes within a hard budget and returns stale/partial data
instead of hanging the sectors page.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote as urlquote
from zoneinfo import ZoneInfo

import httpx

from us_market_pulse.markets import (
    _series_change,
    even_sample_points,
)
from us_market_pulse.quotes import USER_AGENT, _parse_number, _parse_pct
from us_market_pulse.sectors import SECTOR_TIMEFRAMES

_ET = ZoneInfo("America/New_York")
_BJ = ZoneInfo("Asia/Shanghai")

# Yahoo display symbol → CNBC quote / bars symbol.
_CNBC_SYM: dict[str, str] = {
    "ES=F": "@SP.1",
    "NQ=F": "@ND.1",
    "YM=F": "@DJ.1",
    "RTY=F": "@TFS.1",
    "^VIX": ".VIX",
    "GC=F": "@GC.1",
    "CL=F": "@CL.1",
    "BTC-USD": "BTC.CM=",
}

# Yahoo US Markets–style strip.
US_MARKET_STRIP: list[dict[str, str]] = [
    {"id": "es", "symbol": "ES=F", "label": "标普期货", "short": "S&P Fut"},
    {"id": "nq", "symbol": "NQ=F", "label": "纳指期货", "short": "Nasdaq Fut"},
    {"id": "ym", "symbol": "YM=F", "label": "道指期货", "short": "Dow Fut"},
    {"id": "rty", "symbol": "RTY=F", "label": "罗素2000期货", "short": "RUT Fut"},
    {"id": "vix", "symbol": "^VIX", "label": "VIX", "short": "VIX"},
    {"id": "gc", "symbol": "GC=F", "label": "黄金", "short": "Gold"},
    {"id": "cl", "symbol": "CL=F", "label": "原油", "short": "Crude"},
    {"id": "btc", "symbol": "BTC-USD", "label": "比特币", "short": "BTC"},
]

# Full multi-TF charts under the strip (same TFs as sector desk).
US_FUTURES_CHARTS: list[dict[str, str]] = [
    {
        "id": "nq",
        "symbol": "NQ=F",
        "label": "纳斯达克100指数期货主连",
        "short": "纳指期货",
    },
    {
        "id": "es",
        "symbol": "ES=F",
        "label": "标普500指数期货主连",
        "short": "标普期货",
    },
    {
        "id": "ym",
        "symbol": "YM=F",
        "label": "道琼斯指数期货主连",
        "short": "道指期货",
    },
]

# SECTOR_TIMEFRAMES id → CNBC bar type + lookback days.
_TF_BARS: dict[str, tuple[str, int]] = {
    "intraday": ("1M", 3),
    "day": ("1D", 800),
    "month": ("1MO", 4000),
    "quarter": ("3MO", 6000),
}

_CACHE: dict[str, Any] = {"payload": None, "fetched_at": 0.0}
# Soft reuse window — FE polls often; avoid pile-ups on Render free tier.
_CACHE_TTL = 2.0
_FULL_CACHE_TTL = 90.0
_TAPE_BUDGET = 11.0
_FULL_BUDGET = 16.0
_YAHOO_TF: dict[str, tuple[str, str]] = {
    "intraday": ("1d", "1m"),
    "day": ("2y", "1d"),
    "month": ("max", "1mo"),
    "quarter": ("max", "3mo"),
}


def _headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.cnbc.com/",
    }


def _cnbc_for(yahoo_sym: str) -> str:
    return _CNBC_SYM.get(yahoo_sym.upper(), yahoo_sym)


def _series_ok(series: dict[str, Any] | None) -> bool:
    return len(((series or {}).get("points")) or []) >= 2


def _merge_futures_series(
    base: dict[str, Any] | None, overlay: dict[str, Any] | None
) -> dict[str, Any]:
    """Prefer fresh overlay points; never drop a good higher-TF series."""
    out = dict((base or {}).get("series") or {})
    for tf_id, series in ((overlay or {}).get("series") or {}).items():
        if _series_ok(series):
            out[tf_id] = series
        elif tf_id not in out:
            out[tf_id] = series
    return out


def _parse_trade_time(raw: str) -> int | None:
    """CNBC tradeTime like 20260805003300 → unix seconds (ET wall clock)."""
    text = str(raw or "").strip()
    if len(text) < 14 or not text.isdigit():
        return None
    try:
        dt = datetime(
            int(text[0:4]),
            int(text[4:6]),
            int(text[6:8]),
            int(text[8:10]),
            int(text[10:12]),
            int(text[12:14]),
            tzinfo=_ET,
        )
        return int(dt.timestamp())
    except ValueError:
        return None


# Higher-TF sparks for the US markets strip (no intraday — desk uses day/month/quarter).
_STRIP_TFS: tuple[str, ...] = ("day", "month", "quarter")


def _spark_series_from_bars(
    bars: list[dict[str, Any]],
    *,
    tf_id: str,
    source: str,
) -> dict[str, Any] | None:
    if len(bars) < 2:
        return None
    max_n = 56 if tf_id == "day" else 40
    sampled = even_sample_points(bars, max_n)
    points = [
        {"t": b.get("t"), "v": b.get("c")}
        for b in sampled
        if b.get("c") is not None and b.get("t") is not None
    ]
    if len(points) < 2:
        return None
    change, change_pct = _series_change(sampled, "candle")
    return {
        "tf": tf_id,
        "label": {"day": "日图", "month": "月图", "quarter": "季图"}.get(tf_id, tf_id),
        "points": points,
        "change": change,
        "change_pct": change_pct,
        "source": source,
    }


def _merge_strip_series(
    base: dict[str, Any] | None, overlay: dict[str, Any] | None
) -> dict[str, Any]:
    out = dict(base or {})
    for tf_id, series in (overlay or {}).items():
        if _series_ok(series):
            out[tf_id] = series
        elif tf_id not in out:
            out[tf_id] = series
    return out


def _lite_strip_row(
    spec: dict[str, str],
    quote: dict[str, Any] | None,
    points: list[dict[str, Any]] | None = None,
    series: dict[str, Any] | None = None,
) -> dict[str, Any]:
    q = quote or {}
    series_map = dict(series or {})
    # Prefer day spark as the default points payload for older clients.
    day_pts = list(((series_map.get("day") or {}).get("points")) or [])
    pts = day_pts[-48:] if len(day_pts) >= 2 else list(points or [])[-48:]
    return {
        "id": spec["id"],
        "symbol": spec["symbol"],
        "label": spec["label"],
        "short": spec.get("short") or spec["label"],
        "price": q.get("price"),
        "change": q.get("change"),
        "change_pct": q.get("change_pct"),
        "points": pts,
        "series": series_map,
        "url": f"https://finance.yahoo.com/quote/{urlquote(spec['symbol'], safe='')}",
        "source": q.get("source") or "cnbc",
    }


def _futures_shell(
    spec: dict[str, str], quote: dict[str, Any] | None = None
) -> dict[str, Any]:
    q = quote or {}
    return {
        "id": spec["id"],
        "symbol": spec["symbol"],
        "label": spec["label"],
        "short": spec.get("short") or spec["label"],
        "price": q.get("price"),
        "change": q.get("change"),
        "change_pct": q.get("change_pct"),
        "points": [],
        "series": {},
        "lite": True,
        "url": f"https://finance.yahoo.com/quote/{urlquote(spec['symbol'], safe='')}",
        "source": q.get("source") or "cnbc",
    }


async def _fetch_cnbc_quotes(
    client: httpx.AsyncClient, yahoo_symbols: list[str]
) -> dict[str, dict[str, Any]]:
    """Return quotes keyed by Yahoo symbol."""
    out: dict[str, dict[str, Any]] = {}
    cnbc_to_yahoo = {_cnbc_for(s): s for s in yahoo_symbols}
    joined = "|".join(cnbc_to_yahoo.keys())
    if not joined:
        return out
    url = (
        "https://quote.cnbc.com/quote-html-webservice/restQuote/"
        "symbolType/symbol"
        f"?symbols={urlquote(joined, safe='')}"
        "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1"
    )
    try:
        resp = await client.get(url, timeout=4.0, headers=_headers())
        resp.raise_for_status()
        rows = (
            (resp.json().get("FormattedQuoteResult") or {}).get("FormattedQuote") or []
        )
        if isinstance(rows, dict):
            rows = [rows]
        for row in rows:
            if not isinstance(row, dict):
                continue
            if row.get("code") not in (0, "0", None):
                continue
            cnbc_sym = str(row.get("symbol") or "").strip()
            yahoo = cnbc_to_yahoo.get(cnbc_sym)
            if not yahoo:
                yahoo = cnbc_to_yahoo.get(cnbc_sym.upper()) or next(
                    (
                        y
                        for c, y in cnbc_to_yahoo.items()
                        if c.upper() == cnbc_sym.upper()
                    ),
                    None,
                )
            if not yahoo:
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
            out[yahoo.upper()] = {
                "symbol": yahoo.upper(),
                "price": round(price, 2) if price is not None else None,
                "change": round(change, 4) if change is not None else None,
                "change_pct": round(change_pct, 3) if change_pct is not None else None,
                "previous_close": round(float(prev), 6)
                if prev not in (None, 0)
                else None,
                "source": "cnbc",
            }
    except Exception:  # noqa: BLE001
        return out
    return out


async def _fetch_yahoo_bars(
    client: httpx.AsyncClient,
    yahoo_sym: str,
    *,
    range_: str,
    interval: str,
) -> list[dict[str, Any]]:
    """Fallback OHLC when CNBC bars are empty/rate-limited."""
    enc = urlquote(yahoo_sym, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}"
        f"?range={range_}&interval={interval}&includePrePost=false"
    )
    try:
        resp = await client.get(
            url,
            timeout=6.0,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )
        if resp.status_code >= 400:
            return []
        result = ((resp.json().get("chart") or {}).get("result") or [None])[0]
        if not result:
            return []
        ts_list = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [None])[0] or {}
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        vols = quote.get("volume") or []
        out: list[dict[str, Any]] = []
        for i, ts in enumerate(ts_list):
            try:
                t = int(ts)
            except (TypeError, ValueError):
                continue
            close = _parse_number(closes[i] if i < len(closes) else None)
            if close is None:
                continue
            open_ = _parse_number(opens[i] if i < len(opens) else None) or close
            high = _parse_number(highs[i] if i < len(highs) else None) or max(
                open_, close
            )
            low = _parse_number(lows[i] if i < len(lows) else None) or min(open_, close)
            vol = _parse_number(vols[i] if i < len(vols) else None)
            out.append(
                {
                    "t": t,
                    "o": round(float(open_), 6),
                    "h": round(float(high), 6),
                    "l": round(float(low), 6),
                    "c": round(float(close), 6),
                    "v": round(float(vol), 2) if vol is not None else None,
                }
            )
        out.sort(key=lambda p: p["t"])
        return out
    except Exception:  # noqa: BLE001
        return []


async def _fetch_cnbc_bars(
    client: httpx.AsyncClient,
    cnbc_sym: str,
    bar_type: str,
    *,
    lookback_days: int,
) -> list[dict[str, Any]]:
    now = datetime.now(tz=_ET)
    end = now.strftime("%Y%m%d%H%M%S")
    start = (now - timedelta(days=max(1, lookback_days))).strftime("%Y%m%d%H%M%S")
    enc = urlquote(cnbc_sym, safe="@.=")
    url = (
        f"https://ts-api.cnbc.com/harmony/app/bars/{enc}/{bar_type}/"
        f"{start}/{end}/adjusted/EST5EDT.json"
    )
    try:
        resp = await client.get(url, timeout=5.0, headers=_headers())
        if resp.status_code >= 400:
            return []
        payload = resp.json() or {}
        bars = ((payload.get("barData") or {}).get("priceBars")) or []
        if not isinstance(bars, list):
            return []
        out: list[dict[str, Any]] = []
        for bar in bars:
            if not isinstance(bar, dict):
                continue
            ts = _parse_trade_time(str(bar.get("tradeTime") or ""))
            if ts is None and bar.get("tradeTimeinMillis") is not None:
                try:
                    ts = int(int(bar["tradeTimeinMillis"]) / 1000)
                except (TypeError, ValueError):
                    ts = None
            close = _parse_number(bar.get("close"))
            if ts is None or close is None:
                continue
            open_ = _parse_number(bar.get("open")) or close
            high = _parse_number(bar.get("high")) or max(open_, close)
            low = _parse_number(bar.get("low")) or min(open_, close)
            vol = _parse_number(bar.get("volume"))
            out.append(
                {
                    "t": ts,
                    "o": round(float(open_), 6),
                    "h": round(float(high), 6),
                    "l": round(float(low), 6),
                    "c": round(float(close), 6),
                    "v": round(float(vol), 2) if vol is not None else None,
                }
            )
        out.sort(key=lambda p: p["t"])
        return out
    except Exception:  # noqa: BLE001
        return []


def _bj_session_slice(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the Beijing 06:00→05:00 futures session window when dense enough."""
    if len(points) < 8:
        return points
    now_bj = datetime.now(tz=_BJ)
    if now_bj.hour >= 6:
        start_bj = now_bj.replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        start_bj = (now_bj - timedelta(days=1)).replace(
            hour=6, minute=0, second=0, microsecond=0
        )
    start_ts = int(start_bj.timestamp())
    sliced = [p for p in points if int(p.get("t") or 0) >= start_ts]
    return sliced if len(sliced) >= 8 else points


async def _bars_for_tf(
    client: httpx.AsyncClient,
    yahoo_sym: str,
    tf_id: str,
) -> tuple[list[dict[str, Any]], str]:
    """CNBC first (short timeout), Yahoo fallback."""
    bar_type, lookback = _TF_BARS.get(tf_id, ("1D", 800))
    cnbc_sym = _cnbc_for(yahoo_sym)
    try:
        bars = await asyncio.wait_for(
            _fetch_cnbc_bars(client, cnbc_sym, bar_type, lookback_days=lookback),
            timeout=4.5,
        )
    except asyncio.TimeoutError:
        bars = []
    if len(bars) >= 2:
        return bars, "cnbc"
    y_range, y_interval = _YAHOO_TF.get(tf_id, ("2y", "1d"))
    try:
        bars = await asyncio.wait_for(
            _fetch_yahoo_bars(client, yahoo_sym, range_=y_range, interval=y_interval),
            timeout=5.5,
        )
    except asyncio.TimeoutError:
        bars = []
    return bars, "yahoo"


async def _build_futures_bundle(
    client: httpx.AsyncClient,
    spec: dict[str, str],
    quote: dict[str, Any] | None,
    *,
    tf_ids: set[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    want = tf_ids or {tf["id"] for tf in SECTOR_TIMEFRAMES}
    series: dict[str, Any] = {}
    for tf in SECTOR_TIMEFRAMES:
        tf_id = tf["id"]
        if tf_id not in want:
            continue
        try:
            bars, source = await _bars_for_tf(client, spec["symbol"], tf_id)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{spec['symbol']}/{tf['label']}: {exc.__class__.__name__}")
            continue
        if len(bars) < 2:
            errors.append(f"{spec['symbol']}/{tf['label']}: empty")
            continue
        if tf_id == "intraday":
            line = [
                {"t": b["t"], "v": b["c"], "session": "regular"}
                for b in _bj_session_slice(bars)
            ]
            points = even_sample_points(line, 420) if len(line) > 420 else line
            window_change, window_pct = _series_change(points, "line")
            series[tf_id] = {
                "tf": tf_id,
                "label": tf["label"],
                "blurb": (
                    "CNBC 分时 · 主连 北京06:00→05:00"
                    if source == "cnbc"
                    else "Yahoo 分时 · 指数期货主连"
                ),
                "chart": "line",
                "points": points,
                # Prefer session quote % below; keep window stats for tooling.
                "change": window_change,
                "change_pct": window_pct,
                "window_change": window_change,
                "window_change_pct": window_pct,
                "source": source,
            }
        else:
            candle = [
                {
                    "t": b["t"],
                    "o": b["o"],
                    "h": b["h"],
                    "l": b["l"],
                    "c": b["c"],
                    "v": b.get("v"),
                }
                for b in bars
            ]
            points = even_sample_points(candle, 560)
            window_change, window_pct = _series_change(points, "candle")
            series[tf_id] = {
                "tf": tf_id,
                "label": tf["label"],
                "blurb": f"{'CNBC' if source == 'cnbc' else 'Yahoo'} {tf['label']} · 指数期货主连（红涨绿跌）",
                "chart": "candle",
                "points": points,
                "change": window_change,
                "change_pct": window_pct,
                "window_change": window_change,
                "window_change_pct": window_pct,
                "source": source,
            }

    q = quote or {}
    # Card/tape % must match session quote (prev close → last), not full-history
    # first→last window return (was showing multi-year +40~60% on 日/月/季).
    q_change = q.get("change")
    q_pct = q.get("change_pct")
    if q_pct is not None or q_change is not None:
        for row in series.values():
            if not isinstance(row, dict):
                continue
            row["change"] = q_change
            row["change_pct"] = q_pct
            if q.get("previous_close") is not None:
                row["previous_close"] = q.get("previous_close")

    intra = series.get("intraday") or {}
    pts = list(intra.get("points") or [])
    return (
        {
            "id": spec["id"],
            "symbol": spec["symbol"],
            "label": spec["label"],
            "short": spec.get("short") or spec["label"],
            "price": q.get("price"),
            "change": q.get("change"),
            "change_pct": q.get("change_pct"),
            "previous_close": q.get("previous_close"),
            "points": [
                {"t": p.get("t"), "v": p.get("v") if p.get("v") is not None else p.get("c")}
                for p in pts[-48:]
            ],
            "series": series,
            "lite": not bool(series),
            "url": f"https://finance.yahoo.com/quote/{urlquote(spec['symbol'], safe='')}",
            "source": q.get("source") or "cnbc",
        },
        errors,
    )


def _stale_payload(extra_errors: list[str] | None = None) -> dict[str, Any] | None:
    prev = _CACHE.get("payload")
    if not isinstance(prev, dict):
        return None
    out = dict(prev)
    out["cached"] = True
    out["stale"] = True
    errs = list(out.get("errors") or [])
    for e in extra_errors or []:
        if e not in errs:
            errs.append(e)
    out["errors"] = errs[-24:]
    return out


async def build_us_markets_desk(
    *, force: bool = False, mode: str = "full"
) -> dict[str, Any]:
    """Strip quotes + ES/NQ/YM multi-TF charts (sector timeframe set)."""
    now = time.time()
    mode_norm = (mode or "full").strip().lower()
    if mode_norm not in {"full", "tape"}:
        mode_norm = "full"
    prev = _CACHE.get("payload")
    age = now - float(_CACHE.get("fetched_at") or 0)
    if not force and prev and age < _CACHE_TTL:
        out = dict(prev)
        out["cached"] = True
        return out
    # Soft-hit: for tape polls, reuse a very fresh payload.
    if force and mode_norm == "tape" and prev and age < _CACHE_TTL:
        out = dict(prev)
        out["cached"] = True
        return out

    need_full = mode_norm == "full" or not prev
    if prev and mode_norm == "full":
        full_age = now - float(prev.get("fetched_at") or 0)
        have_higher = all(
            any(
                _series_ok((f.get("series") or {}).get(tf))
                for f in (prev.get("futures") or [])
            )
            for tf in ("day", "month", "quarter")
        )
        if have_higher and full_age < _FULL_CACHE_TTL and not force:
            need_full = False

    budget = _FULL_BUDGET if need_full else _TAPE_BUDGET
    try:
        return await asyncio.wait_for(
            _build_us_markets_inner(
                force=force,
                mode_norm=mode_norm,
                need_full=need_full,
                prev=prev if isinstance(prev, dict) else None,
                now=now,
            ),
            timeout=budget,
        )
    except asyncio.TimeoutError:
        stale = _stale_payload(["us-markets: overall timeout"])
        if stale:
            return stale
        # Last resort empty shell so FE stops spinning.
        return {
            "strip": [_lite_strip_row(s, None, []) for s in US_MARKET_STRIP],
            "futures": [_futures_shell(s) for s in US_FUTURES_CHARTS],
            "timeframes": [
                {"id": tf["id"], "label": tf["label"], "chart": tf.get("chart")}
                for tf in SECTOR_TIMEFRAMES
            ],
            "default_tf": "intraday",
            "source": "CNBC/Yahoo · 超时降级",
            "fetched_at": now,
            "errors": ["us-markets: overall timeout"],
            "cached": False,
            "stale": True,
            "mode": "full" if need_full else "tape",
        }


async def _build_us_markets_inner(
    *,
    force: bool,
    mode_norm: str,
    need_full: bool,
    prev: dict[str, Any] | None,
    now: float,
) -> dict[str, Any]:
    errors: list[str] = []
    strip_syms = [s["symbol"] for s in US_MARKET_STRIP]
    fut_specs = list(US_FUTURES_CHARTS)
    tf_ids = None if need_full else {"intraday"}

    async with httpx.AsyncClient(
        follow_redirects=True,
        trust_env=False,
        timeout=httpx.Timeout(8.0, connect=3.0),
        headers=_headers(),
    ) as client:
        try:
            quotes = await asyncio.wait_for(
                _fetch_cnbc_quotes(client, strip_syms), timeout=4.5
            )
        except asyncio.TimeoutError:
            quotes = {}
            errors.append("strip quotes: timeout")

        # Strip sparks: day / month / quarter (no intraday). Reuse prior series on
        # tape polls; only fill missing higher-TF series on full builds.
        prev_strip = {
            str(r.get("symbol") or "").upper(): r
            for r in ((prev or {}).get("strip") or [])
        }
        strip_series_map: dict[str, dict[str, Any]] = {}

        async def strip_series_one(sym: str) -> None:
            old = prev_strip.get(sym.upper()) or {}
            series = dict(old.get("series") or {})
            # Always keep prior good series on tape; only fetch gaps on full.
            want_tfs = (
                [tf for tf in _STRIP_TFS if not _series_ok(series.get(tf))]
                if need_full
                else []
            )
            for tf_id in want_tfs:
                try:
                    bars, src = await asyncio.wait_for(
                        _bars_for_tf(client, sym, tf_id),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    bars, src = [], "timeout"
                spark = _spark_series_from_bars(bars, tf_id=tf_id, source=src)
                if spark:
                    series[tf_id] = spark
            strip_series_map[sym.upper()] = series

        await asyncio.gather(
            *(strip_series_one(s["symbol"]) for s in US_MARKET_STRIP)
        )

        strip = []
        for spec in US_MARKET_STRIP:
            old = prev_strip.get(spec["symbol"].upper()) or {}
            series = _merge_strip_series(
                old.get("series"),
                strip_series_map.get(spec["symbol"].upper()),
            )
            day_pts = list(((series.get("day") or {}).get("points")) or [])
            pts = day_pts or list(old.get("points") or [])
            row = _lite_strip_row(
                spec,
                quotes.get(spec["symbol"].upper()),
                pts,
                series=series,
            )
            if row.get("price") is None and old:
                row["price"] = old.get("price")
                row["change"] = old.get("change")
                row["change_pct"] = old.get("change_pct")
            strip.append(row)

        # Checkpoint: if futures hang, timeout handler can still serve strip quotes.
        _CACHE["payload"] = {
            "strip": strip,
            "futures": list((prev or {}).get("futures") or [])
            or [_futures_shell(s, quotes.get(s["symbol"].upper())) for s in fut_specs],
            "timeframes": [
                {"id": tf["id"], "label": tf["label"], "chart": tf.get("chart")}
                for tf in SECTOR_TIMEFRAMES
            ],
            "default_tf": "intraday",
            "source": "CNBC · 指数期货主连",
            "fetched_at": now,
            "errors": list(errors),
            "cached": False,
            "partial": True,
            "mode": "full" if need_full else "tape",
        }
        _CACHE["fetched_at"] = now

        futures: list[dict[str, Any]] = []
        prev_by_id = {
            str(f.get("id") or "").lower(): f
            for f in ((prev or {}).get("futures") or [])
        }

        async def one(spec: dict[str, str]) -> None:
            q = quotes.get(spec["symbol"].upper())
            try:
                bundle, errs = await asyncio.wait_for(
                    _build_futures_bundle(client, spec, q, tf_ids=tf_ids),
                    timeout=8.0 if need_full else 6.0,
                )
            except (asyncio.TimeoutError, httpx.HTTPError) as exc:
                errors.append(f"{spec['symbol']}: {exc.__class__.__name__}")
                old = prev_by_id.get(spec["id"])
                if old:
                    merged = dict(old)
                    if q:
                        for k in ("price", "change", "change_pct"):
                            if q.get(k) is not None:
                                merged[k] = q.get(k)
                    futures.append(merged)
                else:
                    futures.append(_futures_shell(spec, q))
                return
            errors.extend(errs or [])
            old = prev_by_id.get(spec["id"])
            if not bundle:
                futures.append(old or _futures_shell(spec, q))
                return
            if old:
                bundle = {
                    **old,
                    **bundle,
                    "series": _merge_futures_series(old, bundle),
                    "lite": False,
                }
                if not bundle.get("points") and old.get("points"):
                    bundle["points"] = old.get("points")
            futures.append(bundle)

        await asyncio.gather(*(one(s) for s in fut_specs))

    order = {s["id"]: i for i, s in enumerate(fut_specs)}
    futures.sort(key=lambda r: order.get(str(r.get("id") or ""), 99))

    # Backfill strip higher-TF sparks / quotes from futures when missing.
    by_sym = {str(f.get("symbol") or "").upper(): f for f in futures}
    for row in strip:
        sym = str(row.get("symbol") or "").upper()
        fut = by_sym.get(sym)
        if not fut:
            continue
        series = dict(row.get("series") or {})
        fut_series = fut.get("series") or {}
        for tf_id in _STRIP_TFS:
            if _series_ok(series.get(tf_id)):
                continue
            src = fut_series.get(tf_id) or {}
            raw_pts = list(src.get("points") or [])
            if len(raw_pts) < 2:
                continue
            # Futures series may be candles; spark "v" must be price (close),
            # never candle volume (which is also keyed as "v").
            spark_pts = []
            for p in raw_pts:
                if p.get("t") is None:
                    continue
                is_candle = (
                    p.get("o") is not None
                    or p.get("h") is not None
                    or p.get("l") is not None
                )
                price = p.get("c") if is_candle else p.get("v")
                if price is None:
                    price = p.get("c") if p.get("c") is not None else p.get("v")
                if price is None:
                    continue
                spark_pts.append({"t": p.get("t"), "v": price})
            if len(spark_pts) < 2:
                continue
            series[tf_id] = {
                "tf": tf_id,
                "label": {"day": "日图", "month": "月图", "quarter": "季图"}.get(
                    tf_id, tf_id
                ),
                "points": spark_pts[-56:],
                "change": src.get("change"),
                "change_pct": src.get("change_pct"),
                "source": src.get("source") or fut.get("source") or "cnbc",
            }
        row["series"] = series
        day_pts = list(((series.get("day") or {}).get("points")) or [])
        if len(day_pts) >= 2:
            row["points"] = day_pts[-48:]
        if row.get("price") is None:
            row["price"] = fut.get("price")
            row["change"] = fut.get("change")
            row["change_pct"] = fut.get("change_pct")

    # Targeted Yahoo day fill only when still missing and we have budget left.
    if need_full:
        missing_day = [
            f
            for f in futures
            if not _series_ok((f.get("series") or {}).get("day"))
        ]
        if missing_day:
            async with httpx.AsyncClient(
                follow_redirects=True,
                trust_env=False,
                timeout=httpx.Timeout(7.0, connect=3.0),
                headers=_headers(),
            ) as client:

                async def fill_day(fut: dict[str, Any]) -> None:
                    try:
                        raw = await asyncio.wait_for(
                            _fetch_yahoo_bars(
                                client,
                                str(fut.get("symbol") or ""),
                                range_="2y",
                                interval="1d",
                            ),
                            timeout=5.5,
                        )
                    except asyncio.TimeoutError:
                        return
                    if len(raw) < 2:
                        return
                    points = even_sample_points(raw, 560)
                    change, change_pct = _series_change(points, "candle")
                    series = dict(fut.get("series") or {})
                    series["day"] = {
                        "tf": "day",
                        "label": "日图",
                        "blurb": "Yahoo 日图 · 指数期货主连（红涨绿跌）",
                        "chart": "candle",
                        "points": points,
                        "change": change,
                        "change_pct": change_pct,
                        "source": "yahoo",
                    }
                    fut["series"] = series
                    fut["lite"] = False

                await asyncio.gather(*(fill_day(f) for f in missing_day))

    payload = {
        "strip": strip,
        "futures": futures,
        "timeframes": [
            {"id": tf["id"], "label": tf["label"], "chart": tf.get("chart")}
            for tf in SECTOR_TIMEFRAMES
        ],
        "default_tf": "intraday",
        "source": "CNBC · 指数期货主连",
        "fetched_at": now,
        "errors": errors[-24:],
        "cached": False,
        "mode": "full" if need_full else "tape",
    }
    if prev and not need_full:
        prev_by = {
            str(f.get("id") or "").lower(): f for f in (prev.get("futures") or [])
        }
        for fut in payload["futures"]:
            old = prev_by.get(str(fut.get("id") or "").lower())
            if old:
                fut["series"] = _merge_futures_series(old, fut)
        prev_strip_by = {
            str(r.get("symbol") or "").upper(): r for r in (prev.get("strip") or [])
        }
        for row in payload["strip"]:
            old = prev_strip_by.get(str(row.get("symbol") or "").upper())
            if old:
                row["series"] = _merge_strip_series(old.get("series"), row.get("series"))
                day_pts = list(((row.get("series") or {}).get("day") or {}).get("points") or [])
                if len(day_pts) >= 2:
                    row["points"] = day_pts[-48:]
    _CACHE["payload"] = payload
    _CACHE["fetched_at"] = now
    return dict(payload)
