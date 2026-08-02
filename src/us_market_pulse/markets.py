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

# UI timeframes: 24h / daily / weekly / monthly / yearly
TIMEFRAMES: list[dict[str, str]] = [
    {
        "id": "h24",
        "label": "24小时",
        "blurb": "近 24 小时分时（约 5 分钟点）",
        "range": "1d",
        "interval": "5m",
        "max_points": 120,
    },
    {
        "id": "day",
        "label": "日图",
        "blurb": "近 1 年日线",
        "range": "1y",
        "interval": "1d",
        "max_points": 160,
    },
    {
        "id": "week",
        "label": "周图",
        "blurb": "近 5 年周线",
        "range": "5y",
        "interval": "1wk",
        "max_points": 160,
    },
    {
        "id": "month",
        "label": "月图",
        "blurb": "历史月线",
        "range": "max",
        "interval": "1mo",
        "max_points": 180,
    },
    {
        "id": "year",
        "label": "年图",
        "blurb": "历史季线（年景）",
        "range": "max",
        "interval": "3mo",
        "max_points": 120,
    },
]

CHART_INDEX_IDS = {"spx", "dji", "ixic", "vix", "tnx"}


def _yahoo_chart_url(symbol: str, *, range_: str, interval: str) -> str:
    enc = quote(symbol, safe="")
    return (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}"
        f"?range={range_}&interval={interval}&includePrePost=false"
    )


def _compact_points(
    closes: list[float | None],
    timestamps: list[int],
    *,
    max_points: int = 120,
) -> list[dict[str, Any]]:
    pairs = [
        {"t": int(ts), "v": float(close)}
        for ts, close in zip(timestamps, closes, strict=False)
        if close is not None
    ]
    if len(pairs) <= max_points:
        return pairs
    step = max(1, len(pairs) // max_points)
    trimmed = pairs[::step]
    if trimmed[-1] is not pairs[-1]:
        trimmed.append(pairs[-1])
    return trimmed[:max_points]


def _series_change(points: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    if len(points) < 2:
        return None, None
    first = float(points[0]["v"])
    last = float(points[-1]["v"])
    if first == 0:
        return round(last - first, 4), None
    return round(last - first, 4), round((last - first) / first * 100.0, 3)


async def _fetch_yahoo_series(
    client: httpx.AsyncClient,
    spec: dict[str, str],
    tf: dict[str, str],
) -> tuple[dict[str, Any] | None, str | None]:
    url = _yahoo_chart_url(spec["symbol"], range_=tf["range"], interval=tf["interval"])
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
        closes = quote_block.get("close") or []
        max_points = int(tf.get("max_points") or 120)
        points = _compact_points(closes, timestamps, max_points=max_points)
        if not points:
            return None, f"{spec['label']}/{tf['label']}: no points"

        change, change_pct = _series_change(points)
        price = meta.get("regularMarketPrice")
        if price is None:
            price = points[-1]["v"]
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
    tasks = [_fetch_yahoo_series(client, spec, tf) for tf in TIMEFRAMES]
    results = await asyncio.gather(*tasks)

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
            "points": row["points"],
            "change": row["change"],
            "change_pct": row["change_pct"],
        }
        if quote_seed is None:
            quote_seed = row

    if not series or quote_seed is None:
        return None, errors or [f"{spec['label']}: no series"]

    # Prefer 24h / day for quote fields
    preferred = series.get("h24") or series.get("day") or next(iter(series.values()))
    day_series = series.get("day") or preferred

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
        "points": (day_series.get("points") or [])[-48:],
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
                    "blurb": series.get("blurb") or tf["blurb"],
                }
            )

    return {
        "indices": indices,
        "timeframes": [
            {"id": tf["id"], "label": tf["label"], "blurb": tf["blurb"]} for tf in TIMEFRAMES
        ],
        "default_tf": "h24",
        "charts_by_tf": charts_by_tf,
        # back-compat for older UI
        "charts": charts_by_tf.get("h24") or charts_by_tf.get("day") or [],
        "source": "Yahoo Finance",
    }, errors
