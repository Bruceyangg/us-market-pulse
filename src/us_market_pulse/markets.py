"""US equity index quotes and multi-timeframe chart histories."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

_ET = ZoneInfo("America/New_York")

# Full extended session cycle labels (ET)
_SESSION_META: list[dict[str, str]] = [
    {"id": "night", "label": "夜盘"},
    {"id": "pre", "label": "盘前"},
    {"id": "regular", "label": "盘中"},
    {"id": "post", "label": "盘后"},
]
INDEX_SPECS: list[dict[str, str]] = [
    {
        "id": "spx",
        "symbol": "^GSPC",
        "label": "标普 500",
        "short": "S&P 500",
    },
    {
        "id": "dji",
        "symbol": "^DJI",
        "label": "道琼斯",
        "short": "Dow",
    },
    {
        "id": "ixic",
        "symbol": "^IXIC",
        "label": "纳斯达克",
        "short": "Nasdaq",
    },
    {
        "id": "vix",
        "symbol": "^VIX",
        "label": "VIX 恐慌指数",
        "short": "VIX",
    },
    {
        "id": "tnx",
        "symbol": "^TNX",
        "label": "10年期美债收益率",
        "short": "10Y",
        "unit": "%",
    },
]

# 分时 = intraday line; others = OHLC candlesticks (Chinese red-up / green-down)
TIMEFRAMES: list[dict[str, Any]] = [
    {
        "id": "intraday",
        "label": "分时",
        "blurb": "盘前·盘中·盘后·夜盘一体分时（约 5 分钟点，延迟报价）",
        "range": "5d",
        "interval": "5m",
        "max_points": 360,
        "chart": "line",
        "prepost": True,
        "session_window": True,
    },
    {
        "id": "day",
        "label": "日图",
        "blurb": "近 2 年日 K · MA5/10/30/60/120/250（红涨绿跌）",
        "range": "2y",
        "interval": "1d",
        # Keep enough bars for MA250 without downsampling the SMA window.
        "max_points": 560,
        "chart": "candle",
        "prepost": False,
    },
    {
        "id": "week",
        "label": "周图",
        "blurb": "近 5 年周 K · 均线叠加（红涨绿跌）",
        "range": "5y",
        "interval": "1wk",
        "max_points": 280,
        "chart": "candle",
        "prepost": False,
    },
    {
        "id": "month",
        "label": "月图",
        "blurb": "历史月 K · MA5/10/30/60/120/250（红涨绿跌）",
        "range": "max",
        "interval": "1mo",
        "max_points": 360,
        "chart": "candle",
        "prepost": False,
    },
    {
        "id": "year",
        "label": "年图",
        "blurb": "历史季 K · MA5/10/30/60/120/250（红涨绿跌）",
        "range": "max",
        "interval": "3mo",
        "max_points": 200,
        "chart": "candle",
        "prepost": False,
    },
]

CHART_INDEX_IDS = {"spx", "dji", "ixic", "vix", "tnx"}

# Holdings: 分时 / 日 / 月 / 季 / 年
PORTFOLIO_TIMEFRAMES: list[dict[str, Any]] = [
    {
        "id": "intraday",
        "label": "分时",
        "blurb": "盘前·盘中·盘后·夜盘一体分时（约 5 分钟点，延迟报价）",
        "range": "5d",
        "interval": "5m",
        "max_points": 360,
        "chart": "line",
        "prepost": True,
        "session_window": True,
    },
    {
        "id": "day",
        "label": "日图",
        "blurb": "近 2 年日 K · MA5/10/30/60/120/250（红涨绿跌）",
        "range": "2y",
        "interval": "1d",
        "max_points": 560,
        "chart": "candle",
        "prepost": False,
    },
    {
        "id": "month",
        "label": "月图",
        "blurb": "历史月 K · MA5/10/30/60/120/250（红涨绿跌）",
        "range": "max",
        "interval": "1mo",
        "max_points": 360,
        "chart": "candle",
        "prepost": False,
    },
    {
        "id": "quarter",
        "label": "季图",
        "blurb": "历史季 K · 均线叠加（红涨绿跌）",
        "range": "max",
        "interval": "3mo",
        "max_points": 200,
        "chart": "candle",
        "prepost": False,
    },
]


def _yahoo_chart_url(
    symbol: str,
    *,
    range_: str,
    interval: str,
    prepost: bool,
    period1: int | None = None,
    period2: int | None = None,
) -> str:
    enc = quote(symbol, safe="")
    flag = "true" if prepost else "false"
    base = f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}"
    if period1 is not None and period2 is not None and period2 > period1:
        return (
            f"{base}?period1={int(period1)}&period2={int(period2)}"
            f"&interval={interval}&includePrePost={flag}"
        )
    return f"{base}?range={range_}&interval={interval}&includePrePost={flag}"


def _et_minutes(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def _session_id_for_ts(ts: int) -> str:
    """Map unix ts → night / pre / regular / post (America/New_York)."""
    dt = datetime.fromtimestamp(int(ts), tz=_ET)
    mins = _et_minutes(dt)
    if mins >= 20 * 60 or mins < 4 * 60:
        return "night"
    if mins < 9 * 60 + 30:
        return "pre"
    if mins < 16 * 60:
        return "regular"
    return "post"


def _session_cycle_bounds(
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    """
    Current extended cycle: previous 20:00 ET → now (~24h).
    Always anchor at the prior 20:00 so after 20:00 ET we still keep the
    full day tape (盘前·盘中·盘后) plus the new 夜盘, instead of clipping
    to only the last hour.
    """
    now_et = now.astimezone(_ET) if now else datetime.now(tz=_ET)
    today_night = now_et.replace(hour=20, minute=0, second=0, microsecond=0)
    start = today_night - timedelta(days=1)
    return start, now_et


def _filter_session_window(
    points: list[dict[str, Any]],
    *,
    start_ts: int,
    end_ts: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in points:
        try:
            t = int(p.get("t") or 0)
        except (TypeError, ValueError):
            continue
        if t < start_ts or t > end_ts:
            continue
        row = dict(p)
        row["session"] = _session_id_for_ts(t)
        out.append(row)
    return out


def _session_segments(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build contiguous session bands for the frontend (index ranges)."""
    if not points:
        return []
    label_map = {s["id"]: s["label"] for s in _SESSION_META}
    segs: list[dict[str, Any]] = []
    cur = points[0].get("session") or "regular"
    start_i = 0
    for i, p in enumerate(points):
        sid = p.get("session") or "regular"
        if sid != cur:
            segs.append(
                {
                    "id": cur,
                    "label": label_map.get(cur, cur),
                    "i0": start_i,
                    "i1": i - 1,
                    "t0": points[start_i].get("t"),
                    "t1": points[i - 1].get("t"),
                }
            )
            cur = sid
            start_i = i
    segs.append(
        {
            "id": cur,
            "label": label_map.get(cur, cur),
            "i0": start_i,
            "i1": len(points) - 1,
            "t0": points[start_i].get("t"),
            "t1": points[-1].get("t"),
        }
    )
    return segs


