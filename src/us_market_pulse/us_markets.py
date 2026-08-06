"""US markets strip + index futures charts for the sectors page.

Yahoo chart endpoints are often 403 from datacenter/residential IPs.
CNBC quote + ts-api bars cover futures (ES/NQ/YM) reliably.
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
    # 2+ days so 北京 06:00→05:00 session always has full 1M coverage.
    "intraday": ("1M", 3),
    "day": ("1D", 800),
    "month": ("1MO", 4000),
    "quarter": ("3MO", 6000),
}

_CACHE: dict[str, Any] = {"payload": None, "fetched_at": 0.0}
# Tape (strip + 分时) stays near real-time; higher TFs reuse longer.
_CACHE_TTL = 0.5
_FULL_CACHE_TTL = 90.0
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
        "Origin": "https://www.cnbc.com",
    }


def _cnbc_for(yahoo_sym: str) -> str:
    return _CNBC_SYM.get(yahoo_sym.upper(), yahoo_sym)


def futures_session_bounds_bj(
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    """CME equity-index futures 1D window in Beijing time.

    Summer/winter alike for the desk: 06:00 → next day 05:00 (23h), matching
    broker apps (e.g. 主连 1D axis 06:01 … 05:00).
    """
    now_bj = now.astimezone(_BJ) if now else datetime.now(tz=_BJ)
    today_6 = now_bj.replace(hour=6, minute=0, second=0, microsecond=0)
    start = today_6 if now_bj >= today_6 else today_6 - timedelta(days=1)
    end = start + timedelta(hours=23)
    return start, end


def finalize_futures_intraday_points(
    points: list[dict[str, Any]] | None,
    *,
    now: datetime | None = None,
    max_points: int = 360,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Clip 1M bars to the active 北京 06:00→05:00 session; chronological only."""
    start_bj, end_bj = futures_session_bounds_bj(now)
    start_ts = int(start_bj.timestamp())
    end_ts = int(end_bj.timestamp())
    now_ts = int((now or datetime.now(tz=_BJ)).timestamp())
    clip_end = min(end_ts, now_ts + 60)
    rows: list[dict[str, Any]] = []
    for p in points or []:
        if not isinstance(p, dict) or p.get("t") is None:
            continue
        try:
            t = int(p["t"])
            v = float(p.get("v") if p.get("v") is not None else p.get("c"))
        except (TypeError, ValueError):
            continue
        if t < start_ts or t > clip_end:
            continue
        rows.append({"t": t, "v": round(v, 6)})
    rows.sort(key=lambda p: p["t"])
    # Drop duplicate timestamps (keep last).
    dedup: list[dict[str, Any]] = []
    for p in rows:
        if dedup and dedup[-1]["t"] == p["t"]:
            dedup[-1] = p
        else:
            dedup.append(p)
    if len(dedup) > max_points:
        dedup = even_sample_points(dedup, max_points)
    meta = {
        "cycle_start": start_ts,
        "cycle_end": end_ts,
    }
    return dedup, meta


def _parse_trade_time(raw: str | None) -> int | None:
    """CNBC tradeTime like 20260805003300 → unix seconds (ET wall clock)."""
    text = str(raw or "").strip()
    if len(text) < 14 or not text[:14].isdigit():
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
        resp = await client.get(url, timeout=20.0, headers=_headers())
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
                # case / alias miss
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
                "previous_close": round(float(prev), 6) if prev not in (None, 0) else None,
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
            timeout=10.0,
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
            high = _parse_number(highs[i] if i < len(highs) else None) or max(open_, close)
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
        resp = await client.get(url, timeout=22.0, headers=_headers())
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
            open_ = _parse_number(bar.get("open"))
            high = _parse_number(bar.get("high"))
            low = _parse_number(bar.get("low"))
            vol = _parse_number(bar.get("volume"))
            if open_ is None:
                open_ = close
            if high is None:
                high = max(open_, close)
            if low is None:
                low = min(open_, close)
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


def _lite_strip_row(
    spec: dict[str, str], quote: dict[str, Any] | None, spark: list[dict[str, Any]]
) -> dict[str, Any]:
    q = quote or {}
    pts = list(spark or [])[-48:]
    return {
        "id": spec["id"],
        "symbol": spec["symbol"],
        "label": spec["label"],
        "short": spec.get("short") or spec["label"],
        "price": q.get("price"),
        "change": q.get("change"),
        "change_pct": q.get("change_pct"),
        "previous_close": q.get("previous_close"),
        "points": pts,
        "url": f"https://finance.yahoo.com/quote/{urlquote(spec['symbol'], safe='')}",
    }


