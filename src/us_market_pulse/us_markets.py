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
# Keep futures/strip tape near real-time; FE polls ~1–2s.
_CACHE_TTL = 2.0


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
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    cnbc = _cnbc_for(spec["symbol"])
    series: dict[str, Any] = {}
    quote_seed = dict(quote or {})

    async def one_tf(tf: dict[str, Any]) -> None:
        tf_id = str(tf["id"])
        bar_type, lookback = _TF_BARS.get(tf_id, ("1D", 800))
        chart = str(tf.get("chart") or "line")
        raw = await _fetch_cnbc_bars(
            client, cnbc, bar_type, lookback_days=lookback
        )
        if len(raw) < 2:
            errors.append(f"{spec['label']}/{tf['label']}: no CNBC bars")
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
                "blurb": "CNBC 分时 · 主连 北京06:00→05:00",
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
                "source": "cnbc",
            }
            if price is not None:
                quote_seed.setdefault("price", price)
        else:
            points = even_sample_points(raw, max_pts)
            change, change_pct = _series_change(points, "candle")
            series[tf_id] = {
                "tf": tf_id,
                "label": tf["label"],
                "blurb": f"CNBC {tf['label']} · 指数期货主连（红涨绿跌）",
                "range": tf.get("range"),
                "interval": tf.get("interval"),
                "chart": "candle",
                "points": points,
                "change": change,
                "change_pct": change_pct,
                "source": "cnbc",
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


async def build_us_markets_desk(*, force: bool = False) -> dict[str, Any]:
    """Strip quotes + ES/NQ/YM multi-TF charts (sector timeframe set)."""
    now = time.time()
    if (
        not force
        and _CACHE.get("payload")
        and now - float(_CACHE.get("fetched_at") or 0) < _CACHE_TTL
    ):
        out = dict(_CACHE["payload"])
        out["cached"] = True
        return out

    errors: list[str] = []
    strip_syms = [s["symbol"] for s in US_MARKET_STRIP]
    fut_specs = list(US_FUTURES_CHARTS)

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

        async def one(spec: dict[str, str]) -> None:
            q = quotes.get(spec["symbol"].upper())
            try:
                bundle, errs = await asyncio.wait_for(
                    _build_futures_bundle(client, spec, q),
                    timeout=20.0,
                )
            except (asyncio.TimeoutError, httpx.HTTPError) as exc:
                errors.append(f"{spec['symbol']}: {exc.__class__.__name__}")
                futures.append(
                    {
                        "id": spec["id"],
                        "symbol": spec["symbol"],
                        "label": spec["label"],
                        "short": spec["short"],
                        "price": (q or {}).get("price"),
                        "change": (q or {}).get("change"),
                        "change_pct": (q or {}).get("change_pct"),
                        "points": [],
                        "series": {},
                        "lite": True,
                        "url": f"https://finance.yahoo.com/quote/{urlquote(spec['symbol'], safe='')}",
                    }
                )
                return
            errors.extend(errs or [])
            if not bundle:
                futures.append(
                    {
                        "id": spec["id"],
                        "symbol": spec["symbol"],
                        "label": spec["label"],
                        "short": spec["short"],
                        "price": (q or {}).get("price"),
                        "change": (q or {}).get("change"),
                        "change_pct": (q or {}).get("change_pct"),
                        "points": [],
                        "series": {},
                        "lite": True,
                        "url": f"https://finance.yahoo.com/quote/{urlquote(spec['symbol'], safe='')}",
                    }
                )
                return
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
    }
    _CACHE["payload"] = payload
    _CACHE["fetched_at"] = now
    return dict(payload)
