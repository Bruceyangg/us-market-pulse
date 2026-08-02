"""US equity index quotes and sparkline histories (Yahoo chart API)."""

from __future__ import annotations

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

CHART_RANGE = "3mo"
CHART_INTERVAL = "1d"


def _yahoo_chart_url(symbol: str) -> str:
    enc = quote(symbol, safe="")
    return (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}"
        f"?range={CHART_RANGE}&interval={CHART_INTERVAL}&includePrePost=false"
    )


def _compact_points(closes: list[float | None], timestamps: list[int], *, max_points: int = 48) -> list[dict[str, Any]]:
    pairs = [
        {"t": ts, "v": float(close)}
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


async def _fetch_yahoo_chart(
    client: httpx.AsyncClient, spec: dict[str, str]
) -> tuple[dict[str, Any] | None, str | None]:
    url = _yahoo_chart_url(spec["symbol"])
    try:
        resp = await client.get(
            url,
            timeout=20.0,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; PulseDesk/1.0)",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        result = ((payload.get("chart") or {}).get("result") or [None])[0]
        if not result:
            return None, f"{spec['label']}: empty chart"

        meta = result.get("meta") or {}
        timestamps = result.get("timestamp") or []
        quote_block = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = quote_block.get("close") or []

        price = meta.get("regularMarketPrice")
        if price is None and closes:
            for value in reversed(closes):
                if value is not None:
                    price = float(value)
                    break
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        if prev is None and len(closes) >= 2:
            for value in reversed(closes[:-1]):
                if value is not None:
                    prev = float(value)
                    break

        if price is None:
            return None, f"{spec['label']}: no price"

        price_f = float(price)
        prev_f = float(prev) if prev is not None else None
        change = None if prev_f is None else round(price_f - prev_f, 4)
        change_pct = (
            None
            if prev_f in (None, 0)
            else round((price_f - prev_f) / prev_f * 100.0, 3)
        )

        points = _compact_points(closes, timestamps)
        return {
            "id": spec["id"],
            "symbol": spec["symbol"],
            "label": spec["label"],
            "short": spec["short"],
            "unit": spec.get("unit") or "",
            "price": round(price_f, 4 if spec.get("unit") == "%" else 2),
            "prev_close": round(prev_f, 4) if prev_f is not None else None,
            "change": change,
            "change_pct": change_pct,
            "currency": meta.get("currency") or "USD",
            "as_of": meta.get("regularMarketTime") or (timestamps[-1] if timestamps else None),
            "range": CHART_RANGE,
            "points": points,
            "url": f"https://finance.yahoo.com/quote/{quote(spec['symbol'], safe='')}",
        }, None
    except Exception as exc:  # noqa: BLE001
        return None, f"{spec['label']}: {exc}"


async def fetch_market_board(client: httpx.AsyncClient) -> tuple[dict[str, Any], list[str]]:
    """Fetch index board + 3M sparkline points."""
    errors: list[str] = []
    indices: list[dict[str, Any]] = []
    for spec in INDEX_SPECS:
        row, err = await _fetch_yahoo_chart(client, spec)
        if row:
            indices.append(row)
        if err:
            errors.append(err)

    charts = [
        {
            "id": row["id"],
            "label": row["label"],
            "short": row["short"],
            "unit": row.get("unit") or "",
            "change_pct": row.get("change_pct"),
            "points": row.get("points") or [],
        }
        for row in indices
        if row.get("id") in {"spx", "dji", "ixic", "vix"}
    ]

    return {"indices": indices, "charts": charts, "source": "Yahoo Finance"}, errors