async def _build_futures_bundle(
    client: httpx.AsyncClient,
    spec: dict[str, str],
    quote: dict[str, Any] | None,
    *,
    tf_ids: set[str] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    cnbc = _cnbc_for(spec["symbol"])
    series: dict[str, Any] = {}
    quote_seed = dict(quote or {})
    wanted = {
        str(tf["id"])
        for tf in SECTOR_TIMEFRAMES
        if tf_ids is None or str(tf["id"]) in tf_ids
    }

    async def one_tf(tf: dict[str, Any]) -> None:
        tf_id = str(tf["id"])
        if tf_id not in wanted:
            return
        bar_type, lookback = _TF_BARS.get(tf_id, ("1D", 800))
        chart = str(tf.get("chart") or "line")
        raw = await _fetch_cnbc_bars(
            client, cnbc, bar_type, lookback_days=lookback
        )
        source = "cnbc"
        if len(raw) < 2:
            y_range, y_interval = _YAHOO_TF.get(tf_id, ("2y", "1d"))
            raw = await _fetch_yahoo_bars(
                client, spec["symbol"], range_=y_range, interval=y_interval
            )
            source = "yahoo"
        if len(raw) < 2:
            errors.append(f"{spec['label']}/{tf['label']}: no bars")
            return
        max_pts = int(tf.get("max_points") or 360)
        if chart == "line":
            points = [{"t": b["t"], "v": b["c"]} for b in raw]
            # Dedicated CME 主连 1D: 北京 06:00 → 次日 05:00 (not equity 4–20 ET).
            points, cycle = finalize_futures_intraday_points(
                points, max_points=max_pts
            )
            if len(points) < 2:
                errors.append(f"{spec['label']}/{tf['label']}: empty futures session")
                return
            change, change_pct = _series_change(points, "line")
            prev = quote_seed.get("previous_close")
            price = quote_seed.get("price") or (points[-1]["v"] if points else None)
            day_change = quote_seed.get("change")
            day_change_pct = quote_seed.get("change_pct")
            if day_change_pct is not None:
                change, change_pct = day_change, day_change_pct
            series[tf_id] = {
                "tf": tf_id,
                "label": tf["label"],
                "blurb": (
                    "CNBC 分时 · 主连 北京06:00→05:00"
                    if source == "cnbc"
                    else "Yahoo 分时 · 指数期货"
                ),
                "range": tf.get("range"),
                "interval": tf.get("interval"),
                "chart": "line",
                "axis": "futures_bj",
                "points": points,
                "change": change,
                "change_pct": change_pct,
                "previous_close": prev,
                "cycle_start": cycle.get("cycle_start"),
                "cycle_end": cycle.get("cycle_end"),
                "source": source,
            }
            if price is not None:
                quote_seed.setdefault("price", price)
        else:
            points = even_sample_points(raw, max_pts)
            change, change_pct = _series_change(points, "candle")
            series[tf_id] = {
                "tf": tf_id,
                "label": tf["label"],
                "blurb": f"{'CNBC' if source == 'cnbc' else 'Yahoo'} {tf['label']} · 指数期货主连（红涨绿跌）",
                "range": tf.get("range"),
                "interval": tf.get("interval"),
                "chart": "candle",
                "points": points,
                "change": change,
                "change_pct": change_pct,
                "source": source,
            }

    await asyncio.gather(*(one_tf(tf) for tf in SECTOR_TIMEFRAMES))
    if not series:
        return None, errors or [f"{spec['label']}: no series"]

    spark_src = series.get("intraday") or series.get("day") or next(iter(series.values()))
    spark_points = spark_src.get("points") or []
    if spark_src.get("chart") == "candle":
        spark_points = [{"t": p["t"], "v": p["c"]} for p in spark_points]

    price = quote_seed.get("price")
    if price is None and spark_points:
        price = spark_points[-1].get("v")

    return {
        "id": spec["id"],
        "symbol": spec["symbol"],
        "label": spec["label"],
        "short": spec["short"],
        "price": price,
        "change": quote_seed.get("change"),
        "change_pct": quote_seed.get("change_pct"),
        "previous_close": quote_seed.get("previous_close"),
        "points": spark_points[-64:],
        "series": series,
        "lite": False,
        "source": "cnbc",
        "url": f"https://finance.yahoo.com/quote/{urlquote(spec['symbol'], safe='')}",
    }, errors


def _futures_shell(
    spec: dict[str, str], quote: dict[str, Any] | None
) -> dict[str, Any]:
    q = quote or {}
    return {
        "id": spec["id"],
        "symbol": spec["symbol"],
        "label": spec["label"],
        "short": spec["short"],
        "price": q.get("price"),
        "change": q.get("change"),
        "change_pct": q.get("change_pct"),
        "points": [],
        "series": {},
        "lite": True,
        "url": f"https://finance.yahoo.com/quote/{urlquote(spec['symbol'], safe='')}",
    }


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

    errors: list[str] = []
    strip_syms = [s["symbol"] for s in US_MARKET_STRIP]
    fut_specs = list(US_FUTURES_CHARTS)
    # tape = strip + 分时 only; full = all TFs (or fill missing higher TFs).
    need_full = mode_norm == "full" or not prev
    if prev and mode_norm == "full":
        # Skip hammering higher TFs when they are still warm.
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

    tf_ids = (
        None
        if need_full
        else {"intraday"}
    )

    async with httpx.AsyncClient(
        follow_redirects=True,
        trust_env=False,
        timeout=httpx.Timeout(22.0, connect=5.0),
        headers=_headers(),
    ) as client:
        quotes = await _fetch_cnbc_quotes(client, strip_syms)

        # Strip sparks (5m) for all strip symbols in parallel.
        async def spark_one(sym: str) -> tuple[str, list[dict[str, Any]]]:
            bars = await _fetch_cnbc_bars(
                client, _cnbc_for(sym), "5M", lookback_days=2
            )
            pts = [{"t": b["t"], "v": b["c"]} for b in bars]
            return sym.upper(), pts[-48:]

        spark_pairs = await asyncio.gather(*(spark_one(s) for s in strip_syms))
        sparks = dict(spark_pairs)

        strip = [
            _lite_strip_row(
                spec,
                quotes.get(spec["symbol"].upper()),
                sparks.get(spec["symbol"].upper()) or [],
            )
            for spec in US_MARKET_STRIP
        ]

        futures: list[dict[str, Any]] = []
        prev_by_id = {
            str(f.get("id") or "").lower(): f for f in ((prev or {}).get("futures") or [])
        }

        async def one(spec: dict[str, str]) -> None:
            q = quotes.get(spec["symbol"].upper())
            try:
                bundle, errs = await asyncio.wait_for(
                    _build_futures_bundle(client, spec, q, tf_ids=tf_ids),
                    timeout=20.0 if need_full else 12.0,
                )
            except (asyncio.TimeoutError, httpx.HTTPError) as exc:
                errors.append(f"{spec['symbol']}: {exc.__class__.__name__}")
                old = prev_by_id.get(spec["id"])
                if old:
                    merged = dict(old)
                    merged.update(
                        {
                            "price": q.get("price") if q else old.get("price"),
                            "change": q.get("change") if q else old.get("change"),
                            "change_pct": q.get("change_pct")
                            if q
                            else old.get("change_pct"),
                        }
                    )
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
                # If tape refresh missed higher TFs, keep previous spark/points when needed.
                if not bundle.get("points") and old.get("points"):
                    bundle["points"] = old.get("points")
            futures.append(bundle)

        await asyncio.gather(*(one(s) for s in fut_specs))

    order = {s["id"]: i for i, s in enumerate(fut_specs)}
    futures.sort(key=lambda r: order.get(str(r.get("id") or ""), 99))

    # Backfill strip sparks / quotes from futures when missing.
    by_sym = {str(f.get("symbol") or "").upper(): f for f in futures}
    for row in strip:
        sym = str(row.get("symbol") or "").upper()
        fut = by_sym.get(sym)
        if not fut:
            continue
        if not row.get("points"):
            intra = ((fut.get("series") or {}).get("intraday") or {})
            pts = list(intra.get("points") or [])[-48:]
            if len(pts) >= 2:
                row["points"] = [
                    {
                        "t": p.get("t"),
                        "v": p.get("v") if p.get("v") is not None else p.get("c"),
                    }
                    for p in pts
                    if (p.get("v") is not None or p.get("c") is not None)
                ]
        if row.get("price") is None:
            row["price"] = fut.get("price")
            row["change"] = fut.get("change")
            row["change_pct"] = fut.get("change_pct")

    # If a full rebuild still lacks day bars, do one targeted Yahoo fill.
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
                timeout=httpx.Timeout(12.0, connect=4.0),
                headers=_headers(),
            ) as client:
                async def fill_day(fut: dict[str, Any]) -> None:
                    raw = await _fetch_yahoo_bars(
                        client, str(fut.get("symbol") or ""), range_="2y", interval="1d"
                    )
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
    # Preserve higher TFs if a tape refresh somehow emptied them.
    if prev and not need_full:
        prev_by = {
            str(f.get("id") or "").lower(): f for f in (prev.get("futures") or [])
        }
        for fut in payload["futures"]:
            old = prev_by.get(str(fut.get("id") or "").lower())
            if old:
                fut["series"] = _merge_futures_series(old, fut)
    _CACHE["payload"] = payload
    _CACHE["fetched_at"] = now
    return dict(payload)