def _nth(values: list[Any] | None, idx: int) -> float | None:
    if not values or idx >= len(values):
        return None
    value = values[idx]
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compact_bars(
    timestamps: list[int],
    opens: list[Any] | None,
    highs: list[Any] | None,
    lows: list[Any] | None,
    closes: list[Any] | None,
    volumes: list[Any] | None,
    *,
    max_points: int,
    chart: str,
) -> list[dict[str, Any]]:
    bars: list[dict[str, Any]] = []
    for i, ts in enumerate(timestamps):
        close = _nth(closes, i)
        if close is None:
            continue
        open_ = _nth(opens, i)
        high = _nth(highs, i)
        low = _nth(lows, i)
        vol = _nth(volumes, i)
        if open_ is None:
            open_ = close
        if high is None:
            high = max(open_, close)
        if low is None:
            low = min(open_, close)
        bar = {
            "t": int(ts),
            "o": round(open_, 6),
            "h": round(high, 6),
            "l": round(low, 6),
            "c": round(close, 6),
            "v": round(vol, 2) if vol is not None else None,
        }
        # line charts still expose v=close for sparklines
        bar["v"] = bar["c"] if chart == "line" else bar.get("v")
        if chart == "line":
            bars.append({"t": bar["t"], "v": bar["c"]})
        else:
            bars.append(bar)

    if len(bars) <= max_points:
        return bars
    step = max(1, len(bars) // max_points)
    trimmed = bars[::step]
    if trimmed[-1] is not bars[-1]:
        trimmed.append(bars[-1])
    return trimmed[:max_points]


def _series_change(points: list[dict[str, Any]], chart: str) -> tuple[float | None, float | None]:
    if len(points) < 2:
        return None, None
    if chart == "line":
        first = float(points[0]["v"])
        last = float(points[-1]["v"])
    else:
        first = float(points[0]["o"] if points[0].get("o") is not None else points[0]["c"])
        last = float(points[-1]["c"])
    if first == 0:
        return round(last - first, 4), None
    return round(last - first, 4), round((last - first) / first * 100.0, 3)


async def _fetch_yahoo_series(
    client: httpx.AsyncClient,
    spec: dict[str, str],
    tf: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    use_session = bool(tf.get("session_window") and tf.get("chart") == "line")
    # One Yahoo call only (range=5d + prepost). Clip to ET session cycle locally.
    # Do not also hit period1/period2 — double fetches trip Yahoo 429s.
    url = _yahoo_chart_url(
        spec["symbol"],
        range_=tf["range"],
        interval=tf["interval"],
        prepost=bool(tf.get("prepost")),
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/",
    }

    try:
        resp = await client.get(url, timeout=25.0, headers=headers)
        # Soft-fallback: session window prefers 5d, but Yahoo often 429s — retry 1d once.
        if resp.status_code == 429 and use_session and str(tf.get("range")) != "1d":
            resp = await client.get(
                _yahoo_chart_url(
                    spec["symbol"],
                    range_="1d",
                    interval=tf["interval"],
                    prepost=bool(tf.get("prepost")),
                ),
                timeout=25.0,
                headers=headers,
            )
        resp.raise_for_status()
        payload = resp.json()
        result = ((payload.get("chart") or {}).get("result") or [None])[0]
        if not result:
            return None, f"{spec['label']}/{tf['label']}: empty chart"

        meta = result.get("meta") or {}
        timestamps = result.get("timestamp") or []
        quote_block = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        chart = str(tf.get("chart") or "line")
        # For session-window intraday, compact after filtering so we keep density
        raw_cap = (
            max(int(tf.get("max_points") or 120) * 3, 800)
            if use_session
            else int(tf.get("max_points") or 120)
        )
        points = _compact_bars(
            timestamps,
            quote_block.get("open"),
            quote_block.get("high"),
            quote_block.get("low"),
            quote_block.get("close"),
            quote_block.get("volume"),
            max_points=raw_cap,
            chart=chart,
        )
        sessions: list[dict[str, Any]] = []
        if use_session and points:
            start_et, end_et = _session_cycle_bounds()
            points = _filter_session_window(
                points,
                start_ts=int(start_et.timestamp()),
                end_ts=int(end_et.timestamp()) + 300,
            )
            # Final density cap after window filter
            max_pts = int(tf.get("max_points") or 360)
            if len(points) > max_pts:
                step = max(1, len(points) // max_pts)
                trimmed = points[::step]
                if trimmed[-1] is not points[-1]:
                    trimmed.append(points[-1])
                points = trimmed[:max_pts]
                for p in points:
                    p["session"] = _session_id_for_ts(int(p["t"]))
            sessions = _session_segments(points)

        if not points:
            return None, f"{spec['label']}/{tf['label']}: no points"

        change, change_pct = _series_change(points, chart)
        price = meta.get("regularMarketPrice")
        if price is None:
            price = points[-1]["c"] if chart == "candle" else points[-1]["v"]
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        day_change = None
        day_change_pct = None
        if prev not in (None, 0):
            day_change = round(float(price) - float(prev), 4)
            day_change_pct = round((float(price) - float(prev)) / float(prev) * 100.0, 3)

        # For composite 分时, prefer vs prior close when available (matches list %)
        if use_session and day_change_pct is not None:
            change, change_pct = day_change, day_change_pct

        out: dict[str, Any] = {
            "tf": tf["id"],
            "label": tf["label"],
            "blurb": tf["blurb"],
            "range": tf["range"],
            "interval": tf["interval"],
            "chart": chart,
            "points": points,
            "change": change,
            "change_pct": change_pct,
            "price": round(float(price), 4 if spec.get("unit") == "%" else 2),
            "day_change": day_change,
            "day_change_pct": day_change_pct,
            "as_of": meta.get("regularMarketTime") or points[-1]["t"],
            "previous_close": round(float(prev), 6) if prev not in (None, 0) else None,
        }
        if use_session:
            for p in points:
                if "session" not in p and p.get("t"):
                    p["session"] = _session_id_for_ts(int(p["t"]))
            out["sessions"] = sessions or _session_segments(points)
            # Always advertise all four bands — empty bands still render on the desk.
            out["session_labels"] = [s["label"] for s in _SESSION_META]
        return out, None
    except Exception as exc:  # noqa: BLE001
        return None, f"{spec['label']}/{tf['label']}: {exc}"


def _aggregate_yearly_candles(month_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build yearly OHLC bars from monthly candles."""
    buckets: dict[int, list[dict[str, Any]]] = {}
    for bar in month_points:
        if bar.get("c") is None or not bar.get("t"):
            continue
        year = datetime.fromtimestamp(int(bar["t"]), tz=timezone.utc).year
        buckets.setdefault(year, []).append(bar)
    yearly: list[dict[str, Any]] = []
    for year in sorted(buckets):
        rows = buckets[year]
        o = float(rows[0]["o"])
        c = float(rows[-1]["c"])
        h = max(float(r["h"]) for r in rows)
        l = min(float(r["l"]) for r in rows)
        vol = sum(float(r["v"] or 0) for r in rows) or None
        yearly.append(
            {
                "t": int(rows[0]["t"]),
                "o": round(o, 6),
                "h": round(h, 6),
                "l": round(l, 6),
                "c": round(c, 6),
                "v": round(vol, 2) if vol is not None else None,
            }
        )
    return yearly


async def fetch_symbol_bundle(
    client: httpx.AsyncClient,
    *,
    symbol: str,
    label: str | None = None,
    short: str | None = None,
    unit: str = "",
    timeframes: list[dict[str, Any]] | None = None,
    include_yearly: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Fetch multi-timeframe board row for any Yahoo symbol."""
    sym = (symbol or "").strip().upper()
    if not sym:
        return None, ["empty symbol"]
    spec = {
        "id": sym.lower().replace("^", "").replace(".", "-"),
        "symbol": sym,
        "label": (label or sym).strip() or sym,
        "short": (short or sym).strip() or sym,
        "unit": unit,
    }
    frames = list(timeframes or TIMEFRAMES)
    errors: list[str] = []
    results = await asyncio.gather(
        *[_fetch_yahoo_series(client, spec, tf) for tf in frames]
    )

    series: dict[str, Any] = {}
    quote_seed: dict[str, Any] | None = None
    for (row, err), tf in zip(results, frames, strict=True):
        if err:
            errors.append(err)
        if not row:
            continue
        series_row: dict[str, Any] = {
            "tf": row["tf"],
            "label": row["label"],
            "blurb": row["blurb"],
            "range": row["range"],
            "interval": row["interval"],
            "chart": row["chart"],
            "points": row["points"],
            "change": row["change"],
            "change_pct": row["change_pct"],
        }
        if row.get("sessions"):
            series_row["sessions"] = row["sessions"]
        if row.get("session_labels"):
            series_row["session_labels"] = row["session_labels"]
        if row.get("previous_close") is not None:
            series_row["previous_close"] = row["previous_close"]
        series[tf["id"]] = series_row
        if quote_seed is None or tf["id"] == "intraday":
            quote_seed = row

    if include_yearly and series.get("month", {}).get("points"):
        year_points = _aggregate_yearly_candles(series["month"]["points"])
        if year_points:
            change, change_pct = _series_change(year_points, "candle")
            series["year"] = {
                "tf": "year",
                "label": "年图",
                "blurb": "按年聚合 K 线 · MA5/10/30/60/120/250（红涨绿跌）",
                "range": "max",
                "interval": "1y",
                "chart": "candle",
                "points": year_points,
                "change": change,
                "change_pct": change_pct,
            }

    if not series or quote_seed is None:
        return None, errors or [f"{spec['label']}: no series"]

    spark_src = series.get("intraday") or series.get("day") or next(iter(series.values()))
    spark_points = spark_src.get("points") or []
    if spark_src.get("chart") == "candle":
        spark_points = [{"t": p["t"], "v": p["c"]} for p in spark_points]

    return {
        "id": spec["id"],
        "symbol": spec["symbol"],
        "label": spec["label"],
        "short": spec["short"],
        "unit": spec.get("unit") or "",
        "price": quote_seed["price"],
        "change": quote_seed.get("day_change"),
        "change_pct": quote_seed.get("day_change_pct"),
        "as_of": quote_seed.get("as_of"),
        "points": spark_points[-64:],
        "series": series,
        "url": f"https://finance.yahoo.com/quote/{quote(spec['symbol'], safe='')}",
    }, errors


async def _fetch_index_bundle(
    client: httpx.AsyncClient, spec: dict[str, str]
) -> tuple[dict[str, Any] | None, list[str]]:
    return await fetch_symbol_bundle(
        client,
        symbol=spec["symbol"],
        label=spec.get("label"),
        short=spec.get("short"),
        unit=spec.get("unit") or "",
        timeframes=TIMEFRAMES,
        include_yearly=False,
    )


async def fetch_market_board(client: httpx.AsyncClient) -> tuple[dict[str, Any], list[str]]:
    """Fetch index board + multi-timeframe chart series."""
    bundles = await asyncio.gather(*[_fetch_index_bundle(client, spec) for spec in INDEX_SPECS])
    errors: list[str] = []
    indices: list[dict[str, Any]] = []
    for row, errs in bundles:
        errors.extend(errs)
        if row:
            indices.append(row)

    charts_by_tf: dict[str, list[dict[str, Any]]] = {tf["id"]: [] for tf in TIMEFRAMES}
    for row in indices:
        if row["id"] not in CHART_INDEX_IDS:
            continue
        for tf in TIMEFRAMES:
            series = (row.get("series") or {}).get(tf["id"])
            if not series:
                continue
            charts_by_tf[tf["id"]].append(
                {
                    "id": row["id"],
                    "label": row["label"],
                    "short": row["short"],
                    "unit": row.get("unit") or "",
                    "price": row.get("price"),
                    "change_pct": series.get("change_pct"),
                    "points": series.get("points") or [],
                    "chart": series.get("chart") or tf.get("chart") or "line",
                    "blurb": series.get("blurb") or tf["blurb"],
                }
            )

    return {
        "indices": indices,
        "timeframes": [
            {
                "id": tf["id"],
                "label": tf["label"],
                "blurb": tf["blurb"],
                "chart": tf["chart"],
            }
            for tf in TIMEFRAMES
        ],
        "default_tf": "intraday",
        "charts_by_tf": charts_by_tf,
        "charts": charts_by_tf.get("intraday") or charts_by_tf.get("day") or [],
        "source": "Yahoo Finance",
        "style": {"up": "red", "down": "green", "note": "A股习惯：红涨绿跌"},
    }, errors
