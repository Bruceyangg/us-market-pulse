"""US equity index quotes and multi-timeframe chart histories."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

import httpx

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
        "blurb": "当日分时（含盘前盘后，约 5 分钟点，延迟报价）",
        "range": "1d",
        "interval": "5m",
        "max_points": 160,
        "chart": "line",
        "prepost": True,
    },
    {
        "id": "day",
        "label": "日图",
        "blurb": "近 1 年日 K 线（红涨绿跌）",
        "range": "1y",
        "interval": "1d",
        "max_points": 160,
        "chart": "candle",
        "prepost": False,
    },
    {
        "id": "week",
        "label": "周图",
        "blurb": "近 5 年周 K 线（红涨绿跌）",
        "range": "5y",
        "interval": "1wk",
        "max_points": 160,
        "chart": "candle",
        "prepost": False,
    },
    {
        "id": "month",
        "label": "月图",
        "blurb": "历史月 K 线（红涨绿跌）",
        "range": "max",
        "interval": "1mo",
        "max_points": 180,
        "chart": "candle",
        "prepost": False,
    },
    {
        "id": "year",
        "label": "年图",
        "blurb": "历史季 K 线 / 年景（红涨绿跌）",
        "range": "max",
        "interval": "3mo",
        "max_points": 120,
        "chart": "candle",
        "prepost": False,
    },
]

CHART_INDEX_IDS = {"spx", "dji", "ixic", "vix", "tnx"}


def _yahoo_chart_url(
    symbol: str, *, range_: str, interval: str, prepost: bool
) -> str:
    enc = quote(symbol, safe="")
    flag = "true" if prepost else "false"
    return (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}"
        f"?range={range_}&interval={interval}&includePrePost={flag}"
    )


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
    url = _yahoo_chart_url(
        spec["symbol"],
        range_=tf["range"],
        interval=tf["interval"],
        prepost=bool(tf.get("prepost")),
    )
    try:
        resp = await client.get(
            url,
            timeout=25.0,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; PulseDesk/1.0)",
                "Accept": "application/json",
            },
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
        points = _compact_bars(
            timestamps,
            quote_block.get("open"),
            quote_block.get("high"),
            quote_block.get("low"),
            quote_block.get("close"),
            quote_block.get("volume"),
            max_points=int(tf.get("max_points") or 120),
            chart=chart,
        )
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

        return {
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
        }, None
    except Exception as exc:  # noqa: BLE001
        return None, f"{spec['label']}/{tf['label']}: {exc}"


async def _fetch_index_bundle(
    client: httpx.AsyncClient, spec: dict[str, str]
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    results = await asyncio.gather(
        *[_fetch_yahoo_series(client, spec, tf) for tf in TIMEFRAMES]
    )

    series: dict[str, Any] = {}
    quote_seed: dict[str, Any] | None = None
    for (row, err), tf in zip(results, TIMEFRAMES, strict=True):
        if err:
            errors.append(err)
        if not row:
            continue
        series[tf["id"]] = {
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
        if quote_seed is None or tf["id"] == "intraday":
            quote_seed = row

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
